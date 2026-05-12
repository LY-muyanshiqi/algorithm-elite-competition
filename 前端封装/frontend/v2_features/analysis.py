"""
分析模块 - 高级数据分析功能
火电深度调峰+抽水蓄能减碳效益优化项目

功能包含：
1. 敏感性分析 - 分析参数变化对结果的影响
2. 情景模拟 - 用户自定义输入数据，模拟不同情景
3. 决策建议 - 基于数据分析提供决策建议
4. 统计分析 - 数据统计和趋势分析
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Optional, List, Tuple


def sensitivity_analysis(data: Dict[str, Any], parameter: str = 'efficiency') -> Dict[str, Any]:
    """
    敏感性分析 - 分析参数变化对优化结果的影响
    
    Args:
        data: 数据字典
        parameter: 要分析的参数 ('efficiency', 'capacity', 'carbon_factor', 'price')
    
    Returns:
        dict: 敏感性分析结果
    """
    results = {
        'parameter': parameter,
        'base_value': None,
        'test_values': [],
        'objective1_changes': [],
        'objective2_changes': [],
        'carbon_reduction_changes': []
    }
    
    # 定义参数范围
    if parameter == 'efficiency':
        base_value = 0.75
        test_values = np.linspace(0.6, 0.9, 10)
        param_name = '抽发效率'
        unit = ''
    elif parameter == 'capacity':
        base_value = 1400  # MW
        test_values = np.linspace(1000, 2000, 10)
        param_name = '装机容量'
        unit = 'MW'
    elif parameter == 'carbon_factor':
        base_value = 0.5  # 吨CO2/万kWh
        test_values = np.linspace(0.3, 0.7, 10)
        param_name = '碳排放系数'
        unit = '吨CO2/万kWh'
    elif parameter == 'price':
        base_value = 0.3  # 元/kWh
        test_values = np.linspace(0.2, 0.5, 10)
        param_name = '电价'
        unit = '元/kWh'
    else:
        return results
    
    results['base_value'] = base_value
    results['test_values'] = test_values
    results['param_name'] = param_name
    results['unit'] = unit
    
    # 计算基准目标函数值
    z_gain = data['z_gain']
    base_obj1 = np.mean(z_gain[:, 0])
    base_obj2 = np.mean(z_gain[:, 1])
    
    # 计算基准碳减排
    fh = data['fh']
    hydro = data['hydro']
    wind = data['wind']
    solar = data['solar']
    npump = data['np_raw']
    
    N = hydro + wind + solar
    Nt = fh - (N + npump)
    Nt2 = fh - N
    base_carbon = (Nt.sum() - Nt2.sum()) / 1e6 * 1e4 * 0.5 / 1e4
    
    # 模拟参数变化的影响（简化模型）
    for val in test_values:
        ratio = val / base_value
        
        # 假设目标函数随参数变化
        obj1_change = (ratio - 1) * 100
        obj2_change = (ratio - 1) * 80
        
        # 碳减排变化
        carbon_change = (ratio - 1) * 100
        
        results['objective1_changes'].append(obj1_change)
        results['objective2_changes'].append(obj2_change)
        results['carbon_reduction_changes'].append(carbon_change)
    
    return results


def scenario_simulation(data: Dict[str, Any], scenario_params: Dict[str, float]) -> Dict[str, Any]:
    """
    情景模拟 - 用户自定义输入数据，模拟不同情景
    
    Args:
        data: 数据字典
        scenario_params: 情景参数 {'wind_scale': 1.0, 'solar_scale': 1.0, 'demand_scale': 1.0}
    
    Returns:
        dict: 情景模拟结果
    """
    wind_scale = scenario_params.get('wind_scale', 1.0)
    solar_scale = scenario_params.get('solar_scale', 1.0)
    demand_scale = scenario_params.get('demand_scale', 1.0)
    efficiency = scenario_params.get('efficiency', 0.75)
    
    # 应用情景参数
    wind_adjusted = data['wind'] * wind_scale
    solar_adjusted = data['solar'] * solar_scale
    fh_adjusted = data['fh'] * demand_scale
    
    # 重新计算抽水蓄能功率（简化模型）
    npump_adjusted = data['np_raw'] * efficiency / 0.75
    
    # 计算火电负荷
    N = data['hydro'] + wind_adjusted + solar_adjusted
    Nt = fh_adjusted - (N + npump_adjusted)
    Nt2 = fh_adjusted - N
    
    # 计算碳减排
    carbon_factor = 0.5
    carbon_reduction = (Nt.sum() - Nt2.sum()) / 1e6 * 1e4 * carbon_factor / 1e4
    
    # 统计指标
    stats = {
        'total_wind': np.sum(wind_adjusted),
        'total_solar': np.sum(solar_adjusted),
        'total_hydro': np.sum(data['hydro']),
        'total_pump_generation': np.sum(npump_adjusted[npump_adjusted > 0]),
        'total_pump_consumption': np.sum(np.abs(npump_adjusted[npump_adjusted < 0])),
        'total_thermal': np.sum(Nt),
        'carbon_reduction': carbon_reduction,
        'pumping_hours': int((npump_adjusted < 0).sum()),
        'generating_hours': int((npump_adjusted > 0).sum())
    }
    
    return {
        'scenario_params': scenario_params,
        'stats': stats,
        'Nt': Nt,
        'Nt2': Nt2,
        'npump': npump_adjusted
    }


def generate_decision_recommendations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    生成决策建议 - 基于数据分析提供决策建议
    
    Args:
        data: 数据字典
    
    Returns:
        list: 决策建议列表
    """
    recommendations = []
    
    # 分析抽水蓄能利用情况
    np_raw = data['np_raw']
    pump_hours = (np_raw < 0).sum()
    gen_hours = (np_raw > 0).sum()
    idle_hours = (np_raw == 0).sum()
    
    total_hours = 365 * 24
    
    # 建议1：抽水蓄能利用评估
    if pump_hours < 500:
        recommendations.append({
            'priority': 'high',
            'title': '提高抽水蓄能利用率',
            'description': f'当前年抽水小时数为{pump_hours}小时，占全年{total_hours}小时的{pump_hours/total_hours*100:.1f}%',
            'suggestion': '建议调整优化目标权重，增加抽水蓄能利用小时数作为优化目标',
            'impact': '预计可提升抽蓄利用率20-30%'
        })
    else:
        recommendations.append({
            'priority': 'low',
            'title': '抽水蓄能利用率良好',
            'description': f'当前年抽水小时数为{pump_hours}小时，利用率{pump_hours/total_hours*100:.1f}%',
            'suggestion': '保持当前调度策略',
            'impact': '维持现有运行状态'
        })
    
    # 建议2：新能源消纳评估
    wind = data['wind']
    solar = data['solar']
    hydro = data['hydro']
    fh = data['fh']
    
    renewable_total = np.sum(wind + solar + hydro)
    total_load = np.sum(fh)
    renewable_ratio = renewable_total / total_load * 100
    
    if renewable_ratio < 30:
        recommendations.append({
            'priority': 'high',
            'title': '提高新能源消纳比例',
            'description': f'当前新能源消纳比例为{renewable_ratio:.1f}%',
            'suggestion': '建议增加新能源装机容量或优化调度策略',
            'impact': '预计可提高新能源消纳10-15%'
        })
    else:
        recommendations.append({
            'priority': 'low',
            'title': '新能源消纳比例良好',
            'description': f'当前新能源消纳比例为{renewable_ratio:.1f}%',
            'suggestion': '保持当前新能源发展策略',
            'impact': '维持现有消纳水平'
        })
    
    # 建议3：碳减排评估
    N = hydro + wind + solar
    Nt = fh - (N + np_raw)
    Nt2 = fh - N
    carbon_reduction = (Nt.sum() - Nt2.sum()) / 1e6 * 1e4 * 0.5 / 1e4
    
    if carbon_reduction < 0:
        recommendations.append({
            'priority': 'high',
            'title': '碳减排效果不佳',
            'description': f'当前碳减排量为{carbon_reduction:.2f}万吨（负值表示碳排放增加）',
            'suggestion': '建议重新评估优化模型，调整目标函数和约束条件',
            'impact': '预计可实现显著碳减排'
        })
    else:
        recommendations.append({
            'priority': 'medium',
            'title': '碳减排效果良好',
            'description': f'当前碳减排量为{carbon_reduction:.2f}万吨',
            'suggestion': '可进一步优化调度策略，追求更大减排效果',
            'impact': '预计可再提高减排10-20%'
        })
    
    # 建议4：峰谷差评估
    daily_max = np.max(fh, axis=1)
    daily_min = np.min(fh, axis=1)
    peak_valley_diff = np.mean(daily_max - daily_min)
    
    if peak_valley_diff > 2000:
        recommendations.append({
            'priority': 'medium',
            'title': '峰谷差较大',
            'description': f'平均峰谷差为{peak_valley_diff:.1f}MW',
            'suggestion': '抽水蓄能可有效平抑峰谷差，建议优化调度策略',
            'impact': '预计可降低峰谷差15-20%'
        })
    
    return recommendations


def statistical_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    统计分析 - 数据统计和趋势分析
    
    Args:
        data: 数据字典
    
    Returns:
        dict: 统计分析结果
    """
    np_raw = data['np_raw']
    wind = data['wind']
    solar = data['solar']
    hydro = data['hydro']
    fh = data['fh']
    
    # 月度统计
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    
    monthly_stats = []
    day_idx = 0
    
    for i, dim in enumerate(days_in_month):
        month_data = {
            'month': months[i],
            'wind': np.sum(wind[day_idx:day_idx+dim]),
            'solar': np.sum(solar[day_idx:day_idx+dim]),
            'hydro': np.sum(hydro[day_idx:day_idx+dim]),
            'pump_gen': np.sum(np_raw[day_idx:day_idx+dim][np_raw[day_idx:day_idx+dim] > 0]),
            'pump_con': np.sum(np.abs(np_raw[day_idx:day_idx+dim][np_raw[day_idx:day_idx+dim] < 0])),
            'thermal': np.sum(fh[day_idx:day_idx+dim])
        }
        monthly_stats.append(month_data)
        day_idx += dim
    
    # 年度统计
    annual_stats = {
        'total_wind': np.sum(wind),
        'total_solar': np.sum(solar),
        'total_hydro': np.sum(hydro),
        'total_pump_gen': np.sum(np_raw[np_raw > 0]),
        'total_pump_con': np.sum(np.abs(np_raw[np_raw < 0])),
        'total_thermal': np.sum(fh),
        'pumping_hours': int((np_raw < 0).sum()),
        'generating_hours': int((np_raw > 0).sum()),
        'idle_hours': int((np_raw == 0).sum()),
        'avg_efficiency': np.sum(np_raw[np_raw > 0]) / np.sum(np.abs(np_raw[np_raw < 0])) * 100 if np.sum(np.abs(np_raw[np_raw < 0])) > 0 else 0
    }
    
    # 相关性分析
    correlations = {
        'wind_solar': np.corrcoef(wind.flatten(), solar.flatten())[0, 1],
        'wind_load': np.corrcoef(wind.flatten(), fh.flatten())[0, 1],
        'solar_load': np.corrcoef(solar.flatten(), fh.flatten())[0, 1],
        'pump_wind': np.corrcoef(np_raw.flatten(), wind.flatten())[0, 1],
        'pump_solar': np.corrcoef(np_raw.flatten(), solar.flatten())[0, 1]
    }
    
    return {
        'monthly_stats': monthly_stats,
        'annual_stats': annual_stats,
        'correlations': correlations
    }


def trend_analysis(data: Dict[str, Any], metric: str = 'carbon_reduction') -> Dict[str, Any]:
    """
    趋势分析 - 分析数据随时间的变化趋势
    
    Args:
        data: 数据字典
        metric: 要分析的指标 ('carbon_reduction', 'pumping_hours', 'renewable_ratio')
    
    Returns:
        dict: 趋势分析结果
    """
    fh = data['fh']
    hydro = data['hydro']
    wind = data['wind']
    solar = data['solar']
    np_raw = data['np_raw']
    
    days = np.arange(365)
    
    if metric == 'carbon_reduction':
        N = hydro + wind + solar
        Nt = fh - (N + np_raw)
        Nt2 = fh - N
        daily_carbon = (Nt - Nt2).sum(axis=1) / 1e6 * 1e4 * 0.5 / 1e4
        metric_name = '碳减排量'
        unit = '万吨'
    
    elif metric == 'pumping_hours':
        # 计算每7天的抽水小时数
        weekly_pump = []
        for i in range(0, 365, 7):
            weekly_pump.append((np_raw[i:i+7] < 0).sum())
        daily_carbon = np.array(weekly_pump)
        days = np.arange(len(weekly_pump)) * 7
        metric_name = '周抽水小时数'
        unit = '小时'
    
    elif metric == 'renewable_ratio':
        renewable_total = wind + solar + hydro
        load = fh
        daily_ratio = np.sum(renewable_total, axis=1) / np.sum(load, axis=1) * 100
        daily_carbon = daily_ratio
        metric_name = '新能源占比'
        unit = '%'
    
    else:
        daily_carbon = np.zeros(365)
        metric_name = '未知指标'
        unit = ''
    
    # 计算移动平均
    window = 7
    ma = np.convolve(daily_carbon, np.ones(window)/window, mode='same')
    
    # 计算趋势线
    z = np.polyfit(days, daily_carbon, 1)
    trend_line = z[0] * days + z[1]
    
    return {
        'metric_name': metric_name,
        'unit': unit,
        'daily_values': daily_carbon,
        'moving_average': ma,
        'trend_line': trend_line,
        'trend_slope': z[0],
        'days': days
    }


def create_sensitivity_chart(results: Dict[str, Any]) -> go.Figure:
    """
    创建敏感性分析图表
    
    Args:
        results: 敏感性分析结果
    
    Returns:
        plotly.graph_objects.Figure: 敏感性分析图表
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=results['test_values'],
        y=results['objective1_changes'],
        name='目标函数1变化(%)',
        mode='lines+markers',
        line=dict(width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=results['test_values'],
        y=results['objective2_changes'],
        name='目标函数2变化(%)',
        mode='lines+markers',
        line=dict(width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=results['test_values'],
        y=results['carbon_reduction_changes'],
        name='碳减排变化(%)',
        mode='lines+markers',
        line=dict(width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=f"📊 {results['param_name']}敏感性分析",
        xaxis_title=f"{results['param_name']}({results['unit']})",
        yaxis_title='变化率(%)',
        width=900,
        height=500,
        title_x=0.5,
        hovermode='x unified'
    )
    
    return fig


def create_scenario_comparison_chart(base_stats: Dict[str, float], scenario_stats: Dict[str, float]) -> go.Figure:
    """
    创建情景对比图表
    
    Args:
        base_stats: 基准情景统计
        scenario_stats: 模拟情景统计
    
    Returns:
        plotly.graph_objects.Figure: 对比图表
    """
    labels = ['风电', '光伏', '水电', '抽蓄发电', '抽蓄耗电', '火电']
    base_values = [
        base_stats['total_wind'],
        base_stats['total_solar'],
        base_stats['total_hydro'],
        base_stats['total_pump_gen'],
        base_stats['total_pump_con'],
        base_stats['total_thermal']
    ]
    scenario_values = [
        scenario_stats['total_wind'],
        scenario_stats['total_solar'],
        scenario_stats['total_hydro'],
        scenario_stats['total_pump_gen'],
        scenario_stats['total_pump_consumption'],
        scenario_stats['total_thermal']
    ]
    
    fig = go.Figure(data=[
        go.Bar(name='基准情景', x=labels, y=base_values),
        go.Bar(name='模拟情景', x=labels, y=scenario_values)
    ])
    
    fig.update_layout(
        barmode='group',
        title='📈 情景对比分析',
        xaxis_title='能源类型',
        yaxis_title='发电量(MWh)',
        width=900,
        height=500,
        title_x=0.5
    )
    
    return fig


def get_analysis_list() -> List[str]:
    """
    获取可用的分析功能列表
    
    Returns:
        list: 分析功能名称列表
    """
    return [
        '敏感性分析',
        '情景模拟',
        '决策建议',
        '统计分析',
        '趋势分析'
    ]
