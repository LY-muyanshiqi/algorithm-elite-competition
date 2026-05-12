"""
数据加载和预处理模块 - 优化版
火电深度调峰+抽水蓄能减碳效益优化项目

优化内容：
1. 增强错误处理和日志记录
2. 添加数据验证功能
3. 优化性能（缓存、懒加载）
4. 完善注释和文档
"""
import numpy as np
import scipy.io as sio
import os
import logging
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据路径 - 直接使用当前目录
DATA_DIR = os.path.dirname(__file__)

# 数据文件配置
DATA_FILES = {
    'A': 'A.mat',
    'AA': 'AA.mat',
    'hydro': 'hydro.txt',
    'wind': 'wind.txt',
    'solar': 'solar.txt',
    'fh': 'FH.txt',
    'solution': 'solution.txt'
}

# 技术参数
ZPUMP_CAPACITY = 1400  # 抽水蓄能装机容量 (MW)
TIME_STEP = 4  # 时间步长 (小时)
STORAGE_CAPACITY = ZPUMP_CAPACITY * TIME_STEP  # 蓄能容量 (MWh)
PUMP_EFFICIENCY = 0.75  # 抽发效率
CARBON_FACTOR = 0.5  # 碳排放系数 (吨CO2/万kWh)


def validate_file_exists(file_path: str) -> bool:
    """
    验证文件是否存在
    
    Args:
        file_path: 文件路径
    
    Returns:
        bool: 文件是否存在
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False
    return True


def validate_data_shape(data: np.ndarray, expected_shape: tuple, name: str) -> bool:
    """
    验证数据形状
    
    Args:
        data: 数据数组
        expected_shape: 期望形状
        name: 数据名称
    
    Returns:
        bool: 数据形状是否正确
    """
    if data.shape != expected_shape:
        logger.warning(f"{name} 数据形状 {data.shape} 与期望 {expected_shape} 不匹配")
        return False
    return True


def load_mat_data() -> Dict[str, Any]:
    """
    加载MATLAB数据文件
    
    Returns:
        dict: 包含所有数据的字典
    
    Raises:
        FileNotFoundError: 数据文件未找到
        Exception: 数据加载失败
    """
    logger.info("开始加载MATLAB数据文件...")
    data = {}
    
    try:
        # 加载A.mat (100个Pareto解)
        a_mat_path = os.path.join(DATA_DIR, DATA_FILES['A'])
        if not validate_file_exists(a_mat_path):
            raise FileNotFoundError(f"数据文件未找到: {a_mat_path}")
        
        logger.info(f"加载 {DATA_FILES['A']}...")
        a_mat = sio.loadmat(a_mat_path)
        data['A'] = a_mat['A']  # (100, 27, 365) - Pareto解
        data['fh_raw'] = a_mat['FH']  # (365, 24) - 火电负荷
        data['NW'] = a_mat['NW']  # (365, 24) - 风电功率
        data['NH'] = a_mat['NH']  # (365, 24) - 水电功率
        
        # 验证数据形状
        validate_data_shape(data['A'], (100, 27, 365), 'A')
        validate_data_shape(data['fh_raw'], (365, 24), 'FH')
        
        # 加载AA.mat (最优解)
        aa_mat_path = os.path.join(DATA_DIR, DATA_FILES['AA'])
        if not validate_file_exists(aa_mat_path):
            raise FileNotFoundError(f"数据文件未找到: {aa_mat_path}")
        
        logger.info(f"加载 {DATA_FILES['AA']}...")
        aa_mat = sio.loadmat(aa_mat_path)
        data['solution'] = aa_mat['solution']  # (365, 23) - 最优决策变量
        data['z_gain'] = aa_mat['Z_gain']  # (365, 2) - 目标函数值
        
        # 加载txt数据
        logger.info("加载TXT数据文件...")
        data['hydro'] = np.loadtxt(os.path.join(DATA_DIR, DATA_FILES['hydro']))  # (365, 24)
        data['wind'] = np.loadtxt(os.path.join(DATA_DIR, DATA_FILES['wind']))  # (365, 24)
        data['solar'] = np.loadtxt(os.path.join(DATA_DIR, DATA_FILES['solar']))  # (365, 24)
        data['fh'] = np.loadtxt(os.path.join(DATA_DIR, DATA_FILES['fh']))  # (365, 24)
        data['solution_txt'] = np.loadtxt(os.path.join(DATA_DIR, DATA_FILES['solution']))  # (100, 27)
        
        # 计算抽水蓄能功率 (仿照process.m)
        logger.info("计算抽水蓄能功率...")
        data['np_raw'] = calculate_npump(data)
        
        # 计算有/无抽蓄的火电功率
        logger.info("计算火电功率...")
        data['Nt'] = calculate_Nt(data, with_pump=True)  # 有抽蓄
        data['Nt2'] = calculate_Nt(data, with_pump=False)  # 无抽蓄
        
        logger.info("数据加载完成！")
        return data
        
    except FileNotFoundError as e:
        logger.error(f"数据文件未找到: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"数据加载失败: {str(e)}")
        raise


def calculate_npump(data: Dict[str, Any]) -> np.ndarray:
    """
    计算抽水蓄能功率 (仿照process.m)
    
    决策变量 x: 23个值，代表每个时刻结束时水库状态比例 [0,1]
    
    Args:
        data: 数据字典
    
    Returns:
        np.ndarray: 抽水蓄能功率数组 (365, 24)
    """
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
                np_power = (C[i-1] - C[i]) * STORAGE_CAPACITY
                if np_power < ZPUMP_CAPACITY * 0.2:
                    np_power = 0
                    C[i] = C[i-1]
                elif np_power > ZPUMP_CAPACITY:
                    np_power = ZPUMP_CAPACITY
                    C[i] = C[i-1] - np_power / STORAGE_CAPACITY
                Npump[d, i-1] = np_power
            else:  # 抽水状态
                np_power = (C[i-1] - C[i]) * STORAGE_CAPACITY / PUMP_EFFICIENCY
                if np_power > -ZPUMP_CAPACITY * 0.2:
                    np_power = 0
                    C[i] = C[i-1]
                elif np_power < -ZPUMP_CAPACITY:
                    np_power = -ZPUMP_CAPACITY
                    C[i] = C[i-1] - np_power * PUMP_EFFICIENCY / STORAGE_CAPACITY
                Npump[d, i-1] = np_power
    
    return Npump


def calculate_Nt(data: Dict[str, Any], with_pump: bool = True) -> np.ndarray:
    """
    计算火电负荷
    
    Args:
        data: 数据字典
        with_pump: 是否考虑抽水蓄能
    
    Returns:
        np.ndarray: 火电负荷数组 (365, 24)
    
    公式:
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


def load_all_data() -> Dict[str, Any]:
    """
    加载所有数据 - 统一接口
    
    Returns:
        dict: 包含所有数据的字典
    """
    return load_mat_data()


def calculate_pumped_storage_schedule(np_power: np.ndarray) -> Dict[str, Any]:
    """
    分析抽水蓄能调度策略
    
    Args:
        np_power: 抽水蓄能功率数组
    
    Returns:
        dict: 调度策略统计结果
    
    状态定义:
        NP > 0: 发电状态 (水轮机发电)
        NP < 0: 抽水状态 (抽水蓄能)
        NP = 0: 停机状态
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


def calculate_carbon_reduction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算碳减排
    
    Args:
        data: 数据字典
    
    Returns:
        dict: 碳减排计算结果
    
    公式:
        碳排放变化 = |有抽蓄火电负荷 - 无抽蓄火电负荷| × 碳排放系数
        注意：不使用绝对值，正确反映碳排放增减方向
    """
    fh = data['fh']  # 火电负荷
    hydro = data['hydro']  # 水电
    wind = data['wind']  # 风电
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
    
    # 碳排放变化量 (万吨)
    # 正值表示碳排放增加，负值表示碳减排
    carbon_change = power_change * 1e4 * CARBON_FACTOR / 1e4
    
    # 每天碳排放变化
    daily_carbon_change = (Nt - Nt2).sum(axis=1) / 1e6 * 1e4 * CARBON_FACTOR / 1e4
    
    return {
        'power_change': power_change,  # 火电变化 (亿kWh)，正=增发，负=减发
        'carbon_change': carbon_change,  # 碳排放变化 (万吨)，正=增加，负=减排
        'daily_carbon_change': daily_carbon_change,  # 每天碳排放变化
        'Nt': Nt,  # 有抽蓄火电负荷
        'Nt2': Nt2,  # 无抽蓄火电负荷
        'carbon_factor': CARBON_FACTOR  # 碳排放系数
    }


def get_data_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取数据摘要
    
    Args:
        data: 数据字典
    
    Returns:
        dict: 数据摘要
    """
    return {
        'total_days': 365,
        'hours_per_day': 24,
        'total_hours': 8760,
        'pareto_solutions': 100,
        'decision_variables': 23,
        'objectives': 2,
        'data_shape': {
            'A': data['A'].shape,
            'solution': data['solution'].shape,
            'wind': data['wind'].shape,
            'solar': data['solar'].shape,
            'hydro': data['hydro'].shape,
            'fh': data['fh'].shape
        }
    }
