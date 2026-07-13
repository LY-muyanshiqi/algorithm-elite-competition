"""验证数据库持久化"""
import sys
sys.path.insert(0, r'D:\thermal-peak-shaving-pumped-storage\前端封装\frontend')
from db import init_db, list_runs, load_run_daily, save_run
import api_client as dl

init_db()
runs = list_runs()
print(f'运行记录数: {len(runs)}')
for r in runs:
    rid = r['id']
    print(f'  #{rid}: {r["created_at"]} - {r["note"]}')

if runs:
    rid = runs[0]['id']
    daily = load_run_daily(rid)
    print(f'每日结果: {daily.shape[0]} 行, {daily.shape[1]} 列')
    print(f'第1天: z_peak={daily[0,1]:.2f}, z_carbon={daily[0,2]:.2f}')
    print('✅ 数据库验证通过')
else:
    print('暂无记录，创建一条测试记录...')
    data = dl.load_all_data()
    rid = save_run(data, note='手动验证')
    print(f'已创建 run #{rid}')
    print('✅ 数据库验证通过')
