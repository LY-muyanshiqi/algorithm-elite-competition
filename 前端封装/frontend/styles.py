"""
统一样式模块 - 火电深度调峰+抽水蓄能减碳效益优化系统
"""

CSS = """
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
        overflow: hidden;
        word-break: break-all;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 212, 255, 0.2);
        border-color: rgba(0, 212, 255, 0.5);
    }

    /* 修复st.metric在metric-card内的重叠 */
    .metric-card [data-testid="stMetric"] {
        background: transparent !important;
        padding: 0 !important;
    }

    .metric-card [data-testid="stMetric"] label {
        color: #8ba4c4 !important;
        font-size: 0.9rem !important;
    }

    /* 标题样式 */
    .main-title {
        background: linear-gradient(90deg, #00d4ff, #0096ff, #00d4ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 3s linear infinite;
        line-height: 1.4;
        margin-bottom: 0.3em;
    }

    .sub-title {
        color: #8ba4c4;
        font-size: 1rem;
        text-align: center;
        margin-bottom: 1.5em;
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

    /* 暗色卡片 */
    .dark-card {
        background: rgba(20, 35, 60, 0.8);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }

    /* Section标题 */
    .section-header {
        background: linear-gradient(90deg, rgba(0, 212, 255, 0.2) 0%, transparent 100%);
        padding: 15px 20px;
        border-left: 4px solid #00d4ff;
        margin: 20px 0 15px 0;
        border-radius: 0 8px 8px 0;
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

    /* Plotly图表背景 */
    .js-plotly-plot .plotly, .js-plotly-plot .plotly div {
        background: transparent !important;
    }

    /* ============ 移动端响应式适配 ============ */
    @media screen and (max-width: 768px) {
        /* 指标卡片全宽 */
        .metric-card {
            padding: 12px;
            margin: 6px 0;
        }
        .metric-value {
            font-size: 1.4rem;
        }
        .metric-label {
            font-size: 0.75rem;
        }

        /* 侧边栏折叠后占满宽度 */
        [data-testid="stSidebar"] {
            min-width: 100vw !important;
            max-width: 100vw !important;
        }

        /* 列强制堆叠 */
        [data-testid="column"] {
            flex: 1 1 100% !important;
            max-width: 100% !important;
        }

        /* 按钮更大点击区域 */
        .stButton > button {
            padding: 12px 20px;
            font-size: 1rem;
            min-height: 44px;
        }

        /* 标题缩小 */
        .main-title {
            font-size: 1.5rem !important;
        }

        /* 表格横向滚动 */
        [data-testid="stTable"] {
            overflow-x: auto;
        }

        /* Tab标签缩小间距 */
        [data-testid="stTabs"] button {
            padding: 8px 12px;
            font-size: 0.85rem;
        }

        /* Section header 缩进减少 */
        .section-header {
            padding: 10px 12px;
            margin: 12px 0 8px 0;
        }
    }

    /* 平板适配 */
    @media screen and (min-width: 769px) and (max-width: 1024px) {
        .metric-value {
            font-size: 1.6rem;
        }
        [data-testid="column"] {
            flex: 1 1 50% !important;
            max-width: 50% !important;
        }
    }
</style>
"""


def apply(st):
    """应用CSS样式到Streamlit页面"""
    st.markdown(CSS, unsafe_allow_html=True)
