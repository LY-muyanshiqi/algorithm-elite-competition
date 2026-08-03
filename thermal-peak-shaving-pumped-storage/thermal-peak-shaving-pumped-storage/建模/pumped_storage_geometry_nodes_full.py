"""
Blender 几何节点快速生成器代码（全资产包）- 完整版
基于 Blender 3.6+ 版本编写

⚠️ 重要说明：
- 所有尺寸单位均为 厘米 (cm)，与 Tripo AI 默认输出单位一致
- 每个部件都有独立的 PBR 材质和颜色
- 包含优化的相机视角设置

使用方法：
1. 打开 Blender，切换到 "脚本" 工作区
2. 新建一个文本文件 (New)
3. 复制下面的代码并粘贴
4. 点击 "运行脚本"(Run Script)
5. 切换到 "几何节点" 工作区，在 "添加"→"组" 中找到对应的生成器节点

所有生成器均以 "PSP_" 前缀命名（Pumped Storage Plant）
"""

import bpy
import random

# ======================
# 材质定义（PBR标准）
# ======================
MATERIALS = {
    '混凝土': {'base_color': (0.5, 0.5, 0.5, 1), 'roughness': 0.8, 'metallic': 0.0},
    '水': {'base_color': (0.2, 0.5, 0.8, 0.8), 'roughness': 0.1, 'metallic': 0.0},
    '金属': {'base_color': (0.7, 0.7, 0.7, 1), 'roughness': 0.3, 'metallic': 0.8},
    '白色漆面': {'base_color': (0.95, 0.95, 0.95, 1), 'roughness': 0.3, 'metallic': 0.1},
    '光伏玻璃': {'base_color': (0.1, 0.5, 0.8, 0.9), 'roughness': 0.1, 'metallic': 0.2},
    '住宅外墙': {'base_color': (0.8, 0.7, 0.6, 1), 'roughness': 0.7, 'metallic': 0.0},
    '地面': {'base_color': (0.2, 0.4, 0.2, 1), 'roughness': 0.9, 'metallic': 0.0},
    '工业建筑': {'base_color': (0.7, 0.7, 0.7, 1), 'roughness': 0.6, 'metallic': 0.1},
    '蓝色': {'base_color': (0.2, 0.4, 0.8, 1), 'roughness': 0.5, 'metallic': 0.2},
    '红色': {'base_color': (0.8, 0.2, 0.2, 1), 'roughness': 0.5, 'metallic': 0.2},
    '黄色': {'base_color': (0.8, 0.7, 0.2, 1), 'roughness': 0.5, 'metallic': 0.1},
    '绿色': {'base_color': (0.2, 0.6, 0.3, 1), 'roughness': 0.6, 'metallic': 0.0},
    '橙色': {'base_color': (0.9, 0.5, 0.2, 1), 'roughness': 0.5, 'metallic': 0.1},
    '紫色': {'base_color': (0.6, 0.3, 0.8, 1), 'roughness': 0.5, 'metallic': 0.2},
}

def create_material(name, base_color, roughness, metallic):
    """创建PBR材质"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # 清除默认节点
    for node in nodes:
        nodes.remove(node)
    
    # 创建节点
    output_node = nodes.new('ShaderNodeOutputMaterial')
    bsdf_node = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf_node.inputs['Base Color'].default_value = base_color
    bsdf_node.inputs['Roughness'].default_value = roughness
    bsdf_node.inputs['Metallic'].default_value = metallic
    
    links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
    return mat

def apply_material(obj, material_name):
    """为对象应用材质"""
    if material_name in MATERIALS:
        mat = create_material(f'PBR_{material_name}', **MATERIALS[material_name])
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

# ======================
# 相机设置
# ======================
def setup_camera():
    """设置优化的相机视角"""
    # 删除默认相机
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            bpy.data.objects.remove(obj)
    
    # 创建新相机
    bpy.ops.object.camera_add(location=(30000, -25000, 15000))  # 500m远视角
    camera = bpy.context.active_object
    camera.name = "主相机"
    camera.rotation_euler = (1.0, 0, 0.785)  # 约57度俯视角，45度侧视角
    
    # 设置相机参数
    camera.data.type = 'PERSP'
    camera.data.lens = 35  # 广角镜头
    camera.data.clip_start = 100  # 1m
    camera.data.clip_end = 1000000  # 10000m
    
    # 设置为活动相机
    bpy.context.scene.camera = camera
    
    # 设置渲染分辨率
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080

def setup_lighting():
    """设置环境光照"""
    # 删除默认灯光
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj)
    
    # 创建主光源（太阳光）
    bpy.ops.object.light_add(type='SUN', location=(50000, 50000, 80000))
    sun = bpy.context.active_object
    sun.name = "太阳光"
    sun.data.energy = 3
    sun.data.angle = 0.1
    sun.rotation_euler = (0.8, 0.3, 0.5)
    
    # 创建环境光
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 100000))
    area_light = bpy.context.active_object
    area_light.name = "环境光"
    area_light.data.energy = 1000
    area_light.data.size = 100000
    
    # 设置世界环境
    world = bpy.context.scene.world
    world.use_nodes = True
    bg_node = world.node_tree.nodes['Background']
    bg_node.inputs['Color'].default_value = (0.6, 0.7, 0.8, 1)
    bg_node.inputs['Strength'].default_value = 0.5

# ======================
# 高级功能：一键完整场景生成器 (单位: cm)
# ======================
def generate_complete_system():
    """一键生成完整综合能源系统场景（厘米单位）"""
    # 清空场景
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # 设置相机和光照
    setup_camera()
    setup_lighting()
    
    # 1. 生成地形
    bpy.ops.mesh.primitive_plane_add(size=500000, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "地形"
    apply_material(terrain, '地面')
    
    # 添加地形修改器
    mod = terrain.modifiers.new(name="地形噪声", type='DISPLACE')
    tex = bpy.data.textures.new(name="地形纹理", type='CLOUDS')
    tex.noise_scale = 50000.0
    mod.texture = tex
    mod.strength = 80000.0
    
    # 2. 生成抽水蓄能电站
    # 上水库
    bpy.ops.mesh.primitive_plane_add(size=80000, location=(0, -150000, 60000))
    upper_reservoir = bpy.context.active_object
    upper_reservoir.name = "上水库"
    apply_material(upper_reservoir, '水')
    
    # 上水库大坝
    bpy.ops.mesh.primitive_cube_add(size=5000, location=(0, -150000, 45000))
    upper_dam = bpy.context.active_object
    upper_dam.name = "上水库大坝"
    upper_dam.scale = (30, 1, 12)
    apply_material(upper_dam, '混凝土')
    
    # 下水库
    bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 150000, 10000))
    lower_reservoir = bpy.context.active_object
    lower_reservoir.name = "下水库"
    apply_material(lower_reservoir, '水')
    
    # 下水库大坝
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(0, 150000, 5000))
    lower_dam = bpy.context.active_object
    lower_dam.name = "下水库大坝"
    lower_dam.scale = (25, 1, 8)
    apply_material(lower_dam, '混凝土')
    
    # 地下厂房
    bpy.ops.mesh.primitive_cube_add(size=3000, location=(0, 0, -5000))
    underground_plant = bpy.context.active_object
    underground_plant.name = "地下厂房"
    underground_plant.scale = (67, 10, 17)
    apply_material(underground_plant, '混凝土')
    
    # 引水隧洞（透明效果展示）
    bpy.ops.mesh.primitive_cylinder_add(radius=400, depth=150000, location=(0, -75000, 35000))
    tunnel = bpy.context.active_object
    tunnel.name = "引水隧洞"
    tunnel.rotation_euler = (1.57, 0, 0)
    tunnel_mat = create_material('隧洞材质', (0.3, 0.5, 0.7, 0.5), 0.9, 0.0)
    tunnel.data.materials.append(tunnel_mat)
    
    # 3. 生成火力发电厂
    # 主厂房
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(-200000, 0, 15000))
    thermal_plant = bpy.context.active_object
    thermal_plant.name = "火力发电厂"
    thermal_plant.scale = (30, 10, 7.5)
    apply_material(thermal_plant, '工业建筑')
    
    # 冷却塔 (2座)
    for i in range(2):
        bpy.ops.mesh.primitive_cylinder_add(radius=4000, depth=12000, location=(-200000, -20000+i*40000, 11000))
        cooling_tower = bpy.context.active_object
        cooling_tower.name = f"冷却塔_{i+1}"
        apply_material(cooling_tower, '混凝土')
    
    # 烟囱
    bpy.ops.mesh.primitive_cylinder_add(radius=500, depth=15000, location=(-185000, 0, 20000))
    chimney = bpy.context.active_object
    chimney.name = "烟囱"
    apply_material(chimney, '混凝土')
    
    # 4. 生成风电场 (5台)
    for i in range(5):
        x = -200000 + i * 100000
        y = -200000
        # 塔筒
        bpy.ops.mesh.primitive_cylinder_add(radius=200, depth=10000, location=(x, y, 5000))
        tower = bpy.context.active_object
        tower.name = f"风电机_{i+1}_塔筒"
        apply_material(tower, '白色漆面')
        # 机舱
        bpy.ops.mesh.primitive_cube_add(size=2000, location=(x, y, 15000))
        nacelle = bpy.context.active_object
        nacelle.name = f"风电机_{i+1}_机舱"
        nacelle.scale = (3, 1.5, 1)
        apply_material(nacelle, '白色漆面')
        # 叶片 (简化为锥体)
        for j in range(3):
            angle = j * 2.0944  # 120度
            bpy.ops.mesh.primitive_cone_add(radius1=50, radius2=10, depth=5500, location=(x, y, 15000))
            blade = bpy.context.active_object
            blade.name = f"风电机_{i+1}_叶片_{j+1}"
            blade.rotation_euler = (0, angle, 0.3)
            apply_material(blade, '白色漆面')
    
    # 5. 生成光伏电站 (10x10阵列)
    for i in range(10):
        for j in range(10):
            x = 150000 + i * 3000
            y = -100000 + j * 2000
            bpy.ops.mesh.primitive_plane_add(size=200, location=(x, y, 3000))
            solar_panel = bpy.context.active_object
            solar_panel.name = f"光伏板_{i*10+j+1}"
            solar_panel.rotation_euler = (0.5236, 0, 0)  # 30度倾斜
            apply_material(solar_panel, '光伏玻璃')
    
    # 逆变器房
    bpy.ops.mesh.primitive_cube_add(size=1000, location=(165000, -90000, 1500))
    inverter_room = bpy.context.active_object
    inverter_room.name = "逆变器房"
    inverter_room.scale = (6, 4, 3)
    apply_material(inverter_room, '金属')
    
    # 6. 生成电网系统
    # 220kV枢纽变电站
    bpy.ops.mesh.primitive_cube_add(size=5000, location=(0, 0, 2500))
    substation_220 = bpy.context.active_object
    substation_220.name = "220kV枢纽变电站"
    substation_220.scale = (30, 24, 5)
    apply_material(substation_220, '金属')
    
    # 110kV区域变电站
    bpy.ops.mesh.primitive_cube_add(size=3000, location=(-100000, 50000, 2000))
    substation_110 = bpy.context.active_object
    substation_110.name = "110kV区域变电站"
    substation_110.scale = (20, 16, 4)
    apply_material(substation_110, '蓝色')
    
    # 10kV终端变电站
    bpy.ops.mesh.primitive_cube_add(size=2000, location=(100000, 100000, 1500))
    substation_10 = bpy.context.active_object
    substation_10.name = "10kV终端变电站"
    substation_10.scale = (15, 12, 3)
    apply_material(substation_10, '绿色')
    
    # 输电铁塔 (9座)
    tower_positions = [
        (-150000, 0), (-50000, 0), (50000, 0), (150000, 0),
        (-100000, 50000), (0, 50000), (100000, 50000),
        (50000, 100000), (150000, 100000)
    ]
    colors = ['金属', '金属', '金属', '金属', '蓝色', '蓝色', '蓝色', '绿色', '绿色']
    
    for i, (x, y) in enumerate(tower_positions):
        bpy.ops.mesh.primitive_cone_add(radius1=200, radius2=800, depth=4000, location=(x, y, 2000))
        tower = bpy.context.active_object
        tower.name = f"输电铁塔_{i+1}"
        apply_material(tower, colors[i])
    
    # 7. 生成居民区 (5x5)
    colors = ['住宅外墙', '黄色', '橙色', '蓝色', '紫色']
    for i in range(5):
        for j in range(5):
            x = 150000 + i * 6000
            y = 150000 + j * 6000
            bpy.ops.mesh.primitive_cube_add(size=2000, location=(x, y, 6000))
            building = bpy.context.active_object
            building.name = f"居民楼_{i*5+j+1}"
            building.scale = (1, 0.75, 2)
            apply_material(building, colors[j % 5])
    
    # 小区配电箱
    for i in range(4):
        for j in range(4):
            x = 153000 + i * 6000
            y = 153000 + j * 6000
            bpy.ops.mesh.primitive_cube_add(size=200, location=(x, y, 2000))
            box = bpy.context.active_object
            box.name = f"配电箱_{i*4+j+1}"
            apply_material(box, '金属')
    
    print("\n=== 完整综合能源系统场景已生成！ ===")
    print("✓ 相机视角已优化")
    print("✓ 所有部件已添加PBR材质颜色")

# ======================
# 启动选项
# ======================
if __name__ == "__main__":
    print("=== 生成完整综合能源系统场景 ===")
    print("✓ 配置相机视角")
    print("✓ 配置环境光照")
    print("✓ 添加PBR材质颜色")
    generate_complete_system()