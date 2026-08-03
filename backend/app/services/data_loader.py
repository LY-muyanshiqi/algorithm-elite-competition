"""
数据加载服务 — 桥接 MATLAB .mat 文件与 FastAPI。

支持两种模式:
- 生产模式: 从 .mat 文件加载真实数据
- 测试模式: 返回 mock 数据（不需要 MATLAB 数据文件）
"""

import os
import numpy as np
from typing import Optional
from dataclasses import dataclass


DATA_BASE = os.environ.get(
    "DATA_BASE",
    "C:/Users/mu'yan'shi'qi/Desktop/Github仓库/thermal-peak-shaving-pumped-storage",
)


@dataclass
class OptimizationData:
    """366天×24小时的完整优化数据"""
    # 原始输入数据 (366, 24)
    hydro: np.ndarray
    wind: np.ndarray
    solar: np.ndarray
    load: np.ndarray
    # Pareto 解集 (366, 100, 27)
    pareto_solutions: np.ndarray
    # 最优解 (366, 23)
    optimal_solution: np.ndarray
    # 派生指标 (366,)
    thermal_with_ps: np.ndarray
    thermal_without_ps: np.ndarray
    carbon_reduction: np.ndarray


class DataLoader:
    """加载 .mat 数据或返回 mock 数据"""

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self._data: Optional[OptimizationData] = None

    def load(self) -> OptimizationData:
        if self._data is not None:
            return self._data

        if self.use_mock:
            self._data = self._generate_mock()
        else:
            self._data = self._load_from_mat()
        return self._data

    def _load_from_mat(self) -> OptimizationData:
        from scipy.io import loadmat

        A_path = os.path.join(DATA_BASE, "A.mat")
        AA_path = os.path.join(DATA_BASE, "AA.mat")
        hydro_path = os.path.join(DATA_BASE, "hydro.txt")
        wind_path = os.path.join(DATA_BASE, "wind.txt")
        solar_path = os.path.join(DATA_BASE, "solar.txt")
        load_path = os.path.join(DATA_BASE, "FH.txt")

        hydro = np.loadtxt(hydro_path)
        wind = np.loadtxt(wind_path)
        solar = np.loadtxt(solar_path)
        load = np.loadtxt(load_path)

        A = loadmat(A_path)
        AA = loadmat(AA_path)

        pareto_key = [k for k in A.keys() if not k.startswith("__")][0]
        pareto_solutions = A[pareto_key]

        opt_key = [k for k in AA.keys() if not k.startswith("__")][0]
        optimal_solution = AA[opt_key]

        thermal_with_ps, thermal_without_ps, carbon_reduction = self._compute_derived(
            hydro, wind, solar, load, optimal_solution
        )

        return OptimizationData(
            hydro=hydro,
            wind=wind,
            solar=solar,
            load=load,
            pareto_solutions=pareto_solutions,
            optimal_solution=optimal_solution,
            thermal_with_ps=thermal_with_ps,
            thermal_without_ps=thermal_without_ps,
            carbon_reduction=carbon_reduction,
        )

    def _compute_derived(
        self,
        hydro: np.ndarray,
        wind: np.ndarray,
        solar: np.ndarray,
        load: np.ndarray,
        opt: np.ndarray,
    ):
        """根据最优解计算火电出力与碳减排"""
        n_days = min(opt.shape[0], 365)
        thermal_with_ps = np.zeros(n_days)
        thermal_without_ps = np.zeros(n_days)
        carbon_reduction = np.zeros(n_days)

        for d in range(n_days):
            renewable = hydro[d, :] + wind[d, :] + solar[d, :]
            thermal_without_ps[d] = np.sum(np.maximum(load[d, :] - renewable, 0))
            pump_effect = np.zeros(24)
            for t in range(23):
                delta = opt[d, t] - (opt[d, t - 1] if t > 0 else 0.5)
                pump_effect[t] = delta * 1400
            pump_effect[23] = 0.5 - opt[d, 22]
            net_load = load[d, :] - renewable - pump_effect
            thermal_with_ps[d] = np.sum(np.maximum(net_load, 0))
            carbon_reduction[d] = (thermal_without_ps[d] - thermal_with_ps[d]) * 0.5 / 10000

        return thermal_with_ps, thermal_without_ps, carbon_reduction

    def _generate_mock(self) -> OptimizationData:
        """生成 mock 数据用于测试"""
        rng = np.random.default_rng(42)
        n_days = 365
        hours = 24

        hydro = rng.uniform(100, 300, (n_days, hours))
        wind = rng.uniform(0, 800, (n_days, hours))
        solar = np.maximum(rng.normal(200, 100, (n_days, hours)), 0)
        load = rng.uniform(600, 1400, (n_days, hours))
        pareto = rng.uniform(0, 1, (n_days, 100, 27))
        opt = rng.uniform(0, 1, (n_days, 23))

        thermal_with_ps, thermal_without_ps, carbon_reduction = self._compute_derived(
            hydro, wind, solar, load, opt
        )

        return OptimizationData(
            hydro=hydro,
            wind=wind,
            solar=solar,
            load=load,
            pareto_solutions=pareto,
            optimal_solution=opt,
            thermal_with_ps=thermal_with_ps,
            thermal_without_ps=thermal_without_ps,
            carbon_reduction=carbon_reduction,
        )


_loader: Optional[DataLoader] = None


def get_data_loader(use_mock: bool = False) -> DataLoader:
    global _loader
    if _loader is None:
        _loader = DataLoader(use_mock=use_mock)
    return _loader


def reset_data_loader():
    global _loader
    _loader = None
