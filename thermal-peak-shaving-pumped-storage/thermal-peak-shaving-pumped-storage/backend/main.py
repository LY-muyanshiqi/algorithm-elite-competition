"""
FastAPI 主应用 — 抽水蓄能减碳效益优化 API 服务

启动方式:
    uvicorn backend.main:app --reload --port 8000
    或
    python -m uvicorn backend.main:app --reload --port 8000
"""
import sys
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# 确保 backend 包可被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import SimulateParams, HealthResponse
from backend.data_service import data_service

app = FastAPI(
    title="抽水蓄能减碳效益优化 API",
    description="新型电力系统下抽水蓄能减碳效益优化核算系统 — 后端数据服务",
    version="1.0.0",
    lifespan=startup_event,
)

# ==================== CORS 配置 ====================
# 允许 Streamlit 前端 (localhost:8501) 及开发环境跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        # Streamlit Cloud 部署时可在此添加域名
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 生命周期 ====================

@asynccontextmanager
async def startup_event(app: FastAPI):
    """启动时预加载数据"""
    try:
        data_service.load_all()
        print(f"[API] 数据加载完成，可通过 http://localhost:8000/api/health 检查状态")
    except Exception as e:
        print(f"[API] 数据加载失败: {e}")
        print("[API] 请确保 MATLAB 数据文件 (.mat, .txt) 存在于 前端封装/frontend/ 目录")
    yield


# ==================== 健康检查 ====================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    loaded = data_service._data is not None
    return HealthResponse(
        status="ok" if loaded else "degraded",
        data_loaded=loaded,
    )


# ==================== 数据接口 ====================

@app.get("/api/data/summary")
async def get_summary():
    """总览指标（碳减排、新能源占比、抽蓄统计等）"""
    try:
        return data_service.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/dashboard")
async def get_dashboard():
    """总览页轻量数据"""
    try:
        return data_service.get_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/carbon-analysis")
async def get_carbon_analysis():
    """碳减排分析页轻量数据"""
    try:
        return data_service.get_carbon_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/power")
async def get_power_data():
    """新能源发电数据（风电/光伏/水电/火电负荷）"""
    try:
        return data_service.get_power_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/solution")
async def get_solution():
    """最优解数据（决策变量 + 目标函数值）"""
    try:
        return data_service.get_solution()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/npump")
async def get_npump():
    """抽水蓄能功率 + 水库状态"""
    try:
        return data_service.get_npump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/thermal")
async def get_thermal():
    """火电功率（有抽蓄/无抽蓄对比）"""
    try:
        return data_service.get_thermal()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/carbon")
async def get_carbon():
    """碳减排数据"""
    try:
        return data_service.get_carbon()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/pareto")
async def get_pareto():
    """Pareto 最优解集"""
    try:
        return data_service.get_pareto()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/pumped-storage-schedule")
async def get_pumped_storage_schedule():
    """抽水蓄能调度统计"""
    try:
        return data_service.get_pumped_storage_schedule()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/all")
async def get_all_data():
    """全量数据（一次性返回）"""
    try:
        return data_service.get_all_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/raw")
async def get_raw_dataset(
    dataset: str = Query(..., description="数据集名称"),
    day_start: int = Query(0, ge=0, description="起始日期"),
    day_end: int = Query(6, ge=0, description="结束日期"),
):
    """原始数据浏览"""
    try:
        result = data_service.get_raw_dataset(dataset, day_start, day_end)
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 模拟计算 ====================

@app.post("/api/simulate")
async def simulate(params: SimulateParams):
    """参数调整后重新计算（调参即算）"""
    try:
        result = data_service.simulate(params.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== History API ====================

@app.get("/api/history/list")
async def list_history():
    """列出所有历史运行记录"""
    try:
        import db
        runs = db.list_runs()
        return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history/load/{run_id}")
async def load_history(run_id: int):
    """加载某次历史运行的每日结果"""
    try:
        import db
        arr = db.load_run_daily(run_id)
        if arr.size == 0:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return {
            "run_id": run_id,
            "daily": arr.tolist(),
            "params": db.load_run_params(run_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/history/save")
async def save_history(params: dict):
    """保存当前运行结果到数据库"""
    try:
        import db
        run_id = db.save_run(
            data_service._data,
            params=params.get("params", {}),
            region=params.get("region", "华东"),
            year=params.get("year", 2024),
            note=params.get("note", ""),
        )
        return {"run_id": run_id, "status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 简易入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
