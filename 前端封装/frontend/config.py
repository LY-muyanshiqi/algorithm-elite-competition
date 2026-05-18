"""
集中配置模块 — 参数预设、默认值、页面定义
火电深度调峰+抽水蓄能减碳效益优化系统
"""

# ---- 参数预设方案 ----
PRESETS = {
    "\U0001f3f7️ 自定义（手动调整）": None,
    "\U0001f4cb 默认方案": {
        'zpump': 1400, 'h_val': 4, 'efficiency_val': 0.75, 'min_power': 0.2,
        'carbon_factor': 0.5, 'coal_high': 300, 'coal_mid': 330, 'coal_low': 370,
    },
    "\U0001f33f 高消纳方案": {
        'zpump': 2000, 'h_val': 5, 'efficiency_val': 0.85, 'min_power': 0.15,
        'carbon_factor': 0.4, 'coal_high': 290, 'coal_mid': 320, 'coal_low': 360,
    },
    "\U0001f30d 深度低碳方案": {
        'zpump': 1600, 'h_val': 4, 'efficiency_val': 0.8, 'min_power': 0.15,
        'carbon_factor': 0.35, 'coal_high': 285, 'coal_mid': 315, 'coal_low': 355,
    },
    "⚡ 灵活调峰方案": {
        'zpump': 2500, 'h_val': 3, 'efficiency_val': 0.7, 'min_power': 0.25,
        'carbon_factor': 0.55, 'coal_high': 300, 'coal_mid': 330, 'coal_low': 380,
    },
}

# ---- 默认参数 ----
DEFAULT_PARAMS = {
    'zpump': 1400, 'h_val': 4, 'efficiency_val': 0.75, 'min_power': 0.2,
    'carbon_factor': 0.5, 'coal_high': 300, 'coal_mid': 330, 'coal_low': 370,
    'custom_params': None, 'recalculated_result': None, 'view_mode': '全年总览',
    '_last_preset': '\U0001f3f7️ 自定义（手动调整）',
    'preset_select': '\U0001f3f7️ 自定义（手动调整）',
}

# ---- 页面分组导航 ----
PAGE_GROUPS = {
    "\U0001f4ca 核心看板": ["\U0001f3e0 系统总览", "\U0001f4c8 综合分析报告"],
    "\U0001f4c8 专项分析": ["\U0001f33f 新能源分析", "\U0001f4a7 抽水蓄能调度",
                        "\U0001f525 火电调峰与碳减排", "\U0001f3af Pareto前沿分析"],
    "⚙️ 模型与参数": ["\U0001f4d0 计算公式详解", "⚙️ 参数调整",
                         "\U0001f5c3️ 原始数据浏览"],
    "\U0001f52c 高级功能": ["\U0001f3a8 高级可视化", "\U0001f9e0 高级分析", "\U0001f52c A/B参数对比"],
}
