"""Streamlit adapter for the scenario-robust RLDE-F experiment API.

The original Streamlit pages display the historical MATLAB comparison.  The
Python implementation now exposes a different contract: four variants are
evaluated on the same representative/extreme scenarios and report a common
HV, joint-front IGD, spacing, expected/CVaR objectives, and RLDE-F state.  This
module keeps that contract in one place so ``app.py`` and ``streamlit_app.py``
cannot drift apart.

No synthetic values are produced here.  When the API is unavailable or no
experiment has been run, the page reports that state and gives the command
needed to start the backend.
"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


DEFAULT_API_ROOT = "http://127.0.0.1:8000"
PROVINCES = {
    "shaanxi": "陕西",
    "gansu": "甘肃",
    "qinghai": "青海",
    "ningxia": "宁夏",
}


class RobustApiError(RuntimeError):
    """An actionable API or response-contract error."""


def api_root() -> str:
    """Return the configured backend root.

    ``API_BASE`` is the documented setting.  ``API_BASE_URL`` is accepted for
    compatibility with local deployments that used the earlier name.
    """

    configured = (os.getenv("API_BASE") or os.getenv("API_BASE_URL") or
                  DEFAULT_API_ROOT).strip()
    return configured.rstrip("/")


def _api_url(path: str) -> str:
    root = api_root()
    suffix = path if path.startswith("/") else f"/{path}"
    # The endpoint paths in the backend include /api.  Also accept an API_BASE
    # value that already contains that prefix, which is convenient in a
    # reverse-proxy deployment.
    if suffix.startswith("/api/") and root.endswith("/api"):
        suffix = suffix[4:]
    return f"{root}{suffix}"


def request_json(path: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None,
                timeout: float = 8.0) -> Dict[str, Any]:
    """Call the JSON API and normalize transport/contract failures."""

    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(_api_url(path), data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
            parsed = json.loads(error_body)
            detail = parsed.get("detail") or parsed.get("error") or error_body
        except Exception:
            detail = str(exc)
        raise RobustApiError(f"后端返回 HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RobustApiError(
            f"无法连接后端 {api_root()}。请先启动 FastAPI："
            "python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
        ) from exc

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RobustApiError("后端响应不是有效 JSON，请检查 API_BASE 配置") from exc
    if not isinstance(parsed, dict):
        raise RobustApiError("后端响应格式异常：应为 JSON 对象")
    return parsed


def _finite(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _points(value: Any) -> np.ndarray:
    """Convert a Pareto payload to a finite ``n x 2`` array."""

    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return np.empty((0, 2), dtype=float)
    if array.ndim == 1:
        if array.size < 2:
            return np.empty((0, 2), dtype=float)
        # Older snapshots occasionally contain a trailing scalar.  Ignore
        # that incomplete pair instead of raising during page rendering.
        usable = (array.size // 2) * 2
        array = array[:usable].reshape(-1, 2)
    if array.ndim != 2 or array.shape[1] < 2:
        return np.empty((0, 2), dtype=float)
    array = array[:, :2]
    return array[np.isfinite(array).all(axis=1)]


def _vector(value: Any, size: int = 2) -> List[Optional[float]]:
    if value is None:
        return [None] * size
    try:
        values = list(value)
    except TypeError:
        values = []
    return [_finite(values[index]) if index < len(values) else None
            for index in range(size)]


def normalize_variants(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Accept the current list contract and older dict-shaped snapshots."""

    raw = result.get("variants", [])
    if isinstance(raw, dict):
        converted = []
        for key, value in raw.items():
            item = dict(value) if isinstance(value, dict) else {}
            item.setdefault("key", key)
            item.setdefault("label", key)
            converted.append(item)
        raw = converted
    if not isinstance(raw, list):
        return []
    variants = []
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            continue
        item = dict(value)
        item.setdefault("key", f"variant_{index + 1}")
        item.setdefault("label", item["key"])
        item["pareto"] = _points(item.get("pareto", item.get("front"))).tolist()
        item["hv"] = item.get("hv", item.get("hypervolume"))
        item["igd"] = item.get("igd", item.get("IGD"))
        item["spacing"] = item.get("spacing", item.get("spacing_mean"))
        item["expected_objectives"] = _vector(
            item.get("expected_objectives", item.get("expected")))
        item["cvar_objectives"] = _vector(
            item.get("cvar_objectives", item.get("cvar")))
        item["worst_objectives"] = _vector(
            item.get("worst_objectives", item.get("worst")))
        item["rl"] = item.get("rl", item.get("rl_summary"))
        item["rl"] = item["rl"] if isinstance(item["rl"], dict) else None
        item["dispatch_quality"] = (item.get("dispatch_quality")
                                     if isinstance(item.get("dispatch_quality"), dict)
                                     else {})
        variants.append(item)
    return variants


def _display_number(value: Any, digits: int = 4) -> str:
    number = _finite(value)
    if number is None:
        return "--"
    if abs(number) >= 10000 or (0 < abs(number) < 0.001):
        return f"{number:.3e}"
    return f"{number:.{digits}f}"


def _result_rows(variants: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in variants:
        expected = _vector(item.get("expected_objectives"))
        cvar = _vector(item.get("cvar_objectives"))
        worst = _vector(item.get("worst_objectives"))
        rl = item.get("rl") or {}
        quality = item.get("dispatch_quality") or {}
        rows.append({
            "算法变体": str(item.get("label", item.get("key", "--"))),
            "解数": _finite(item.get("solutions")),
            "HV": _finite(item.get("hv")),
            "IGD": _finite(item.get("igd")),
            "Spacing": _finite(item.get("spacing")),
            "最小调峰": _finite(item.get("f1_best")),
            "最小碳排": _finite(item.get("f2_best")),
            "期望 f1": expected[0],
            "CVaR f1": cvar[0],
            "最坏 f1": worst[0],
            "F 均值": _finite(rl.get("f_mean")),
            # Keep this column numeric even when the non-RL variants have no
            # controller; mixed int/string columns fail Arrow serialization.
            "Q 更新": _finite(rl.get("updates")) if rl else None,
            "启停": _finite(quality.get("starts")),
            "模式切换": _finite(quality.get("mode_switches")),
        })
    frame = pd.DataFrame(rows)
    numeric_columns = [
        "解数", "HV", "IGD", "Spacing", "最小调峰", "最小碳排",
        "期望 f1", "CVaR f1", "最坏 f1", "F 均值", "Q 更新", "启停", "模式切换",
    ]
    for column in numeric_columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _render_result(result: Dict[str, Any]) -> None:
    variants = normalize_variants(result)
    if not variants:
        st.info("后端已返回结果，但没有可展示的算法变体。请检查实验参数或后端日志。")
        return

    risk = result.get("risk") if isinstance(result.get("risk"), dict) else {}
    summary = [
        f"省份：{result.get('province_name') or result.get('province') or '--'}",
        f"算法版本：{result.get('algorithm_version') or '--'}",
        f"代表日：{len(result.get('scenario_days') or [])} 个",
        f"CVaR α={_display_number(risk.get('alpha'), 2)} / β={_display_number(risk.get('beta'), 2)}",
        f"耗时：{_display_number(result.get('runtime_seconds'), 2)} s",
    ]
    st.caption("　·　".join(summary))
    if result.get("objective_definition"):
        st.caption(f"目标口径：{result['objective_definition']}")

    st.subheader("四组算法结果")
    table = _result_rows(variants)
    if not table.empty:
        st.dataframe(table, use_container_width=True, hide_index=True)

    labels = [str(item.get("label", item.get("key", "--"))) for item in variants]
    colors = ["#43e7c5", "#48a8ff", "#ffc857", "#ff6b8a", "#b58cff"]

    with st.expander("Pareto 前沿与统一指标", expanded=True):
        pareto_col, metric_col = st.columns([1.5, 1])
        with pareto_col:
            fig = go.Figure()
            has_points = False
            for index, item in enumerate(variants):
                points = _points(item.get("pareto"))
                if len(points):
                    has_points = True
                    fig.add_trace(go.Scatter(
                        x=points[:, 0], y=points[:, 1], mode="markers",
                        name=labels[index], marker=dict(size=7, color=colors[index % len(colors)]),
                    ))
            fig.update_layout(
                title="真实 Pareto 前沿（共同鲁棒测试目标）",
                xaxis_title="调峰目标 f1", yaxis_title="碳排目标 f2",
                template="plotly_dark", height=430,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            if has_points:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("结果中没有有限 Pareto 点。")
        with metric_col:
            metric_names = ["HV", "IGD", "Spacing"]
            metric_values = [[_finite(item.get(name.lower())) for item in variants]
                             for name in metric_names]
            metric_fig = make_subplots(rows=1, cols=3, subplot_titles=metric_names)
            for col, (name, values) in enumerate(zip(metric_names, metric_values), 1):
                metric_fig.add_trace(go.Bar(
                    x=labels, y=values, name=name,
                    marker_color=colors[:len(labels)],
                    text=[_display_number(value, 3) for value in values],
                    textposition="outside",
                ), row=1, col=col)
            metric_fig.update_layout(
                showlegend=False, template="plotly_dark", height=430,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=55, b=95, l=35, r=15),
            )
            metric_fig.update_xaxes(tickangle=-25)
            st.plotly_chart(metric_fig, use_container_width=True)

    with st.expander("期望目标 / CVaR 风险目标", expanded=True):
        risk_fig = make_subplots(rows=1, cols=2, subplot_titles=("目标 f1", "目标 f2"))
        for objective_index, title in enumerate(("f1", "f2"), 1):
            risk_fig.add_trace(go.Bar(
                x=labels,
                y=[_vector(item.get("expected_objectives"))[objective_index - 1]
                   for item in variants],
                name=f"期望 {title}", marker_color="#43e7c5",
            ), row=1, col=objective_index)
            risk_fig.add_trace(go.Bar(
                x=labels,
                y=[_vector(item.get("cvar_objectives"))[objective_index - 1]
                   for item in variants],
                name=f"CVaR {title}", marker_color="#ff6b8a",
            ), row=1, col=objective_index)
        risk_fig.update_layout(
            barmode="group", template="plotly_dark", height=390,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.12), margin=dict(t=70, b=90),
        )
        risk_fig.update_xaxes(tickangle=-25)
        st.plotly_chart(risk_fig, use_container_width=True)

    rl_items = [item for item in variants if item.get("rl")]
    if rl_items:
        st.subheader("RLDE-F 个体自适应状态")
        rl_rows = []
        for item in rl_items:
            rl = item["rl"]
            rl_rows.append({
                "算法变体": str(item.get("label", item.get("key", "--"))),
                "F 均值": _finite(rl.get("f_mean")),
                "F 最小": _finite(rl.get("f_min")),
                "F 最大": _finite(rl.get("f_max")),
                "Q 更新次数": _finite(rl.get("updates")),
                "SoftMax 温度": _finite(rl.get("temperature")),
                "动作计数": json.dumps(rl.get("action_counts"), ensure_ascii=False)
                if isinstance(rl.get("action_counts"), (list, tuple))
                else str(rl.get("action_counts", "--")),
            })
        rl_frame = pd.DataFrame(rl_rows)
        for column in ("F 均值", "F 最小", "F 最大", "Q 更新次数", "SoftMax 温度"):
            if column in rl_frame:
                rl_frame[column] = pd.to_numeric(rl_frame[column], errors="coerce")
        st.dataframe(rl_frame, use_container_width=True, hide_index=True)

    convergence_items = []
    for index, item in enumerate(variants):
        raw = item.get("convergence")
        if not isinstance(raw, list):
            continue
        points = []
        for pair in raw:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                x = _finite(pair[0]); y = _finite(pair[1])
                if x is not None and y is not None:
                    points.append((x, y))
        if points:
            convergence_items.append((index, points))
    if convergence_items:
        st.subheader("鲁棒目标收敛曲线")
        convergence_fig = go.Figure()
        for index, points in convergence_items:
            convergence_fig.add_trace(go.Scatter(
                x=[point[0] for point in points], y=[point[1] for point in points],
                mode="lines+markers", name=labels[index],
                line=dict(color=colors[index % len(colors)]),
            ))
        convergence_fig.update_layout(
            template="plotly_dark", height=360,
            xaxis_title="代数", yaxis_title="HV",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(convergence_fig, use_container_width=True)
    else:
        st.info("当前后端结果没有收敛历史，未生成模拟曲线。")

    scenario_days = result.get("scenario_days") or []
    scenario_labels = result.get("scenario_labels") or []
    weights = result.get("scenario_weights") or []
    if scenario_days:
        scenario_rows = []
        for index, day in enumerate(scenario_days):
            label = scenario_labels[index] if index < len(scenario_labels) else "--"
            weight = weights[index] if index < len(weights) else None
            scenario_rows.append({
                "代表日": str(day), "场景类型": str(label), "权重": _finite(weight),
            })
        st.subheader("代表场景构成")
        scenario_frame = pd.DataFrame(scenario_rows)
        scenario_frame["权重"] = pd.to_numeric(scenario_frame["权重"], errors="coerce")
        st.dataframe(scenario_frame, use_container_width=True, hide_index=True)


def _parameters_form(key_prefix: str) -> Dict[str, Any]:
    """Render controls and return values accepted by ``RobustOptimizationParams``."""

    with st.expander("鲁棒实验参数", expanded=True):
        cols = st.columns(4)
        with cols[0]:
            province = st.selectbox("省份", list(PROVINCES),
                                    format_func=lambda value: PROVINCES[value],
                                    key=f"{key_prefix}_province")
            population = st.number_input("种群规模", min_value=8, max_value=100,
                                         value=24, step=1, key=f"{key_prefix}_population")
            generations = st.number_input("迭代代数", min_value=1, max_value=500,
                                          value=20, step=1, key=f"{key_prefix}_generations")
        with cols[1]:
            scenario_count = st.number_input("场景数量", min_value=2, max_value=16,
                                              value=6, step=1, key=f"{key_prefix}_scenarios")
            extreme_count = st.number_input("极端场景", min_value=1, max_value=6,
                                            value=2, step=1, key=f"{key_prefix}_extremes")
            seed = st.number_input("随机种子", min_value=0, max_value=2147483647,
                                   value=42, step=1, key=f"{key_prefix}_seed")
        with cols[2]:
            beta = st.number_input("风险权重 β", min_value=0.0, max_value=2.0,
                                   value=0.3, step=0.1, key=f"{key_prefix}_beta")
            alpha = st.number_input("CVaR 分位 α", min_value=0.5, max_value=0.99,
                                    value=0.9, step=0.01, key=f"{key_prefix}_alpha")
            f_delta = st.number_input("F 自适应步长", min_value=0.01, max_value=0.5,
                                      value=0.1, step=0.01, key=f"{key_prefix}_f_delta")
        with cols[3]:
            rl_alpha = st.number_input("RL 学习率", min_value=0.001, max_value=1.0,
                                       value=0.1, step=0.01, key=f"{key_prefix}_rl_alpha")
            rl_gamma = st.number_input("RL 折扣因子", min_value=0.0, max_value=1.0,
                                       value=0.9, step=0.01, key=f"{key_prefix}_rl_gamma")
            rl_temperature = st.number_input("SoftMax 温度", min_value=0.01, max_value=10.0,
                                             value=1.0, step=0.1, key=f"{key_prefix}_temperature")
    if extreme_count >= scenario_count:
        st.warning("极端场景数量必须小于场景总数。")
    return {
        "province": province, "population": int(population),
        "generations": int(generations), "scenario_count": int(scenario_count),
        "extreme_count": int(extreme_count), "beta": float(beta),
        "alpha": float(alpha), "seed": int(seed), "rl_alpha": float(rl_alpha),
        "rl_gamma": float(rl_gamma), "rl_temperature": float(rl_temperature),
        "f_delta": float(f_delta),
    }


def _poll_task(task_id: str, timeout_seconds: float = 900.0,
               on_update: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    started = time.monotonic()
    progress = st.progress(0, text="等待后端开始计算…")
    while time.monotonic() - started < timeout_seconds:
        task = request_json(f"/api/optimization/robust/{task_id}", timeout=10.0)
        if on_update:
            on_update(task)
        current = _finite(task.get("progress"), 0.0) or 0.0
        progress.progress(int(max(0, min(100, current))), text=str(task.get("stage") or "计算中…"))
        status = task.get("status")
        if status == "completed":
            progress.progress(100, text="计算完成")
            return task
        if status == "failed":
            raise RobustApiError(str(task.get("error") or "后端优化失败"))
        time.sleep(0.7)
    raise RobustApiError("后端计算超过 15 分钟仍未完成，请检查后端日志或降低种群/代数")


def show_robust_algorithm_comparison(data: Optional[Dict[str, Any]] = None,
                                     key_prefix: str = "robust") -> None:
    """Render the current scenario-robust RLDE-F comparison workflow."""

    del data  # The experiment is evaluated by the backend on province data.
    st.markdown("## 🧪 场景鲁棒算法对比（RLDE-F）")
    st.markdown(
        "后端将使用相同代表场景和极端剩余负荷场景，对比原始 NSLDE、场景鲁棒 NSLDE、"
        "RLDE-F 场景鲁棒和 RLDE-F 热启动。HV 越大越好，IGD/Spacing 越小越好；"
        "页面只展示真实后端结果，不生成随机占位数据。"
    )
    params = _parameters_form(key_prefix)
    control_a, control_b, control_c = st.columns([1, 1, 2])
    with control_a:
        run_clicked = st.button("▶ 运行四组对比", key=f"{key_prefix}_run", type="primary")
    with control_b:
        load_clicked = st.button("↻ 加载最近结果", key=f"{key_prefix}_load")
    with control_c:
        st.caption(f"API：`{api_root()}/api`（可通过环境变量 `API_BASE` 修改）")

    result_key = f"{key_prefix}_result"
    task_key = f"{key_prefix}_task"
    if load_clicked:
        try:
            latest = request_json("/api/optimization/robust/latest")
            status = latest.get("status")
            if status == "completed" and isinstance(latest.get("result"), dict):
                st.session_state[result_key] = latest["result"]
                st.session_state[task_key] = latest
            elif status in {"queued", "running"} and latest.get("task_id"):
                with st.spinner("正在读取后端任务状态…"):
                    finished = _poll_task(str(latest["task_id"]))
                st.session_state[result_key] = finished.get("result")
                st.session_state[task_key] = finished
            else:
                st.info(latest.get("message") or "后端尚无鲁棒优化结果，请先运行实验。")
        except RobustApiError as exc:
            st.error(str(exc))

    if run_clicked:
        if params["extreme_count"] >= params["scenario_count"]:
            st.error("极端场景数量必须小于场景总数。")
        else:
            try:
                with st.spinner("正在提交鲁棒优化任务…"):
                    task = request_json("/api/optimization/robust/start", method="POST",
                                        payload=params, timeout=15.0)
                task_id = task.get("task_id")
                if not task_id:
                    raise RobustApiError("后端未返回 task_id，无法轮询实验进度")
                with st.spinner("后端正在运行四组算法，请耐心等待…"):
                    finished = _poll_task(str(task_id))
                result = finished.get("result")
                if not isinstance(result, dict):
                    raise RobustApiError("任务完成但结果为空")
                st.session_state[result_key] = result
                st.session_state[task_key] = finished
            except RobustApiError as exc:
                st.error(str(exc))

    result = st.session_state.get(result_key)
    if isinstance(result, dict):
        _render_result(result)
    else:
        st.info("尚未加载鲁棒实验结果。请启动后端后运行实验，或点击“加载最近结果”。")
        st.code(
            "python -m uvicorn backend.main:app --reload "
            "--host 127.0.0.1 --port 8000",
            language="powershell",
        )


__all__ = [
    "RobustApiError", "api_root", "normalize_variants",
    "request_json", "show_robust_algorithm_comparison",
]
