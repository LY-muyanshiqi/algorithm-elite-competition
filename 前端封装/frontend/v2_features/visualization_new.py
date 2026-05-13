#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的3D水库可视化模块
"""

import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any


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
                title='水位高度',
                titlefont=dict(size=14, color='white'),
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
            title='时间(小时)',
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            titlefont=dict(color='white', size=12),
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis2=dict(
            domain=[0.58, 0.95],
            anchor='x2',
            title='功率(MW)',
            titlefont=dict(size=12, color='white'),
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)',
            zerolinecolor='rgba(100, 100, 100, 0.5)'
        ),
        xaxis3=dict(
            domain=[0.52, 0.95],
            anchor='y3',
            title='时间(小时)',
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            titlefont=dict(color='white', size=12),
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis3=dict(
            domain=[0.58, 0.95],
            anchor='x3',
            title='水位(%)',
            titlefont=dict(size=12, color='white'),
            tickfont=dict(color='white', size=10),
            range=[0, 100],
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)',
            zerolinecolor='rgba(100, 100, 100, 0.5)'
        ),
        xaxis4=dict(
            domain=[0.05, 0.95],
            anchor='y4',
            title='时间(小时)',
            tickvals=list(range(0, 24, 3)),
            dtick=3,
            titlefont=dict(color='white', size=12),
            tickfont=dict(color='white', size=10),
            gridcolor='rgba(50, 50, 50, 0.3)',
            linecolor='rgba(100, 100, 100, 0.5)'
        ),
        yaxis4=dict(
            domain=[0.05, 0.18],
            anchor='x4',
            title='运行状态',
            titlefont=dict(size=12, color='white'),
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
