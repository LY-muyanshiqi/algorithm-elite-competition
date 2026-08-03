"""
API 客户端 — 面向 FastAPI 后端的 HTTP 调用封装
提供与 data_loader.py 兼容的接口，方便 app.py 无缝切换

使用方式:
    import api_client as dl        # 改用 API 模式
    # 或
    from api_client import (        # 按需导入
        load_all_data,
        calculate_carbon_reduction,
        calculate_pumped_storage_schedule,
        recalculate_with_parameters,
    )
"""
import numpy as np
import os
from typing import Dict, Any, Optional

# ==================== 配置 ====================

# 默认 API 地址，可通过环境变量覆盖
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ==================== HTTP 请求封装 ====================

try:
    import httpx

    # 复用连接池 — 避免每次请求都新建连接（第一次请求可省 100-200ms）
    _client = httpx.Client(timeout=httpx.Timeout(60.0, connect=5.0))

    def _get(path: str) -> dict:
        """GET 请求（复用连接池）"""
        url = f"{API_BASE_URL}{path}"
        resp = _client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(path: str, body: dict) -> dict:
        """POST 请求（复用连接池）"""
        url = f"{API_BASE_URL}{path}"
        resp = _client.post(url, json=body, timeout=60)
        resp.raise_for_status()
        return resp.json()

    HTTP_AVAILABLE = True

except ImportError:
    # 降级：httpx 不可用时用 urllib
    import urllib.request
    import json

    def _get(path: str) -> dict:
        url = f"{API_BASE_URL}{path}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def _post(path: str, body: dict) -> dict:
        url = f"{API_BASE_URL}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    HTTP_AVAILABLE = False


# ==================== 反序列化工具 ====================

def _to_numpy(obj: Any) -> Any:
    """递归将列表转换回 numpy 数组"""
    if isinstance(obj, list):
        # 如果是一维数字列表
        if all(isinstance(x, (int, float)) for x in obj):
            return np.array(obj)
        # 如果是二维数字列表
        if all(isinstance(x, list) for x in obj):
            inner = obj[0] if obj else []
            if all(isinstance(x, (int, float)) for x in inner):
                return np.array(obj)
        # 更深层嵌套 → 先递归
        return [_to_numpy(x) for x in obj]
    return obj


def _decode_data(raw: dict) -> dict:
    """将 API 返回的纯 JSON 数据解码为含 numpy 数组的 dict"""
    result = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = _decode_data(v)
        elif isinstance(v, list):
            result[k] = _to_numpy(v)
        else:
            result[k] = v
    return result


# ==================== 兼容 data_loader 的公开 API ====================

def load_all_data() -> Dict[str, Any]:
    """
    加载全部数据（兼容 data_loader.load_all_data）
    返回与原始 data_loader 相同结构的 dict
    """
    raw = _get("/api/data/all")
    return _decode_data(raw)


def calculate_carbon_reduction(
    data: Dict[str, Any],
    carbon_factor: float = 0.5,
    coal_consumption_high: int = 300,
    coal_consumption_mid: int = 330,
    coal_consumption_low: int = 370,
) -> dict:
    """
    计算碳减排（兼容 data_loader.calculate_carbon_reduction）
    如果 API 返回了 carbon_result 则直接使用，否则本地计算
    """
    # 如果数据中包含 API 计算的 carbon_result，直接返回
    if 'carbon_result' in data:
        return data['carbon_result']

    # 否则从 API 获取（带上参数）
    try:
        return _decode_data(_get("/api/data/carbon"))
    except Exception:
        # 极端降级：回到本地计算（引入 data_loader）
        import data_loader as dl
        return dl.calculate_carbon_reduction(
            data, carbon_factor, coal_consumption_high,
            coal_consumption_mid, coal_consumption_low
        )


def calculate_pumped_storage_schedule(np_power: np.ndarray, data: dict = None) -> dict:
    """
    抽水蓄能调度统计（兼容 data_loader.calculate_pumped_storage_schedule）

    参数:
    - np_power: 抽水蓄能功率数组
    - data: 可选，完整数据字典。如果包含 'ps_stats' 则直接返回（避免冗余HTTP调用）
    """
    # 如果 data 中已有预计算的 ps_stats，直接返回
    if data and 'ps_stats' in data:
        return data['ps_stats']
    # 否则从 API 获取
    try:
        return _get("/api/data/pumped-storage-schedule")
    except Exception:
        import data_loader as dl
        return dl.calculate_pumped_storage_schedule(np_power)


def recalculate_with_parameters(data: Dict[str, Any], params: dict) -> dict:
    """
    使用自定义参数重新计算（兼容 data_loader.recalculate_with_parameters）
    """
    # 映射参数名：data_loader 用的小写 → API 用的首字母大写
    api_params = {
        'Zpump': params.get('Zpump', params.get('zpump', 1400)),
        'h': params.get('h', params.get('h_val', 4)),
        'efficiency': params.get('efficiency', params.get('efficiency_val', 0.75)),
        'min_power_ratio': params.get('min_power_ratio', params.get('min_power', 0.2)),
        'carbon_factor': params.get('carbon_factor', 0.5),
        'coal_consumption_high': params.get('coal_consumption_high', params.get('coal_high', 300)),
        'coal_consumption_mid': params.get('coal_consumption_mid', params.get('coal_mid', 330)),
        'coal_consumption_low': params.get('coal_consumption_low', params.get('coal_low', 370)),
    }
    try:
        raw = _post("/api/simulate", api_params)
        return _decode_data(raw)
    except Exception:
        import data_loader as dl
        return dl.recalculate_with_parameters(data, params)


# ==================== 健康检查 ====================

def check_health() -> dict:
    """检查后端是否在线"""
    try:
        return _get("/api/health")
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


# ==================== 便捷访问 ====================

def is_api_available() -> bool:
    """快速检测 API 是否可用"""
    try:
        return check_health().get("status") == "ok"
    except Exception:
        return False
