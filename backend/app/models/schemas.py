from pydantic import BaseModel
from typing import Optional


class OverviewResponse(BaseModel):
    annual_carbon_reduction: float
    renewable_penetration_rate: float
    pump_hours: float
    generation_hours: float
    pump_efficiency: float
    pareto_coverage: float
    monthly_trend: list[dict]


class RenewableResponse(BaseModel):
    day: int
    wind: list[float]
    solar: list[float]
    hydro: list[float]
    total: list[float]


class PumpedStorageResponse(BaseModel):
    day: int
    pump_power: list[float]
    gen_power: list[float]
    reservoir_level: list[float]
    sankey_data: dict
    daily_stats: dict


class ThermalCarbonResponse(BaseModel):
    with_ps: list[float]
    without_ps: list[float]
    daily_carbon_reduction: list[float]
    monthly_carbon_reduction: list[float]
    annual_total_reduction: float


class ParetoResponse(BaseModel):
    season: int
    solutions: list[dict]
    objectives: list[str]


class RecalculateRequest(BaseModel):
    pump_capacity: float = 1400
    storage_hours: float = 4
    pump_efficiency: float = 0.75
    min_output_ratio: float = 0.2
    carbon_coefficient: float = 0.5
    levy_prob: float = 0.3
    population: int = 100
    generations: int = 3000


class RecalculateStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: Optional[str] = None


class ScenarioRequest(BaseModel):
    wind_multiplier: float = 1.0
    solar_multiplier: float = 1.0
    load_multiplier: float = 1.0


class ScenarioResponse(BaseModel):
    params: dict
    results: dict


class ABCompareRequest(BaseModel):
    params_a: dict
    params_b: dict


class ABCompareResponse(BaseModel):
    kpi_comparison: list[dict]
    thermal_overlay: dict
    detailed_diff: list[dict]


class SensitivityResponse(BaseModel):
    parameter: str
    values: list[float]
    carbon_reduction: list[float]
    renewable_rate: list[float]


class TrendResponse(BaseModel):
    moving_avg_7d: list[float]
    linear_trend: list[float]
    slope: float


class StatisticsResponse(BaseModel):
    annual: dict
    correlation_matrix: list[list[float]]
    parameter_names: list[str]


class DecisionResponse(BaseModel):
    recommendations: list[dict]
    priority_order: list[str]
