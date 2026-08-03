"""
报告生成模块 — HTML综合报告导出
火电深度调峰+抽水蓄能减碳效益优化系统
"""

import datetime
from html import escape as html_escape


def generate_html_report(data, derived, params=None):
    """生成综合报告HTML用于导出"""
    t = derived['totals']
    c = derived['carbon']
    ps = derived['ps_stats']
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = ""
    metrics = [
        ("碳减排量", f"{c['carbon_change']:.2f} 万吨"),
        ("火电变化量", f"{c['power_change']:.2f} 亿kWh"),
        ("新能源渗透率", f"{t['renewable_ratio']:.1f}%"),
        ("新能源发电量", f"{t['total_renewable']:.2f} 亿kWh"),
        ("抽水小时数", f"{t['pump_hours']} h"),
        ("发电小时数", f"{t['gen_hours']} h"),
        ("抽发效率", f"{ps['efficiency']:.2f}%"),
        ("总发电量", f"{ps['total_generation']:.2f} MWh"),
    ]
    for label, val in metrics:
        rows += f"<tr><td>{html_escape(label)}</td><td>{html_escape(val)}</td></tr>"

    params_html = ""
    if params:
        params_html = "<h3>参数设置</h3><table>"
        for k, v in params.items():
            params_html += f"<tr><td>{html_escape(str(k))}</td><td>{html_escape(str(v))}</td></tr>"
        params_html += "</table>"

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>抽水蓄能减碳效益优化 — 综合报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; background: #0a1628; color: #e0e6ed; max-width: 800px; margin: auto; padding: 40px 20px; }}
h1 {{ color: #00d4ff; border-bottom: 2px solid rgba(0,212,255,0.3); padding-bottom: 12px; }}
h3 {{ color: #00d4ff; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
td, th {{ padding: 10px 16px; border: 1px solid rgba(255,255,255,0.1); text-align: left; }}
th {{ background: rgba(0,212,255,0.15); }}
.footer {{ color: #8ba4c4; font-size: 0.8rem; margin-top: 40px; text-align: center; }}
</style></head>
<body>
<h1>⚡ 抽水蓄能减碳效益优化核算系统 — 综合报告</h1>
<p>生成时间: {now} | 数据周期: 全年8760小时</p>
<h3>关键指标</h3>
<table><tr><th>指标</th><th>数值</th></tr>{rows}</table>
{params_html}
<p class="footer">新型电力系统下抽水蓄能减碳效益优化核算系统 | Powered by NSLDE</p>
</body></html>"""
    return html
