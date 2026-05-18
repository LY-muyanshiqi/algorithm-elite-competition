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
    data['np_raw'], C_all = calculate_npump(data)
    # 构建水库状态向量CC（仿main.m）
    data['cc'] = compute_cc_from_C(C_all)
    # 计算有/无抽蓄的火电功率
    data['Nt'] = calculate_Nt(data, with_pump=True)  # 有抽蓄
    data['Nt2'] = calculate_Nt(data, with_pump=False)  # 无抽蓄
    
    return data


def calculate_npump(data, Zpump=1400, h=4, efficiency=0.75, min_power_ratio=0.2):
    """
    计算抽水蓄能功率 (仿照process.m)
    决策变量 x: 23个值，代表每个时刻结束时水库状态比例 [0,1]
    
    参数:
    - Zpump: 抽水蓄能装机容量 (MW)，默认1400
    - h: 蓄能时长 (小时)，默认4
    - efficiency: 抽水效率，默认0.75
    - min_power_ratio: 最小出力比例，默认0.2
    """
    V = Zpump * h  # 蓄能容量 (MWh)
    
    solution = data['solution']  # (365, 23)
    Npump = np.zeros((365, 24))
    C_all = np.zeros((365, 25))

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
                if np_power < Zpump * min_power_ratio:
                    np_power = 0
                    C[i] = C[i-1]
                elif np_power > Zpump:
                    np_power = Zpump
                    C[i] = C[i-1] - np_power / V
                Npump[d, i-1] = np_power
            else:  # 抽水状态
                np_power = (C[i-1] - C[i]) * V / efficiency
                if np_power > -Zpump * min_power_ratio:
                    np_power = 0
                    C[i] = C[i-1]
                elif np_power < -Zpump:
                    np_power = -Zpump
                    C[i] = C[i-1] - np_power * efficiency / V
                Npump[d, i-1] = np_power

        C_all[d, :] = C

    return Npump, C_all


def compute_cc_from_C(C_all):
    """根据水库状态矩阵构建CC向量（仿main.m）
    C_all: (365, 25) - 每天25个水库状态值
    CC[0] = 0.5 初始状态, CC[1:8761] = 8760小时水库状态
    """
    cc = np.zeros(8761)
    cc[0] = 0.5
    cc[1:8761] = C_all[:, 1:25].reshape(8760)
    return cc


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


def calculate_carbon_reduction(data, carbon_factor=0.5, coal_consumption_high=300, coal_consumption_mid=330, coal_consumption_low=370):
    """
    计算碳减排
    碳排放变化 = |有抽蓄火电负荷 - 无抽蓄火电负荷| × 碳排放系数
    注意：不使用绝对值，正确反映碳排放增减方向
    
    参数:
    - carbon_factor: 碳排放系数 (吨CO2/万kWh)，默认0.5
    - coal_consumption_high: 高负荷煤耗 (g/kWh)，默认300
    - coal_consumption_mid: 中度调峰煤耗 (g/kWh)，默认330
    - coal_consumption_low: 深度调峰煤耗 (g/kWh)，默认370
    """
    fh = data['fh']  # 火电负荷
    hydro = data['hydro']  # 水电
    wind = data['wind']  #风电
    solar = data['solar']  # 光伏
    npump = data.get('np_raw', np.zeros_like(fh))  # 抽水蓄能功率
    
    N = hydro + wind + solar  # 新能源总功率
    
    # 有抽蓄时的火电负荷
    Nt = fh - (N + npump)
    # 无抽蓄时的火电负荷
    Nt2 = fh - N
    
    # 计算分段碳排放强度
    def calculate_emission_intensity(power, max_power=1000):
        """根据负荷率计算碳排放强度"""
        load_rate = power / max_power
        if load_rate > 0.5:
            return coal_consumption_high * 3.67 / 1000  # kg/kWh -> t/MWh
        elif load_rate > 0.3:
            return coal_consumption_mid * 3.67 / 1000
        else:
            return coal_consumption_low * 3.67 / 1000
    
    # 火电负荷变化量 (亿kWh)
    # 正值表示火电增发，负值表示火电减少
    power_change = (Nt.sum() - Nt2.sum()) / 1e6
    
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
        'carbon_factor': carbon_factor,  # 碳排放系数
        'coal_consumption': {'high': coal_consumption_high, 'mid': coal_consumption_mid, 'low': coal_consumption_low}
    }


def recalculate_with_parameters(data, params):
    """
    使用自定义参数重新计算所有指标
    params字典包含:
    - Zpump: 抽蓄额定功率 (MW)
    - h: 蓄能时长 (h)
    - efficiency: 抽水效率
    - min_power_ratio: 最小出力比例
    - carbon_factor: 碳排放系数
    - coal_consumption_high: 高负荷煤耗
    - coal_consumption_mid: 中度调峰煤耗
    - coal_consumption_low: 深度调峰煤耗
    """
    # 重新计算抽蓄功率
    np_raw, C_all = calculate_npump(
        data,
        Zpump=params.get('Zpump', 1400),
        h=params.get('h', 4),
        efficiency=params.get('efficiency', 0.75),
        min_power_ratio=params.get('min_power_ratio', 0.2)
    )
    cc = compute_cc_from_C(C_all)
    
    # 重新计算火电功率
    fh = data['fh']
    hydro = data['hydro']
    wind = data['wind']
    solar = data['solar']
    N = hydro + wind + solar
    
    Nt = fh - (N + np_raw)  # 有抽蓄
    Nt2 = fh - N  # 无抽蓄
    
    # 重新计算碳减排
    carbon_result = calculate_carbon_reduction(
        {**data, 'np_raw': np_raw},
        carbon_factor=params.get('carbon_factor', 0.5),
        coal_consumption_high=params.get('coal_consumption_high', 300),
        coal_consumption_mid=params.get('coal_consumption_mid', 330),
        coal_consumption_low=params.get('coal_consumption_low', 370)
    )
    
    # 计算抽水蓄能调度统计
    ps_stats = calculate_pumped_storage_schedule(np_raw)
    
    return {
        'np_raw': np_raw,
        'Nt': Nt,
        'Nt2': Nt2,
        'cc': cc,
        'carbon_result': carbon_result,
        'ps_stats': ps_stats,
        'params': params
    }
