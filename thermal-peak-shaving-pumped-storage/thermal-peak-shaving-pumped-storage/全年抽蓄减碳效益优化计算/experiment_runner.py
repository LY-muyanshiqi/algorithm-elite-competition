"""
experiment_runner.py - NSLDE 三维实验体系自动化框架 v2.0

实验体系:
  1. 消融实验 (Ablation): 7组配置 x 30次重复, 验证每个模块的独立贡献
  2. 横向对比 (Benchmark): 7种算法对比, 多指标评估
  3. 场景泛化 (Generalization): 32组代表性场景组合

数据流:
  MATLAB run_ablation.m / compare_algorithms.m -> .mat 文件 -> Python 分析 -> JSON/图表

用法:
  python experiment_runner.py --mode ablation --output ./experiment_results
  python experiment_runner.py --mode benchmark --output ./experiment_results
  python experiment_runner.py --mode all --output ./experiment_results
"""

import numpy as np
import json
import os
import argparse
from datetime import datetime
from scipy import stats as scipy_stats
import warnings
warnings.filterwarnings('ignore')


def _finite_metric_values(results, metric):
    """Return finite values for *metric* without treating NaN as feasible.

    Experiment outputs can contain ``inf`` for an infeasible run and ``NaN``
    when an upstream solver failed.  Both values must be excluded from
    summary statistics and hypothesis tests.
    """
    values = []
    for result in results or []:
        metrics = result.get('metrics', {}) if isinstance(result, dict) else {}
        try:
            value = float(metrics.get(metric, np.nan))
        except (TypeError, ValueError):
            continue
        if np.isfinite(value):
            values.append(value)
    return np.asarray(values, dtype=float)


def _finite_mean(values):
    """Mean of finite values, or ``None`` when no valid value exists."""
    values = np.asarray(values, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    return float(np.mean(values)) if values.size else None


def compute_spacing_metric(points):
    """Compute the normalized nearest-neighbour spacing of a 2-D front.

    The backend and MATLAB benchmark use the same spacing convention: remove
    non-finite objective rows, min-max normalize each objective independently,
    find each point's nearest *other* point, then return the sample standard
    deviation of those distances.  The normalization keeps the metric from
    being dominated by the different units/scales of the two objectives.  A
    front with fewer than three valid points has no meaningful distribution
    estimate and returns ``0.0``.
    """
    try:
        points = np.asarray(points, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError('points must be a numeric 2-D array with two objectives') from exc
    if points.size == 0:
        return 0.0
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError(f'points must have shape (n, 2), got {points.shape}')

    points = points[np.all(np.isfinite(points), axis=1)]
    if len(points) < 3:
        return 0.0

    # Match backend.robust_optimization_service._spacing exactly.  The tiny
    # denominator offset also handles an objective with zero range.
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        normalized = (points - points.min(axis=0)) / (np.ptp(points, axis=0) + 1e-12)
        deltas = normalized[:, None, :] - normalized[None, :, :]
        distances = np.sqrt(np.sum(deltas * deltas, axis=2))
    np.fill_diagonal(distances, np.inf)
    nearest = np.min(distances, axis=1)
    if not np.all(np.isfinite(nearest)):
        return 0.0
    return float(np.std(nearest, ddof=1))


def _json_safe(value):
    """Convert NumPy/scalar values to strict-JSON-compatible values.

    ``inf`` is useful in memory to denote an all-infeasible run, but standard
    JSON has no Infinity literal.  Persist such values as ``null`` so result
    files remain valid JSON and the in-memory statistical filters can still
    distinguish them before serialization.
    """
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value

OP_NAMES = [
    'DE/rand/1', 'DE/rand/2', 'DE/current-to-best/1',
    'PM', 'SBX', 'Levy', 'Cauchy'
]

INIT_METHODS = ['logistic', 'tent', 'sobol', 'random']

SCENARIOS = {
    'season': ['spring', 'summer', 'autumn', 'winter'],
    'province': ['shaanxi', 'gansu', 'qinghai', 'ningxia'],
    'penetration': ['low_20', 'mid_40', 'high_60', 'very_high_80'],
    'capacity': ['600MW', '800MW', '1400MW', '2000MW'],
    'extreme': ['max_load', 'min_load', 'max_wind', 'zero_wind'],
}


def ablation_configs():
    return [
        {'name': 'A0_NSGAII_baseline', 'init': 'random', 'op_probs': [0,0,0,0.5,0.5,0,0], 'description': 'Standard NSGA-II (SBX+PM)'},
        {'name': 'A1_chaos_only', 'init': 'logistic', 'op_probs': [0,0,0,0.5,0.5,0,0], 'description': 'Logistic chaos init only'},
        {'name': 'A2_de_only', 'init': 'random', 'op_probs': [0.5,0,0,0,0.5,0,0], 'description': 'DE/rand/1 crossover only'},
        {'name': 'A3_levy_only', 'init': 'random', 'op_probs': [0,0,0,0.5,0,0.5,0], 'description': 'Levy mutation only'},
        {'name': 'A4_NSLDE', 'init': 'logistic', 'op_probs': [0.4,0,0,0,0,0.3,0.3], 'description': 'Chaos+DE+Levy (NSLDE)'},
        {'name': 'A5_QLearning', 'init': 'logistic', 'op_probs': 'learned', 'description': 'NSLDE + Q-Learning adaptive'},
        {'name': 'A6_NSLDE_full', 'init': 'logistic', 'op_probs': 'uniform', 'description': 'Full model (all 7 operators)'},
    ]


def benchmark_configs():
    return [
        {'name': 'NSGA-II', 'type': 'classic'},
        {'name': 'NSGA-III', 'type': 'reference'},
        {'name': 'MOEA/D', 'type': 'decomposition'},
        {'name': 'MOEA/D-DE', 'type': 'decomposition_de'},
        {'name': 'RVEA', 'type': 'reference_vector'},
        {'name': 'C-TAEA', 'type': 'constraint_archive'},
        {'name': 'NSLDE (Ours)', 'type': 'proposed'},
    ]


def generalization_scenarios():
    scenarios = []
    for season in ['spring', 'summer', 'autumn', 'winter']:
        for province in ['shaanxi', 'gansu']:
            scenarios.append({
                'season': season, 'province': province,
                'penetration': 'mid_40', 'capacity': '1400MW', 'extreme': 'normal'
            })
    scenarios.append({'season': 'summer', 'province': 'ningxia', 'penetration': 'high_60', 'capacity': '600MW', 'extreme': 'normal'})
    scenarios.append({'season': 'winter', 'province': 'qinghai', 'penetration': 'low_20', 'capacity': '800MW', 'extreme': 'normal'})
    scenarios.append({'season': 'summer', 'province': 'shaanxi', 'penetration': 'mid_40', 'capacity': '1400MW', 'extreme': 'max_load'})
    scenarios.append({'season': 'summer', 'province': 'shaanxi', 'penetration': 'mid_40', 'capacity': '1400MW', 'extreme': 'min_load'})
    scenarios.append({'season': 'spring', 'province': 'gansu', 'penetration': 'very_high_80', 'capacity': '1400MW', 'extreme': 'max_wind'})
    scenarios.append({'season': 'winter', 'province': 'shaanxi', 'penetration': 'low_20', 'capacity': '1400MW', 'extreme': 'zero_wind'})

    for cap in ['600MW', '800MW', '2000MW']:
        scenarios.append({'season': 'summer', 'province': 'shaanxi', 'penetration': 'mid_40', 'capacity': cap, 'extreme': 'normal'})

    for pen in ['low_20', 'high_60', 'very_high_80']:
        if len(scenarios) < 32:
            scenarios.append({'season': 'winter', 'province': 'gansu', 'penetration': pen, 'capacity': '1400MW', 'extreme': 'normal'})

    return scenarios[:32]


def compute_metrics(chromosome, V=23):
    """Compute summary metrics from a chromosome/objective matrix.

    ``V`` is the number of decision variables; columns ``V`` and ``V+1``
    contain the two minimisation objectives.  A row is feasible for the
    purpose of reporting only when *both* objective values are finite.  The
    previous implementation used ``~isinf`` and therefore admitted NaN rows,
    which silently contaminated every mean/std value.
    """
    try:
        chromosome = np.asarray(chromosome, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError('chromosome must be a numeric 2-D array') from exc
    if chromosome.ndim != 2:
        raise ValueError(f'chromosome must be 2-D, got shape {chromosome.shape}')
    if not isinstance(V, (int, np.integer)) or V < 0:
        raise ValueError(f'V must be a non-negative integer, got {V!r}')
    if chromosome.shape[1] <= V + 1:
        raise ValueError(
            f'chromosome has {chromosome.shape[1]} columns; '
            f'objective columns {V} and {V + 1} are required'
        )

    f1 = chromosome[:, V]
    f2 = chromosome[:, V + 1]
    feasible = np.isfinite(f1) & np.isfinite(f2)
    n_feasible = int(np.sum(feasible))
    N = chromosome.shape[0]

    metrics = {
        'n_feasible': n_feasible,
        'feasibility_rate': float(n_feasible / N) if N > 0 else 0.0,
        'f1_mean': float(np.mean(f1[feasible])) if n_feasible > 0 else float('inf'),
        'f2_mean': float(np.mean(f2[feasible])) if n_feasible > 0 else float('inf'),
        'f1_std': float(np.std(f1[feasible])) if n_feasible > 1 else 0.0,
        'f2_std': float(np.std(f2[feasible])) if n_feasible > 1 else 0.0,
        'spread': float(np.std(f1[feasible]) + np.std(f2[feasible])) if n_feasible > 1 else 0.0,
        # Keep the key present for empty/singleton fronts so downstream
        # aggregation and statistical reporting do not raise KeyError.
        'spacing': 0.0,
    }

    if n_feasible > 2:
        metrics['spacing'] = compute_spacing_metric(
            np.column_stack([f1[feasible], f2[feasible]])
        )

    return metrics


def compute_objective_metrics(objectives):
    """Compute the same metrics for an ``N x 2`` objective-only array.

    MATLAB benchmark files store objective values separately from decision
    variables.  Converting through this helper keeps their metric definition
    identical to :func:`compute_metrics` without inventing decision columns.
    """
    try:
        objectives = _normalise_objective_points(objectives)
    except (TypeError, ValueError) as exc:
        raise ValueError('objectives must be a numeric array with a final dimension of 2') from exc

    # Use a compact synthetic chromosome solely to reuse the validated metric
    # implementation; no decision-variable values are exposed to callers.
    chromosome = np.full((objectives.shape[0], 25), np.nan, dtype=float)
    chromosome[:, 23:25] = objectives
    return compute_metrics(chromosome, V=23)


def load_matlab_results(mat_path):
    """从 .mat 文件加载消融实验结果"""
    try:
        import scipy.io as sio
        mat_data = sio.loadmat(mat_path)
        return mat_data
    except ImportError as exc:
        raise RuntimeError('scipy is required to read MATLAB .mat results') from exc


def _matlab_strings(value):
    """Best-effort conversion of a MATLAB cell/string array to Python names."""
    if value is None:
        return []
    array = np.asarray(value, dtype=object).reshape(-1)
    names = []
    for item in array:
        while isinstance(item, np.ndarray) and item.size == 1:
            item = item.reshape(-1)[0]
        if isinstance(item, bytes):
            item = item.decode('utf-8', errors='replace')
        elif isinstance(item, np.ndarray):
            item = ''.join(str(x) for x in item.reshape(-1))
        names.append(str(item))
    return names


def _normalise_objective_points(points):
    """Flatten MATLAB objective arrays to ``N x 2`` without filling values."""
    points = np.asarray(points, dtype=float)
    if points.size == 0:
        return np.empty((0, 2), dtype=float)
    if points.ndim == 1:
        if points.size != 2:
            raise ValueError(f'objective vector must have two values, got {points.shape}')
        return points.reshape(1, 2)
    if points.ndim == 2:
        if points.shape[1] == 2:
            return points
        if points.shape[0] == 2:
            return points.T
    if points.ndim >= 3 and points.shape[-1] == 2:
        return points.reshape(-1, 2)
    raise ValueError(f'cannot interpret objective array with shape {points.shape}')


def _safe_result_path(path, allowed_suffixes=None):
    """Validate an explicitly supplied result path and return its absolute path."""
    if path is None:
        return None
    path = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.isfile(path):
        raise FileNotFoundError(f'experiment result file not found: {path}')
    if allowed_suffixes and os.path.splitext(path)[1].lower() not in allowed_suffixes:
        suffixes = ', '.join(sorted(allowed_suffixes))
        raise ValueError(f'unsupported result format {path!r}; expected {suffixes}')
    return path


def _pending_entries(items, reason):
    """Return explicit pending records instead of synthetic/random metrics."""
    return [
        {
            **item,
            'status': 'pending',
            'metrics': {},
            'reason': reason,
        }
        for item in items
    ]


def _load_json_records(path, section=None):
    with open(path, 'r', encoding='utf-8') as handle:
        payload = json.load(handle)
    if section and isinstance(payload, dict):
        payload = payload.get(section)
    if isinstance(payload, dict):
        payload = payload.get('results', payload.get('records'))
    if not isinstance(payload, list):
        raise ValueError(f'{path} must contain a JSON list of result records')
    return payload


def _benchmark_records_from_mat(mat_data, source):
    """Convert ``compare_algorithms.m`` output into benchmark records."""
    if not isinstance(mat_data, dict):
        raise ValueError('MATLAB benchmark data must be a mapping')

    z_fields = [
        key for key in mat_data
        if not key.startswith('__') and key.lower().startswith('z_')
    ]
    # Keep the order used by compare_algorithms.m when possible.  Sorting
    # alphabetically would pair ``algorithm_names`` with the wrong objective
    # array (NSGA-II would receive NSLDE's points, for example).
    preferred_fields = ['z_nslde', 'z_nsga2', 'z_nsga3', 'z_moead', 'z_moead_de']
    z_fields = [
        field for field in preferred_fields if field in z_fields
    ] + [field for field in z_fields if field not in preferred_fields]
    if not z_fields:
        raise ValueError('MATLAB benchmark file contains no z_<algorithm> objective arrays')

    names = _matlab_strings(mat_data.get('algorithm_names'))
    if len(names) != len(z_fields):
        # ``compare_algorithms.m`` saves both fields.  The fallback keeps files
        # produced by older scripts readable while making the source explicit.
        names = [field[2:] for field in z_fields]

    hv = np.asarray(mat_data.get('hv', np.empty((0, 0))), dtype=float)
    igd = np.asarray(mat_data.get('igd', np.empty((0, 0))), dtype=float)
    spacing = np.asarray(mat_data.get('spacing', np.empty((0, 0))), dtype=float)
    timing = np.asarray(mat_data.get('timing', np.empty((0, 0))), dtype=float)
    records = []
    for index, (name, field) in enumerate(zip(names, z_fields)):
        points = _normalise_objective_points(mat_data[field])
        metrics = compute_objective_metrics(points)
        for key, values in (
            ('hv_mean', hv[:, index] if hv.ndim == 2 and hv.shape[1] > index else []),
            ('igd_mean', igd[:, index] if igd.ndim == 2 and igd.shape[1] > index else []),
            ('spacing_mean', spacing[:, index] if spacing.ndim == 2 and spacing.shape[1] > index else []),
            ('time_mean', timing[:, index] if timing.ndim == 2 and timing.shape[1] > index else []),
        ):
            mean_value = _finite_mean(values)
            if mean_value is not None:
                metrics[key] = mean_value
                # ``spacing`` is the canonical field consumed by reports and
                # the Vue/Streamlit adapters.  Keep ``spacing_mean`` as the
                # source-specific alias so the MATLAB aggregate remains
                # auditable without leaving downstream readers with the
                # Python recomputation from a flattened multi-day front.
                if key == 'spacing_mean':
                    metrics['spacing'] = mean_value
        records.append({
            'name': str(name),
            'type': 'benchmark',
            'status': 'complete',
            'source': source,
            'metrics': metrics,
        })
    return records


def _normalise_generalization_records(records, source):
    """Validate externally generated scenario records and compute raw metrics."""
    normalised = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f'generalization record {index} is not an object')
        item = dict(record)
        raw = item.get('chromosome')
        if raw is not None:
            item['metrics'] = compute_metrics(raw)
        elif item.get('objectives') is not None:
            item['metrics'] = compute_objective_metrics(item['objectives'])
        elif item.get('f1') is not None and item.get('f2') is not None:
            item['metrics'] = compute_objective_metrics([[item['f1'], item['f2']]])
        elif isinstance(item.get('metrics'), dict):
            # Metrics-only records are accepted for interoperability with a
            # separately executed solver, but must contain at least one finite
            # numeric metric to be considered complete.
            finite_count = 0
            for value in item['metrics'].values():
                try:
                    finite_count += int(np.isfinite(float(value)))
                except (TypeError, ValueError):
                    continue
            if finite_count == 0:
                raise ValueError(f'generalization record {index} has no finite metrics')
        else:
            raise ValueError(
                f'generalization record {index} needs chromosome, objectives, '
                'f1/f2, or a metrics object'
            )
        item.pop('chromosome', None)
        item.pop('objectives', None)
        item['status'] = 'complete'
        item['source'] = source
        normalised.append(item)
    return normalised


def _record_field(record, field):
    """Read a field from dict, NumPy structured, or MATLAB struct records."""
    while isinstance(record, np.ndarray) and record.size == 1 and not record.dtype.names:
        record = record.reshape(-1)[0]
    if isinstance(record, dict):
        value = record.get(field)
    elif isinstance(record, np.void) and record.dtype.names and field in record.dtype.names:
        value = record[field]
    elif isinstance(record, np.ndarray) and record.dtype.names and field in record.dtype.names:
        value = record[field]
    else:
        value = getattr(record, field, None)
    while isinstance(value, np.ndarray) and value.size == 1:
        value = value.reshape(-1)[0]
    return value


def mann_whitney_test(results_a, results_b, metric='f1_mean', min_samples=5):
    """Compare two independent samples with the Mann–Whitney U test.

    The old function was named ``wilcoxon_test`` but called
    :func:`scipy.stats.mannwhitneyu`.  These are different tests: Wilcoxon
    signed-rank is paired, whereas the ablation runs use independent seeds.
    Keep the independent-sample test explicit in both the function name and
    returned metadata.
    """
    vals_a = _finite_metric_values(results_a, metric)
    vals_b = _finite_metric_values(results_b, metric)
    result = {
        'test': 'mannwhitneyu',
        'alternative': 'two-sided',
        'metric': metric,
        'n_a': int(vals_a.size),
        'n_b': int(vals_b.size),
        'statistic': None,
        'p_value': None,
    }
    if vals_a.size < min_samples or vals_b.size < min_samples:
        result['reason'] = f'at least {min_samples} finite observations per group are required'
        return result
    stat, p = scipy_stats.mannwhitneyu(vals_a, vals_b, alternative='two-sided')
    result['statistic'] = float(stat)
    result['p_value'] = float(p)
    return result


def kruskal_wallis_test(all_results, metric='f1_mean', min_samples=2):
    """Compare independent configuration samples with Kruskal-Wallis.

    The MATLAB ablation runner assigns different seeds to configurations, so
    the observations are independent rather than paired.  This omnibus test
    is therefore the appropriate replacement for the old Friedman summary.
    """
    groups = {
        name: _finite_metric_values(records, metric)
        for name, records in (all_results or {}).items()
    }
    result = {
        'test': 'kruskal',
        'metric': metric,
        'groups': {name: int(values.size) for name, values in groups.items()},
        'statistic': None,
        'p_value': None,
    }
    if len(groups) < 2 or any(values.size < min_samples for values in groups.values()):
        result['reason'] = (
            f'at least {min_samples} finite observations per configuration '
            'are required'
        )
        return result
    statistic, p_value = scipy_stats.kruskal(*groups.values())
    result['statistic'] = float(statistic)
    result['p_value'] = float(p_value)
    return result


def _holm_adjust(p_values):
    """Holm step-down adjustment for a sequence of finite p-values."""
    raw = np.asarray(p_values, dtype=float)
    adjusted = np.full(raw.shape, np.nan, dtype=float)
    finite = np.isfinite(raw)
    indices = np.flatnonzero(finite)
    if indices.size == 0:
        return adjusted
    order = indices[np.argsort(raw[indices])]
    running = 0.0
    m = order.size
    for rank, index in enumerate(order):
        candidate = min(1.0, (m - rank) * raw[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def wilcoxon_test(results_a, results_b, metric='f1_mean'):
    """Backward-compatible alias for :func:`mann_whitney_test`.

    Existing callers may still import this name.  It intentionally returns
    ``test='mannwhitneyu'`` so reports cannot mislabel the statistical test.
    """
    return mann_whitney_test(results_a, results_b, metric=metric)


def friedman_test(all_results, metric='f1_mean'):
    """Compute aligned rank summaries for a repeated-measures Friedman test.

    The function keeps the historical chi-square calculation but now reports
    an explicit ``pending`` status when there are no complete common runs.
    Missing/NaN metrics are never converted into artificial finite values.
    """
    rankings = {}
    for cfg_name in all_results:
        rankings[cfg_name] = []
    if not all_results or any(not values for values in all_results.values()):
        return {
            'status': 'pending',
            'reason': 'complete runs for every configuration are required',
            'chi2': None,
            'ranks': {},
        }
    n_configs = len(all_results)
    for run_idx in range(min(len(v) for v in all_results.values())):
        vals = []
        for cfg_name in all_results:
            metric_values = _finite_metric_values([all_results[cfg_name][run_idx]], metric)
            if metric_values.size == 0:
                # A run with a missing/non-finite metric cannot participate in
                # a paired rank comparison; skip this run consistently.
                vals = []
                break
            val = float(metric_values[0])
            vals.append((cfg_name, val))
        if not vals:
            continue
        vals.sort(key=lambda x: x[1])
        for rank, (cfg_name, _) in enumerate(vals):
            rankings[cfg_name].append(rank + 1)

    if not rankings or not all(rankings[name] for name in rankings):
        return {
            'status': 'pending',
            'reason': 'no common finite runs available for Friedman test',
            'chi2': None,
            'ranks': {},
        }
    ranks_array = np.array([rankings[name] for name in all_results])
    n, k = ranks_array.shape[1], ranks_array.shape[0]
    if n == 0 or k < 2:
        return {
            'status': 'pending',
            'reason': 'at least two configurations and one common run are required',
            'chi2': None,
            'ranks': {},
        }
    R = np.mean(ranks_array, axis=1)
    chi2 = 12 * n / (k * (k + 1)) * (np.sum(R**2) - k * (k + 1)**2 / 4)
    return {
        'status': 'complete',
        'chi2': float(chi2),
        'ranks': {name: float(R[i]) for i, name in enumerate(all_results)},
    }


def compute_effect_size(results_a, results_b, metric='f1_mean'):
    """Cohen's d 效应量"""
    vals_a = _finite_metric_values(results_a, metric)
    vals_b = _finite_metric_values(results_b, metric)
    if len(vals_a) < 2 or len(vals_b) < 2:
        return None
    pooled_std = np.sqrt((np.var(vals_a, ddof=1) + np.var(vals_b, ddof=1)) / 2)
    if pooled_std < 1e-10:
        return 0.0
    return float((np.mean(vals_a) - np.mean(vals_b)) / pooled_std)


def run_ablation_analysis(mat_data_or_json, output_dir):
    """消融实验分析: 统计检验 + 效应量 + 图表数据"""
    print('\n=== Ablation Study Analysis ===')
    os.makedirs(output_dir, exist_ok=True)

    configs = ablation_configs()
    results_by_config = {}

    for cfg in configs:
        results_by_config[cfg['name']] = []

    print(f'  Processing {len(configs)} configurations...')

    ablation_results = []
    if mat_data_or_json is not None and isinstance(mat_data_or_json, dict) and 'results' in mat_data_or_json:
        raw_results = mat_data_or_json['results']
        # Preserve structured dtypes; coercing them to object turns each
        # record into an unnamed tuple and loses the ``chromosome`` field.
        results_array = np.asarray(raw_results)
        if results_array.dtype.names is None and results_array.dtype != object:
            results_array = np.asarray(raw_results, dtype=object)
        if results_array.ndim == 0:
            results_array = results_array.reshape(1, 1)
        elif results_array.ndim == 1:
            # ``squeeze`` removes the singleton run dimension from a MATLAB
            # 7x1 result.  Since the experiment defines seven configurations,
            # infer that shape explicitly; otherwise treat the vector as one
            # configuration with multiple runs.
            if results_array.size == len(configs):
                results_array = results_array.reshape(-1, 1)
            else:
                results_array = results_array.reshape(1, -1)
        for c in range(min(results_array.shape[0], len(configs))):
            cfg = configs[c]
            config_runs = []
            for r in range(results_array.shape[1]):
                result = results_array[c, r]
                chromo = _record_field(result, 'chromosome')
                metrics = compute_metrics(chromo) if chromo is not None else {}
                config_runs.append({
                    'config': cfg['name'],
                    'run': int(r + 1),
                    'metrics': metrics,
                })
            results_by_config[cfg['name']] = config_runs
            avg_metrics = {}
            metric_names = set()
            for run in config_runs:
                metric_names.update(run.get('metrics', {}).keys())
            for k in metric_names:
                vals = _finite_metric_values(config_runs, k)
                avg_metrics[k] = float(np.mean(vals)) if vals.size else float('inf')
            ablation_results.append({
                'config': cfg,
                'n_runs': len(config_runs),
                'status': 'complete',
                'metrics': avg_metrics,
            })
        # A partially populated MAT file should not silently omit configured
        # methods from the report.
        if len(ablation_results) < len(configs):
            reason = 'pending: MATLAB file contains fewer configurations than expected'
            for cfg in configs[len(ablation_results):]:
                ablation_results.append({
                    'config': cfg,
                    'n_runs': 0,
                    'status': 'pending',
                    'metrics': {},
                    'reason': reason,
                })
    else:
        reason = (
            'pending: no MATLAB ablation result was supplied; run run_ablation.m '
            'and pass its .mat file with --mat-path'
        )
        print(f'  {reason}')
        # Do not fabricate random chromosomes merely to populate a report.
        # Keep one explicit record per configured method so consumers can show
        # what is still waiting for a real solver run.
        ablation_results = _pending_entries(
            [{'config': cfg, 'n_runs': 0} for cfg in configs], reason
        )
        with open(os.path.join(output_dir, 'ablation_results.json'), 'w', encoding='utf-8') as f:
            json.dump(_json_safe(ablation_results), f, indent=2, ensure_ascii=False)
        with open(os.path.join(output_dir, 'ablation_statistics.json'), 'w', encoding='utf-8') as f:
            json.dump({'status': 'pending', 'reason': reason}, f, indent=2, ensure_ascii=False)
        return ablation_results

    print('\n  --- Statistical Tests ---')
    baseline_name = configs[0]['name']
    statistical_results = {}
    for metric in ['f1_mean', 'f2_mean', 'feasibility_rate', 'spacing']:
        print(f'\n  Metric: {metric}')
        omnibus = kruskal_wallis_test(results_by_config, metric)
        pairwise = []
        raw_p_values = []
        for cfg in configs:
            if cfg['name'] != baseline_name:
                test = mann_whitney_test(
                    results_by_config[cfg['name']],
                    results_by_config[baseline_name],
                    metric,
                )
                raw_p_values.append(test['p_value'])
                pairwise.append({'comparison': f'{cfg["name"]} vs {baseline_name}',
                                 **test})
                effect = compute_effect_size(results_by_config[cfg['name']], results_by_config[baseline_name], metric)
                pairwise[-1]['effect_size'] = effect
        adjusted = _holm_adjust(raw_p_values)
        for item, adjusted_p in zip(pairwise, adjusted):
            item['p_value_holm'] = (float(adjusted_p)
                                    if np.isfinite(adjusted_p) else None)
            p = item['p_value_holm']
            sig = ('***' if p is not None and p < 0.001 else
                   '**' if p is not None and p < 0.01 else
                   '*' if p is not None and p < 0.05 else 'ns')
            if p is not None:
                print(f'    {item["comparison"]:45s}: Holm p={p:.4f} {sig}')
        omnibus_p = omnibus.get('p_value')
        if omnibus_p is not None:
            print(f'    Kruskal-Wallis p={omnibus_p:.4f}')
        else:
            print(f'    Kruskal-Wallis: pending ({omnibus.get("reason", "insufficient data")})')
        statistical_results[metric] = {
            'omnibus': omnibus,
            'pairwise_vs_baseline': pairwise,
        }

    with open(os.path.join(output_dir, 'ablation_results.json'), 'w') as f:
        json.dump(_json_safe(ablation_results), f, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, 'ablation_statistics.json'), 'w', encoding='utf-8') as f:
        json.dump(_json_safe({
            'design': 'independent configuration samples',
            'statistics': statistical_results,
        }), f, indent=2, ensure_ascii=False)

    return ablation_results


def run_benchmark_analysis(output_dir, result_path=None):
    """Analyse benchmark output produced by MATLAB or an explicit JSON file.

    ``compare_algorithms.m`` is the current project benchmark entry point. It
    writes ``comparison_results.mat``; this function consumes that file when
    supplied (or when it is found in the current directory/output directory).
    Without solver output, a pending record is written.  No random objective
    values are generated.
    """
    print('\n=== Benchmark Comparison ===')
    os.makedirs(output_dir, exist_ok=True)
    algorithms = benchmark_configs()
    for alg in algorithms:
        print(f'    {alg["name"]} ({alg["type"]})')

    source = None
    if result_path is not None:
        source = _safe_result_path(result_path, {'.mat', '.json'})
    else:
        candidates = [
            os.path.join(output_dir, 'comparison_results.mat'),
            os.path.join(os.getcwd(), 'comparison_results.mat'),
        ]
        source = next((os.path.abspath(path) for path in candidates if os.path.isfile(path)), None)

    if source is None:
        reason = (
            'pending: no benchmark output found; run compare_algorithms.m and '
            'pass comparison_results.mat with --benchmark-path'
        )
        print(f'  {reason}')
        benchmark_results = _pending_entries(
            [dict(alg) for alg in algorithms], reason
        )
    elif source.lower().endswith('.mat'):
        benchmark_results = _benchmark_records_from_mat(load_matlab_results(source), source)
    else:
        benchmark_results = _load_json_records(source, section='benchmark')
        if not benchmark_results:
            raise ValueError(f'benchmark JSON contains no result records: {source}')
        # JSON benchmark files are accepted only as an explicit, already
        # executed result.  Mark the provenance; do not recompute or invent
        # objective values.
        for record in benchmark_results:
            if not isinstance(record, dict) or not isinstance(record.get('metrics'), dict):
                raise ValueError(f'benchmark record lacks a metrics object: {record!r}')
            record.setdefault('status', 'complete')
            record['source'] = source

    with open(os.path.join(output_dir, 'benchmark_results.json'), 'w', encoding='utf-8') as f:
        json.dump(_json_safe(benchmark_results), f, indent=2, ensure_ascii=False, allow_nan=False)

    return benchmark_results


def run_generalization_analysis(output_dir, result_path=None):
    """Analyse externally generated scenario results.

    There is no in-process generalization solver in this module.  A JSON file
    containing scenario records must therefore be supplied via
    ``--generalization-path``.  Missing input is represented explicitly as
    ``status='pending'`` rather than filled with random chromosomes.
    """
    print('\n=== Scenario Generalization ===')
    os.makedirs(output_dir, exist_ok=True)
    scenarios = generalization_scenarios()
    print(f'  Testing {len(scenarios)} scenarios...')

    if result_path is None:
        reason = (
            'pending: no scenario result file supplied; execute the solver for '
            'each scenario and pass a JSON file with --generalization-path'
        )
        print(f'  {reason}')
        scenario_results = _pending_entries(
            [{'scenario': scenario} for scenario in scenarios], reason
        )
    else:
        source = _safe_result_path(result_path, {'.json'})
        records = _load_json_records(source, section='generalization')
        scenario_results = _normalise_generalization_records(records, source)
        if not scenario_results:
            raise ValueError(f'generalization JSON contains no result records: {source}')

    with open(os.path.join(output_dir, 'generalization_results.json'), 'w', encoding='utf-8') as f:
        json.dump(_json_safe(scenario_results), f, indent=2, ensure_ascii=False, allow_nan=False)

    return scenario_results


def print_results_summary(results, mode_name):
    print(f'\n{"="*70}')
    print(f'  {mode_name} Results Summary')
    print(f'{"="*70}')

    if isinstance(results, list):
        for r in results[:10]:
            m = r.get('metrics', r.get('metrics', {}))
            name = r.get('config', {}).get('name', r.get('name', 'unknown'))
            if r.get('status') == 'pending':
                print(f'  {name:30s} | status=pending | {r.get("reason", "input required")}')
                continue
            if m:
                print(f'  {name:30s} | Feas: {m.get("feasibility_rate", 0):.3f} | '
                      f'f1: {m.get("f1_mean", 0):.1f} | f2: {m.get("f2_mean", 0):.1f} | '
                      f'Spacing: {m.get("spacing", 0):.4f}')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n  Report generated: {now}')
    print(f'{"="*70}\n')


def run_experiments(args):
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    all_results = {
        'metadata': {
            'mode': args.mode,
            'n_runs': args.n_runs,
            'timestamp': datetime.now().isoformat(),
        }
    }

    mat_path = args.mat_path

    if args.mode in ('ablation', 'all'):
        mat_data = None
        if mat_path:
            validated_mat_path = _safe_result_path(mat_path, {'.mat'})
            mat_data = load_matlab_results(validated_mat_path)
            print(f'Loaded MATLAB results from: {validated_mat_path}')
        elif not mat_path:
            mat_files = [f for f in os.listdir('.') if f.startswith('ablation_') and f.endswith('.mat')]
            if mat_files:
                mat_data = load_matlab_results(mat_files[0])
                print(f'Loaded MATLAB results from: {mat_files[0]}')

        if mat_data is None:
            print('NOTE: No MATLAB .mat results found. ')
            print('First run in MATLAB:')
            print('  >> run_ablation(1, ''shaanxi'', 5)')
            print('Then re-run: python experiment_runner.py --mode ablation --mat-path ablation_shaanxi_day1.mat')

        ablation_results = run_ablation_analysis(mat_data, output_dir)
        all_results['ablation'] = ablation_results
        print_results_summary(ablation_results, 'Ablation Study')

    if args.mode in ('benchmark', 'all'):
        benchmark_results = run_benchmark_analysis(
            output_dir,
            getattr(args, 'benchmark_path', None),
        )
        all_results['benchmark'] = benchmark_results
        print_results_summary(benchmark_results, 'Benchmark')

    if args.mode in ('generalization', 'all'):
        generalization_results = run_generalization_analysis(
            output_dir,
            getattr(args, 'generalization_path', None),
        )
        all_results['generalization'] = generalization_results
        print(f'  Scenarios tested: {len(generalization_results)}')

    with open(os.path.join(output_dir, 'experiment_results.json'), 'w', encoding='utf-8') as f:
        json.dump(_json_safe(all_results), f, indent=2, ensure_ascii=False)

    print(f'\nAll results saved to: {output_dir}/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NSLDE Experiment Automation v2.0')
    parser.add_argument('--mode', choices=['ablation', 'benchmark', 'generalization', 'all'],
                        default='all', help='Experiment mode')
    parser.add_argument('--n_runs', type=int, default=30, help='Repeats per config')
    parser.add_argument('--output', default='./experiment_results', help='Output directory')
    parser.add_argument('--mat-path', default=None, help='Path to MATLAB ablation .mat file')
    parser.add_argument(
        '--benchmark-path', '--benchmark-mat-path', dest='benchmark_path', default=None,
        help='Path to compare_algorithms.m output (.mat) or an executed benchmark JSON file',
    )
    parser.add_argument(
        '--generalization-path', dest='generalization_path', default=None,
        help='Path to executed scenario-result JSON (no random placeholder is generated)',
    )
    args = parser.parse_args()
    run_experiments(args)
