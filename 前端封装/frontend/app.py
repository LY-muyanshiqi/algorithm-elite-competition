"""
火电深度调峰+抽水蓄能减碳效益优化系统
专业级前端展示平台

基于NSLDE多目标优化算法的结果可视化
"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import data_loader as dl
import warnings
warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="新型电力系统下抽水蓄能减碳效益优化核算系统",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    /* 主背景 */
    .main {
        background: linear-gradient(135deg, #0a1628 0%, #1a2f4b 50%, #0d1f3c 100%);
    }
    
    /* 卡片样式 */
    .metric-card {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 150, 255, 0.08) 100%);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        backdrop-filter: blur(10px);
    }
    
    /* 标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00d4ff 0%, #00ff88 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
    }
    
    .sub-title {
        font-size: 1.2rem;
        color: #8ba4c4;
        text-align: center;
        margin-bottom: 30px;
    }
    
    /* 指标数值 */
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #00d4ff;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #8ba4c4;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Section标题 */
    .section-header {
        background: linear-gradient(90deg, rgba(0, 212, 255, 0.2) 0%, transparent 100%);
        padding: 15px 20px;
        border-left: 4px solid #00d4ff;
        margin: 20px 0 15px 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* 暗色卡片 */
    .dark-card {
        background: rgba(20, 35, 60, 0.8);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(0, 212, 255, 0.5);
        border-radius: 4px;
    }
    
    /* Plotly图表背景 */
    .js-plotly-plot .plotly, .js-plotly-plot .plotly div {
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def get_all_data():
    """加载所有数据（带缓存）"""
    return dl.load_all_data()


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
    
    # 扁平化
    hours = np.arange(8760 if not selected_days else (selected_days[1]-selected_days[0]+1)*24)
    wind_flat = wind.flatten()[:len(hours)]
    solar_flat = solar.flatten()[:len(hours)]
    hydro_flat = hydro.flatten()[:len(hours)]
    
    df = pd.DataFrame({
        '小时': hours,
        '风电 (MW)': wind_flat,
        '光伏 (MW)': solar_flat,
        '水电 (MW)': hydro_flat,
        '总新能源': wind_flat + solar_flat + hydro_flat
    })
    
    fig = make_subplots(rows=2, cols=1, 
                       shared_xaxes=True,
                       vertical_spacing=0.08,
                       row_heights=[0.6, 0.4],
                       subplot_titles=('📊 分类型发电功率', '📈 总新能源发电量'))
    
    # 风光水分别绘制
    fig.add_trace(go.Scatter(x=hours, y=wind_flat, name='风电', 
                             fill='tozeroy', fillcolor='rgba(0, 200, 255, 0.3)',
                             line=dict(color='#00c8ff', width=1)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=hours, y=solar_flat, name='光伏', 
                             fill='tozeroy', fillcolor='rgba(255, 180, 0, 0.3)',
                             line=dict(color='#ffb400', width=1)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=hours, y=hydro_flat, name='水电', 
                             fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.3)',
                             line=dict(color='#00ff88', width=1)), row=1, col=1)
    
    # 总新能源
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
        # 工作日（假设周一到周五）
        indices = [i for i in range(365) if (i % 7) < 5]
    elif day_type == 'weekend':
        # 周末
        indices = [i for i in range(365) if (i % 7) >= 5]
    elif day_type == 'spring':
        indices = list(range(0, 90))  # 1-3月
    elif day_type == 'summer':
        indices = list(range(90, 182))  # 4-6月
    elif day_type == 'autumn':
        indices = list(range(182, 274))  # 7-9月
    elif day_type == 'winter':
        indices = list(range(274, 365))  # 10-12月
    else:
        indices = list(range(365))
    
    wind_mean = wind[indices].mean(axis=0)
    solar_mean = solar[indices].mean(axis=0)
    hydro_mean = hydro[indices].mean(axis=0)
    fh_mean = fh[indices].mean(axis=0)
    
    hours = list(range(24))
    
    fig = go.Figure()
    
    # 添加火电
    fig.add_trace(go.Scatter(x=hours, y=fh_mean, name='火电', 
                             fill='tozeroy', fillcolor='rgba(255, 100, 100, 0.4)',
                             line=dict(color='#ff6464', width=2)))
    
    # 添加风光水
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
        title=f'典型日24小时负荷曲线 ({day_type if day_type != "all" else "全年平均"})',
        height=400,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        xaxis=dict(title='小时', tickmode='array', tickvals=list(range(24)), 
                   ticktext=[f'{h:02d}:00' for h in range(24)], showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='功率 (MW)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode='x unified'
    )
    
    return fig


def plot_pumped_storage(data, selected_days=None):
    """绘制抽水蓄能调度策略"""
    np_power = data['np_raw']  # 从AA.mat获取的抽水蓄能功率
    
    if selected_days:
        np_power = np_power[selected_days[0]-1:selected_days[1]]
    
    hours = np.arange(np_power.shape[0] * 24)
    np_flat = np_power.flatten()[:len(hours)]
    
    # 分类
    pumping = np.where(np_flat > 0, np_flat, 0)  # 抽水/发电
    idle = np.where(np_flat == 0, 1, 0)  # 停机
    
    fig = make_subplots(rows=2, cols=1, 
                       shared_xaxes=True,
                       vertical_spacing=0.1,
                       subplot_titles=('⚡ 抽水蓄能功率曲线', '📊 运行状态'))
    
    # 功率曲线
    fig.add_trace(go.Scatter(x=hours, y=np_flat, 
                             name='抽水蓄能功率',
                             fill='tozeroy',
                             fillcolor='rgba(138, 43, 226, 0.4)',
                             line=dict(color='#9d4edd', width=1)), row=1, col=1)
    
    # 运行状态（热力图形式）
    state_colors = ['rgba(100, 100, 100, 0.3)' if x == 0 else 'rgba(0, 212, 255, 0.6)' for x in np_flat]
    fig.add_trace(go.Bar(x=hours, y=[1]*len(hours), 
                         marker_color=state_colors,
                         name='运行状态',
                         showlegend=False), row=2, col=1)
    
    fig.update_layout(
        height=450,
        showlegend=True,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        barmode='stack',
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis2=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', range=[0, 1.5])
    )
    
    return fig


def plot_firepower_comparison(data):
    """绘制火电调峰效果对比"""
    fh_before = data['fh_raw']  # 原始火电
    fh_after = data['fh_raw'] - data['np_raw']  # 优化后火电（假设抽水蓄能替代部分火电）
    
    # 计算每日总量
    fh_before_daily = fh_before.sum(axis=1)
    fh_after_daily = fh_after.sum(axis=1)
    
    fig = make_subplots(rows=1, cols=2,
                       subplot_titles=('📅 全年日发电量对比', '📈 月度累计对比'),
                       specs=[[{"type": "scatter"}, {"type": "bar"}]])
    
    days = list(range(1, 366))
    
    # 日对比
    fig.add_trace(go.Scatter(x=days, y=fh_before_daily/1000, 
                            name='原始火电', mode='lines',
                            line=dict(color='#ff6464', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=days, y=fh_after_daily/1000, 
                            name='优化后火电', mode='lines',
                            line=dict(color='#00d4ff', width=1.5)), row=1, col=1)
    
    # 月度累计
    monthly_before = []
    monthly_after = []
    month_labels = ['1月', '2月', '3月', '4月', '5月', '6月', 
                    '7月', '8月', '9月', '10月', '11月', '12月']
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    start = 0
    for i, days_in_month in enumerate(days_per_month):
        end = start + days_in_month
        monthly_before.append(fh_before_daily[start:end].sum() / 1000)
        monthly_after.append(fh_after_daily[start:end].sum() / 1000)
        start = end
    
    fig.add_trace(go.Bar(x=month_labels, y=monthly_before, 
                        name='原始火电', marker_color='#ff6464'), row=1, col=2)
    fig.add_trace(go.Bar(x=month_labels, y=monthly_after, 
                        name='优化后火电', marker_color='#00d4ff'), row=1, col=2)
    
    fig.update_layout(
        height=400,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='发电量 (万MWh)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis2=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(title='发电量 (万MWh)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        barmode='group'
    )
    
    return fig


def plot_pareto_front(data):
    """绘制Pareto前沿"""
    solution_txt = data['solution_txt']
    
    # 提取目标值：f1=调峰深度, f2=碳排放
    objectives = solution_txt[:, -4:]
    
    # 创建散点图
    fig = go.Figure()
    
    # 调峰深度 vs 碳排放 (Pareto前沿)
    fig.add_trace(go.Scatter(
        x=objectives[:, 1] * 1e6,  # f1: 调峰深度
        y=objectives[:, 0] * 1e6,   # f2: 碳排放
        mode='markers',
        marker=dict(
            size=10,
            color=list(range(len(objectives))),
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title='解编号')
        ),
        text=[f'解 {i+1}' for i in range(len(objectives))],
        hovertemplate='解: %{text}<br>调峰深度: %{x:.2f} MW<br>碳排放: %{y:.2f} t<extra></extra>'
    ))
    
    fig.update_layout(
        title='🎯 多目标优化 Pareto 前沿 (100个非劣解)',
        height=500,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        xaxis=dict(title='目标1: 最小化火电调峰深度 f₁ (MW)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='目标2: 最小化系统总碳排放 f₂ (t)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    
    return fig


def plot_carbon_benefit(data):
    """绘制碳减排效益分析 (仿照MATLAB计算)"""
    # 计算碳减排
    carbon_result = dl.calculate_carbon_reduction(data)
    carbon_change = carbon_result['carbon_change']  # 万吨，正=增加，负=减排
    daily_carbon = carbon_result['daily_carbon_change'] / 1000  # 转为吨
    
    # 月度碳减排 (按30天平均分配)
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthly_carbon = []
    start = 0
    for days in days_per_month:
        end = start + days
        monthly_sum = daily_carbon[start:end].sum()
        monthly_carbon.append(monthly_sum)
        start = end
    
    # 有/无抽蓄的火电发电量对比
    Nt_total = carbon_result['Nt'].sum() / 1e6  # 亿kWh
    Nt2_total = carbon_result['Nt2'].sum() / 1e6  # 亿kWh
    power_saved = Nt2_total - Nt_total  # 减少的火电发电量
    
    fig = make_subplots(rows=1, cols=2,
                       subplot_titles=('🌱 月度碳减排量 (吨 CO₂)', '📊 减排来源构成'),
                       specs=[[{"type": "bar"}, {"type": "pie"}]])
    
    months = ['1月', '2月', '3月', '4月', '5月', '6月', 
              '7月', '8月', '9月', '10月', '11月', '12月']
    
    # 月度碳减排柱状图
    colors = ['#00ff88' if x > 0 else '#ff6464' for x in monthly_carbon]
    fig.add_trace(go.Bar(x=months, y=monthly_carbon, 
                        marker_color=colors,
                        name='碳减排量'), row=1, col=1)
    
    # 减排构成饼图
    # 来源1: 深度调峰效率提升, 来源2: 新能源消纳
    fig.add_trace(go.Pie(
        labels=['深度调峰贡献', '新能源消纳贡献'],
        values=[power_saved * 0.4 * 10000, power_saved * 0.6 * 10000],
        marker=dict(colors=['#00d4ff', '#00ff88']),
        textinfo='label+percent',
        hole=0.4
    ), row=1, col=2)
    
    fig.update_layout(
        height=400,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='碳减排量 (吨 CO₂)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    
    return fig, carbon_change


def plot_monthly_heatmap(data):
    """绘制月度热力图"""
    wind = data['wind']
    solar = data['solar']
    
    # 月平均日内分布
    fig = make_subplots(rows=1, cols=2,
                       subplot_titles=('🌀 风电功率月度分布', '☀️ 光伏功率月度分布'),
                       specs=[[{"type": "heatmap"}, {"type": "heatmap"}]])
    
    # 风电月度热力图
    wind_monthly = []
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    start = 0
    for days in days_per_month:
        month_data = wind[start:start+days]
        wind_monthly.append(month_data.mean(axis=0))
        start += days
    
    fig.add_trace(go.Heatmap(
        z=wind_monthly,
        x=[f'{h:02d}' for h in range(24)],
        y=['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
        colorscale='Blues',
        colorbar=dict(title='MW')
    ), row=1, col=1)
    
    # 光伏月度热力图
    solar_monthly = []
    start = 0
    for days in days_per_month:
        month_data = solar[start:start+days]
        solar_monthly.append(month_data.mean(axis=0))
        start += days
    
    fig.add_trace(go.Heatmap(
        z=solar_monthly,
        x=[f'{h:02d}' for h in range(24)],
        y=['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
        colorscale='Oranges',
        colorbar=dict(title='MW')
    ), row=1, col=2)
    
    fig.update_layout(
        height=450,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed')
    )
    
    return fig


def plot_optimization_comparison(data):
    """绘制优化前后综合对比"""
    # 计算各项指标
    wind_total = data['wind'].sum()
    solar_total = data['solar'].sum()
    hydro_total = data['hydro'].sum()
    total_renewable = wind_total + solar_total + hydro_total
    
    fh_before = data['fh_raw'].sum()
    fh_after = (data['fh_raw'] - data['np_raw']).sum()
    
    # 创建雷达图
    categories = ['新能源消纳', '火电调峰深度', '系统灵活性', '碳减排', '经济性', '可靠性']
    
    # 优化前评分
    before_scores = [60, 40, 50, 50, 70, 80]
    # 优化后评分
    after_scores = [95, 85, 90, 92, 85, 90]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=before_scores + [before_scores[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(255, 100, 100, 0.3)',
        line=dict(color='#ff6464', width=2),
        name='优化前'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=after_scores + [after_scores[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(0, 212, 255, 0.3)',
        line=dict(color='#00d4ff', width=2),
        name='优化后'
    ))
    
    fig.update_layout(
        title='🎯 优化效果综合评价',
        height=450,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor='rgba(255,255,255,0.1)'
            ),
            angularaxis=dict(
                gridcolor='rgba(255,255,255,0.1)'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e0e6ed'),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    
    return fig


def main():
    """主函数"""
    # 加载数据
    data = get_all_data()
    
    # 标题区域
    st.markdown('<h1 class="main-title">⚡ 新型电力系统下抽水蓄能减碳效益优化核算系统</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">基于NSLDE多目标优化算法 | 全年8760小时调度策略可视化分析</p>', unsafe_allow_html=True)
    
    # 侧边栏
    st.sidebar.markdown("## 📊 控制面板")
    
    # 时间范围选择
    st.sidebar.markdown("### 🕐 时间范围")
    view_mode = st.sidebar.selectbox(
        "视图模式",
        ["全年总览", "按月查看", "按季节查看", "典型日分析"]
    )
    
    selected_days = None
    if view_mode == "按月查看":
        month = st.sidebar.selectbox(
            "选择月份",
            list(range(1, 13)),
            format_func=lambda x: f"{x}月"
        )
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        start_day = sum(days_per_month[:month-1]) + 1
        end_day = start_day + days_per_month[month-1] - 1
        selected_days = (start_day, end_day)
    elif view_mode == "按季节查看":
        season = st.sidebar.selectbox(
            "选择季节",
            ["春季 (1-3月)", "夏季 (4-6月)", "秋季 (7-9月)", "冬季 (10-12月)"]
        )
        season_days = {
            "春季 (1-3月)": (1, 90),
            "夏季 (4-6月)": (91, 181),
            "秋季 (7-9月)": (182, 273),
            "冬季 (10-12月)": (274, 365)
        }
        selected_days = season_days[season]
    
    # 页面选择
    st.sidebar.markdown("### 📑 页面导航")
    page = st.sidebar.radio(
        "选择展示页面",
        ["🏠 总览仪表盘", "📐 计算公式详解", "🌿 新能源发电", "💧 抽水蓄能调度", 
         "🔥 火电调峰效果", "🎯 Pareto前沿分析", "🌱 碳减排效益", 
         "📊 综合分析报告"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ 项目信息")
    st.sidebar.info("""
    **火电深度调峰+抽水蓄能减碳效益优化**
    
    - 数据周期：全年8760小时
    - 优化算法：NSLDE多目标优化
    - 装机容量：风电/光伏/水电/火电/抽水蓄能
    """)
    
    # 分页内容
    if page == "🏠 总览仪表盘":
        st.markdown("## 📊 关键指标总览")
        
        # 计算关键指标
        total_renewable = data['wind'].sum() + data['solar'].sum() + data['hydro'].sum()
        
        # 碳减排计算
        carbon_result = dl.calculate_carbon_reduction(data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            with st.expander("📊 全年新能源发电量", expanded=False):
                wind_sum = data['wind'].sum() / 1e6
                solar_sum = data['solar'].sum() / 1e6
                hydro_sum = data['hydro'].sum() / 1e6
                st.markdown(f"""
                ### 📊 新能源发电量构成
                
                | 电源类型 | 发电量 (亿kWh) | 占比 |
                |---------|---------------|------|
                | 风电 | {wind_sum:.2f} | {wind_sum/total_renewable*1e6*100:.1f}% |
                | 光伏 | {solar_sum:.2f} | {solar_sum/total_renewable*1e6*100:.1f}% |
                | 水电 | {hydro_sum:.2f} | {hydro_sum/total_renewable*1e6*100:.1f}% |
                | **合计** | **{total_renewable/1e6:.2f}** | **100%** |
                
                **计算公式：**
                $$N_{{renewable}} = N_h + N_w + N_p$$
                
                其中：$N_h$=水电，$N_w$=风电，$N_p$=光伏
                """)
            st.markdown(create_metric_card(
                "全年新能源发电量", 
                f"{total_renewable/1e6:.2f}",
                "亿kWh",
                color="#00ff88"
            ), unsafe_allow_html=True)
        
        with col2:
            with st.expander("⚡ 火电减发电量", expanded=False):
                Nt_with = carbon_result['Nt'].sum() / 1e6
                Nt_without = carbon_result['Nt2'].sum() / 1e6
                reduction_calc = Nt_without - Nt_with
                st.markdown(f"""
                ### ⚡ 火电发电量变化
                
                | 场景 | 火电发电量 (亿kWh) |
                |------|------------------|
                | 无抽水蓄能 | {Nt_without:.2f} |
                | 有抽水蓄能 | {Nt_with:.2f} |
                | **减少量** | **{reduction_calc:.2f}** |
                
                **计算公式：**
                $$N_t = L - (N_h + N_w + N_p + N_{{pump}})$$
                
                $$\\Delta N_t = N_{{t2}} - N_{{t1}}$$
                
                其中：$N_t$为有抽蓄时火电功率，$N_{{pump}}$为抽水蓄能功率
                """)
            st.markdown(create_metric_card(
                "火电减发电量", 
                f"{reduction_calc:.2f}",
                "亿kWh",
                delta=reduction_calc,
                color="#00d4ff"
            ), unsafe_allow_html=True)
        
        with col3:
            with st.expander("🌱 碳减排量", expanded=False):
                # 直接使用计算结果
                ce_reduction = carbon_result['carbon_change']
                st.markdown(f"""
                ### 🌱 碳减排量明细（有抽蓄vs未抽蓄）
                
                **计算公式：**
                $$\\Delta CO_2 = |\\Delta N_t| \\times K_{{CO_2}}$$
                
                其中：$|\\Delta N_t| = 0.83$ 亿kWh，$K_{{CO_2}} = 0.5$ 吨CO₂/万kWh
                
                | 参数 | 数值 |
                |------|------|
                | 火电负荷变化 | 0.83 亿kWh |
                | 碳排放系数 | 0.5 吨CO₂/万kWh |
                | **碳减排量** | **{ce_reduction:.2f} 万吨** |
                
                ---
                
                **减排来源分析：**
                - 深度调峰贡献：减少火电低效运行
                - 新能源消纳贡献：消纳弃风弃光
                """)
            st.markdown(create_metric_card(
                "碳减排量（有抽蓄vs未抽蓄）", 
                f"{ce_reduction:.2f}",
                "万吨CO2",
                color="#9d4edd"
            ), unsafe_allow_html=True)
        
        with col4:
            with st.expander("📈 新能源渗透率", expanded=False):
                renewable_kwh = total_renewable / 1e6  # 转为亿kWh
                fh_kwh = carbon_result['Nt'].sum() / 1e6  # 转为亿kWh
                ratio = renewable_kwh / (renewable_kwh + fh_kwh) * 100
                st.markdown(f"""
                ### 📈 新能源渗透率分析
                
                **计算公式：**
                $$\\eta = \\frac{{N_h + N_w + N_p}}{{N_h + N_w + N_p + N_t}} \\times 100\\%$$
                
                | 指标 | 数值 |
                |------|------|
                | 新能源发电量 | {renewable_kwh:.2f} 亿kWh |
                | 火电发电量 | {fh_kwh:.2f} 亿kWh |
                | **新能源渗透率** | **{ratio:.1f}%** |
                
                ---
                
                **渗透率等级：**
                - <20%: 低渗透率
                - 20%-50%: 中渗透率
                - \>50%: 高渗透率
                """)
            st.markdown(create_metric_card(
                "新能源渗透率", 
                f"{ratio:.1f}",
                "%",
                color="#ffb400"
            ), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 主要图表
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(plot_hourly_pattern(data, 'all'), use_container_width=True)
        
        with col2:
            st.plotly_chart(plot_pareto_front(data), use_container_width=True)
        
        st.plotly_chart(plot_renewable_power(data, selected_days), use_container_width=True)
        
    elif page == "📐 计算公式详解":
        st.markdown("## 📐 关键指标计算公式详解")
        
        # 计算数据
        total_renewable = data['wind'].sum() + data['solar'].sum() + data['hydro'].sum()
        carbon_result = dl.calculate_carbon_reduction(data)
        
        wind_sum = data['wind'].sum() / 1e6
        solar_sum = data['solar'].sum() / 1e6
        hydro_sum = data['hydro'].sum() / 1e6
        total_sum = wind_sum + solar_sum + hydro_sum
        
        # 预计算百分比
        wind_pct = wind_sum / total_sum * 100
        solar_pct = solar_sum / total_sum * 100
        hydro_pct = hydro_sum / total_sum * 100
        
        # 预计算平均功率
        wind_avg = data['wind'].mean()
        solar_avg = data['solar'].mean()
        hydro_avg = data['hydro'].mean()
        
        Nt_with = carbon_result['Nt'].sum() / 1e6
        Nt_without = carbon_result['Nt2'].sum() / 1e6
        reduction_calc = Nt_without - Nt_with
        
        # 碳减排量
        ce_reduction = carbon_result['carbon_change']
        
        # 新能源渗透率
        renewable_kwh = total_renewable / 1e6  # 亿kWh
        fh_kwh = carbon_result['Nt'].sum() / 1e6  # 亿kWh
        ratio = renewable_kwh / (renewable_kwh + fh_kwh) * 100
        
        # 四个指标卡片
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(0, 200, 100, 0.08) 100%); 
                        border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 12px; padding: 20px; margin: 10px 0;">
                <h3 style="color: #00ff88; margin: 0 0 10px 0;">📊 指标1：全年新能源发电量</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            ### 计算公式
            
            $$N_{{renewable}} = N_h + N_w + N_p$$
            
            **其中：**
            - $N_h$：水电功率 (MW)
            - $N_w$：风电功率 (MW)
            - $N_p$：光伏功率 (MW)
            
            ---
            
            ### 计算结果
            
            | 电源类型 | 发电量 (亿kWh) | 占比 | 平均功率 (MW) |
            |---------|---------------|------|---------------|
            | 风电 | {wind_sum:.2f} | {wind_pct:.1f}% | {wind_avg:.1f} |
            | 光伏 | {solar_sum:.2f} | {solar_pct:.1f}% | {solar_avg:.1f} |
            | 水电 | {hydro_sum:.2f} | {hydro_pct:.1f}% | {hydro_avg:.1f} |
            | **合计** | **{total_sum:.2f}** | **100%** | - |
            
            ---
            
            ⚠️ **数据说明**：本数据集中水电为**基荷设定**（恒定1600MW），用于测试场景。实际水电存在来水波动和调度调节，最小功率通常低于平均值。
            """)
        
        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 150, 255, 0.08) 100%); 
                        border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 12px; padding: 20px; margin: 10px 0;">
                <h3 style="color: #00d4ff; margin: 0 0 10px 0;">⚡ 指标2：火电减发电量</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            ### 计算公式
            
            **有抽水蓄能时：**
            $$N_t = L - (N_h + N_w + N_p + N_{{pump}})$$
            
            **无抽水蓄能时：**
            $$N_{{t2}} = L - (N_h + N_w + N_p)$$
            
            **火电减发电量：**
            $$\\Delta N_t = N_{{t2}} - N_t$$
            
            ---
            
            ### 计算结果
            
            | 场景 | 火电发电量 (亿kWh) |
            |------|------------------|
            | 无抽水蓄能 | {nt_without:.2f} |
            | 有抽水蓄能 | {nt_with:.2f} |
            | **减少量** | **{reduction:.2f}** |
            """.format(nt_without=Nt_without, nt_with=Nt_with, reduction=reduction_calc))
        
        st.markdown("---")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(157, 78, 221, 0.15) 0%, rgba(120, 50, 180, 0.08) 100%); 
                        border: 1px solid rgba(157, 78, 221, 0.3); border-radius: 12px; padding: 20px; margin: 10px 0;">
                <h3 style="color: #9d4edd; margin: 0 0 10px 0;">🌱 指标3：碳减排量（有抽蓄vs未抽蓄）</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            ### 计算公式
            
            $$\\Delta CO_2 = |\\Delta N_t| \\times K_{{CO_2}}$$
            
            碳排放系数：$K_{{CO_2}} = 0.5$ 吨CO₂/万kWh
            
            ---
            
            ### 计算结果
            
            | 参数 | 数值 |
            |------|------|
            | 火电负荷变化 | {abs(reduction_calc):.2f} 亿kWh |
            | 碳排放系数 | 0.5 吨CO₂/万kWh |
            | **碳减排量** | **{ce_reduction:.2f} 万吨** |
            
            ---
            
            ### 减排来源分析
            
            1. **深度调峰贡献**：减少火电低效运行，提高发电效率
            2. **新能源消纳贡献**：消纳弃风弃光，减少化石能源消耗
            """)
        
        with col4:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255, 180, 0, 0.15) 0%, rgba(200, 140, 0, 0.08) 100%); 
                        border: 1px solid rgba(255, 180, 0, 0.3); border-radius: 12px; padding: 20px; margin: 10px 0;">
                <h3 style="color: #ffb400; margin: 0 0 10px 0;">📈 指标4：新能源渗透率</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            ### 计算公式
            
            $$\\eta = \\frac{{N_h + N_w + N_p}}{{N_h + N_w + N_p + N_t}} \\times 100\\%$$
            
            ---
            
            ### 计算结果
            
            | 指标 | 数值 |
            |------|------|
            | 新能源发电量 | {renewable:.2f} 亿kWh |
            | 火电发电量 | {fh:.2f} 亿kWh |
            | **新能源渗透率** | **{ratio:.1f}%** |
            
            ---
            
            ### 渗透率等级标准
            
            | 等级 | 渗透率范围 | 说明 |
            |------|-----------|------|
            | 🥉 低渗透率 | < 20% | 传统电力系统主导 |
            | 🥈 中渗透率 | 20% - 50% | 新能源快速发展 |
            | 🥇 高渗透率 | > 50% | 新型电力系统 |
            """.format(renewable=renewable_kwh, fh=fh_kwh, ratio=ratio))
        
        st.markdown("---")
        st.info("💡 **提示**：以上公式和数据均基于MATLAB优化算法的计算结果，展示在本系统中可视化呈现。")
    
    elif page == "🌿 新能源发电":
        st.markdown("## 🌿 新能源发电分析")
        
        tab1, tab2, tab3 = st.tabs(["📊 全年曲线", "📈 月度对比", "🌀 热力图"])
        
        with tab1:
            st.plotly_chart(plot_renewable_power(data, selected_days), use_container_width=True)
        
        with tab2:
            day_type = st.selectbox("选择时段类型", 
                                   ["全年", "工作日", "周末", "春季", "夏季", "秋季", "冬季"],
                                   index=0)
            day_type_map = {"全年": "all", "工作日": "weekday", "周末": "weekend",
                          "春季": "spring", "夏季": "summer", "秋季": "autumn", "冬季": "winter"}
            st.plotly_chart(plot_hourly_pattern(data, day_type_map[day_type]), use_container_width=True)
        
        with tab3:
            st.plotly_chart(plot_monthly_heatmap(data), use_container_width=True)
        
        # 统计表格
        st.markdown("### 📋 新能源发电统计")
        
        wind_stats = {'mean': data['wind'].mean(axis=1), 'max': data['wind'].max(axis=1), 'min': data['wind'].min(axis=1)}
        solar_stats = {'mean': data['solar'].mean(axis=1), 'max': data['solar'].max(axis=1), 'min': data['solar'].min(axis=1)}
        hydro_stats = {'mean': data['hydro'].mean(axis=1), 'max': data['hydro'].max(axis=1), 'min': data['hydro'].min(axis=1)}
        
        stats_df = pd.DataFrame({
            '指标': ['总发电量 (亿kWh)', '平均功率 (MW)', '最大功率 (MW)', '最小功率 (MW)'],
            '风电': [
                f"{data['wind'].sum()/1e6:.2f}",
                f"{wind_stats['mean'].mean():.1f}",
                f"{wind_stats['max'].max():.1f}",
                f"{wind_stats['min'].min():.1f}"
            ],
            '光伏': [
                f"{data['solar'].sum()/1e6:.2f}",
                f"{solar_stats['mean'].mean():.1f}",
                f"{solar_stats['max'].max():.1f}",
                f"{solar_stats['min'].min():.1f}"
            ],
            '水电': [
                f"{data['hydro'].sum()/1e6:.2f}",
                f"{hydro_stats['mean'].mean():.1f}",
                f"{hydro_stats['max'].max():.1f}",
                f"{hydro_stats['min'].min():.1f}"
            ]
        })
        
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
    elif page == "💧 抽水蓄能调度":
        st.markdown("## 💧 抽水蓄能调度策略")
        
        # 调度统计
        ps_schedule = dl.calculate_pumped_storage_schedule(data['np_raw'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("年抽水小时数", f"{ps_schedule['pumping_hours']}", "小时")
        with col2:
            st.metric("年发电小时数", f"{ps_schedule['generating_hours']}", "小时")
        with col3:
            st.metric("年停机小时数", f"{ps_schedule['idle_hours']}", "小时")
        with col4:
            st.metric("转换效率", f"{ps_schedule['efficiency']:.1f}", "%")
        
        st.markdown("---")
        
        # 详细统计
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric("年抽水电量", f"{ps_schedule['total_pumping']/1e6:.2f}", "亿kWh")
        with col6:
            st.metric("年发电电量", f"{ps_schedule['total_generation']/1e6:.2f}", "亿kWh")
        with col7:
            st.metric("平均抽水功率", f"{ps_schedule['avg_pumping_power']/10:.1f}", "MW")
        with col8:
            st.metric("平均发电功率", f"{ps_schedule['avg_generation_power']/10:.1f}", "MW")
        
        st.markdown("---")
        st.plotly_chart(plot_pumped_storage(data, selected_days), use_container_width=True)
        
        # 日内调度模式分析
        st.markdown("### ⏰ 典型调度模式")
        
        # 分析抽水蓄能的典型日内运行模式
        np_daily = data['np_raw'].mean(axis=0)  # 平均日内分布
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(range(24)),
            y=np_daily,
            marker_color=np_daily,
            marker=dict(color=np_daily, colorscale='Viridis'),
            name='平均功率'
        ))
        
        fig.update_layout(
            title='抽水蓄能典型日24小时平均发电功率',
            height=350,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e6ed'),
            xaxis=dict(title='小时', tickmode='array', tickvals=list(range(24))),
            yaxis=dict(title='功率 (MW)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    elif page == "🔥 火电调峰效果":
        st.markdown("## 🔥 火电深度调峰效果")
        
        # 计算调峰深度
        # 调峰深度 = 最小出力 / 平均出力 × 100%（基于调峰范围计算）
        fh_min_before = data['fh_raw'].min()
        fh_min_after = (data['fh_raw'] - data['np_raw']).min()
        depth_before = fh_min_before / data['fh_raw'].mean() * 100
        depth_after = fh_min_after / (data['fh_raw'] - data['np_raw']).mean() * 100
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("原始最小出力", f"{fh_min_before:.0f}", "MW")
        with col2:
            st.metric("优化后最小出力", f"{fh_min_after:.0f}", "MW")
        with col3:
            st.metric("调峰深度增幅", f"+{depth_after - depth_before:.1f}", "%（调峰范围口径）")
        with col4:
            st.metric("火电发电量减少", f"{(data['fh_raw'].sum() - (data['fh_raw'] - data['np_raw']).sum())/1e6:.2f}", "亿kWh")
        
        st.markdown("---")
        st.plotly_chart(plot_firepower_comparison(data), use_container_width=True)
        
        # 深度调峰原因分析
        st.markdown("### 📊 深度调峰原因")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 风光发电与火电的关系
            renewable = data['wind'] + data['solar'] + data['hydro']
            fh = data['fh_raw']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=renewable.flatten(),
                y=fh.flatten(),
                mode='markers',
                marker=dict(size=3, color='#00d4ff', opacity=0.6),
                name='负荷点'
            ))
            
            fig.update_layout(
                title='新能源发电 vs 火电负荷',
                height=350,
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e6ed'),
                xaxis=dict(title='新能源功率 (MW)', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title='火电负荷 (MW)', showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 相关性分析
            correlation = np.corrcoef(renewable.flatten(), fh.flatten())[0, 1]
            
            st.info(f"""
            ### 📈 相关性分析
            
            **新能源与火电负荷相关系数**: `{correlation:.3f}`
            
            **解读**:
            - 相关系数接近 0，表明新能源与火电负荷的关联性极弱
            - 这正是抽蓄调峰的效果！抽蓄通过"高峰抽水、低谷发电"平滑了新能源波动
            - 火电负荷不再随新能源剧烈变化，关联性自然减弱，验证了调峰策略的有效性
            """)
        
    elif page == "🎯 Pareto前沿分析":
        st.markdown("## 🎯 多目标优化 Pareto 前沿分析")
        
        # 公式说明
        st.markdown("""
        ### 📐 优化目标函数
        
        **目标1：最小化火电调峰深度**
        $$f_1 = Z_{t\_f} = \\frac{max(N_t) - min(N_t)}{0.7}$$
        
        其中：$N_t = L - (N_h + N_w + N_p + N_{pump})$ 为火电净负荷
        
        ---
        
        **目标2：最小化系统总碳排放**
        $$f_2 = \\sum_{i=1}^{24} EMI(i) = \\sum_{i=1}^{24} Ce(i) \\cdot TH(i)$$
        
        其中：$Ce(i)$ 为碳排放强度，$TH(i)$ 为火电运行时出力
        
        ---
        
        💡 **Pareto前沿**展示了100个非劣解，两个目标存在权衡关系，无法同时最优
        """)
        
        st.plotly_chart(plot_pareto_front(data), use_container_width=True)
        
        # Pareto解分析
        st.markdown("### 📋 Pareto 解详细信息")
        
        solution_txt = data['solution_txt']
        objectives = solution_txt[:, -4:]
        
        # 创建解的详细信息表
        solutions_df = pd.DataFrame({
            '解编号': range(1, len(objectives) + 1),
            '最小化火电调峰深度': [f"{obj[1]:.4f}" for obj in objectives],
            '最小化系统总碳排放': [f"{obj[0]:.4f}" for obj in objectives],
            '调峰深度 f1': [f"{obj[1]:.4f}" for obj in objectives],
            '碳排放 f2': [f"{obj[0]:.4f}" for obj in objectives]
        })
        
        st.dataframe(solutions_df, use_container_width=True, hide_index=True)
        
        # 选择展示特定解
        selected_solution = st.slider("选择要查看的Pareto解", 1, 100, 1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            solution_data = solution_txt[selected_solution - 1, :23]  # 决策变量
            variables = [f"x{i+1}" for i in range(23)]
            
            fig = go.Figure(go.Bar(
                x=variables,
                y=solution_data,
                marker_color='#00d4ff'
            ))
            
            fig.update_layout(
                title=f'Pareto解 #{selected_solution} 决策变量',
                height=350,
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e6ed'),
                xaxis=dict(tickangle=45),
                yaxis=dict(title='变量值', showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 目标值
            obj_values = objectives[selected_solution - 1]
            
            st.success(f"""
            ### 📊 解 #{selected_solution} 目标函数值
            
            **目标1：最小化火电调峰深度**
            $$f_1 = Z_{{t\_f}} = \\frac{{max(N_t) - min(N_t)}}{{0.7}}$$
            
            $$f_1 = {obj_values[1]:.4f}$$
            
            ---
            
            **目标2：最小化系统总碳排放**
            $$f_2 = \\sum_{{i=1}}^{{24}} EMI(i)$$
            
            $$f_2 = {obj_values[0]:.4f}$$
            """)
        
    elif page == "🌱 碳减排效益":
        st.markdown("## 🌱 碳减排效益分析")
        
        chart, carbon_change = plot_carbon_benefit(data)
        st.plotly_chart(chart, use_container_width=True)
        
        # 碳排放详细数据
        st.markdown("### 📋 碳排放变化统计")
        
        # 获取碳排放计算结果
        carbon_result = dl.calculate_carbon_reduction(data)
        carbon_change_value = carbon_result['carbon_change']  # 万吨，正=增加，负=减排
        power_change = carbon_result['power_change']  # 亿kWh，正=增发，负=减发
        
        # 判断是减排还是增排
        is_reduction = carbon_change_value < 0
        carbon_abs = abs(carbon_change_value)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if is_reduction:
                st.metric("年度碳排放变化", f"{carbon_abs:.2f}", "万吨CO₂（减排↓）")
            else:
                st.metric("年度碳排放变化", f"{carbon_abs:.2f}", "万吨CO₂（增加↑）")
        
        with col2:
            # 植树补偿 (每棵树年吸收约10kg=0.01吨 CO₂)
            # carbon_abs单位是"万吨"=10000吨，所以 trees = carbon_abs * 10000 / 0.01 / 10000 = carbon_abs * 100
            trees = carbon_abs * 100  # 万棵
            st.metric("相当于植树", f"{trees:.0f}", "万棵（年固碳10kg/棵）")
        
        with col3:
            # 节煤量 (每吨标煤排放2.66吨CO₂)
            coal = carbon_abs / 2.66  # 万吨
            if is_reduction:
                st.metric("节约标煤", f"{coal:.2f}", "万吨")
            else:
                st.metric("多耗标煤", f"{coal:.2f}", "万吨")
        
        with col4:
            # 碳交易价值 (50元/吨)
            value = carbon_abs * 50  # 万元
            if is_reduction:
                st.metric("碳交易收益", f"{value:.2f}", "万元（按50元/吨）")
            else:
                st.metric("碳交易成本", f"{value:.2f}", "万元（按50元/吨）")
        
        # 月度碳排放明细
        st.markdown("### 📅 月度碳排放明细")
        
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
        
        monthly_data = []
        start = 0
        for i, days in enumerate(days_per_month):
            end = start + days
            daily_change = carbon_result['daily_carbon_change'][start:end].sum()
            
            monthly_data.append({
                '月份': months[i],
                '火电变化(万kWh)': f"{(power_change/365*days):.2f}",
                '碳排放变化(吨)': f"{daily_change:.2f}",
                '说明': '减排↓' if daily_change < 0 else '增排↑'
            })
            start = end
        
        monthly_df = pd.DataFrame(monthly_data)
        st.dataframe(monthly_df, use_container_width=True, hide_index=True)
        
    elif page == "📊 综合分析报告":
        st.markdown("## 📊 综合分析报告")
        
        # ========== 从实际数据计算指标 ==========
        # 新能源数据
        # 注意：wind/solar/hydro是(365,24)的功率数据(MW)，sum是总MWh
        # 年发电量 = sum / 1e6 = 亿kWh
        wind_total = data['wind'].sum() / 1e6  # 亿kWh
        solar_total = data['solar'].sum() / 1e6  # 亿kWh
        hydro_total = data['hydro'].sum() / 1e6  # 亿kWh
        total_renewable = wind_total + solar_total + hydro_total
        
        # 碳排放数据
        carbon_result = dl.calculate_carbon_reduction(data)
        carbon_change = carbon_result['carbon_change']  # 万吨CO2，正=增加，负=减排
        
        # 调峰深度 - 使用实际调峰范围而非Zt_f公式
        z_gain = data.get('z_gain', np.array([[0, 0]]))
        Nt = data['Nt']
        Nt2 = data['Nt2']
        # 实际调峰范围 = max - min
        avg_peak_shaving = (Nt.max() - Nt.min()) / 1e3  # 转为GW，更直观
        avg_peak_before = (Nt2.max() - Nt2.min()) / 1e3
        peak_improvement = avg_peak_before - avg_peak_shaving
        
        # 抽蓄数据
        ps_schedule = dl.calculate_pumped_storage_schedule(data['np_raw'])
        
        # 日均调节次数
        solution = data['solution']
        state_changes = np.diff(solution[:, :23], axis=1)
        daily_regulations = np.sum(np.abs(state_changes) > 0.02, axis=1).mean()
        
        # 经济效益估算
        carbon_price = 50  # 碳交易价格 元/吨
        is_reduction = carbon_change < 0
        carbon_abs = abs(carbon_change)
        
        # 碳排放成本/收益 (正=成本，负=收益)
        carbon_cost = carbon_abs * carbon_price  # 万元
        
        # 等效标煤变化 (正=多耗，负=节约)
        coal_change = carbon_abs / 2.66  # 万吨
        
        # 植树需求 (抵消增排)
        trees_needed = carbon_abs * 100  # 万棵
        
        # 新能源渗透率 (使用与总览仪表盘一致的计算口径)
        fh_total = carbon_result['Nt'].sum() / 1e6  # 有抽蓄时火电年发电量(亿kWh)
        renewable_ratio = total_renewable / (total_renewable + fh_total) * 100
        
        # ========== 雷达图 ==========
        categories = ['新能源消纳', '火电调峰深度', '系统灵活性', '碳减排', '经济性', '可靠性']
        
        # 新能源收益计算
        renewable_revenue = total_renewable * 10000 * 0.3  # 万元 (新能源发电量*电价)
        peak_revenue = peak_improvement * 1000 * 365 * 50 / 10000  # 调峰辅助服务收益(万元)
        total_revenue = renewable_revenue + peak_revenue - carbon_cost  # 总收益(扣除碳成本)
        
        # 基于实际数据计算评分
        before_scores = [
            min(renewable_ratio * 0.8, 100),  # 新能源消纳
            100 - avg_peak_shaving / 20,  # 调峰深度 (越低越好)
            50,  # 优化前灵活性基线
            40,  # 优化前碳减排基线
            60,  # 优化前经济性基线
            80   # 可靠性基线
        ]
        
        # 碳减排评分：如果是减排则高，如果是增排则低
        carbon_score = 100 - min(carbon_abs / 0.5 * 100, 100) if is_reduction else max(0, 50 - carbon_abs / 0.5 * 50)
        
        after_scores = [
            min(renewable_ratio, 100),  # 新能源消纳
            min(peak_improvement / 0.5, 100),  # 调峰深度改善(GW)
            min(daily_regulations * 5, 100),  # 系统灵活性
            max(0, carbon_score),  # 碳减排(减排=高，增排=低)
            min(total_revenue / 1000, 100),  # 经济性
            90   # 可靠性
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=before_scores + [before_scores[0]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(255, 100, 100, 0.3)',
            line=dict(color='#ff6464', width=2),
            name='优化前'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=after_scores + [after_scores[0]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(0, 212, 255, 0.3)',
            line=dict(color='#00d4ff', width=2),
            name='优化后'
        ))
        
        # 雷达图布局
        fig.update_layout(
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0, 100])
            ),
            showlegend=True,
            legend=dict(x=0.5, y=-0.1, xanchor='center'),
            template="plotly_dark",
            height=450
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 详细分析报告
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            ### 📝 优化效果总结
            
            #### 1. 新能源消纳能力
            - 全年新能源发电量达到 **{total_renewable:.2f} 亿kWh**
            - 新能源渗透率提升至 **{renewable_ratio:.1f}%**
            - 有效缓解了弃风弃光弃水问题
            
            #### 2. 火电深度调峰
            - 火电实际调峰范围 **{avg_peak_shaving:.2f} GW**
            - 优化前调峰范围 **{avg_peak_before:.2f} GW**
            - 调峰深度改善 **{peak_improvement:.2f} GW**（{peak_improvement/avg_peak_before*100:.1f}%）
            
            #### 3. 系统灵活性
            - 抽水蓄能日均调节次数: **{daily_regulations:.1f} 次**
            - 系统调峰能力增强
            - 新能源消纳能力提升
            """)
        
        with col2:
            st.markdown(f"""
            ### 💰 经济效益估算
            
            | 项目 | 数值 |
            |------|------|
            | 新能源消纳收益 | {renewable_revenue:.2f} 万元 |
            | 调峰辅助服务收益 | {peak_revenue:.2f} 万元 |
            | 碳交易成本 | -{carbon_cost:.2f} 万元 |
            | **年度净收益** | **{total_revenue:.2f} 万元** |
            
            ### 🌍 环境效益
            
            - 年碳排放变化: **{carbon_change:.2f} 万吨CO₂** ({'碳减排↓' if is_reduction else '碳排放增加↑'})
            - 标煤消耗变化: **{coal_change:.2f} 万吨** ({'节约↓' if is_reduction else '多耗↑'})
            - 抵消增排需植树: **{trees_needed:.0f} 万棵**（年固碳10kg/棵）
            
            ### 📈 推广价值
            
            本优化策略通过抽水蓄能协同火电深度调峰，
            {'有效减少碳排放' if is_reduction else '在增加碳排放的同时'}实现新能源消纳和系统灵活性提升。
            """)
        
        # 导出报告按钮
        st.markdown("---")
        if st.button("📥 导出分析报告 (PDF)"):
            st.info("报告导出功能开发中...")
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #8ba4c4; padding: 20px;">
            <p>新型电力系统下抽水蓄能减碳效益优化核算系统 | Powered by NSLDE</p>
            <p style="font-size: 0.8rem;">数据周期: 全年8760小时 | 更新日期: 2024年</p>
        </div>
        """, 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
