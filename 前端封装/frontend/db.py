"""
数据库持久化模块 — SQLite 存储优化运行记录
用于历史对比、多场景检索、调参留痕

设计三张表：
- runs:        每次运行的基本信息
- daily_results:   每日的 Pareto 最优解和目标值
- raw_series:      每日每小时的原始和调度数据（可选，量大）
"""
import sqlite3
import os
import json
import numpy as np

# 数据库路径（与当前脚本同目录）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.db")


def init_db():
    """初始化数据库表结构（幂等，可重复调用）"""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at  TEXT DEFAULT (datetime('now')),
        region      TEXT,
        year        INTEGER,
        params_json TEXT,
        note        TEXT
    );
    CREATE TABLE IF NOT EXISTS daily_results (
        run_id          INTEGER,
        day             INTEGER,
        z_peak          REAL,
        z_carbon        REAL,
        carbon_reduction REAL,
        FOREIGN KEY (run_id) REFERENCES runs(id)
    );
    CREATE TABLE IF NOT EXISTS raw_series (
        run_id  INTEGER,
        day     INTEGER,
        hour    INTEGER,
        hydro   REAL,
        wind    REAL,
        solar   REAL,
        fh      REAL,
        npump   REAL,
        FOREIGN KEY (run_id) REFERENCES runs(id)
    );
    """)
    conn.commit()
    conn.close()
    return DB_PATH


def save_run(data, params=None, region="华东", year=2024, note=""):
    """
    将 load_all_data() 的结果保存到数据库。
    返回 run_id。
    """
    # 延时导入，避免循环依赖
    from data_loader import calculate_carbon_reduction

    init_db()
    conn = sqlite3.connect(DB_PATH)

    # 1) 写入 runs 表
    params_json = json.dumps(params or {}, ensure_ascii=False)
    cur = conn.execute(
        "INSERT INTO runs(region, year, params_json, note) VALUES (?,?,?,?)",
        (region, year, params_json, note),
    )
    run_id = cur.lastrowid

    # 2) 写入 daily_results
    z_gain = data["z_gain"]  # (365, 2)
    carbon = calculate_carbon_reduction(data)
    daily_carbon = carbon.get("daily_carbon_change",
                              np.zeros(365))  # (365,)
    daily_rows = [
        (run_id, d + 1,
         float(z_gain[d, 0]),
         float(z_gain[d, 1]),
         float(daily_carbon[d]))
        for d in range(365)
    ]
    conn.executemany(
        "INSERT INTO daily_results(run_id,day,z_peak,z_carbon,carbon_reduction) "
        "VALUES (?,?,?,?,?)", daily_rows)

    # 3) 写入 raw_series（逐小时数据，量大但可做精细分析）
    npump = data["np_raw"]
    hydro = data["hydro"]
    wind = data["wind"]
    solar = data["solar"]
    fh = data["fh"]
    raw_rows = [
        (run_id, d + 1, h + 1,
         float(hydro[d, h]), float(wind[d, h]),
         float(solar[d, h]), float(fh[d, h]), float(npump[d, h]))
        for d in range(365) for h in range(24)
    ]
    conn.executemany(
        "INSERT INTO raw_series(run_id,day,hour,hydro,wind,solar,fh,npump) "
        "VALUES (?,?,?,?,?,?,?,?)", raw_rows)

    conn.commit()
    conn.close()
    return run_id


def list_runs():
    """列出所有运行记录"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, created_at, region, year, note FROM runs ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "created_at": r[1], "region": r[2],
             "year": r[3], "note": r[4]} for r in rows]


def load_run_daily(run_id):
    """
    读取某次运行的每日结果。
    返回 (365, 4) numpy 数组：[day, z_peak, z_carbon, carbon_reduction]
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT day, z_peak, z_carbon, carbon_reduction FROM daily_results "
        "WHERE run_id=? ORDER BY day", (run_id,)
    ).fetchall()
    conn.close()
    arr = np.array(rows, dtype=np.float64)
    return arr  # (365, 4)


def load_run_params(run_id):
    """读取某次运行的参数快照"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT params_json FROM runs WHERE id=?", (run_id,)
    ).fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return {}


def delete_run(run_id):
    """删除某次运行及其关联数据"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM raw_series WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM daily_results WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM runs WHERE id=?", (run_id,))
    conn.commit()
    conn.close()
