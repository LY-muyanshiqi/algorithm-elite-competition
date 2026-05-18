"""
图表模块 - 火电深度调峰+抽水蓄能减碳效益优化系统
提供可复用的图表绘制函数和工具函数
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import traceback
import streamlit as st


def safe_plotly_chart(fig, chart_name="图表", **kwargs):
    """安全渲染图表，失败时显示友好提示而非崩溃"""
    try:
        st.plotly_chart(fig, **kwargs)
    except Exception as e:
        st.warning(f"⚠️ **{chart_name}** 渲染失败: {str(e)[:120]}")
        with st.expander("查看详细错误"):
            st.code(traceback.format_exc())

# 统一图表主题配置
CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e0e6ed"),
)


def export_to_csv(data, filename="data_export.csv"):
    try:
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = data
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="stButton">\U0001f4e5 下载CSV文件</a>'
        return href
    except Exception as e:
        st.error(f"导出失败: {str(e)}")
        return None


def download_plotly_figure(fig, filename="chart.png", width=1200, height=600):
    try:
        img_bytes = fig.to_image(format="png", width=width, height=height)
        return img_bytes
    except Exception:
        return None


def create_metric_card(label, value, unit="", delta=None, color="#00d4ff"):
    """创建自定义指标卡片"""
    delta_html = f'<span style="color: {"#00ff88" if delta and delta > 0 else "#ff6b6b" if delta and delta < 0 else "#8ba4c4"}; font-size: 0.9rem;">{"▲" if delta and delta > 0 else "▼" if delta and delta < 0 else ""} {abs(delta) if delta else ""}</span>' if delta is not None else ""

    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color};">{value}</div>
        <div style="color: #8ba4c4; font-size: 0.9rem;">{unit} {delta_html}</div>
    </div>
    """
    return html


def plot_renewable_power(data, selected_days=None):
    """绘制新能源发电曲线（风光水）"""
    wind = data['wind']
    solar = data['solar']
    hydro = data['hydro']

    if selected_days:
        wind = wind[selected_days[0]-1:selected_days[1]]
        solar = solar[selected_days[0]-1:selected_days[1]]
        hydro = hydro[selected_days[0]-1:selected_days[1]]

    hours = np.arange(8760 if not selected_days else (selected_days[1]-selected_days[0]+1)*24)
    wind_flat = wind.flatten()[:len(hours)]
    solar_flat = solar.flatten()[:len(hours)]
    hydro_flat = hydro.flatten()[:len(hours)]

    fig = make_subplots(rows=2, cols=1,
                       shared_xaxes=True,
                       vertical_spacing=0.08,
                       row_heights=[0.6, 0.4],
                       subplot_titles=('\U0001f4ca 分类型发电功率', '\U0001f4c8 总新能源发电量'))

    fig.add_trace(go.Scatter(x=hours, y=wind_flat, name='风电',
                             fill='tozeroy', fillcolor='rgba(0, 200, 255, 0.3)',
                             line=dict(color='#00c8ff', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hours, y=solar_flat, name='光伏',
                             fill='tozeroy', fillcolor='rgba(255, 180, 0, 0.3)',
                             line=dict(color='#ffb400', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hours, y=hydro_flat, name='水电',
                             fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.3)',
                             line=dict(color='#00ff88', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hours, y=wind_flat + solar_flat + hydro_flat,
                             name='总发电量',
                             line=dict(color='#ff6b9d', width=2),
                             fill='tonexty', fillcolor='rgba(255, 107, 157, 0.2)'), row=2, col=1)

    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis2=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    )

    return fig


def plot_hourly_pattern(data, day_type='all'):
    """绘制典型日负荷曲线"""
    wind = data['wind']
    solar = data['solar']
    hydro = data['hydro']
    fh = data['fh']

    if day_type == 'weekday':
        indices = [i for i in range(365) if (i % 7) < 5]
    elif day_type == 'weekend':
        indices = [i for i in range(365) if (i % 7) >= 5]
    elif day_type == 'spring':
        indices = list(range(0, 90))
    elif day_type == 'summer':
        indices = list(range(90, 182))
    elif day_type == 'autumn':
        indices = list(range(182, 274))
    elif day_type == 'winter':
        indices = list(range(274, 365))
    else:
        indices = list(range(365))

    wind_mean = wind[indices].mean(axis=0)
    solar_mean = solar[indices].mean(axis=0)
    hydro_mean = hydro[indices].mean(axis=0)
    fh_mean = fh[indices].mean(axis=0)

    hours = list(range(24))
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=hours, y=fh_mean, name='火电',
                             fill='tozeroy', fillcolor='rgba(255, 100, 100, 0.4)',
                             line=dict(color='#ff6464', width=2)))
    fig.add_trace(go.Scatter(x=hours, y=wind_mean, name='风电',
                             fill='tozeroy', fillcolor='rgba(0, 200, 255, 0.3)',
                             line=dict(color='#00c8ff', width=1.5)))
    fig.add_trace(go.Scatter(x=hours, y=solar_mean, name='光伏',
                             fill='tozeroy', fillcolor='rgba(255, 180, 0, 0.3)',
                             line=dict(color='#ffb400', width=1.5)))
    fig.add_trace(go.Scatter(x=hours, y=hydro_mean, name='水电',
                             fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.3)',
                             line=dict(color='#00ff88', width=1.5)))

    fig.update_layout(
        title=f'典型{day_type}负荷曲线',
        xaxis_title='小时',
        yaxis_title='功率(MW)',
        height=400,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def plot_pumped_storage_schedule(data, day_index):
    """绘制抽水蓄能日调度曲线"""
    np_raw = data['np_raw'][day_index]
    hours = np.arange(24)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=hours,
        y=np_raw,
        name='抽水蓄能功率',
        marker_color=np.where(np_raw >= 0, 'rgba(0, 255, 128, 0.8)', 'rgba(255, 100, 100, 0.8)')
    ))

    fig.update_layout(
        title=f'抽水蓄能日调度曲线 (第{day_index+1}天)',
        xaxis_title='小时',
        yaxis_title='功率(MW)',
        height=400,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def plot_thermal_power(data, selected_days=None):
    """绘制火电功率曲线"""
    fh = data['fh']
    Nt = data.get('Nt', fh)
    Nt2 = data.get('Nt2', fh)

    if selected_days:
        fh = fh[selected_days[0]-1:selected_days[1]]
        Nt = Nt[selected_days[0]-1:selected_days[1]]
        Nt2 = Nt2[selected_days[0]-1:selected_days[1]]

    hours = np.arange(8760 if not selected_days else (selected_days[1]-selected_days[0]+1)*24)
    fh_flat = fh.flatten()[:len(hours)]
    Nt_flat = Nt.flatten()[:len(hours)]
    Nt2_flat = Nt2.flatten()[:len(hours)]

    # CC水库状态数据
    cc = data.get('cc', None)
    if cc is not None and len(cc) >= 8761:
        cc_daily = cc[1:8761].reshape(365, 24)
        if selected_days:
            cc_daily = cc_daily[selected_days[0]-1:selected_days[1]]
        cc_flat = cc_daily.flatten()[:len(hours)]
    else:
        cc_flat = np.zeros(len(hours))

    fig = make_subplots(rows=2, cols=1,
                       shared_xaxes=True,
                       vertical_spacing=0.08,
                       row_heights=[0.6, 0.4],
                       subplot_titles=('火电功率对比', '抽水蓄能水库状态'))

    fig.add_trace(go.Scatter(x=hours, y=Nt_flat, name='有抽蓄',
                             line=dict(color='#00d4ff', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hours, y=Nt2_flat, name='无抽蓄',
                             line=dict(color='#ff6464', width=1, dash='dash')), row=1, col=1)

    fig.add_trace(go.Scatter(x=hours, y=cc_flat, name='水库状态',
                             fill='tozeroy', fillcolor='rgba(0, 180, 255, 0.25)',
                             line=dict(color='#00b4ff', width=1.5)), row=2, col=1)

    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def plot_pareto_frontier(data):
    """绘制Pareto前沿"""
    z_gain = data['z_gain']

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=z_gain[:, 0],
        y=z_gain[:, 1],
        mode='markers',
        marker=dict(
            size=10,
            color=np.arange(len(z_gain)),
            colorscale='Viridis',
            showscale=True
        ),
        name='Pareto解'
    ))

    fig.update_layout(
        title='Pareto最优前沿',
        xaxis_title='目标函数1',
        yaxis_title='目标函数2',
        height=500,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )


def generate_html_report(data, derived, params=None):
    """生成综合报告HTML用于导出"""
    t = derived['totals']
    c = derived['carbon']
    ps = derived['ps_stats']
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = ""
    metrics = [
        ("碳减排量", f"{c['carbon_change']:.2f} 万吨"),
        ("火电变化量", f"{c['power_change']:.2f} 亿kWh"),
        ("新能源渗透率", f"{t['renewable_ratio']:.1f}%"),
        ("新能源发电量", f"{t['total_renewable']:.2f} 亿kWh"),
        ("抽水小时数", f"{t['pump_hours']} h"),
        ("发电小时数", f"{t['gen_hours']} h"),
        ("抽发效率", f"{ps['efficiency']:.2f}%"),
        ("总发电量", f"{ps['total_generation']:.2f} MWh"),
    ]
    for label, val in metrics:
        rows += f"<tr><td>{label}</td><td>{val}</td></tr>"

    params_html = ""
    if params:
        params_html = "<h3>参数设置</h3><table>"
        for k, v in params.items():
            params_html += f"<tr><td>{k}</td><td>{v}</td></tr>"
        params_html += "</table>"

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>抽水蓄能减碳效益优化 — 综合报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; background: #0a1628; color: #e0e6ed; max-width: 800px; margin: auto; padding: 40px 20px; }}
h1 {{ color: #00d4ff; border-bottom: 2px solid rgba(0,212,255,0.3); padding-bottom: 12px; }}
h3 {{ color: #00d4ff; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
td, th {{ padding: 10px 16px; border: 1px solid rgba(255,255,255,0.1); text-align: left; }}
th {{ background: rgba(0,212,255,0.15); }}
.footer {{ color: #8ba4c4; font-size: 0.8rem; margin-top: 40px; text-align: center; }}
</style></head>
<body>
<h1>⚡ 抽水蓄能减碳效益优化核算系统 — 综合报告</h1>
<p>生成时间: {now} | 数据周期: 全年8760小时</p>
<h3>关键指标</h3>
<table><tr><th>指标</th><th>数值</th></tr>{rows}</table>
{params_html}
<p class="footer">新型电力系统下抽水蓄能减碳效益优化核算系统 | Powered by NSLDE</p>
</body></html>"""
    return html

    return fig
