"""
数据服务层 — 封装数据加载与计算逻辑，供 FastAPI 调用
复用 前端封装/frontend/data_loader.py 的核心逻辑
"""
import sys
import os
import numpy as np
from typing import Dict, Any, Optional

# 将前端目录加入路径，复用其 data_loader 模块
_frontend_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '前端封装', 'frontend')
)
if _frontend_dir not in sys.path:
    sys.path.insert(0, _frontend_dir)

import data_loader as dl


class NumpyEncoder:
    """numpy 类型 → Python 原生类型 的序列化工具"""

    @staticmethod
    def encode(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    @staticmethod
    def _clean_val(v: Any, round_digits: int = 2) -> Any:
        """递归清理单个值（处理 inf/nan + 浮点数精度压缩）"""
        if isinstance(v, dict):
            return {k: NumpyEncoder._clean_val(v, round_digits) for k, v in v.items()}
        if isinstance(v, list):
            return [NumpyEncoder._clean_val(x, round_digits) for x in v]
        if isinstance(v, float):
            if np.isinf(v) or np.isnan(v):
                return None
            return round(v, round_digits)
        if isinstance(v, np.floating):
            if np.isinf(v) or np.isnan(v):
                return None
            return round(float(v), round_digits)
        return v

    @staticmethod
    def dict_to_native(d: dict, round_digits: int = 2) -> dict:
        """递归将 dict 中所有 numpy 类型转为原生类型（批量取整，比逐元素快百倍）"""
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = NumpyEncoder.dict_to_native(v, round_digits)
            elif isinstance(v, np.ndarray):
                # 直接 numpy 批量取整 → tolist，避免 Python 逐元素遍历
                result[k] = np.round(v, round_digits).tolist()
            elif isinstance(v, np.integer):
                result[k] = int(v)
            elif isinstance(v, np.floating):
                result[k] = None if (np.isinf(v) or np.isnan(v)) else round(float(v), round_digits)
            elif isinstance(v, np.bool_):
                result[k] = bool(v)
            else:
                result[k] = NumpyEncoder._clean_val(v, round_digits)
        return result


class DataService:
    """数据服务 — 单例模式，数据加载后缓存"""

    _instance = None
    _data: Optional[Dict[str, Any]] = None
    _carbon_cache: Optional[dict] = None
    _ps_cache: Optional[dict] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_all(self) -> Dict[str, Any]:
        """加载全部数据（缓存）"""
        if self._data is None:
            print("[DataService] 正在加载数据...")
            self._data = dl.load_all_data()
            # 预计算并缓存派生结果
            print("[DataService] 预计算碳减排...")
            self._carbon_cache = dl.calculate_carbon_reduction(self._data)
            print("[DataService] 预计算抽蓄统计...")
            self._ps_cache = dl.calculate_pumped_storage_schedule(self._data['np_raw'])
            print("[DataService] 数据加载完成")
        return self._data

    def reload(self) -> Dict[str, Any]:
        """强制重新加载"""
        self._data = None
        self._carbon_cache = None
        self._ps_cache = None
        return self.load_all()

    # ==================== 各端点数据 ====================

    def get_summary(self) -> dict:
        """总览指标"""
        data = self.load_all()
        fh = data['fh']
        hydro = data['hydro']
        wind = data['wind']
        solar = data['solar']
        np_raw = data['np_raw']

        N = hydro + wind + solar
        carbon_result = self._carbon_cache or dl.calculate_carbon_reduction(data)

        return NumpyEncoder.dict_to_native({
            'carbon_reduction': carbon_result['carbon_change'],
            'power_change': carbon_result['power_change'],
            'total_wind': float(np.sum(wind) / 10000),
            'total_solar': float(np.sum(solar) / 10000),
            'total_hydro': float(np.sum(hydro) / 10000),
            'total_fh': float(np.sum(fh) / 10000),
            'total_renewable': float((np.sum(wind) + np.sum(solar) + np.sum(hydro)) / 10000),
            'renewable_ratio': float(
                (np.sum(wind) + np.sum(solar) + np.sum(hydro))
                / (np.sum(wind) + np.sum(solar) + np.sum(hydro) + np.sum(fh)) * 100
            ),
            'pump_hours': int((np_raw < 0).sum()),
            'gen_hours': int((np_raw > 0).sum()),
            'generating_hours': ps_stats['generating_hours'],
            'pumping_hours': ps_stats['pumping_hours'],
            'idle_hours': ps_stats['idle_hours'],
            'total_generation': float(ps_stats['total_generation']),
            'total_pumping': float(ps_stats['total_pumping']),
            'avg_generation_power': float(ps_stats['avg_generation_power']),
            'avg_pumping_power': float(ps_stats['avg_pumping_power']),
            'efficiency': float(ps_stats['efficiency']),
        })

    def get_power_data(self) -> dict:
        """新能源发电数据"""
        data = self.load_all()
        return NumpyEncoder.dict_to_native({
            'wind': data['wind'],
            'solar': data['solar'],
            'hydro': data['hydro'],
            'fh': data['fh'],
        })

    def get_solution(self) -> dict:
        """最优解数据"""
        data = self.load_all()
        return NumpyEncoder.dict_to_native({
            'solution': data['solution'],
            'z_gain': data['z_gain'],
        })

    def get_npump(self) -> dict:
        """抽水蓄能功率"""
        data = self.load_all()
        return NumpyEncoder.dict_to_native({
            'np_raw': data['np_raw'],
            'cc': data['cc'],
        })

    def get_thermal(self) -> dict:
        """火电功率（有/无抽蓄）"""
        data = self.load_all()
        return NumpyEncoder.dict_to_native({
            'Nt': data['Nt'],
            'Nt2': data['Nt2'],
        })

    def get_carbon(self) -> dict:
        """碳减排数据"""
        data = self.load_all()
        carbon_result = self._carbon_cache or dl.calculate_carbon_reduction(data)
        return NumpyEncoder.dict_to_native(carbon_result)

    def get_carbon_analysis(self) -> dict:
        """碳减排分析页轻量数据"""
        data = self.load_all()
        carbon_result = self._carbon_cache or dl.calculate_carbon_reduction(data)
        # 预计算月度汇总
        days_in_month = [31,28,31,30,31,30,31,31,30,31,30,31]
        daily = carbon_result['daily_carbon_change']
        monthly = []
        idx = 0
        for d in days_in_month:
            monthly.append(float(sum(daily[idx:idx+d])))
            idx += d
        # 累计
        cum = []
        s = 0
        for v in daily:
            s += v
            cum.append(float(s))
        # 手动序列化，避免 NumpyEncoder round_digits 把碳减排小值吞掉
        def _f(v): return round(float(v), 4)
        return {
            'carbon_change': _f(carbon_result['carbon_change']),
            'power_change': _f(carbon_result['power_change']),
            'daily_carbon': [_f(v) for v in daily],
            'cumulative_carbon': [_f(v) for v in cum],
            'monthly_carbon': [_f(v) for v in monthly],
            'Nt_first30': [round(float(v), 1) for v in data['Nt'].flat[:720]],
            'Nt2_first30': [round(float(v), 1) for v in data['Nt2'].flat[:720]],
            'Nt_total': _f(float(np.sum(data['Nt']))),
            'Nt2_total': _f(float(np.sum(data['Nt2']))),
        }

    def get_pareto(self) -> dict:
        """Pareto 解集（不含原始 A 矩阵 — 100×27×365 过大）"""
        data = self.load_all()
        return NumpyEncoder.dict_to_native({
            'solution': data['solution'],
            'z_gain': data['z_gain'],
        })

    def get_dashboard(self) -> dict:
        """总览页轻量数据（不含完整 365×24 原始数据）"""
        data = self.load_all()
        carbon_result = self._carbon_cache or dl.calculate_carbon_reduction(data)
        ps_stats = self._ps_cache or dl.calculate_pumped_storage_schedule(data['np_raw'])
        w, so, h, f = data['wind'], data['solar'], data['hydro'], data['fh']

        # 手动序列化，避免 NumpyEncoder 把碳减排小值 round 成 0
        def _f(v): return round(float(v), 4)
        carbon_out = {
            'carbon_change': _f(carbon_result['carbon_change']),
            'power_change': _f(carbon_result['power_change']),
            'daily_carbon_change': [_f(v) for v in carbon_result['daily_carbon_change']],
        }
        return {
            'carbon_result': carbon_out,
            'ps_stats': {
                k: (round(float(v), 2) if isinstance(v, (int, float)) else
                   int(v) if isinstance(v, np.integer) else v)
                for k, v in ps_stats.items()
            },
            'total_wind': round(float(np.sum(w) / 10000), 1),
            'total_solar': round(float(np.sum(so) / 10000), 1),
            'total_hydro': round(float(np.sum(h) / 10000), 1),
            'total_fh': round(float(np.sum(f) / 10000), 1),
            'Nt_first30': [round(float(v), 1) for v in data['Nt'].flat[:720]],
            'Nt2_first30': [round(float(v), 1) for v in data['Nt2'].flat[:720]],
            'daily_carbon': [_f(v) for v in carbon_result['daily_carbon_change']],
        }

    def get_pumped_storage_schedule(self) -> dict:
        """抽水蓄能调度统计"""
        data = self.load_all()
        ps_stats = self._ps_cache or dl.calculate_pumped_storage_schedule(data['np_raw'])
        return NumpyEncoder.dict_to_native(ps_stats)

    def get_all_data(self) -> dict:
        """全量数据（一次性返回，前端缓存用）"""
        data = self.load_all()
        carbon_result = self._carbon_cache or dl.calculate_carbon_reduction(data)
        ps_stats = self._ps_cache or dl.calculate_pumped_storage_schedule(data['np_raw'])

        return NumpyEncoder.dict_to_native({
            'wind': data['wind'],
            'solar': data['solar'],
            'hydro': data['hydro'],
            'fh': data['fh'],
            'solution': data['solution'],
            'z_gain': data['z_gain'],
            'np_raw': data['np_raw'],
            'cc': data['cc'],
            'Nt': data['Nt'],
            'Nt2': data['Nt2'],
            'carbon_result': carbon_result,
            'ps_stats': ps_stats,
        })

    def simulate(self, params: dict) -> dict:
        """使用自定义参数重新计算"""
        data = self.load_all()
        result = dl.recalculate_with_parameters(data, params)
        carbon_result = result['carbon_result']
        ps_stats = result['ps_stats']

        return NumpyEncoder.dict_to_native({
            'np_raw': result['np_raw'],
            'Nt': result['Nt'],
            'Nt2': result['Nt2'],
            'cc': result['cc'],
            'carbon_result': carbon_result,
            'ps_stats': ps_stats,
            'params': result['params'],
        })

    def get_raw_dataset(self, dataset: str, day_start: int, day_end: int) -> dict:
        """原始数据浏览"""
        data = self.load_all()
        DATASET_MAP = {
            'wind': data['wind'],
            'solar': data['solar'],
            'hydro': data['hydro'],
            'fh': data['fh'],
            'np_raw': data['np_raw'],
            'Nt': data['Nt'],
            'Nt2': data['Nt2'],
            'solution': data['solution'],
            'z_gain': data['z_gain'],
        }
        if dataset not in DATASET_MAP:
            return {'error': f'未知数据集: {dataset}', 'available': list(DATASET_MAP.keys())}

        arr = DATASET_MAP[dataset]
        sliced = arr[day_start:day_end + 1] if day_end >= day_start else arr

        return NumpyEncoder.dict_to_native({
            'dataset': dataset,
            'shape': list(arr.shape),
            'day_start': day_start,
            'day_end': day_end,
            'data': sliced,
            'min': float(arr.min()),
            'max': float(arr.max()),
            'mean': float(arr.mean()),
            'std': float(arr.std()),
        })


# 全局单例
data_service = DataService()
