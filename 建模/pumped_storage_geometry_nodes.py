"""
Blender 几何节点快速生成器代码（全资产包）
基于 Blender 3.6+ 版本编写

使用方法：
1. 打开 Blender，切换到 "脚本" 工作区
2. 新建一个文本文件 (New)
3. 复制下面的代码并粘贴
4. 点击 "运行脚本"(Run Script)
5. 切换到 "几何节点" 工作区，在 "添加"→"组" 中找到对应的生成器节点

所有生成器均以 "PSP_" 前缀命名（Pumped Storage Plant）
"""

import bpy

# 清空现有节点组
for group in bpy.data.node_groups:
    if group.name.startswith("PSP_"):
        bpy.data.node_groups.remove(group)

# ======================
# 1. 上水库大坝生成器
# ======================
def create_dam_generator():
    group = bpy.data.node_groups.new("PSP_UpperDam", "GeometryNodeTree")
    
    # 输入节点
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 300.0
    group.inputs.new("NodeSocketFloat", "底部宽度")
    group.inputs["底部宽度"].default_value = 50.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 120.0
    group.inputs.new("NodeSocketFloat", "迎水面坡度")
    group.inputs["迎水面坡度"].default_value = 0.7
    group.inputs.new("NodeSocketFloat", "背水面坡度")
    group.inputs["背水面坡度"].default_value = 0.5
    
    # 梯形截面生成
    curve_node = group.nodes.new("GeometryNodeCurvePrimitiveBezierSegment")
    curve_node.location = (-200, 200)
    curve_node.inputs["Resolution"].default_value = 2
    
    # 计算顶部宽度
    math1 = group.nodes.new("ShaderNodeMath")
    math1.location = (-200, 100)
    math1.operation = "MULTIPLY"
    group.links.new(input_node.outputs["高度"], math1.inputs[0])
    group.links.new(input_node.outputs["迎水面坡度"], math1.inputs[1])
    
    math2 = group.nodes.new("ShaderNodeMath")
    math2.location = (-200, 50)
    math2.operation = "MULTIPLY"
    group.links.new(input_node.outputs["高度"], math2.inputs[0])
    group.links.new(input_node.outputs["背水面坡度"], math2.inputs[1])
    
    math3 = group.nodes.new("ShaderNodeMath")
    math3.location = (-200, 0)
    math3.operation = "ADD"
    group.links.new(math1.outputs[0], math3.inputs[0])
    group.links.new(math2.outputs[0], math3.inputs[1])
    
    math4 = group.nodes.new("ShaderNodeMath")
    math4.location = (-200, -50)
    math4.operation = "SUBTRACT"
    group.links.new(input_node.outputs["底部宽度"], math4.inputs[0])
    group.links.new(math3.outputs[0], math4.inputs[1])
    
    # 设置曲线点
    set_point1 = group.nodes.new("GeometryNodeSetPosition")
    set_point1.location = (0, 200)
    group.links.new(curve_node.outputs["Curve"], set_point1.inputs["Geometry"])
    
    # 挤出成体
    extrude_node = group.nodes.new("GeometryNodeExtrudeMesh")
    extrude_node.location = (200, 0)
    extrude_node.inputs["Offset Scale"].default_value = 1.0
    
    # 曲线转网格
    curve_to_mesh = group.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (0, 0)
    group.links.new(curve_node.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    
    group.links.new(curve_to_mesh.outputs["Mesh"], extrude_node.inputs["Mesh"])
    group.links.new(input_node.outputs["长度"], extrude_node.inputs["Offset"])
    
    # 输出节点
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (400, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(extrude_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 2. 水库水体生成器
# ======================
def create_reservoir_generator():
    group = bpy.data.node_groups.new("PSP_ReservoirWater", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 800.0
    group.inputs.new("NodeSocketFloat", "宽度")
    group.inputs["宽度"].default_value = 600.0
    group.inputs.new("NodeSocketFloat", "深度")
    group.inputs["深度"].default_value = 30.0
    group.inputs.new("NodeSocketFloat", "不规则度")
    group.inputs["不规则度"].default_value = 0.2
    
    # 基础平面
    plane_node = group.nodes.new("GeometryNodeMeshPrimitivePlane")
    plane_node.location = (-200, 0)
    group.links.new(input_node.outputs["长度"], plane_node.inputs["Size X"])
    group.links.new(input_node.outputs["宽度"], plane_node.inputs["Size Y"])
    plane_node.inputs["Vertices X"].default_value = 20
    plane_node.inputs["Vertices Y"].default_value = 20
    
    # 添加噪声变形
    noise_node = group.nodes.new("GeometryNodeDisplace")
    noise_node.location = (0, 0)
    noise_node.inputs["Scale"].default_value = 50.0
    group.links.new(plane_node.outputs["Mesh"], noise_node.inputs["Geometry"])
    
    # 噪波纹理
    texture_node = group.nodes.new("GeometryNodeTextureNoise")
    texture_node.location = (-100, -100)
    texture_node.inputs["Scale"].default_value = 50.0
    group.links.new(texture_node.outputs["Color"], noise_node.inputs["Displacement"])
    
    # 挤出成水体
    extrude_node = group.nodes.new("GeometryNodeExtrudeMesh")
    extrude_node.location = (200, 0)
    extrude_node.inputs["Offset Scale"].default_value = -1.0
    group.links.new(noise_node.outputs["Geometry"], extrude_node.inputs["Mesh"])
    group.links.new(input_node.outputs["深度"], extrude_node.inputs["Offset"])
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (400, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(extrude_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 3. 隧洞生成器
# ======================
def create_tunnel_generator():
    group = bpy.data.node_groups.new("PSP_Tunnel", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 1500.0
    group.inputs.new("NodeSocketFloat", "直径")
    group.inputs["直径"].default_value = 8.0
    group.inputs.new("NodeSocketFloat", "弯曲角度")
    group.inputs["弯曲角度"].default_value = 0.0
    
    # 圆形截面
    circle_node = group.nodes.new("GeometryNodeCurvePrimitiveCircle")
    circle_node.location = (-200, 100)
    group.links.new(input_node.outputs["直径"], circle_node.inputs["Radius"])
    circle_node.inputs["Resolution"].default_value = 16
    
    # 沿曲线挤出
    curve_node = group.nodes.new("GeometryNodeCurvePrimitiveBezierSegment")
    curve_node.location = (-200, 0)
    group.links.new(input_node.outputs["长度"], curve_node.inputs["Length"])
    
    # 曲线转网格
    curve_to_mesh = group.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.location = (0, 0)
    group.links.new(curve_node.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    group.links.new(circle_node.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
    
    # 输出节点
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (200, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(curve_to_mesh.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 4. 地下厂房生成器
# ======================
def create_underground_plant_generator():
    group = bpy.data.node_groups.new("PSP_UndergroundPlant", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 200.0
    group.inputs.new("NodeSocketFloat", "宽度")
    group.inputs["宽度"].default_value = 30.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 50.0
    
    # 基础立方体
    cube_node = group.nodes.new("GeometryNodeMeshPrimitiveCube")
    cube_node.location = (-200, 0)
    group.links.new(input_node.outputs["长度"], cube_node.inputs["Size X"])
    group.links.new(input_node.outputs["宽度"], cube_node.inputs["Size Y"])
    group.links.new(input_node.outputs["高度"], cube_node.inputs["Size Z"])
    
    # 输出节点
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cube_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 5. 水轮发电机组生成器
# ======================
def create_turbine_generator():
    group = bpy.data.node_groups.new("PSP_Turbine", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "直径")
    group.inputs["直径"].default_value = 20.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 25.0
    
    # 圆柱体底座
    cylinder_node = group.nodes.new("GeometryNodeMeshPrimitiveCylinder")
    cylinder_node.location = (-200, 0)
    group.links.new(input_node.outputs["直径"], cylinder_node.inputs["Radius"])
    group.links.new(input_node.outputs["高度"], cylinder_node.inputs["Depth"])
    cylinder_node.inputs["Vertices"].default_value = 32
    
    # 输出节点
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cylinder_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 6. 火力发电厂生成器
# ======================
def create_thermal_plant_generator():
    group = bpy.data.node_groups.new("PSP_ThermalPlant", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "厂房长度")
    group.inputs["厂房长度"].default_value = 120.0
    group.inputs.new("NodeSocketFloat", "厂房宽度")
    group.inputs["厂房宽度"].default_value = 40.0
    group.inputs.new("NodeSocketFloat", "厂房高度")
    group.inputs["厂房高度"].default_value = 30.0
    
    # 厂房主体
    cube_node = group.nodes.new("GeometryNodeMeshPrimitiveCube")
    cube_node.location = (-200, 0)
    group.links.new(input_node.outputs["厂房长度"], cube_node.inputs["Size X"])
    group.links.new(input_node.outputs["厂房宽度"], cube_node.inputs["Size Y"])
    group.links.new(input_node.outputs["厂房高度"], cube_node.inputs["Size Z"])
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cube_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 7. 双曲线冷却塔生成器
# ======================
def create_cooling_tower_generator():
    group = bpy.data.node_groups.new("PSP_CoolingTower", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "底部直径")
    group.inputs["底部直径"].default_value = 80.0
    group.inputs.new("NodeSocketFloat", "顶部直径")
    group.inputs["顶部直径"].default_value = 40.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 120.0
    
    # 基础圆柱体（用缩放模拟双曲线）
    cylinder_node = group.nodes.new("GeometryNodeMeshPrimitiveCylinder")
    cylinder_node.location = (-200, 0)
    cylinder_node.inputs["Radius"].default_value = 40.0
    group.links.new(input_node.outputs["高度"], cylinder_node.inputs["Depth"])
    cylinder_node.inputs["Vertices"].default_value = 64
    
    # 缩放修改
    transform_node = group.nodes.new("GeometryNodeTransform")
    transform_node.location = (0, 0)
    transform_node.inputs["Scale Y"].default_value = 0.5
    group.links.new(cylinder_node.outputs["Mesh"], transform_node.inputs["Geometry"])
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (200, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(transform_node.outputs["Geometry"], output_node.inputs["Geometry"])

# ======================
# 8. 烟囱生成器
# ======================
def create_chimney_generator():
    group = bpy.data.node_groups.new("PSP_Chimney", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "底部直径")
    group.inputs["底部直径"].default_value = 10.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 150.0
    
    # 圆柱体烟囱
    cylinder_node = group.nodes.new("GeometryNodeMeshPrimitiveCylinder")
    cylinder_node.location = (-200, 0)
    group.links.new(input_node.outputs["底部直径"], cylinder_node.inputs["Radius"])
    group.links.new(input_node.outputs["高度"], cylinder_node.inputs["Depth"])
    cylinder_node.inputs["Vertices"].default_value = 32
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cylinder_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 9. 光伏板阵列生成器
# ======================
def create_solar_panel_generator():
    group = bpy.data.node_groups.new("PSP_SolarPanel", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 2.0
    group.inputs.new("NodeSocketFloat", "宽度")
    group.inputs["宽度"].default_value = 1.0
    group.inputs.new("NodeSocketFloat", "厚度")
    group.inputs["厚度"].default_value = 0.1
    group.inputs.new("NodeSocketFloat", "倾斜角度")
    group.inputs["倾斜角度"].default_value = 30.0
    
    # 基础平面
    plane_node = group.nodes.new("GeometryNodeMeshPrimitivePlane")
    plane_node.location = (-200, 0)
    group.links.new(input_node.outputs["长度"], plane_node.inputs["Size X"])
    group.links.new(input_node.outputs["宽度"], plane_node.inputs["Size Y"])
    
    # 挤出厚度
    extrude_node = group.nodes.new("GeometryNodeExtrudeMesh")
    extrude_node.location = (0, 0)
    group.links.new(plane_node.outputs["Mesh"], extrude_node.inputs["Mesh"])
    group.links.new(input_node.outputs["厚度"], extrude_node.inputs["Offset"])
    
    # 旋转倾斜
    rotate_node = group.nodes.new("GeometryNodeRotate")
    rotate_node.location = (200, 0)
    rotate_node.inputs["Rotation"].default_value = (0.5236, 0, 0)  # 30度
    group.links.new(extrude_node.outputs["Mesh"], rotate_node.inputs["Geometry"])
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (400, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(rotate_node.outputs["Geometry"], output_node.inputs["Geometry"])

# ======================
# 10. 风电机组生成器
# ======================
def create_wind_turbine_generator():
    group = bpy.data.node_groups.new("PSP_WindTurbine", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "塔筒高度")
    group.inputs["塔筒高度"].default_value = 100.0
    group.inputs.new("NodeSocketFloat", "塔筒直径")
    group.inputs["塔筒直径"].default_value = 4.0
    group.inputs.new("NodeSocketFloat", "叶片长度")
    group.inputs["叶片长度"].default_value = 55.0
    
    # 塔筒
    cylinder_node = group.nodes.new("GeometryNodeMeshPrimitiveCylinder")
    cylinder_node.location = (-200, 0)
    group.links.new(input_node.outputs["塔筒直径"], cylinder_node.inputs["Radius"])
    group.links.new(input_node.outputs["塔筒高度"], cylinder_node.inputs["Depth"])
    cylinder_node.inputs["Vertices"].default_value = 32
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cylinder_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 11. 变电站生成器
# ======================
def create_substation_generator():
    group = bpy.data.node_groups.new("PSP_Substation", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 150.0
    group.inputs.new("NodeSocketFloat", "宽度")
    group.inputs["宽度"].default_value = 120.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 25.0
    
    # 变电站主体（简化为平台）
    cube_node = group.nodes.new("GeometryNodeMeshPrimitiveCube")
    cube_node.location = (-200, 0)
    group.links.new(input_node.outputs["长度"], cube_node.inputs["Size X"])
    group.links.new(input_node.outputs["宽度"], cube_node.inputs["Size Y"])
    group.links.new(input_node.outputs["高度"], cube_node.inputs["Size Z"])
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cube_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 12. 输电铁塔生成器
# ======================
def create_transmission_tower_generator():
    group = bpy.data.node_groups.new("PSP_TransmissionTower", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 40.0
    
    # 简化为锥体
    cone_node = group.nodes.new("GeometryNodeMeshPrimitiveCone")
    cone_node.location = (-200, 0)
    cone_node.inputs["Radius Top"].default_value = 2.0
    cone_node.inputs["Radius Bottom"].default_value = 8.0
    group.links.new(input_node.outputs["高度"], cone_node.inputs["Depth"])
    cone_node.inputs["Vertices"].default_value = 4
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cone_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 13. 居民楼生成器
# ======================
def create_residential_building_generator():
    group = bpy.data.node_groups.new("PSP_ResidentialBuilding", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-400, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 20.0
    group.inputs.new("NodeSocketFloat", "宽度")
    group.inputs["宽度"].default_value = 15.0
    group.inputs.new("NodeSocketFloat", "高度")
    group.inputs["高度"].default_value = 20.0
    
    # 住宅楼主体
    cube_node = group.nodes.new("GeometryNodeMeshPrimitiveCube")
    cube_node.location = (-200, 0)
    group.links.new(input_node.outputs["长度"], cube_node.inputs["Size X"])
    group.links.new(input_node.outputs["宽度"], cube_node.inputs["Size Y"])
    group.links.new(input_node.outputs["高度"], cube_node.inputs["Size Z"])
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(cube_node.outputs["Mesh"], output_node.inputs["Geometry"])

# ======================
# 14. 山地地形生成器
# ======================
def create_mountain_terrain_generator():
    group = bpy.data.node_groups.new("PSP_MountainTerrain", "GeometryNodeTree")
    
    input_node = group.nodes.new("NodeGroupInput")
    input_node.location = (-600, 0)
    group.inputs.new("NodeSocketFloat", "长度")
    group.inputs["长度"].default_value = 5000.0
    group.inputs.new("NodeSocketFloat", "宽度")
    group.inputs["宽度"].default_value = 5000.0
    group.inputs.new("NodeSocketFloat", "最大高度")
    group.inputs["最大高度"].default_value = 800.0
    group.inputs.new("NodeSocketFloat", "粗糙度")
    group.inputs["粗糙度"].default_value = 0.5
    
    # 基础平面
    plane_node = group.nodes.new("GeometryNodeMeshPrimitivePlane")
    plane_node.location = (-400, 0)
    group.links.new(input_node.outputs["长度"], plane_node.inputs["Size X"])
    group.links.new(input_node.outputs["宽度"], plane_node.inputs["Size Y"])
    plane_node.inputs["Vertices X"].default_value = 100
    plane_node.inputs["Vertices Y"].default_value = 100
    
    # 噪声变形
    noise_node = group.nodes.new("GeometryNodeDisplace")
    noise_node.location = (-200, 0)
    group.links.new(plane_node.outputs["Mesh"], noise_node.inputs["Geometry"])
    
    # 噪波纹理
    texture_node = group.nodes.new("GeometryNodeTextureNoise")
    texture_node.location = (-300, -100)
    texture_node.inputs["Scale"].default_value = 500.0
    group.links.new(texture_node.outputs["Color"], noise_node.inputs["Displacement"])
    
    # 缩放高度
    math_node = group.nodes.new("ShaderNodeMath")
    math_node.location = (-200, -100)
    math_node.operation = "MULTIPLY"
    group.links.new(input_node.outputs["最大高度"], math_node.inputs[0])
    noise_node.inputs["Scale"].default_value = 1.0
    
    output_node = group.nodes.new("NodeGroupOutput")
    output_node.location = (0, 0)
    group.outputs.new("NodeSocketGeometry", "Geometry")
    group.links.new(noise_node.outputs["Geometry"], output_node.inputs["Geometry"])

# ======================
# 运行所有生成器
# ======================
if __name__ == "__main__":
    print("=== 创建抽水蓄能电站几何节点生成器 ===")
    
    create_dam_generator()
    print("✓ PSP_UpperDam - 上水库大坝生成器")
    
    create_reservoir_generator()
    print("✓ PSP_ReservoirWater - 水库水体生成器")
    
    create_tunnel_generator()
    print("✓ PSP_Tunnel - 隧洞生成器")
    
    create_underground_plant_generator()
    print("✓ PSP_UndergroundPlant - 地下厂房生成器")
    
    create_turbine_generator()
    print("✓ PSP_Turbine - 水轮发电机组生成器")
    
    create_thermal_plant_generator()
    print("✓ PSP_ThermalPlant - 火力发电厂生成器")
    
    create_cooling_tower_generator()
    print("✓ PSP_CoolingTower - 双曲线冷却塔生成器")
    
    create_chimney_generator()
    print("✓ PSP_Chimney - 烟囱生成器")
    
    create_solar_panel_generator()
    print("✓ PSP_SolarPanel - 光伏板阵列生成器")
    
    create_wind_turbine_generator()
    print("✓ PSP_WindTurbine - 风电机组生成器")
    
    create_substation_generator()
    print("✓ PSP_Substation - 变电站生成器")
    
    create_transmission_tower_generator()
    print("✓ PSP_TransmissionTower - 输电铁塔生成器")
    
    create_residential_building_generator()
    print("✓ PSP_ResidentialBuilding - 居民楼生成器")
    
    create_mountain_terrain_generator()
    print("✓ PSP_MountainTerrain - 山地地形生成器")
    
    print("\n=== 所有生成器创建完成 ===")
    print("切换到几何节点工作区，在「添加」→「组」中找到生成器节点")


# ======================
# 高级功能：一键完整场景生成器
# ======================
def generate_complete_system():
    """一键生成完整综合能源系统场景"""
    # 清空场景
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # 1. 生成地形
    bpy.ops.mesh.primitive_plane_add(size=5000, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "地形"
    
    # 添加地形修改器
    mod = terrain.modifiers.new(name="地形噪声", type='DISPLACE')
    tex = bpy.data.textures.new(name="地形纹理", type='CLOUDS')
    tex.noise_scale = 500.0
    mod.texture = tex
    mod.strength = 800.0
    
    # 2. 生成抽水蓄能电站
    # 上水库
    bpy.ops.mesh.primitive_plane_add(size=800, location=(0, -1500, 600))
    upper_reservoir = bpy.context.active_object
    upper_reservoir.name = "上水库"
    
    # 下水库
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 1500, 100))
    lower_reservoir = bpy.context.active_object
    lower_reservoir.name = "下水库"
    
    # 3. 生成火力发电厂
    bpy.ops.mesh.primitive_cube_add(size=120, location=(-2000, 0, 50))
    thermal_plant = bpy.context.active_object
    thermal_plant.name = "火力发电厂"
    
    # 冷却塔
    for i in range(2):
        bpy.ops.mesh.primitive_cylinder_add(radius=40, depth=120, location=(-2000, -200+i*400, 110))
        cooling_tower = bpy.context.active_object
        cooling_tower.name = f"冷却塔_{i+1}"
    
    # 4. 生成风电场
    import random
    for i in range(5):
        x = random.uniform(-2500, 2500)
        y = random.uniform(-2500, -1000)
        bpy.ops.mesh.primitive_cylinder_add(radius=2, depth=100, location=(x, y, 50))
        wind_turbine = bpy.context.active_object
        wind_turbine.name = f"风电机_{i+1}"
    
    # 5. 生成光伏电站
    for i in range(10):
        for j in range(10):
            x = 1500 + i*30
            y = -1000 + j*20
            bpy.ops.mesh.primitive_plane_add(size=2, location=(x, y, 30))
            solar_panel = bpy.context.active_object
            solar_panel.name = f"光伏板_{i*10+j+1}"
            solar_panel.rotation_euler = (0.5236, 0, 0)  # 30度倾斜
    
    # 6. 生成居民区
    for i in range(5):
        for j in range(5):
            x = 1500 + i*50
            y = 1500 + j*50
            bpy.ops.mesh.primitive_cube_add(size=20, location=(x, y, 30))
            building = bpy.context.active_object
            building.name = f"居民楼_{i*5+j+1}"
            building.scale = (1, 0.75, 1)
    
    print("\n=== 完整综合能源系统场景已生成！ ===")


# ======================
# 启动选项
# ======================
if __name__ == "__main__":
    # 创建几何节点生成器
    create_dam_generator()
    create_reservoir_generator()
    create_tunnel_generator()
    create_underground_plant_generator()
    create_turbine_generator()
    create_thermal_plant_generator()
    create_cooling_tower_generator()
    create_chimney_generator()
    create_solar_panel_generator()
    create_wind_turbine_generator()
    create_substation_generator()
    create_transmission_tower_generator()
    create_residential_building_generator()
    create_mountain_terrain_generator()
    
    print("=== 几何节点生成器创建完成 ===")
    print("=== 正在一键生成完整综合能源系统场景 ===")
    
    # 一键生成完整场景
    generate_complete_system()