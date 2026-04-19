"""
数据加载和预处理模块
火电深度调峰+抽水蓄能减碳效益优化项目
"""
import numpy as np
import scipy.io as sio
import os

# 数据路径 - 直接使用当前目录
DATA_DIR = os.path.dirname(__file__)


def load_mat_data():
    """加载MATLAB数据文件"""
    data = {}
    
    # 加载A.mat (100个Pareto解)
    a_mat = sio.loadmat(os.path.join(DATA_DIR, 'A.mat'))
    data['A'] = a_mat['A']  # (100, 27, 365) - Pareto解
    data['fh_raw'] = a_mat['FH']  # (365, 24) - 火电负荷
    data['NW'] = a_mat['NW']  # (365, 24) - 风电功率
    data['NH'] = a_mat['NH']  # (365, 24) - 水电功率
    
    # 加载AA.mat (最优解)
    aa_mat = sio.loadmat(os.path.join(DATA_DIR, 'AA.mat'))
    data['solution'] = aa_mat['solution']  # (365, 23) - 最优决策变量
    data['z_gain'] = aa_mat['Z_gain']  # (365, 2) - 目标函数值
    
    # 加载txt数据
    data['hydro'] = np.loadtxt(os.path.join(DATA_DIR, 'hydro.txt'))  # (365, 24)
    data['wind'] = np.loadtxt(os.path.join(DATA_DIR, 'wind.txt'))  # (365, 24)
    data['solar'] = np.loadtxt(os.path.join(DATA_DIR, 'solar.txt'))  # (365, 24)
    data['fh'] = np.loadtxt(os.path.join(DATA_DIR, 'FH.txt'))  # (365, 24)
    data['solution_txt'] = np.loadtxt(os.path.join(DATA_DIR, 'solution.txt'))  # (100, 27)
    
    # 计算抽水蓄能功率 (仿照process.m)
    data['np_raw'] = calculate_npump(data)
    # 计算有/无抽蓄的火电功率
    data['Nt'] = calculate_Nt(data, with_pump=True)  # 有抽蓄
    data['Nt2'] = calculate_Nt(data, with_pump=False)  # 无抽蓄
    
    return data


def calculate_npump(data):
    """
    计算抽水蓄能功率 (仿照process.m)
    决策变量 x: 23个值，代表每个时刻结束时水库状态比例 [0,1]
    """
    Zpump = 1400  # 抽水蓄能装机容量 (MW)，与MATLAB源代码保持一致
    h = 4  # 时间步长 (小时)
    V = Zpump * h  # 蓄能容量 (MWh)
    
    solution = data['solution']  # (365, 23)
    Npump = np.zeros((365, 24))
    
    for d in range(365):
        x = solution[d, :23]  # 23个决策变量
        
        # 初始化水库状态
        C = np.zeros(25)
        C[0] = 0.5  # 初始状态
        C[1:24] = x  # 23个决策变量
        C[24] = 0.5  # 周期约束
        
        for i in range(1, 25):
            if C[i] <= C[i-1]:  # 发电状态
                np_power = (C[i-1] - C[i]) * V
                if np_power < Zpump * 0.2:
                    np_power = 0
                    C[i] = C[i-1]
                elif np_power > Zpump:
                    np_power = Zpump
                    C[i] = C[i-1] - np_power / V
                Npump[d, i-1] = np_power
            else:  # 抽水状态
                np_power = (C[i-1] - C[i]) * V / 0.75
                if np_power > -Zpump * 0.2:
                    np_power = 0
                    C[i] = C[i-1]
                elif np_power < -Zpump:
                    np_power = -Zpump
                    C[i] = C[i-1] - np_power * 0.75 / V
                Npump[d, i-1] = np_power
    
    return Npump


def calculate_Nt(data, with_pump=True):
    """
    计算火电负荷
    Nt = L - (N + Npump)  有抽蓄
    Nt2 = L - N            无抽蓄
    """
    fh = data['fh']  # 火电负荷
    hydro = data['hydro']  # 水电
    wind = data['wind']  # 风电
    solar = data['solar']  # 光伏
    npump = data['np_raw']  # 抽水蓄能功率
    
    N = hydro + wind + solar  # 新能源总功率
    
    if with_pump:
        Nt = fh - (N + npump)  # 有抽蓄
    else:
        Nt = fh - N  # 无抽蓄
    
    return Nt


def load_all_data():
    """加载所有数据"""
    return load_mat_data()


def calculate_pumped_storage_schedule(np_power):
    """
    分析抽水蓄能调度策略
    NP > 0: 发电状态 (水轮机发电)
    NP < 0: 抽水状态 (抽水蓄能)
    NP = 0: 停机状态
    返回: 发电小时数, 抽水小时数, 停机小时数, 总发电量, 平均功率
    """
    # 发电小时数 (Npump > 0)
    generating_hours = int((np_power > 0).sum())
    # 抽水小时数 (Npump < 0)
    pumping_hours = int((np_power < 0).sum())
    # 停机小时数 (Npump = 0)
    idle_hours = int((np_power == 0).sum())
    
    # 总发电量 (MWh)
    total_generation = np_power[np_power > 0].sum() if generating_hours > 0 else 0
    # 总抽水耗电 (MWh)
    total_pumping = abs(np_power[np_power < 0].sum()) if pumping_hours > 0 else 0
    
    # 平均发电功率 (MW)
    avg_generation_power = np_power[np_power > 0].mean() if generating_hours > 0 else 0
    # 平均抽水功率 (MW)
    avg_pumping_power = abs(np_power[np_power < 0].mean()) if pumping_hours > 0 else 0
    
    # 综合转换效率
    efficiency = (total_generation / total_pumping * 100) if total_pumping > 0 else 0
    
    return {
        'generating_hours': generating_hours,
        'pumping_hours': pumping_hours,
        'idle_hours': idle_hours,
        'total_generation': total_generation,
        'total_pumping': total_pumping,
        'avg_generation_power': avg_generation_power,
        'avg_pumping_power': avg_pumping_power,
        'efficiency': efficiency
    }


def calculate_carbon_reduction(data):
    """
    计算碳减排
    碳排放变化 = |有抽蓄火电负荷 - 无抽蓄火电负荷| × 碳排放系数
    注意：不使用绝对值，正确反映碳排放增减方向
    """
    fh = data['fh']  # 火电负荷
    hydro = data['hydro']  # 水电
    wind = data['wind']  #风电
    solar = data['solar']  # 光伏
    npump = data['np_raw']  # 抽水蓄能功率
    
    N = hydro + wind + solar  # 新能源总功率
    
    # 有抽蓄时的火电负荷
    Nt = fh - (N + npump)
    # 无抽蓄时的火电负荷
    Nt2 = fh - N
    
    # 火电负荷变化量 (亿kWh)
    # 正值表示火电增发，负值表示火电减少
    power_change = (Nt.sum() - Nt2.sum()) / 1e6
    
    # 碳排放系数 (吨CO2/万kWh)
    carbon_factor = 0.5
    
    # 碳排放变化量 (万吨)
    # 正值表示碳排放增加，负值表示碳减排
    carbon_change = power_change * 1e4 * carbon_factor / 1e4
    
    # 每天碳排放变化
    daily_carbon_change = (Nt - Nt2).sum(axis=1) / 1e6 * 1e4 * carbon_factor / 1e4
    
    return {
        'power_change': power_change,  # 火电变化 (亿kWh)，正=增发，负=减发
        'carbon_change': carbon_change,  # 碳排放变化 (万吨)，正=增加，负=减排
        'daily_carbon_change': daily_carbon_change,  # 每天碳排放变化
        'Nt': Nt,  # 有抽蓄火电负荷
        'Nt2': Nt2,  # 无抽蓄火电负荷
        'carbon_factor': carbon_factor  # 碳排放系数
    }
