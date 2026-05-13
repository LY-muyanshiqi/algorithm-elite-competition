"""
可视化模块 - 高级数据可视化功能
火电深度调峰+抽水蓄能减碳效益优化项目

功能包含：
1. 桑基图 - 能量流向可视化
2. 3D可视化 - 水库状态变化
3. 动态流程图 - 能量平衡图
4. 交互式图表 - 增强用户交互体验
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional, List


def create_sankey_diagram(data: Dict[str, Any], day_index: int = 0) -> go.Figure:
    """
    创建桑基图，展示能量流向和转换效率
    
    Args:
        data: 数据字典
        day_index: 选择第几天的数据（0-364）
    
    Returns:
        plotly.graph_objects.Figure: 桑基图对象
    """
    day_data = {
        'wind': data['wind'][day_index],
        'solar': data['solar'][day_index],
        'hydro': data['hydro'][day_index],
        'fh': data['fh'][day_index],  # 火电负荷
        'npump': data['np_raw'][day_index]
    }
    
    # 节点定义
    labels = [
        '风电', '光伏', '常规水电', '抽水蓄能(发电)', '抽水蓄能(抽水)',
        '火电', '电网负荷', '弃风弃光', '净负荷'
    ]
    
    # 流量计算（取平均值）
    wind_avg = np.mean(day_data['wind'])
    solar_avg = np.mean(day_data['solar'])
    hydro_avg = np.mean(day_data['hydro'])
    npump_avg = np.mean(day_data['npump'])
    
    # 抽水蓄能分解
    pump_generation = np.max([0, npump_avg])  # 发电
    pump_consumption = np.max([0, -npump_avg])  # 抽水消耗
    
    # 计算净负荷和火电
    renewable_total = wind_avg + solar_avg + hydro_avg
    grid_load = np.mean(day_data['fh']) + pump_consumption
    
    # 假设弃风弃光比例
    curtailment_ratio = 0.1
    curtailment = renewable_total * curtailment_ratio
    renewable_used = renewable_total * (1 - curtailment_ratio)
    
    # 火电出力
    thermal_power = grid_load - renewable_used + pump_generation
    
    # 流量定义
    source = [0, 1, 2, 3, 4, 5, 6, 0, 1]  # 源节点索引
    target = [6, 6, 6, 6, 5, 6, 7, 8, 8]  # 目标节点索引
    value = [
        wind_avg * (1 - curtailment_ratio),  # 风电到电网
        solar_avg * (1 - curtailment_ratio),  # 光伏到电网
        hydro_avg,  # 水电到电网
        pump_generation,  # 抽蓄发电到电网
        pump_consumption,  # 抽蓄抽水消耗从火电
        thermal_power,  # 火电到电网
        renewable_used + thermal_power + pump_generation - grid_load,  # 净负荷
        wind_avg * curtailment_ratio,  # 弃风
        solar_avg * curtailment_ratio  # 弃光
    ]
    
    # 颜色定义
    colors = [
        'rgba(102, 204, 255, 0.8)',   # 风电 - 浅蓝色
        'rgba(255, 204, 102, 0.8)',   # 光伏 - 橙色
        'rgba(51, 204, 102, 0.8)',    # 水电 - 绿色
        'rgba(153, 102, 255, 0.8)',   # 抽蓄发电 - 紫色
        'rgba(255, 102, 153, 0.8)',   # 抽蓄抽水 - 粉色
        'rgba(255, 153, 102, 0.8)',   # 火电 - 橙红色
        'rgba(102, 153, 255, 0.8)',   # 电网负荷 - 蓝色
        'rgba(204, 204, 204, 0.8)',   # 弃风弃光 - 灰色
        'rgba(255, 255, 102, 0.8)'    # 净负荷 - 黄色
    ]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=labels,
            color=colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=['rgba(102, 204, 255, 0.5)',
                   'rgba(255, 204, 102, 0.5)',
                   'rgba(51, 204, 102, 0.5)',
                   'rgba(153, 102, 255, 0.5)',
                   'rgba(255, 102, 153, 0.5)',
                   'rgba(255, 153, 102, 0.5)',
                   'rgba(102, 153, 255, 0.5)',
                   'rgba(204, 204, 204, 0.5)',
                   'rgba(204, 204, 204, 0.5)']
        )
    )])
    
    fig.update_layout(
        title_text=f"⚡ 第{day_index+1}天能量流向桑基图",
        font_size=14,
        width=900,
        height=500,
        title_x=0.5
    )
    
    return fig


def create_3d_reservoir_visualization(data: Dict[str, Any], day_index: int = 0) -> go.Figure:
    """
    创建3D可视化，展示抽水蓄能水库状态变化
    
    Args:
        data: 数据字典
        day_index: 选择第几天的数据（0-364）
    
    Returns:
        plotly.graph_objects.Figure: 3D可视化对象
    """
    solution = data['solution']
    x = solution[day_index, :23]
    
    hours = np.arange(24)
    
    reservoir_level = np.zeros(25)
    reservoir_level[0] = 0.5
    reservoir_level[1:24] = x
    reservoir_level[24] = 0.5
    
    npump = data['np_raw'][day_index]
    
    theta = np.linspace(0, 2 * np.pi, 36)
    phi = np.linspace(0, np.pi, 18)
    theta, phi = np.meshgrid(theta, phi)
    
    fig = go.Figure()
    
    colorscale = [
        [0, 'rgba(50, 50, 50, 0.6)'],
        [0.3, 'rgba(70, 70, 70, 0.7)'],
        [0.5, 'rgba(90, 90, 90, 0.75)'],
        [0.7, 'rgba(110, 110, 110, 0.8)'],
        [1, 'rgba(130, 130, 130, 0.85)']
    ]
    
    for hour in range(24):
        level = reservoir_level[hour]
        radius = 1.2 + level * 0.5
        x_surface = radius * np.sin(phi) * np.cos(theta)
        y_surface = radius * np.sin(phi) * np.sin(theta)
        z_surface = (level * 2 - 1) * np.cos(phi)
        
        fig.add_trace(go.Surface(
            x=x_surface,
            y=y_surface,
            z=z_surface,
            colorscale=colorscale,
            opacity=0.85,
            name=f'{hour}:00',
            showscale=False,
            visible=False,
            contours=go.surface.Contours(
                z=dict(show=True, usecolormap=True, highlightcolor="#00ff00", project_z=True)
            ),
            lighting=go.surface.Lighting(
                ambient=0.4,
                diffuse=0.9,
                specular=0.4,
                roughness=0.4
            ),
            lightposition=dict(x=0, y=0, z=1.5)
        ))
    
    fig.data[0].visible = True
    
    steps = []
    for i in range(24):
        level = reservoir_level[i]
        status = "抽水" if npump[i] < 0 else ("发电" if npump[i] > 0 else "空闲")
        color = "#ff6b6b" if npump[i] < 0 else ("#51cf66" if npump[i] > 0 else "#ffd43b")
        
        step = dict(
            method='restyle',
            args=['visible', [False] * 24],
            label=f'{i}:00'
        )
        step['args'][1][i] = True
        
        annotation_text = f"⏰ {i}:00 | 水位: {level*100:.1f}% | 状态: {status} | 功率: {npump[i]:.2f}MW"
        step['args'][1].append(annotation_text)
        steps.append(step)
    
    sliders = [dict(
        active=0,
        currentvalue={'prefix': '时间: ', 'font': dict(size=14)},
        pad={'t': 60, 'b': 10},
        len=0.9,
        steps=steps,
        ticklen=5,
        minorticklen=3
    )]
    
    fig.add_trace(go.Bar(
        x=hours,
        y=npump,
        name='抽水蓄能功率',
        marker_color=['#51cf66' if v < 0 else '#ff6b6b' if v > 0 else '#ffd43b' for v in npump],
        opacity=0.8,
        xaxis='x2',
        yaxis='y2',
        hovertemplate='时间: %{x}时<br>功率: %{y:.2f}MW<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=hours,
        y=reservoir_level[0:24] * 100,
        name='水位百分比',
        line=dict(color='#339af0', width=3),
        fill='tozeroy',
        fillcolor='rgba(51, 154, 240, 0.2)',
        xaxis='x3',
        yaxis='y3',
        hovertemplate='时间: %{x}时<br>水位: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=f'🏊 第{day_index+1}天抽水蓄能水库状态3D动态可视化<br><sub style="color: gray; font-size: 12px;">🟢绿色=抽水(储水) | 🔴红色=发电 | 🟡黄色=空闲</sub>',
            x=0.5,
            font=dict(size=18)
        ),
        scene=dict(
            xaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False, backgroundcolor='rgba(0,0,0,0)'),
            yaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False, backgroundcolor='rgba(0,0,0,0)'),
            zaxis=dict(title='水位', titlefont=dict(size=14, color='white'), tickformat='.0%', tickfont=dict(color='white')),
            camera=dict(eye=dict(x=1.8, y=1.8, z=0.8), up=dict(x=0, y=0, z=1)),
            aspectmode='cube',
            bgcolor='rgba(0, 0, 0, 1)'
        ),
        sliders=sliders,
        width=1000,
        height=700,
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(30, 30, 30, 0.9)', font=dict(color='white')),
        xaxis2=dict(
            domain=[0.08, 0.45],
            anchor='y2',
            title='时间(小时)',
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            titlefont=dict(color='white'),
            tickfont=dict(color='white'),
            gridcolor='rgba(100, 100, 100, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis2=dict(
            domain=[0.55, 0.95],
            anchor='x2',
            title='功率(MW)',
            titlefont=dict(size=12, color='white'),
            tickfont=dict(color='white'),
            gridcolor='rgba(100, 100, 100, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        xaxis3=dict(
            domain=[0.55, 0.92],
            anchor='y3',
            title='时间(小时)',
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            showticklabels=False,
            titlefont=dict(color='white'),
            gridcolor='rgba(100, 100, 100, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis3=dict(
            domain=[0.55, 0.95],
            anchor='x3',
            title='水位(%)',
            titlefont=dict(size=12, color='white'),
            tickfont=dict(color='white'),
            range=[0, 100],
            gridcolor='rgba(100, 100, 100, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        margin=dict(l=50, r=50, t=100, b=150),
        paper_bgcolor='rgba(10, 10, 10, 1)',
        plot_bgcolor='rgba(20, 20, 20, 1)'
    )
    
    return fig


def create_energy_balance_chart(data: Dict[str, Any], day_index: int = 0) -> go.Figure:
    """
    创建动态能量平衡图
    
    Args:
        data: 数据字典
        day_index: 选择第几天的数据（0-364）
    
    Returns:
        plotly.graph_objects.Figure: 能量平衡图对象
    """
    hours = np.arange(24)
    
    # 各类电源出力
    wind = data['wind'][day_index]
    solar = data['solar'][day_index]
    hydro = data['hydro'][day_index]
    npump = data['np_raw'][day_index]
    fh = data['fh'][day_index]  # 火电负荷
    
    # 计算火电出力
    N = hydro + wind + solar
    Nt = fh - (N + npump)  # 有抽蓄
    Nt2 = fh - N  # 无抽蓄
    
    # 创建堆叠面积图
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('⚡ 各类电源出力', '🔥 火电负荷对比'),
        vertical_spacing=0.15
    )
    
    # 第一行：各类电源出力堆叠图
    fig.add_trace(go.Scatter(
        x=hours, y=wind, name='风电', stackgroup='one',
        line=dict(width=0), fill='tonexty',
        marker=dict(color='rgba(102, 204, 255, 0.8)')
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=hours, y=solar, name='光伏', stackgroup='one',
        line=dict(width=0), fill='tonexty',
        marker=dict(color='rgba(255, 204, 102, 0.8)')
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=hours, y=hydro, name='水电', stackgroup='one',
        line=dict(width=0), fill='tonexty',
        marker=dict(color='rgba(51, 204, 102, 0.8)')
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=hours, y=npump, name='抽水蓄能', stackgroup='one',
        line=dict(width=0), fill='tonexty',
        marker=dict(color='rgba(153, 102, 255, 0.8)')
    ), row=1, col=1)
    
    # 第二行：火电负荷对比
    fig.add_trace(go.Scatter(
        x=hours, y=Nt, name='有抽蓄火电',
        line=dict(width=3, color='rgba(255, 102, 102, 0.8)')
    ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=hours, y=Nt2, name='无抽蓄火电',
        line=dict(width=3, color='rgba(255, 153, 102, 0.6)', dash='dash')
    ), row=2, col=1)
    
    fig.update_layout(
        title=f"📊 第{day_index+1}天能量平衡图",
        width=900,
        height=600,
        title_x=0.5,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2),
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text='功率(MW)', row=1, col=1)
    fig.update_yaxes(title_text='火电负荷(MW)', row=2, col=1)
    fig.update_xaxes(title_text='时间(小时)', row=2, col=1)
    
    return fig


def create_pareto_3d_scatter(data: Dict[str, Any]) -> go.Figure:
    """
    创建Pareto前沿3D散点图
    
    Args:
        data: 数据字典
    
    Returns:
        plotly.graph_objects.Figure: 3D散点图对象
    """
    z_gain = data['z_gain']  # (365, 2)
    
    # 计算第三个维度：抽水蓄能利用小时数
    np_raw = data['np_raw']
    pump_hours = (np_raw < 0).sum(axis=1)  # 抽水小时数
    
    fig = go.Figure(data=[go.Scatter3d(
        x=z_gain[:, 0],
        y=z_gain[:, 1],
        z=pump_hours,
        mode='markers',
        marker=dict(
            size=8,
            color=pump_hours,
            colorscale='Viridis',
            opacity=0.8,
            colorbar_title='抽水小时数'
        ),
        text=[f'第{i+1}天: 抽水{pump_hours[i]}小时' for i in range(365)]
    )])
    
    fig.update_layout(
        title='📈 Pareto前沿三维分布图',
        scene=dict(
            xaxis_title='目标函数1',
            yaxis_title='目标函数2',
            zaxis_title='抽水小时数',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1))
        ),
        width=900,
        height=600,
        title_x=0.5
    )
    
    return fig


def create_carbon_reduction_heatmap(data: Dict[str, Any]) -> go.Figure:
    """
    创建碳减排热力图
    
    Args:
        data: 数据字典
    
    Returns:
        plotly.graph_objects.Figure: 热力图对象
    """
    # 计算每天的碳减排
    fh = data['fh']
    hydro = data['hydro']
    wind = data['wind']
    solar = data['solar']
    npump = data['np_raw']
    
    N = hydro + wind + solar
    Nt = fh - (N + npump)  # 有抽蓄
    Nt2 = fh - N  # 无抽蓄
    
    carbon_factor = 0.5  # 吨CO2/万kWh
    daily_carbon_change = (Nt.sum(axis=1) - Nt2.sum(axis=1)) / 1e6 * 1e4 * carbon_factor / 1e4
    
    # 转换为矩阵形式用于热力图（按月份分组）
    monthly_data = np.zeros((12, 31))
    monthly_data[:] = np.nan
    
    day_of_month = 0
    for month in range(12):
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
        for day in range(days_in_month):
            monthly_data[month, day] = daily_carbon_change[day_of_month]
            day_of_month += 1
    
    fig = px.imshow(
        monthly_data,
        labels=dict(x="日期", y="月份", color="碳减排(万吨)"),
        x=[f'{i+1}日' for i in range(31)],
        y=['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
        color_continuous_scale='RdBu_r',
        title='🌍 全年碳减排热力图'
    )
    
    fig.update_layout(
        width=1000,
        height=500,
        title_x=0.5
    )
    
    return fig


def create_interactive_comparison_chart(data: Dict[str, Any]) -> go.Figure:
    """
    创建交互式对比图表
    
    Args:
        data: 数据字典
    
    Returns:
        plotly.graph_objects.Figure: 对比图表对象
    """
    # 计算月度统计数据
    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    monthly_wind = []
    monthly_solar = []
    monthly_hydro = []
    monthly_pump_generation = []
    monthly_pump_consumption = []
    
    day_idx = 0
    for dim in days_in_month:
        month_data = data['np_raw'][day_idx:day_idx+dim]
        monthly_pump_generation.append(np.sum(month_data[month_data > 0]))
        monthly_pump_consumption.append(np.sum(np.abs(month_data[month_data < 0])))
        
        monthly_wind.append(np.sum(data['wind'][day_idx:day_idx+dim]))
        monthly_solar.append(np.sum(data['solar'][day_idx:day_idx+dim]))
        monthly_hydro.append(np.sum(data['hydro'][day_idx:day_idx+dim]))
        
        day_idx += dim
    
    # 创建分组柱状图
    fig = go.Figure(data=[
        go.Bar(name='风电', x=months, y=monthly_wind, marker_color='rgba(102, 204, 255, 0.8)'),
        go.Bar(name='光伏', x=months, y=monthly_solar, marker_color='rgba(255, 204, 102, 0.8)'),
        go.Bar(name='水电', x=months, y=monthly_hydro, marker_color='rgba(51, 204, 102, 0.8)'),
        go.Bar(name='抽蓄发电', x=months, y=monthly_pump_generation, marker_color='rgba(153, 102, 255, 0.8)'),
        go.Bar(name='抽蓄耗电', x=months, y=monthly_pump_consumption, marker_color='rgba(255, 102, 153, 0.8)')
    ])
    
    fig.update_layout(
        barmode='group',
        title='📊 月度各类电源出力对比',
        xaxis_title='月份',
        yaxis_title='发电量(MWh)',
        width=1000,
        height=500,
        title_x=0.5,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2)
    )
    
    return fig


def create_energy_flow_animation(data: Dict[str, Any], day_index: int = 0) -> go.Figure:
    """
    创建能量流动动画图
    
    Args:
        data: 数据字典
        day_index: 选择第几天的数据（0-364）
    
    Returns:
        plotly.graph_objects.Figure: 动画图对象
    """
    hours = np.arange(24)
    wind = data['wind'][day_index]
    solar = data['solar'][day_index]
    hydro = data['hydro'][day_index]
    npump = data['np_raw'][day_index]
    fh = data['fh'][day_index]
    
    # 计算各类能源占比
    total_energy = wind + solar + hydro + npump + fh
    wind_ratio = wind / total_energy * 100
    solar_ratio = solar / total_energy * 100
    hydro_ratio = hydro / total_energy * 100
    pump_ratio = npump / total_energy * 100
    thermal_ratio = fh / total_energy * 100
    
    fig = go.Figure()
    
    # 添加各能源轨迹
    fig.add_trace(go.Scatter(
        x=hours, y=wind_ratio, name='风电',
        mode='lines+markers', line=dict(width=2),
        marker=dict(color='rgba(102, 204, 255, 1)', size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=hours, y=solar_ratio, name='光伏',
        mode='lines+markers', line=dict(width=2),
        marker=dict(color='rgba(255, 204, 102, 1)', size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=hours, y=hydro_ratio, name='水电',
        mode='lines+markers', line=dict(width=2),
        marker=dict(color='rgba(51, 204, 102, 1)', size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=hours, y=pump_ratio, name='抽水蓄能',
        mode='lines+markers', line=dict(width=2),
        marker=dict(color='rgba(153, 102, 255, 1)', size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=hours, y=thermal_ratio, name='火电',
        mode='lines+markers', line=dict(width=2),
        marker=dict(color='rgba(255, 102, 102, 1)', size=8)
    ))
    
    fig.update_layout(
        title=f"🔄 第{day_index+1}天能源结构动态变化",
        xaxis_title='时间(小时)',
        yaxis_title='占比(%)',
        width=900,
        height=500,
        title_x=0.5,
        hovermode='x unified'
    )
    
    return fig


def get_visualization_list() -> List[str]:
    """
    获取可用的可视化功能列表
    
    Returns:
        list: 可视化功能名称列表
    """
    return [
        '桑基图 - 能量流向',
        '3D水库可视化',
        '能量平衡图',
        'Pareto前沿3D图',
        '碳减排热力图',
        '月度对比图',
        '能源流动动画'
    ]
