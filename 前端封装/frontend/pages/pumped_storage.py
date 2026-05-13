"""
抽水蓄能调度页面模块
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go


def show_pumped_storage(data):
    """显示抽水蓄能调度页面"""
    st.title("💧 抽水蓄能调度分析")
    
    # 功率分布
    st.subheader("功率分布统计")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=data['np_raw'].flatten(),
        name='功率分布',
        nbinsx=50,
        marker_color='#00d4ff'
    ))
    fig_hist.update_layout(
        title='抽水蓄能功率分布',
        xaxis_title='功率(MW)',
        yaxis_title='小时数',
        height=400,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # 选择日期
    day = st.slider("选择日期", 1, 365, 180)
    
    # 日调度曲线
    st.subheader(f"第{day}天调度曲线")
    fig_day = go.Figure()
    fig_day.add_trace(go.Bar(
        x=np.arange(24),
        y=data['np_raw'][day-1, :],
        name='蓄能功率',
        marker_color=np.where(data['np_raw'][day-1, :] >= 0, '#00ff88', '#ff6b6b')
    ))
    fig_day.update_layout(
        title=f'抽水蓄能日调度曲线（正值:发电, 负值:抽水）',
        xaxis_title='小时',
        yaxis_title='功率(MW)',
        height=400,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_day, use_container_width=True)
    
    # 当日统计
    day_data = data['np_raw'][day-1, :]
    pump_energy = np.sum(day_data[day_data < 0]) * -1
    gen_energy = np.sum(day_data[day_data > 0])
    
    col1, col2 = st.columns(2)
    col1.metric("抽水能量", f"{pump_energy:.1f} MWh")
    col2.metric("发电能量", f"{gen_energy:.1f} MWh")
    
    st.markdown("---")
    
    # 月度统计
    st.subheader("月度调度统计")
    month_stats = calculate_month_stats(data)
    
    fig_month = go.Figure()
    fig_month.add_trace(go.Bar(x=np.arange(1, 13), y=month_stats['pump'], name='抽水', marker_color='#ff6b6b'))
    fig_month.add_trace(go.Bar(x=np.arange(1, 13), y=month_stats['gen'], name='发电', marker_color='#00ff88'))
    
    fig_month.update_layout(
        title='月度抽水/发电量对比(万kWh)',
        xaxis_title='月份',
        height=400,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_month, use_container_width=True)


def calculate_month_stats(data):
    """计算月度统计数据"""
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    pump = []
    gen = []
    
    start_day = 0
    for days in days_per_month:
        month_data = data['np_raw'][start_day:start_day+days, :].flatten()
        pump.append(np.sum(month_data[month_data < 0]) * -1 / 100)
        gen.append(np.sum(month_data[month_data > 0]) / 100)
        start_day += days
    
    return {'pump': pump, 'gen': gen}