"""
图表模块 - 火电深度调峰+抽水蓄能减碳效益优化系统
提供可复用的图表绘制函数和工具函数
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import streamlit as st

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

    return fig
