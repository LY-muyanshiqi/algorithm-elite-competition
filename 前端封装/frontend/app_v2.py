"""
火电深度调峰+抽水蓄能减碳效益优化系统 - 优化版 v2.1
新增可视化和分析功能模块

功能包含：
1. 可视化模块：桑基图、3D水库可视化、能量平衡图、Pareto前沿3D图、碳减排热力图、月度对比图、能源流动动画
2. 分析模块：敏感性分析、情景模拟、决策建议、统计分析、趋势分析
"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
import os
from typing import Dict, Any
import sys

# 页面配置 - 必须是第一个Streamlit命令
st.set_page_config(
    page_title="火电深度调峰+抽水蓄能优化系统",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入自定义模块
use_optimized_module = True
try:
    import data_loader_optimized as dl
    import visualization as vis
    import analysis as ana
except ImportError:
    use_optimized_module = False
    import data_loader as dl

# 增强的CSS样式
st.markdown("""
<style>
    /* 主背景 - 渐变效果 */
    .main {
        background: linear-gradient(135deg, #0a1628 0%, #1a2f4b 50%, #0d1f3c 100%);
        min-height: 100vh;
    }
    
    /* 卡片样式 - 增强阴影和动画 */
    .metric-card {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 150, 255, 0.08) 100%);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.1);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 212, 255, 0.2);
        border-color: rgba(0, 212, 255, 0.5);
    }
    
    /* 标题样式 */
    .main-title {
        background: linear-gradient(90deg, #00d4ff, #0096ff, #00d4ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 3s linear infinite;
    }
    
    @keyframes shine {
        0% { background-position: 0% center; }
        100% { background-position: 200% center; }
    }
    
    /* 按钮样式 */
    .stButton>button {
        background: linear-gradient(135deg, #00d4ff 0%, #0096ff 100%);
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        color: white;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
    }
    
    /* 侧边栏样式 */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 150, 255, 0.05) 100%);
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 212, 255, 0.1);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(0, 212, 255, 0.5);
        border-radius: 4px;
    }
    
    /* 进度条样式 */
    .stProgress > div > div {
        background: linear-gradient(90deg, #00d4ff, #0096ff);
    }
    
    /* 动画容器 */
    .animated-container {
        animation: fadeIn 0.5s ease-in-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

# 数据加载缓存
@st.cache_data(ttl=3600, show_spinner="正在加载数据...")
def get_all_data():
    return dl.load_all_data()

# 数据导出功能
def export_to_csv(data, filename="data_export.csv"):
    try:
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = data
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="stButton">📥 下载CSV文件</a>'
        return href
    except Exception as e:
        st.error(f"导出失败: {str(e)}")
        return None

# 图表下载功能
def download_plotly_figure(fig, filename="chart.png", width=1200, height=600):
    try:
        img_bytes = fig.to_image(format="png", width=width, height=height)
        return img_bytes
    except Exception as e:
        st.warning(f"图表导出需要安装kaleido: pip install kaleido")
        return None

# 主页面功能
def show_overview(data):
    """显示总览页面"""
    st.title("📊 系统总览")
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    # 计算关键指标
    np_raw = data['np_raw']
    pump_hours = int((np_raw < 0).sum())
    gen_hours = int((np_raw > 0).sum())
    efficiency = dl.calculate_pumped_storage_schedule(np_raw)['efficiency']
    
    carbon_result = dl.calculate_carbon_reduction(data)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🌍 碳减排量", f"{carbon_result['carbon_change']:.2f}万吨")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("💧 抽水小时数", f"{pump_hours}小时")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("⚡ 发电小时数", f"{gen_hours}小时")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🔄 抽发效率", f"{efficiency:.2f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 月度趋势图
    st.subheader("📈 月度能源产出趋势")
    fig = vis.create_interactive_comparison_chart(data)
    st.plotly_chart(fig, use_container_width=True)
    
    # 导出按钮
    if st.button("📥 导出总览数据"):
        overview_data = {
            '碳减排量(万吨)': carbon_result['carbon_change'],
            '抽水小时数': pump_hours,
            '发电小时数': gen_hours,
            '抽发效率(%)': efficiency
        }
        st.markdown(export_to_csv(overview_data, "系统总览数据.csv"), unsafe_allow_html=True)

def show_new_energy(data):
    """显示新能源数据页面"""
    st.title("☀️ 新能源数据")
    
    # 选择日期
    day_index = st.slider("选择日期", 0, 364, 0)
    
    # 当日数据
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🌬️ 当日风电", f"{data['wind'][day_index].sum():.1f} MWh")
    
    with col2:
        st.metric("☀️ 当日光伏", f"{data['solar'][day_index].sum():.1f} MWh")
    
    with col3:
        st.metric("💧 当日水电", f"{data['hydro'][day_index].sum():.1f} MWh")
    
    # 能量平衡图
    st.subheader("⚡ 当日能量平衡")
    fig = vis.create_energy_balance_chart(data, day_index)
    st.plotly_chart(fig, use_container_width=True)
    
    # 导出按钮
    if st.button("📥 导出新能源数据"):
        day_data = pd.DataFrame({
            '时间': np.arange(24),
            '风电(MW)': data['wind'][day_index],
            '光伏(MW)': data['solar'][day_index],
            '水电(MW)': data['hydro'][day_index]
        })
        st.markdown(export_to_csv(day_data, f"新能源数据_第{day_index+1}天.csv"), unsafe_allow_html=True)

def show_pareto(data):
    """显示Pareto解集页面"""
    st.title("📈 Pareto最优解集")
    
    # 3D散点图
    st.subheader("🎯 Pareto前沿三维分布")
    fig = vis.create_pareto_3d_scatter(data)
    st.plotly_chart(fig, use_container_width=True)
    
    # 目标函数值分布
    st.subheader("📊 目标函数值分布")
    z_gain = data['z_gain']
    
    fig2 = make_subplots(rows=1, cols=2, subplot_titles=('目标函数1', '目标函数2'))
    fig2.add_trace(go.Histogram(x=z_gain[:, 0], name='目标1', marker_color='rgba(0, 212, 255, 0.8)'), row=1, col=1)
    fig2.add_trace(go.Histogram(x=z_gain[:, 1], name='目标2', marker_color='rgba(0, 255, 128, 0.8)'), row=1, col=2)
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

def show_pumped_storage(data):
    """显示抽水蓄能调度页面"""
    st.title("🏭 抽水蓄能调度")
    
    # 选择日期
    day_index = st.slider("选择日期", 0, 364, 0)
    
    # 桑基图
    st.subheader("🔄 能量流向桑基图")
    fig_sankey = vis.create_sankey_diagram(data, day_index)
    st.plotly_chart(fig_sankey, use_container_width=True)
    
    # 3D水库可视化
    st.subheader("💧 水库状态3D可视化")
    fig_3d = vis.create_3d_reservoir_visualization(data, day_index)
    st.plotly_chart(fig_3d, use_container_width=True)
    
    # 调度策略统计
    st.subheader("📋 调度策略统计")
    ps_schedule = dl.calculate_pumped_storage_schedule(data['np_raw'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⚡ 发电小时", f"{ps_schedule['generating_hours']}小时")
    with col2:
        st.metric("💧 抽水小时", f"{ps_schedule['pumping_hours']}小时")
    with col3:
        st.metric("⏸️ 停机小时", f"{ps_schedule['idle_hours']}小时")
    with col4:
        st.metric("🔄 综合效率", f"{ps_schedule['efficiency']:.2f}%")

def show_carbon(data):
    """显示碳减排分析页面"""
    st.title("🌍 碳减排分析")
    
    # 碳减排热力图
    st.subheader("🔥 全年碳减排热力图")
    fig_heatmap = vis.create_carbon_reduction_heatmap(data)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # 碳减排结果
    carbon_result = dl.calculate_carbon_reduction(data)
    
    st.subheader("📊 碳减排统计")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("🌱 年碳减排量", f"{carbon_result['carbon_change']:.2f}万吨")
    
    with col2:
        st.metric("📈 火电变化", f"{carbon_result['power_change']:.2f}亿kWh")
    
    # 月度碳减排趋势
    st.subheader("📈 月度碳减排趋势")
    monthly_carbon = np.array_split(carbon_result['daily_carbon_change'], 12)
    monthly_avg = [np.mean(m) for m in monthly_carbon]
    
    fig_monthly = go.Figure(data=[go.Bar(
        x=['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
        y=monthly_avg,
        marker_color='rgba(0, 212, 255, 0.8)'
    )])
    fig_monthly.update_layout(title='月度碳减排量', xaxis_title='月份', yaxis_title='碳减排(万吨)')
    st.plotly_chart(fig_monthly, use_container_width=True)

def show_visualization(data):
    """显示高级可视化页面"""
    st.title("🎨 高级可视化")
    
    # 可视化功能选择
    vis_options = vis.get_visualization_list()
    selected_vis = st.selectbox("选择可视化功能", vis_options)
    
    # 日期选择（部分功能需要）
    day_index = st.slider("选择日期", 0, 364, 0)
    
    # 根据选择显示相应的可视化
    if selected_vis == '桑基图 - 能量流向':
        fig = vis.create_sankey_diagram(data, day_index)
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_vis == '3D水库可视化':
        fig = vis.create_3d_reservoir_visualization(data, day_index)
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_vis == '能量平衡图':
        fig = vis.create_energy_balance_chart(data, day_index)
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_vis == 'Pareto前沿3D图':
        fig = vis.create_pareto_3d_scatter(data)
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_vis == '碳减排热力图':
        fig = vis.create_carbon_reduction_heatmap(data)
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_vis == '月度对比图':
        fig = vis.create_interactive_comparison_chart(data)
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_vis == '能源流动动画':
        fig = vis.create_energy_flow_animation(data, day_index)
        st.plotly_chart(fig, use_container_width=True)
    
    # 下载按钮
    st.download_button(
        label="📥 下载图表",
        data=download_plotly_figure(fig, f"{selected_vis}.png"),
        file_name=f"{selected_vis}.png",
        mime="image/png"
    )

def show_analysis(data):
    """显示高级分析页面"""
    st.title("🧠 高级分析")
    
    # 分析功能选择
    analysis_options = ana.get_analysis_list()
    selected_analysis = st.selectbox("选择分析功能", analysis_options)
    
    if selected_analysis == '敏感性分析':
        # 参数选择
        param_options = ['efficiency', 'capacity', 'carbon_factor', 'price']
        param_labels = ['抽发效率', '装机容量', '碳排放系数', '电价']
        selected_param = st.selectbox("选择分析参数", param_labels, index=0)
        param_key = param_options[param_labels.index(selected_param)]
        
        # 执行分析
        results = ana.sensitivity_analysis(data, param_key)
        
        # 显示图表
        fig = ana.create_sensitivity_chart(results)
        st.plotly_chart(fig, use_container_width=True)
        
        # 结果解释
        st.subheader("📊 分析结果")
        st.write(f"基准值: {results['base_value']}{results['unit']}")
        st.write(f"分析范围: {results['test_values'][0]} - {results['test_values'][-1]}{results['unit']}")
    
    elif selected_analysis == '情景模拟':
        st.subheader("⚙️ 设置情景参数")
        
        # 参数滑块
        col1, col2, col3 = st.columns(3)
        
        with col1:
            wind_scale = st.slider("风电增长比例", 0.5, 2.0, 1.0, 0.1)
        
        with col2:
            solar_scale = st.slider("光伏增长比例", 0.5, 2.0, 1.0, 0.1)
        
        with col3:
            demand_scale = st.slider("负荷增长比例", 0.8, 1.5, 1.0, 0.1)
        
        # 执行模拟
        scenario_params = {
            'wind_scale': wind_scale,
            'solar_scale': solar_scale,
            'demand_scale': demand_scale
        }
        scenario_result = ana.scenario_simulation(data, scenario_params)
        
        # 基准情景
        base_stats = {
            'total_wind': np.sum(data['wind']),
            'total_solar': np.sum(data['solar']),
            'total_hydro': np.sum(data['hydro']),
            'total_pump_gen': np.sum(data['np_raw'][data['np_raw'] > 0]),
            'total_pump_con': np.sum(np.abs(data['np_raw'][data['np_raw'] < 0])),
            'total_thermal': np.sum(data['fh'])
        }
        
        # 显示对比图表
        fig = ana.create_scenario_comparison_chart(base_stats, scenario_result['stats'])
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示关键指标
        st.subheader("📈 情景指标对比")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("碳减排量", f"{scenario_result['stats']['carbon_reduction']:.2f}万吨")
        
        with col2:
            st.metric("抽水小时数", f"{scenario_result['stats']['pumping_hours']}小时")
    
    elif selected_analysis == '决策建议':
        # 生成建议
        recommendations = ana.generate_decision_recommendations(data)
        
        st.subheader("💡 决策建议")
        
        # 按优先级排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order[x['priority']])
        
        # 显示建议卡片
        for rec in recommendations:
            priority_color = {
                'high': 'rgba(255, 102, 102, 0.2)',
                'medium': 'rgba(255, 204, 102, 0.2)',
                'low': 'rgba(51, 204, 102, 0.2)'
            }
            
            priority_badge = {
                'high': '🔴 高优先级',
                'medium': '🟡 中优先级',
                'low': '🟢 低优先级'
            }
            
            st.markdown(f"""
            <div style='background: {priority_color[rec['priority']]}; border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 12px; padding: 16px; margin: 8px 0;'>
                <h4>{rec['title']} <span style='font-size:14px; margin-left:8px;'>{priority_badge[rec['priority']]}</span></h4>
                <p><strong>现状分析:</strong> {rec['description']}</p>
                <p><strong>建议措施:</strong> {rec['suggestion']}</p>
                <p><strong>预期效果:</strong> {rec['impact']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    elif selected_analysis == '统计分析':
        # 执行统计分析
        stats = ana.statistical_analysis(data)
        
        st.subheader("📊 年度统计")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总风电(MWh)", f"{stats['annual_stats']['total_wind']:.1f}")
        
        with col2:
            st.metric("总光伏(MWh)", f"{stats['annual_stats']['total_solar']:.1f}")
        
        with col3:
            st.metric("总水电(MWh)", f"{stats['annual_stats']['total_hydro']:.1f}")
        
        with col4:
            st.metric("总火电(MWh)", f"{stats['annual_stats']['total_thermal']:.1f}")
        
        st.subheader("📈 相关性分析")
        corr_df = pd.DataFrame({
            '相关系数': [
                stats['correlations']['wind_solar'],
                stats['correlations']['wind_load'],
                stats['correlations']['solar_load'],
                stats['correlations']['pump_wind'],
                stats['correlations']['pump_solar']
            ]
        }, index=['风电-光伏', '风电-负荷', '光伏-负荷', '抽蓄-风电', '抽蓄-光伏'])
        st.dataframe(corr_df)
    
    elif selected_analysis == '趋势分析':
        # 指标选择
        metric_options = ['carbon_reduction', 'pumping_hours', 'renewable_ratio']
        metric_labels = ['碳减排量', '抽水小时数', '新能源占比']
        selected_metric = st.selectbox("选择分析指标", metric_labels, index=0)
        metric_key = metric_options[metric_labels.index(selected_metric)]
        
        # 执行趋势分析
        trend_result = ana.trend_analysis(data, metric_key)
        
        # 创建趋势图表
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_result['days'],
            y=trend_result['daily_values'],
            name='每日值',
            mode='lines',
            line=dict(width=1, color='rgba(0, 212, 255, 0.5)')
        ))
        fig.add_trace(go.Scatter(
            x=trend_result['days'],
            y=trend_result['moving_average'],
            name='7日移动平均',
            mode='lines',
            line=dict(width=2, color='rgba(0, 255, 128, 0.8)')
        ))
        fig.add_trace(go.Scatter(
            x=trend_result['days'],
            y=trend_result['trend_line'],
            name='趋势线',
            mode='lines',
            line=dict(width=2, color='rgba(255, 102, 102, 0.8)', dash='dash')
        ))
        
        fig.update_layout(
            title=f"{trend_result['metric_name']}趋势分析",
            xaxis_title='日期',
            yaxis_title=f"{trend_result['metric_name']}({trend_result['unit']})",
            width=900,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 趋势说明
        trend_direction = "上升" if trend_result['trend_slope'] > 0 else "下降" if trend_result['trend_slope'] < 0 else "平稳"
        st.write(f"📈 趋势方向: {trend_direction}，斜率: {trend_result['trend_slope']:.6f}")

def main():
    """主应用入口"""
    try:
        # 加载数据
        data = get_all_data()
        
        # 检查模块加载状态
        global use_optimized_module
        if not use_optimized_module:
            st.warning("⚠️ 使用原始数据加载模块，部分高级功能可能不可用")
        
        # 侧边栏导航
        st.sidebar.title("⚡ 系统导航")
        pages = [
            "📊 系统总览",
            "☀️ 新能源数据",
            "📈 Pareto解集",
            "🏭 抽水蓄能调度",
            "🌍 碳减排分析",
            "🎨 高级可视化",
            "🧠 高级分析"
        ]
        selected_page = st.sidebar.selectbox("选择页面", pages)
        
        # 帮助信息
        st.sidebar.markdown("---")
        st.sidebar.subheader("❓ 使用帮助")
        st.sidebar.info("""
        - 使用侧边栏导航不同功能模块
        - 点击图表可查看详细数据
        - 支持导出CSV和图表图片
        - 高级可视化和分析模块提供深度分析功能
        """)
        
        # 根据选择显示页面
        if selected_page == "📊 系统总览":
            show_overview(data)
        
        elif selected_page == "☀️ 新能源数据":
            show_new_energy(data)
        
        elif selected_page == "📈 Pareto解集":
            show_pareto(data)
        
        elif selected_page == "🏭 抽水蓄能调度":
            show_pumped_storage(data)
        
        elif selected_page == "🌍 碳减排分析":
            show_carbon(data)
        
        elif selected_page == "🎨 高级可视化":
            show_visualization(data)
        
        elif selected_page == "🧠 高级分析":
            show_analysis(data)
    
    except FileNotFoundError as e:
        st.error(f"数据文件未找到: {str(e)}")
        st.info("请确保数据文件位于正确的目录中。")
    
    except Exception as e:
        st.error(f"系统运行出错: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()
