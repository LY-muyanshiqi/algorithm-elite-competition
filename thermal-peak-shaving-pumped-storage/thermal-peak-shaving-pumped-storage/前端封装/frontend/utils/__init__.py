"""
工具函数模块
包含通用的辅助功能
"""

import base64
import numpy as np
import pandas as pd


def export_to_csv(data, filename="data_export.csv"):
    """导出数据为CSV文件"""
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
        from streamlit import error as st_error
        st_error(f"导出失败: {str(e)}")
        return None


def download_plotly_figure(fig, filename="chart.png", width=1200, height=600):
    """下载Plotly图表为PNG图片"""
    try:
        img_bytes = fig.to_image(format="png", width=width, height=height)
        return img_bytes
    except Exception:
        return None


def create_metric_card(label, value, unit="", delta=None, color="#00d4ff"):
    """创建自定义指标卡片HTML"""
    delta_html = f'<span style="color: {"#00ff88" if delta and delta > 0 else "#ff6b6b" if delta and delta < 0 else "#8ba4c4"}; font-size: 0.9rem;">{"▲" if delta and delta > 0 else "▼" if delta and delta < 0 else ""} {abs(delta) if delta else ""}</span>' if delta is not None else ""
    
    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color};">{value}</div>
        <div style="color: #8ba4c4; font-size: 0.9rem;">{unit} {delta_html}</div>
    </div>
    """
    return html


def get_season_days(season):
    """根据季节获取日期范围"""
    season_days = {
        "春季 (1-3月)": (1, 90),
        "夏季 (4-6月)": (91, 181),
        "秋季 (7-9月)": (182, 273),
        "冬季 (10-12月)": (274, 365)
    }
    return season_days.get(season, (1, 365))


def get_month_days(month):
    """根据月份获取日期范围"""
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    start_day = sum(days_per_month[:month-1]) + 1
    end_day = start_day + days_per_month[month-1] - 1
    return (start_day, end_day)


def format_number(value, decimals=2):
    """格式化数字显示"""
    if abs(value) >= 100000000:
        return f"{value / 100000000:.{decimals}f}亿"
    elif abs(value) >= 10000:
        return f"{value / 10000:.{decimals}f}万"
    else:
        return f"{value:.{decimals}f}"


def calculate_statistics(data):
    """计算数据统计信息"""
    stats = {
        'total_wind': np.sum(data['wind']) / 10000,  # 亿kWh
        'total_solar': np.sum(data['solar']) / 10000,
        'total_hydro': np.sum(data['hydro']) / 10000,
        'total_fh': np.sum(data['fh']) / 10000,
        'total_renewable': (np.sum(data['wind']) + np.sum(data['solar']) + np.sum(data['hydro'])) / 10000,
        'pump_hours': int((data['np_raw'] < 0).sum()),
        'gen_hours': int((data['np_raw'] > 0).sum()),
    }
    stats['renewable_ratio'] = stats['total_renewable'] / (stats['total_renewable'] + stats['total_fh']) * 100
    return stats