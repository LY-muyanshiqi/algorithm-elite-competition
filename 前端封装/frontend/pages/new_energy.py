"""
新能源发电页面模块
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def show_new_energy(data):
    """显示新能源发电页面"""
    st.title("🌿 新能源发电分析")
    
    # 季节选择
    season = st.selectbox(
        "选择分析季节",
        ["全年", "春季 (1-3月)", "夏季 (4-6月)", "秋季 (7-9月)", "冬季 (10-12月)"]
    )
    
    day_range = get_day_range(season)
    
    # 选择日期
    day = st.slider("选择日期", day_range[0], day_range[1], int((day_range[0] + day_range[1]) / 2))
    
    # 日发电曲线
    st.subheader(f"第{day}天发电曲线")
    fig_day = make_subplots(rows=3, cols=1, subplot_titles=("风电", "光伏", "水电"))
    
    fig_day.add_trace(go.Scatter(x=np.arange(24), y=data['wind'][day-1, :], name='风电', line_color='#00d4ff'), row=1, col=1)
    fig_day.add_trace(go.Scatter(x=np.arange(24), y=data['solar'][day-1, :], name='光伏', line_color='#ffcc00'), row=2, col=1)
    fig_day.add_trace(go.Scatter(x=np.arange(24), y=data['hydro'][day-1, :], name='水电', line_color='#00ff88'), row=3, col=1)
    
    fig_day.update_layout(height=700, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_day, use_container_width=True)
    
    # 统计信息
    col1, col2, col3 = st.columns(3)
    col1.metric("当日风电", f"{np.sum(data['wind'][day-1, :]):.1f} MWh")
    col2.metric("当日光伏", f"{np.sum(data['solar'][day-1, :]):.1f} MWh")
    col3.metric("当日水电", f"{np.sum(data['hydro'][day-1, :]):.1f} MWh")
    
    st.markdown("---")
    
    # 季节发电对比
    st.subheader("季节发电对比")
    season_data = calculate_season_stats(data)
    
    fig_season = go.Figure()
    fig_season.add_trace(go.Bar(x=['春季', '夏季', '秋季', '冬季'], y=season_data['wind'], name='风电', marker_color='#00d4ff'))
    fig_season.add_trace(go.Bar(x=['春季', '夏季', '秋季', '冬季'], y=season_data['solar'], name='光伏', marker_color='#ffcc00'))
    fig_season.add_trace(go.Bar(x=['春季', '夏季', '秋季', '冬季'], y=season_data['hydro'], name='水电', marker_color='#00ff88'))
    
    fig_season.update_layout(title='各季节新能源发电量(亿kWh)', height=500, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_season, use_container_width=True)


def get_day_range(season):
    """根据季节获取日期范围"""
    season_days = {
        "全年": (1, 365),
        "春季 (1-3月)": (1, 90),
        "夏季 (4-6月)": (91, 181),
        "秋季 (7-9月)": (182, 273),
        "冬季 (10-12月)": (274, 365)
    }
    return season_days.get(season, (1, 365))


def calculate_season_stats(data):
    """计算各季节统计数据"""
    seasons = {
        'spring': slice(0, 90),
        'summer': slice(90, 181),
        'autumn': slice(181, 273),
        'winter': slice(273, 365)
    }
    
    stats = {
        'wind': [],
        'solar': [],
        'hydro': []
    }
    
    for season in seasons.values():
        stats['wind'].append(np.sum(data['wind'][season]) / 10000)
        stats['solar'].append(np.sum(data['solar'][season]) / 10000)
        stats['hydro'].append(np.sum(data['hydro'][season]) / 10000)
    
    return stats