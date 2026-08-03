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

    # 基于新能源实际出力比的弃电估算
    renewable_used_total = np.sum(day_data['wind']) + np.sum(day_data['solar']) + np.sum(day_data['hydro'])
    fh_total = np.sum(day_data['fh'])
    curtailment_ratio = max(0, min(0.15, 1 - fh_total / max(renewable_used_total, 1)))
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

    优化内容：
    1. 颜色分层显示 - 根据水位高度显示不同深浅的蓝色
    2. 球体变形 - 水位越低，球体越细长；水位越高，球体越扁
    3. 添加水面高光效果
    4. 添加水位刻度标记
    5. 添加播放控制按钮
    6. 添加运行状态指示曲线

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

    theta = np.linspace(0, 2 * np.pi, 48)
    phi = np.linspace(0, np.pi, 24)
    theta, phi = np.meshgrid(theta, phi)

    fig = go.Figure()

    # 创建高对比度颜色渐变 - 根据水位高度显示不同颜色
    def get_water_color(level):
        """根据水位返回高对比度颜色"""
        if level < 0.25:
            return [
                [0, 'rgba(0, 255, 255, 0.6)'],
                [0.5, 'rgba(0, 200, 200, 0.7)'],
                [1, 'rgba(0, 150, 150, 0.8)']
            ]
        elif level < 0.5:
            return [
                [0, 'rgba(0, 200, 100, 0.6)'],
                [0.5, 'rgba(0, 150, 50, 0.7)'],
                [1, 'rgba(0, 100, 30, 0.8)']
            ]
        elif level < 0.75:
            return [
                [0, 'rgba(255, 200, 0, 0.6)'],
                [0.5, 'rgba(200, 150, 0, 0.7)'],
                [1, 'rgba(150, 100, 0, 0.8)']
            ]
        else:
            return [
                [0, 'rgba(255, 50, 50, 0.7)'],
                [0.5, 'rgba(200, 30, 30, 0.8)'],
                [1, 'rgba(150, 20, 20, 0.9)']
            ]

    # 创建24小时的水库状态
    for hour in range(24):
        level = reservoir_level[hour]

        # 根据水位调整球体形状 - 水位越高越扁，水位越低越长
        base_radius = 1.0
        radius_x = base_radius + level * 0.4
        radius_y = base_radius + level * 0.4
        radius_z = base_radius + (1 - level) * 0.6  # 水位越低，z轴越长

        x_surface = radius_x * np.sin(phi) * np.cos(theta)
        y_surface = radius_y * np.sin(phi) * np.sin(theta)
        z_surface = radius_z * np.cos(phi)

        # 根据水位获取颜色
        colorscale = get_water_color(level)

        # 添加主水库球体
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
                z=dict(show=True, usecolormap=True, highlightcolor="#4dabf7", project_z=True),
                x=dict(show=False),
                y=dict(show=False)
            ),
            lighting=go.surface.Lighting(
                ambient=0.45,
                diffuse=0.85,
                specular=0.35,
                roughness=0.35,
                fresnel=0.2
            ),
            lightposition=dict(x=2, y=2, z=2)
        ))

        # 添加水面高光层
        if level > 0.1:
            theta_ring = np.linspace(0, 2 * np.pi, 60)
            x_ring = (radius_x * 1.02) * np.cos(theta_ring)
            y_ring = (radius_y * 1.02) * np.sin(theta_ring)
            z_ring = np.full_like(theta_ring, radius_z * 0.95)

            fig.add_trace(go.Scatter3d(
                x=x_ring,
                y=y_ring,
                z=z_ring,
                mode='lines',
                line=dict(color='rgba(255, 255, 255, 0.8)', width=3),
                name=f'{hour}:00水面',
                visible=False,
                showlegend=False
            ))

    # 设置第0小时可见
    fig.data[0].visible = True
    if len(fig.data) > 24:
        fig.data[24].visible = True  # 水面高光

    # 创建滑块
    steps = []
    for i in range(24):
        level = reservoir_level[i]

        step = dict(
            method='restyle',
            args=['visible', [False] * len(fig.data)],
            label=f'{i}:00'
        )

        # 显示当前小时的水库和水面
        step['args'][1][i] = True
        if len(fig.data) > 24 + i:
            step['args'][1][24 + i] = True

        steps.append(step)

    sliders = [dict(
        active=0,
        currentvalue={
            'prefix': '⏰ 时间: ',
            'font': dict(size=14, color='white'),
            'suffix': ' | 水位: {:.1f}%'.format(reservoir_level[0] * 100)
        },
        pad={'t': 70, 'b': 15},
        len=0.9,
        steps=steps,
        ticklen=5,
        minorticklen=3,
        font=dict(color='white'),
        bgcolor='rgba(30, 30, 30, 0.9)',
        bordercolor='rgba(100, 100, 100, 0.5)'
    )]

    # 添加功率柱状图
    fig.add_trace(go.Bar(
        x=hours,
        y=npump,
        name='抽水蓄能功率',
        marker_color=['#51cf66' if v < 0 else '#ff6b6b' if v > 0 else '#ffd43b' for v in npump],
        opacity=0.85,
        xaxis='x2',
        yaxis='y2',
        hovertemplate='时间: %{x}:00<br>功率: %{y:.2f}MW<br>状态: %{customdata}',
        customdata=['抽水' if v < 0 else '发电' if v > 0 else '空闲' for v in npump]
    ))

    # 添加水位曲线
    fig.add_trace(go.Scatter(
        x=hours,
        y=reservoir_level[0:24] * 100,
        name='水位百分比',
        line=dict(color='#4dabf7', width=3, dash='solid'),
        fill='tozeroy',
        fillcolor='rgba(77, 171, 247, 0.15)',
        xaxis='x3',
        yaxis='y3',
        hovertemplate='时间: %{x}:00<br>水位: %{y:.1f}%<extra></extra>'
    ))

    # 添加状态指示曲线
    status_values = np.where(npump < 0, -1, np.where(npump > 0, 1, 0))
    fig.add_trace(go.Scatter(
        x=hours,
        y=status_values * 10,
        name='运行状态',
        line=dict(color='#ffd43b', width=2),
        marker=dict(
            size=8,
            color=['#51cf66' if v < 0 else '#ff6b6b' if v > 0 else '#ffd43b' for v in npump]
        ),
        xaxis='x4',
        yaxis='y4',
        hovertemplate='时间: %{x}:00<br>状态: %{customdata}',
        customdata=['抽水' if v < 0 else '发电' if v > 0 else '空闲' for v in npump]
    ))

    # 添加水位刻度标记
    for level_marker in [0.25, 0.5, 0.75]:
        theta_marker = np.linspace(0, 2 * np.pi, 30)
        x_marker = 1.3 * np.cos(theta_marker)
        y_marker = 1.3 * np.sin(theta_marker)
        z_marker = np.full_like(theta_marker, (level_marker * 2 - 1) * 0.8)

        fig.add_trace(go.Scatter3d(
            x=x_marker,
            y=y_marker,
            z=z_marker,
            mode='lines',
            line=dict(color='rgba(100, 100, 100, 0.5)', width=1, dash='dash'),
            name=f'{level_marker*100:.0f}%水位',
            showlegend=False
        ))

    fig.update_layout(
        title=dict(
            text=f'🏊 第{day_index+1}天抽水蓄能水库状态3D动态可视化<br><sub>🔵青色(0-25%) | 🟢绿色(25-50%) | 🟡黄色(50-75%) | 🔴红色(75-100%)</sub>',
            x=0.5,
            font=dict(size=20, color='white'),
            y=0.98
        ),
        title_font_color='white',
        scene=dict(
            xaxis=dict(
                title='',
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                backgroundcolor='rgba(0, 0, 0, 0)',
                showbackground=False
            ),
            yaxis=dict(
                title='',
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                backgroundcolor='rgba(0, 0, 0, 0)',
                showbackground=False
            ),
            zaxis=dict(
                title=dict(text='水位高度', font=dict(size=14, color='white')),
                tickformat='.0%',
                tickfont=dict(color='white'),
                range=[-1.5, 1.5],
                showgrid=True,
                gridcolor='rgba(50, 50, 50, 0.5)',
                zeroline=True,
                zerolinecolor='rgba(100, 100, 100, 0.5)'
            ),
            camera=dict(
                eye=dict(x=2.2, y=2.2, z=1.0),
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0)
            ),
            aspectmode='auto',
            bgcolor='rgba(10, 10, 15, 1)',
            annotations=[
                dict(
                    x=0, y=0, z=-1.3,
                    text='低水位 (青色)',
                    showarrow=False,
                    font=dict(size=12, color='rgba(0, 255, 255, 0.9)')
                ),
                dict(
                    x=0, y=0, z=1.3,
                    text='高水位 (红色)',
                    showarrow=False,
                    font=dict(size=12, color='rgba(255, 50, 50, 0.9)')
                )
            ]
        ),
        sliders=sliders,
        width=1100,
        height=750,
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.92,
            bgcolor='rgba(20, 20, 25, 0.95)',
            bordercolor='rgba(100, 100, 100, 0.5)',
            font=dict(color='white', size=12),
            itemsizing='constant'
        ),
        xaxis2=dict(
            domain=[0.05, 0.48],
            anchor='y2',
            title=dict(text='时间(小时)', font=dict(color='white', size=12)),
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis2=dict(
            domain=[0.58, 0.95],
            anchor='x2',
            title=dict(text='功率(MW)', font=dict(size=12, color='white')),
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)',
            zerolinecolor='rgba(100, 100, 100, 0.5)'
        ),
        xaxis3=dict(
            domain=[0.52, 0.95],
            anchor='y3',
            title=dict(text='时间(小时)', font=dict(color='white', size=12)),
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis3=dict(
            domain=[0.58, 0.95],
            anchor='x3',
            title=dict(text='水位(%)', font=dict(size=12, color='white')),
            tickfont=dict(color='white', size=10),
            range=[0, 100],
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)',
            zerolinecolor='rgba(100, 100, 100, 0.5)'
        ),
        xaxis4=dict(
            domain=[0.05, 0.95],
            anchor='y4',
            title=dict(text='时间(小时)', font=dict(color='white', size=12)),
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis4=dict(
            domain=[0.05, 0.18],
            anchor='x4',
            title=dict(text='运行状态', font=dict(size=12, color='white')),
            tickfont=dict(color='white', size=10),
            range=[-15, 15],
            tickvals=[-10, 0, 10],
            ticktext=['抽水', '空闲', '发电'],
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)',
            zerolinecolor='rgba(100, 100, 100, 0.5)'
        ),
        margin=dict(l=40, r=40, t=80, b=80),
        paper_bgcolor='rgba(10, 10, 15, 1)',
        plot_bgcolor='rgba(15, 15, 20, 1)',
        updatemenus=[dict(
            type='buttons',
            showactive=True,
            buttons=[dict(
                label='▶ 播放',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=500, redraw=True),
                    fromcurrent=True,
                    transition=dict(duration=300)
                )]
            )],
            x=0.85,
            y=0.98
        )]
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
