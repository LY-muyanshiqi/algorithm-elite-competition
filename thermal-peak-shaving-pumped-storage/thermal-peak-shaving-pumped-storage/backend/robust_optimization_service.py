"""Background service for scenario-robust NSLDE experiments."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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
for path in (str(CALC_DIR), str(PYTHON_ENV)):
    if path not in sys.path:
        sys.path.insert(0, path)

from data_loader_py import load_all_days
from evaluate_objective import evaluate_objective_np
from nslde_env import NSLDEEnv
from operators import compute_hv_2d
from robust_scenarios import (ExperienceArchive, RobustScenarioEvaluator,
                              extract_representative_scenarios)


PROVINCES = {
    "shaanxi": ("陕西", "", 1400.0),
    "gansu": ("甘肃", "gansu_", 1400.0),
    "qinghai": ("青海", "qinghai_", 800.0),
    "ningxia": ("宁夏", "ningxia_", 600.0),
}


def _load_province(province):
    name, prefix, capacity = PROVINCES[province]
    if not prefix:
        return name, capacity, load_all_days(str(CALC_DIR))
    files = [f"{prefix}hydro.txt", f"{prefix}wind.txt",
             f"{prefix}solar.txt", f"{prefix}fh.txt"]
    return name, capacity, tuple(np.loadtxt(CALC_DIR / file) for file in files)


def _pareto(population):
    front = population[population[:, 25] == 1, :25]
    return front if len(front) else population[:, :25]


def _spacing(points):
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
        return self.get(self._latest) if self._latest else None

    def _update(self, task_id, **values):
        with self._lock:
            self._tasks[task_id].update(values)

    def _run_variant(self, data, capacity, evaluator, initial, params, seed,
                     task_id, start_progress, end_progress, label):
        env = NSLDEEnv(*[item[0] for item in data], Zpump=capacity,
                       pop=params["population"], gen=params["generations"],
                       seed=seed, evaluator=evaluator, initial_solutions=initial,
                       op_probs=np.array([0.4, 0, 0, 0, 0, 0.3, 0.3]))
        env.reset()
        for generation in range(params["generations"]):
            env.step(0)
            progress = start_progress + (end_progress - start_progress) * (
                generation + 1) / params["generations"]
            self._update(task_id, progress=round(progress),
                         stage=f"{label}：第 {generation + 1}/{params['generations']} 代")
        return _pareto(env.pop_sorted), env.hv_history

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
            representative_day = int(scenarios.indices[0])
            single = lambda x: evaluate_objective_np(
                x, *(item[representative_day] for item in data), capacity, 4.0)

            variants = []
            baseline, baseline_hv = self._run_variant(
                data, capacity, single, None, params, params["seed"], task_id,
                5, 25, "原始 NSLDE")
            variants.append(("baseline", "原始 NSLDE", baseline, baseline_hv))

            robust_front, robust_hv = self._run_variant(
                data, capacity, robust, None, params, params["seed"] + 1, task_id,
                25, 48, "场景鲁棒 NSLDE")
            variants.append(("robust", "场景鲁棒", robust_front, robust_hv))

            archive = ExperienceArchive()
            archive.add(scenarios.features[representative_day], baseline[:, :23])
            warm = archive.warm_start(scenarios.features[representative_day],
                                      max(2, params["population"] // 3),
                                      np.random.default_rng(params["seed"] + 2))
            transfer, transfer_hv = self._run_variant(
                data, capacity, single, warm, params, params["seed"] + 2, task_id,
                48, 71, "经验热启动 NSLDE")
            variants.append(("transfer", "经验热启动", transfer, transfer_hv))

            robust_warm, robust_warm_hv = self._run_variant(
                data, capacity, robust, warm, params, params["seed"] + 3, task_id,
                71, 94, "鲁棒+热启动 NSLDE")
            variants.append(("robust_transfer", "鲁棒+热启动", robust_warm, robust_warm_hv))

            all_points = np.vstack([item[2][:, 23:25] for item in variants])
            ref = np.max(all_points, axis=0) * 1.05
            union = all_points
            results = []
            for key, label, front, history in variants:
                points = front[:, 23:25]
                normalized = (points - union.min(0)) / (np.ptp(union, axis=0) + 1e-12)
                union_normalized = (union - union.min(0)) / (np.ptp(union, axis=0) + 1e-12)
                igd = float(cdist(union_normalized, normalized).min(1).mean())
                best_idx = int(np.argmin(normalized.sum(1)))
                _, _, quality = evaluate_objective_np(
                    front[best_idx, :23], *(item[representative_day] for item in data),
                    capacity, 4.0, return_details=True)
                results.append({
                    "key": key, "label": label, "pareto": np.round(points, 3).tolist(),
                    "hv": float(compute_hv_2d(points, ref)), "igd": igd,
                    "spacing": _spacing(points), "f1_best": float(points[:, 0].min()),
                    "f2_best": float(points[:, 1].min()), "solutions": len(points),
                    "convergence": [[i, float(value)] for i, value in enumerate(history)],
                    "dispatch_quality": {
                        key: float(value) if isinstance(value, (float, np.floating)) else int(value)
                        for key, value in quality.items() if key not in ("reservoir_level", "pump_power")
                    },
                })

            result = {
                "province": params["province"], "province_name": province_name,
                "capacity_mw": capacity, "scenario_days": (scenarios.indices + 1).tolist(),
                "scenario_labels": scenarios.labels,
                "risk": {"beta": params["beta"], "alpha": params["alpha"]},
                "variants": results, "runtime_seconds": round(time.perf_counter() - started, 3),
            }
            self._latest = task_id
            self._update(task_id, status="completed", progress=100, stage="计算完成", result=result)
        except Exception as exc:
            self._update(task_id, status="failed", stage="计算失败", error=str(exc))


robust_optimization_service = RobustOptimizationService()
