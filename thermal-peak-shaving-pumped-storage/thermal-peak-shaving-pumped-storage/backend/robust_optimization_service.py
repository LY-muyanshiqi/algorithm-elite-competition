"""Background service for scenario-robust NSLDE experiments."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
import sys
import time
import uuid

import numpy as np
from scipy.spatial.distance import cdist


ROOT = Path(__file__).resolve().parents[1]
CALC_DIR = ROOT / "全年抽蓄减碳效益优化计算"
PYTHON_ENV = CALC_DIR / "python_env"
RESULTS_DIR = CALC_DIR / "experiment_results"
LATEST_RESULT_PATH = RESULTS_DIR / "robust_latest.json"
for path in (str(CALC_DIR), str(PYTHON_ENV)):
    if path not in sys.path:
        sys.path.insert(0, path)

from data_loader_py import load_all_days
from evaluate_objective import evaluate_objective_np
from nslde_env import NSLDEEnv
from operators import compute_hv_2d, non_domination_sort
from robust_scenarios import (ExperienceArchive, RobustScenarioEvaluator,
                              extract_representative_scenarios)


PROVINCES = {
    "shaanxi": ("陕西", "", 1400.0),
    "gansu": ("甘肃", "gansu_", 1400.0),
    "qinghai": ("青海", "qinghai_", 800.0),
    "ningxia": ("宁夏", "ningxia_", 600.0),
}


# Used only when no feasible calibration policy can be evaluated.  Under the
# normal path the HV reference is estimated from feasible robust objectives;
# infeasible penalty values must not set the scale of the comparison.
_HV_FALLBACK_REFERENCE = np.array([1e6, 1e12], dtype=float)


def _common_hv_reference(evaluator, seed=42):
    """Estimate a feasible-objective reference shared by all variants.

    Infeasible schedules receive large optimization penalties, but those
    penalties must not determine the HV scale.  Sample smooth schedules around
    the neutral reservoir level and use only feasible robust objectives; the
    fallback is used only when the evaluator cannot produce any feasible
    sample.
    """
    candidates = [np.full(23, 0.5, dtype=float)]
    grid = np.linspace(0.0, 2.0 * np.pi, 23)
    for amplitude in (0.03, 0.06, 0.1, 0.15):
        for phase in (0.0, 0.7, 1.4):
            candidate = 0.5 + amplitude * np.sin(grid + phase)
            candidate[-2:] = 0.5
            candidates.append(np.clip(candidate, 0.0, 1.0))
    rng = np.random.default_rng(seed)
    for _ in range(32):
        candidate = 0.5 + rng.normal(0.0, 0.04, 23)
        candidate[-2:] = 0.5
        candidates.append(np.clip(candidate, 0.0, 1.0))
    values = []
    for candidate in candidates:
        result = evaluator.evaluate(candidate)
        if result['feasible'] and np.all(np.isfinite(result['objective'])):
            values.append(result['objective'])
    if not values:
        return _HV_FALLBACK_REFERENCE.copy()
    upper = np.max(np.asarray(values, dtype=float), axis=0)
    return np.maximum(upper * 1.2, np.array([1.0, 1.0]))


def _load_province(province):
    name, prefix, capacity = PROVINCES[province]
    if not prefix:
        return name, capacity, load_all_days(str(CALC_DIR))
    files = [f"{prefix}hydro.txt", f"{prefix}wind.txt",
             f"{prefix}solar.txt", f"{prefix}fh.txt"]
    return name, capacity, tuple(np.loadtxt(CALC_DIR / file) for file in files)


def _pareto(population):
    rank_col = population.shape[1] - 2
    front = population[population[:, rank_col] == 1, :rank_col]
    return front if len(front) else population[:, :rank_col]


def _nondominated_points(points):
    """Return the unique non-dominated subset of a 2-D minimization set."""
    points = np.asarray(points, dtype=float)
    if points.size == 0:
        return np.empty((0, 2), dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError('points must have shape (n, 2)')
    points = points[np.all(np.isfinite(points), axis=1)]
    if len(points) == 0:
        return np.empty((0, 2), dtype=float)
    order = np.lexsort((points[:, 1], points[:, 0]))
    ordered = points[order]
    kept = []
    best_y = np.inf
    for point in ordered:
        if point[1] < best_y:
            kept.append(point)
            best_y = point[1]
    return np.asarray(kept, dtype=float)


def _reevaluate_front(front, evaluator, V=23, M=2):
    """Re-score a training front with the common test evaluator."""
    if len(front) == 0:
        return np.empty((0, V + M), dtype=float)
    decisions = front[:, :V]
    valid_decisions = []
    scored = []
    for decision in decisions:
        if hasattr(evaluator, 'evaluate'):
            evaluation = evaluator.evaluate(decision)
            if not evaluation.get('feasible', True):
                continue
            scored.append(evaluation['objective'])
        else:
            scored.append(evaluator(decision))
        valid_decisions.append(decision)
    if not scored:
        return np.empty((0, V + M), dtype=float)
    valid_decisions = np.asarray(valid_decisions, dtype=float)
    objectives = np.asarray(scored, dtype=float)
    if objectives.ndim != 2 or objectives.shape[1] != M:
        raise ValueError('evaluator must return exactly M objective values')
    finite = np.all(np.isfinite(objectives), axis=1)
    if not np.any(finite):
        return np.empty((0, V + M))
    scored_matrix = np.hstack([valid_decisions[finite], objectives[finite]])
    ranked = non_domination_sort(scored_matrix, M, V)
    return ranked[ranked[:, V + M] == 1, :V + M]


def _spacing(points):
    points = np.asarray(points, dtype=float)
    if points.size == 0:
        return 0.0
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError('points must have shape (n, 2)')
    points = points[np.all(np.isfinite(points), axis=1)]
    if len(points) < 3:
        return 0.0
    normalized = (points - points.min(0)) / (np.ptp(points, axis=0) + 1e-12)
    distances = cdist(normalized, normalized)
    np.fill_diagonal(distances, np.inf)
    return float(np.std(distances.min(1), ddof=1))


class RobustOptimizationService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="robust-nslde")
        self._tasks = {}
        self._latest = None
        self._latest_snapshot = self._read_latest_snapshot()
        self._lock = Lock()

    def start(self, params):
        task_id = uuid.uuid4().hex
        task = {
            "task_id": task_id, "status": "queued", "progress": 0,
            "stage": "等待计算资源", "params": params,
            "created_at": datetime.now(timezone.utc).isoformat(), "result": None,
            "error": None,
        }
        with self._lock:
            self._tasks[task_id] = task
        self._executor.submit(self._run, task_id, params)
        return self.get(task_id)

    def get(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            return None if task is None else dict(task)

    def latest(self):
        with self._lock:
            memory_task = (
                dict(self._tasks[self._latest])
                if self._latest and self._latest in self._tasks else None
            )
            disk_task = (dict(self._latest_snapshot)
                         if self._latest_snapshot is not None else None)
            if memory_task is None:
                return disk_task
            if disk_task is None:
                return memory_task
            # A reload can leave an older completed task in memory while a
            # newer completed snapshot is already on disk.  Compare the
            # creation timestamps so stale memory cannot mask the real latest
            # result.  Keep memory as the tie-breaker when persistence failed.
            memory_created = str(memory_task.get("created_at") or "")
            disk_created = str(disk_task.get("created_at") or "")
            return disk_task if disk_created > memory_created else memory_task

    @staticmethod
    def _read_latest_snapshot():
        """Load the last completed real run after a process restart.

        The file is only a cache of a completed task response.  Invalid or
        partial files are ignored so a failed write can never prevent the API
        from starting.
        """
        try:
            if not LATEST_RESULT_PATH.exists():
                return None
            payload = json.loads(LATEST_RESULT_PATH.read_text(encoding="utf-8"))
            if (not isinstance(payload, dict) or payload.get("status") != "completed"
                    or not isinstance(payload.get("result"), dict)):
                return None
            return payload
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            return None

    def _persist_latest(self, task_id):
        """Atomically persist a completed task without blocking task updates."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            snapshot = dict(task)
            self._latest_snapshot = snapshot
        temporary = LATEST_RESULT_PATH.with_name(
            f".{LATEST_RESULT_PATH.name}.{task_id}.tmp")
        try:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(snapshot, ensure_ascii=False, allow_nan=False),
                encoding="utf-8",
            )
            temporary.replace(LATEST_RESULT_PATH)
        except (OSError, TypeError, ValueError) as exc:
            # The in-memory result remains available when a deployment is
            # read-only; persistence is a resilience feature, not a reason to
            # mark a successful optimization as failed.
            print(f"[Robust] 最近结果持久化失败: {exc}")
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _update(self, task_id, **values):
        with self._lock:
            self._tasks[task_id].update(values)

    def _run_variant(self, data, capacity, evaluator, initial, params, seed,
                     task_id, start_progress, end_progress, label,
                     use_rlde=False, ref_point=None, history_evaluator=None):
        env = NSLDEEnv(*[item[0] for item in data], Zpump=capacity,
                       pop=params["population"], gen=params["generations"],
                       seed=seed, evaluator=evaluator, initial_solutions=initial,
                       op_probs=np.array([0.4, 0, 0, 0, 0, 0.3, 0.3]),
                       use_rlde=use_rlde, rlde_options={
                           "alpha": params.get("rl_alpha", 0.1),
                           "gamma": params.get("rl_gamma", 0.9),
                           "f_delta": params.get("f_delta", 0.1),
                           "temperature": params.get("rl_temperature", 1.0),
                       }, ref_point=ref_point)
        env.reset()
        infos = []
        history = [float(value) for value in env.hv_history]
        if history_evaluator is not None:
            history = [self._history_hv(env.pop_sorted, history_evaluator, ref_point)]
        for generation in range(params["generations"]):
            _, _, _, info = env.step(return_info=True)
            infos.append(info)
            if history_evaluator is None:
                history.append(float(env.hv_history[-1]))
            else:
                history.append(self._history_hv(
                    env.pop_sorted, history_evaluator, ref_point))
            progress = start_progress + (end_progress - start_progress) * (
                generation + 1) / params["generations"]
            self._update(task_id, progress=round(progress),
                         stage=f"{label}：第 {generation + 1}/{params['generations']} 代")
        return _pareto(env.pop_sorted), history, env, infos

    @staticmethod
    def _history_hv(population, evaluator, ref_point):
        """Evaluate one population on the common test objective for history."""
        points = []
        for row in population:
            evaluation = evaluator.evaluate(row[:23])
            objective = np.asarray(evaluation.get('objective'), dtype=float)
            if evaluation.get('feasible', True) and objective.shape == (2,):
                if np.all(np.isfinite(objective)):
                    points.append(objective)
        if not points:
            return 0.0
        return float(compute_hv_2d(np.asarray(points, dtype=float), ref_point))

    def _run(self, task_id, params):
        started = time.perf_counter()
        try:
            self._update(task_id, status="running", progress=2, stage="加载年度数据")
            province_name, capacity, data = _load_province(params["province"])
            clusters = max(1, params["scenario_count"] - params["extreme_count"])
            scenarios = extract_representative_scenarios(
                *data, n_clusters=clusters, n_extremes=params["extreme_count"],
                seed=params["seed"])
            robust = RobustScenarioEvaluator(
                *data, scenarios, Zpump=capacity, beta=params["beta"], alpha=params["alpha"])
            expected = RobustScenarioEvaluator(
                *data, scenarios, Zpump=capacity, beta=0.0, alpha=params["alpha"])
            common_ref = _common_hv_reference(robust, seed=params["seed"])
            representative_day = int(scenarios.indices[0])

            variants = []
            # Use common random numbers so each algorithm starts from the same
            # population; the RLDE controller has its own independent RNG.
            comparison_seed = params["seed"]
            baseline, baseline_hv, baseline_env, baseline_infos = self._run_variant(
                data, capacity, expected, None, params, comparison_seed, task_id,
                5, 25, "原始 NSLDE", ref_point=common_ref,
                history_evaluator=robust)
            variants.append(("baseline", "原始 NSLDE", baseline, baseline_hv,
                             baseline_env, baseline_infos, False))

            robust_front, robust_hv, robust_env, robust_infos = self._run_variant(
                data, capacity, robust, None, params, comparison_seed, task_id,
                25, 48, "场景鲁棒 NSLDE", ref_point=common_ref)
            variants.append(("robust", "场景鲁棒", robust_front, robust_hv,
                             robust_env, robust_infos, False))

            archive = ExperienceArchive()
            archive.add(scenarios.features[representative_day], baseline[:, :23])
            warm = archive.warm_start(scenarios.features[representative_day],
                                      max(2, params["population"] // 3),
                                      np.random.default_rng(comparison_seed + 1),
                                      lower=np.array([0.0] * 21 + [0.125, 0.3125]),
                                      upper=np.array([1.0] * 21 + [1.0, 0.75]))
            rlde_front, rlde_hv, rlde_env, rlde_infos = self._run_variant(
                data, capacity, robust, None, params, comparison_seed, task_id,
                48, 71, "RLDE-F 场景鲁棒", use_rlde=True, ref_point=common_ref)
            variants.append(("rlde", "RLDE-F 场景鲁棒", rlde_front, rlde_hv,
                             rlde_env, rlde_infos, True))

            robust_warm, robust_warm_hv, robust_warm_env, robust_warm_infos = self._run_variant(
                data, capacity, robust, warm, params, comparison_seed, task_id,
                71, 94, "RLDE-F + 同次运行热启动", use_rlde=True, ref_point=common_ref)
            variants.append(("rlde_warm", "RLDE-F + 同次运行热启动", robust_warm, robust_warm_hv,
                             robust_warm_env, robust_warm_infos, True))

            # All variants are compared on the same robust test objective.
            evaluated = []
            for key, label, front, history, env, infos, is_rlde in variants:
                evaluated.append((key, label, _reevaluate_front(front, robust),
                                  history, env, infos, is_rlde))
            point_sets = [item[2][:, 23:25] for item in evaluated if len(item[2])]
            all_points = np.vstack(point_sets) if point_sets else np.empty((0, 2))
            reference_points = _nondominated_points(all_points)
            # Match the reference used by each environment's history.  A late
            # outlier must not silently change the scale of only the final HV.
            ref = common_ref
            results = []
            for key, label, front, history, env, infos, is_rlde in evaluated:
                if len(front) == 0:
                    continue
                points = front[:, 23:25]
                union_min = all_points.min(0)
                union_span = np.ptp(all_points, axis=0) + 1e-12
                normalized = (points - union_min) / union_span
                reference_normalized = (reference_points - union_min) / union_span
                igd = float(cdist(reference_normalized, normalized).min(1).mean())
                best_idx = int(np.argmin(normalized.sum(1)))
                best_solution = front[best_idx, :23]
                evaluation = robust.evaluate(best_solution)
                quality = self._quality_summary(best_solution, data, scenarios, capacity)
                rl_summary = None if not is_rlde else env.rlde.summary()
                results.append({
                    "key": key, "label": label, "pareto": np.round(points, 3).tolist(),
                    "hv": float(compute_hv_2d(points, ref)), "igd": igd,
                    "spacing": _spacing(points), "f1_best": float(points[:, 0].min()),
                    "f2_best": float(points[:, 1].min()), "solutions": len(points),
                    "convergence": [[i, float(value)] for i, value in enumerate(history)],
                    "expected_objectives": np.round(evaluation['expected'], 6).tolist(),
                    "cvar_objectives": np.round(evaluation['cvar'], 6).tolist(),
                    "worst_objectives": np.round(evaluation['worst'], 6).tolist(),
                    "nfe": int(env.nfe),
                    "operator_use": env.operator_use_count.astype(int).tolist(),
                    "rl": rl_summary,
                    "dispatch_quality": {
                        key: float(value) if isinstance(value, (float, np.floating)) else int(value)
                        for key, value in quality.items()
                    },
                })

            result = {
                "province": params["province"], "province_name": province_name,
                "capacity_mw": capacity, "scenario_days": (scenarios.indices + 1).tolist(),
                "scenario_labels": scenarios.labels,
                "algorithm_version": "NSLDE + scenario CVaR + RLDE-F",
                "objective_definition": "common robust test objective: E[f] + beta * CVaR_alpha(f)",
                "risk": {"beta": params["beta"], "alpha": params["alpha"]},
                "hv_reference_point": np.round(common_ref, 6).tolist(),
                "scenario_weights": np.round(scenarios.weights, 6).tolist(),
                "variants": results, "runtime_seconds": round(time.perf_counter() - started, 3),
            }
            self._update(task_id, status="completed", progress=100, stage="计算完成", result=result)
            with self._lock:
                self._latest = task_id
            self._persist_latest(task_id)
        except Exception as exc:
            self._update(task_id, status="failed", stage="计算失败", error=str(exc))

    @staticmethod
    def _quality_summary(solution, data, scenarios, capacity):
        values = []
        for day in scenarios.indices:
            _, _, details = evaluate_objective_np(
                solution, *(item[day] for item in data), capacity, 4.0,
                return_details=True)
            values.append([details[name] for name in
                           ('ramp_mw', 'starts', 'mode_switches', 'short_runs')])
        values = np.asarray(values, dtype=float)
        return dict(zip(('ramp_mw', 'starts', 'mode_switches', 'short_runs'),
                        np.average(values, axis=0, weights=scenarios.weights)))


robust_optimization_service = RobustOptimizationService()
