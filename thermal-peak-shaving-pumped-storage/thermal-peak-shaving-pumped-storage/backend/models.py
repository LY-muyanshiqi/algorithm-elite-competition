"""
Pydantic 模型 — 请求/响应数据结构定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class SimulateParams(BaseModel):
    """调参模拟请求参数"""
    Zpump: int = Field(1400, ge=500, le=3000, description="抽蓄额定功率 (MW)")
    h: int = Field(4, ge=1, le=12, description="蓄能时长 (h)")
    efficiency: float = Field(0.75, ge=0.5, le=1.0, description="抽水效率")
    min_power_ratio: float = Field(0.2, ge=0.0, le=0.5, description="最小出力比例")
    carbon_factor: float = Field(0.5, ge=0.1, le=2.0, description="碳排放系数 (吨CO₂/万kWh)")
    coal_consumption_high: int = Field(300, ge=200, le=500, description="高负荷煤耗 (g/kWh)")
    coal_consumption_mid: int = Field(330, ge=200, le=500, description="中度调峰煤耗 (g/kWh)")
    coal_consumption_low: int = Field(370, ge=200, le=500, description="深度调峰煤耗 (g/kWh)")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str = "1.0.0"
    data_loaded: bool


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


class ExperimentData(BaseModel):
    """实验分析数据"""
    ablation_results: Optional[list] = None
    benchmark_results: Optional[list] = None
    generalization_results: Optional[list] = None


class StrategyData(BaseModel):
    """策略贡献数据"""
    strategy_history: Optional[list] = None
    strategy_use_count: Optional[list] = None


class RobustOptimizationParams(BaseModel):
    """年度代表场景鲁棒优化参数。"""
    province: str = Field("shaanxi", pattern="^(shaanxi|gansu|qinghai|ningxia)$")
    population: int = Field(24, ge=8, le=100)
    generations: int = Field(20, ge=1, le=500)
    scenario_count: int = Field(6, ge=2, le=16)
    extreme_count: int = Field(2, ge=1, le=6)
    beta: float = Field(0.3, ge=0.0, le=2.0)
    alpha: float = Field(0.9, ge=0.5, lt=1.0)
    seed: int = Field(42, ge=0, le=2147483647)
