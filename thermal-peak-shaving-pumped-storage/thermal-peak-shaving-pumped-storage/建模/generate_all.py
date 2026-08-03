"""
抽水蓄能电站 + 火电深度调峰 综合能源系统 - 全操作一键生成脚本
基于 Blender 3.6+
单位: 厘米 (cm)

包含所有操作:
  1. 14个几何节点生成器
  2. PBR材质系统
  3. 相机 + 光照
  4. 完整场景（地形、上下水库、大坝、隧洞、地下厂房、
     火电厂+冷却塔+烟囱、风电场+叶片+机舱、光伏阵列、
     变电站、输电铁塔、居民区）
  5. 保存为 抽蓄电站2.blender

用法: blender --background --python generate_all.py
  或在Blender脚本编辑器中打开运行
"""

import bpy
import random
import math
import os

# ============================================================
# 输出路径
# ============================================================
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "抽蓄电站2.blender")

# ============================================================
# 阶段 1: 清空场景
# ============================================================
def clear_scene():
    """删除场景中所有对象"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # 清空网格数据
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)
    for tex in bpy.data.textures:
        bpy.data.textures.remove(tex)

    # 清空旧几何节点组
    for group in bpy.data.node_groups:
        if group.name.startswith("PSP_"):
            bpy.data.node_groups.remove(group)

    print("✓ 场景已清空")


# ============================================================
# 阶段 2: PBR 材质系统
# ============================================================
MATERIALS_DEF = {
    '混凝土':    {'base_color': (0.50, 0.50, 0.50, 1), 'roughness': 0.8, 'metallic': 0.0},
    '水':        {'base_color': (0.20, 0.50, 0.80, 0.8), 'roughness': 0.1, 'metallic': 0.0},
    '金属':      {'base_color': (0.70, 0.70, 0.70, 1), 'roughness': 0.3, 'metallic': 0.8},
    '白色漆面':  {'base_color': (0.95, 0.95, 0.95, 1), 'roughness': 0.3, 'metallic': 0.1},
    '光伏玻璃':  {'base_color': (0.10, 0.50, 0.80, 0.9), 'roughness': 0.1, 'metallic': 0.2},
    '住宅外墙':  {'base_color': (0.80, 0.70, 0.60, 1), 'roughness': 0.7, 'metallic': 0.0},
    '地面':      {'base_color': (0.20, 0.40, 0.20, 1), 'roughness': 0.9, 'metallic': 0.0},
    '工业建筑':  {'base_color': (0.70, 0.70, 0.70, 1), 'roughness': 0.6, 'metallic': 0.1},
    '蓝色':      {'base_color': (0.20, 0.40, 0.80, 1), 'roughness': 0.5, 'metallic': 0.2},
    '红色':      {'base_color': (0.80, 0.20, 0.20, 1), 'roughness': 0.5, 'metallic': 0.2},
    '黄色':      {'base_color': (0.80, 0.70, 0.20, 1), 'roughness': 0.5, 'metallic': 0.1},
    '绿色':      {'base_color': (0.20, 0.60, 0.30, 1), 'roughness': 0.6, 'metallic': 0.0},
    '橙色':      {'base_color': (0.90, 0.50, 0.20, 1), 'roughness': 0.5, 'metallic': 0.1},
    '紫色':      {'base_color': (0.60, 0.30, 0.80, 1), 'roughness': 0.5, 'metallic': 0.2},
    '隧洞材质':  {'base_color': (0.30, 0.50, 0.70, 0.5), 'roughness': 0.9, 'metallic': 0.0},
    '风叶白':    {'base_color': (0.92, 0.92, 0.94, 1), 'roughness': 0.2, 'metallic': 0.05},
}

MAT_CACHE = {}

def create_pbr_material(name, base_color, roughness, metallic):
    """创建PBR材质"""
    mat = bpy.data.materials.new(name=name)
    # Blender 5.x: 新材质默认启用节点，use_nodes 将在 6.0 移除
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    output_node = nodes.new('ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    bsdf_node = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf_node.location = (0, 0)
    bsdf_node.inputs['Base Color'].default_value = base_color
    bsdf_node.inputs['Roughness'].default_value = roughness
    bsdf_node.inputs['Metallic'].default_value = metallic

    links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

    MAT_CACHE[name] = mat
    return mat


def apply_material(obj, material_name):
    """为对象应用材质"""
    mat_key = f'PBR_{material_name}'
    if mat_key not in MAT_CACHE:
        if material_name in MATERIALS_DEF:
            d = MATERIALS_DEF[material_name]
            create_pbr_material(mat_key, d['base_color'], d['roughness'], d['metallic'])
        else:
            print(f"  ⚠ 未知材质: {material_name}")
            return

    mat = MAT_CACHE[mat_key]
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    print(f"  ✓ 材质 {material_name} → {obj.name}")


# ============================================================
# 阶段 3: 14个几何节点生成器 (全部 cm 单位)
# ============================================================
def _add_interface_socket(group, name, socket_type, in_out, default=None):
    """Blender 5.x 兼容: 添加接口套接字"""
    sock = group.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if default is not None:
        sock.default_value = default
    return sock


def create_all_geometry_node_generators():
    """创建全部14个PSP_几何节点生成器 (Blender 5.x 兼容)"""

    # --- PSP_UpperDam 上水库大坝 ---
    group = bpy.data.node_groups.new("PSP_UpperDam", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput")
    inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 30000.0)
    _add_interface_socket(group, "底部宽度", "NodeSocketFloat", 'INPUT', 5000.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 12000.0)
    _add_interface_socket(group, "迎水面坡度", "NodeSocketFloat", 'INPUT', 0.7)
    _add_interface_socket(group, "背水面坡度", "NodeSocketFloat", 'INPUT', 0.5)

    curve = group.nodes.new("GeometryNodeCurvePrimitiveBezierSegment")
    curve.location = (-200, 200); curve.inputs["Resolution"].default_value = 2

    m1 = group.nodes.new("ShaderNodeMath"); m1.location = (-200, 100); m1.operation = "MULTIPLY"
    m2 = group.nodes.new("ShaderNodeMath"); m2.location = (-200, 50);  m2.operation = "MULTIPLY"
    m3 = group.nodes.new("ShaderNodeMath"); m3.location = (-200, 0);   m3.operation = "ADD"
    m4 = group.nodes.new("ShaderNodeMath"); m4.location = (-200, -50); m4.operation = "SUBTRACT"
    group.links.new(inp.outputs["高度"], m1.inputs[0]); group.links.new(inp.outputs["迎水面坡度"], m1.inputs[1])
    group.links.new(inp.outputs["高度"], m2.inputs[0]); group.links.new(inp.outputs["背水面坡度"], m2.inputs[1])
    group.links.new(m1.outputs[0], m3.inputs[0]);      group.links.new(m2.outputs[0], m3.inputs[1])
    group.links.new(inp.outputs["底部宽度"], m4.inputs[0]); group.links.new(m3.outputs[0], m4.inputs[1])

    c2m = group.nodes.new("GeometryNodeCurveToMesh"); c2m.location = (0, 0)
    group.links.new(curve.outputs["Curve"], c2m.inputs["Curve"])

    extrude = group.nodes.new("GeometryNodeExtrudeMesh"); extrude.location = (200, 0)
    extrude.inputs["Offset Scale"].default_value = 1.0
    group.links.new(c2m.outputs["Mesh"], extrude.inputs["Mesh"])
    group.links.new(inp.outputs["长度"], extrude.inputs["Offset"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (400, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(extrude.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_UpperDam")

    # --- PSP_ReservoirWater 水库水体 ---
    group = bpy.data.node_groups.new("PSP_ReservoirWater", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 80000.0)
    _add_interface_socket(group, "宽度", "NodeSocketFloat", 'INPUT', 60000.0)
    _add_interface_socket(group, "深度", "NodeSocketFloat", 'INPUT', 3000.0)
    _add_interface_socket(group, "不规则度", "NodeSocketFloat", 'INPUT', 0.2)

    plane = group.nodes.new("GeometryNodeMeshPrimitivePlane"); plane.location = (-200, 0)
    group.links.new(inp.outputs["长度"], plane.inputs["Size X"])
    group.links.new(inp.outputs["宽度"], plane.inputs["Size Y"])
    plane.inputs["Vertices X"].default_value = 20; plane.inputs["Vertices Y"].default_value = 20

    noise = group.nodes.new("GeometryNodeDisplace"); noise.location = (0, 0)
    noise.inputs["Scale"].default_value = 5000.0
    group.links.new(plane.outputs["Mesh"], noise.inputs["Geometry"])

    tex = group.nodes.new("GeometryNodeTextureNoise"); tex.location = (-100, -100)
    tex.inputs["Scale"].default_value = 5000.0
    group.links.new(tex.outputs["Color"], noise.inputs["Displacement"])

    extrude = group.nodes.new("GeometryNodeExtrudeMesh"); extrude.location = (200, 0)
    extrude.inputs["Offset Scale"].default_value = -1.0
    group.links.new(noise.outputs["Geometry"], extrude.inputs["Mesh"])
    group.links.new(inp.outputs["深度"], extrude.inputs["Offset"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (400, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(extrude.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_ReservoirWater")

    # --- PSP_Tunnel 隧洞 ---
    group = bpy.data.node_groups.new("PSP_Tunnel", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 150000.0)
    _add_interface_socket(group, "直径", "NodeSocketFloat", 'INPUT', 800.0)
    _add_interface_socket(group, "弯曲角度", "NodeSocketFloat", 'INPUT', 0.0)

    circle = group.nodes.new("GeometryNodeCurvePrimitiveCircle"); circle.location = (-200, 100)
    group.links.new(inp.outputs["直径"], circle.inputs["Radius"])
    circle.inputs["Resolution"].default_value = 16

    curve = group.nodes.new("GeometryNodeCurvePrimitiveBezierSegment"); curve.location = (-200, 0)
    group.links.new(inp.outputs["长度"], curve.inputs["Length"])

    c2m = group.nodes.new("GeometryNodeCurveToMesh"); c2m.location = (0, 0)
    group.links.new(curve.outputs["Curve"], c2m.inputs["Curve"])
    group.links.new(circle.outputs["Curve"], c2m.inputs["Profile Curve"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (200, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(c2m.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_Tunnel")

    # --- PSP_UndergroundPlant 地下厂房 ---
    group = bpy.data.node_groups.new("PSP_UndergroundPlant", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 20000.0)
    _add_interface_socket(group, "宽度", "NodeSocketFloat", 'INPUT', 3000.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 5000.0)

    cube = group.nodes.new("GeometryNodeMeshPrimitiveCube"); cube.location = (-200, 0)
    group.links.new(inp.outputs["长度"], cube.inputs["Size X"])
    group.links.new(inp.outputs["宽度"], cube.inputs["Size Y"])
    group.links.new(inp.outputs["高度"], cube.inputs["Size Z"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cube.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_UndergroundPlant")

    # --- PSP_Turbine 水轮发电机组 ---
    group = bpy.data.node_groups.new("PSP_Turbine", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "直径", "NodeSocketFloat", 'INPUT', 2000.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 2500.0)

    cyl = group.nodes.new("GeometryNodeMeshPrimitiveCylinder"); cyl.location = (-200, 0)
    group.links.new(inp.outputs["直径"], cyl.inputs["Radius"])
    group.links.new(inp.outputs["高度"], cyl.inputs["Depth"])
    cyl.inputs["Vertices"].default_value = 32

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cyl.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_Turbine")

    # --- PSP_ThermalPlant 火力发电厂 ---
    group = bpy.data.node_groups.new("PSP_ThermalPlant", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "厂房长度", "NodeSocketFloat", 'INPUT', 12000.0)
    _add_interface_socket(group, "厂房宽度", "NodeSocketFloat", 'INPUT', 4000.0)
    _add_interface_socket(group, "厂房高度", "NodeSocketFloat", 'INPUT', 3000.0)

    cube = group.nodes.new("GeometryNodeMeshPrimitiveCube"); cube.location = (-200, 0)
    group.links.new(inp.outputs["厂房长度"], cube.inputs["Size X"])
    group.links.new(inp.outputs["厂房宽度"], cube.inputs["Size Y"])
    group.links.new(inp.outputs["厂房高度"], cube.inputs["Size Z"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cube.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_ThermalPlant")

    # --- PSP_CoolingTower 双曲线冷却塔 ---
    group = bpy.data.node_groups.new("PSP_CoolingTower", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "底部直径", "NodeSocketFloat", 'INPUT', 8000.0)
    _add_interface_socket(group, "顶部直径", "NodeSocketFloat", 'INPUT', 4000.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 12000.0)

    cyl = group.nodes.new("GeometryNodeMeshPrimitiveCylinder"); cyl.location = (-200, 0)
    cyl.inputs["Radius"].default_value = 4000.0
    group.links.new(inp.outputs["高度"], cyl.inputs["Depth"])
    cyl.inputs["Vertices"].default_value = 64

    xform = group.nodes.new("GeometryNodeTransform"); xform.location = (0, 0)
    xform.inputs["Scale Y"].default_value = 0.5
    group.links.new(cyl.outputs["Mesh"], xform.inputs["Geometry"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (200, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(xform.outputs["Geometry"], out.inputs["Geometry"])
    print("✓ PSP_CoolingTower")

    # --- PSP_Chimney 烟囱 ---
    group = bpy.data.node_groups.new("PSP_Chimney", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "底部直径", "NodeSocketFloat", 'INPUT', 1000.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 15000.0)

    cyl = group.nodes.new("GeometryNodeMeshPrimitiveCylinder"); cyl.location = (-200, 0)
    group.links.new(inp.outputs["底部直径"], cyl.inputs["Radius"])
    group.links.new(inp.outputs["高度"], cyl.inputs["Depth"])
    cyl.inputs["Vertices"].default_value = 32

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cyl.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_Chimney")

    # --- PSP_SolarPanel 光伏板 ---
    group = bpy.data.node_groups.new("PSP_SolarPanel", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 200.0)
    _add_interface_socket(group, "宽度", "NodeSocketFloat", 'INPUT', 100.0)
    _add_interface_socket(group, "厚度", "NodeSocketFloat", 'INPUT', 10.0)
    _add_interface_socket(group, "倾斜角度", "NodeSocketFloat", 'INPUT', 30.0)

    plane = group.nodes.new("GeometryNodeMeshPrimitivePlane"); plane.location = (-200, 0)
    group.links.new(inp.outputs["长度"], plane.inputs["Size X"])
    group.links.new(inp.outputs["宽度"], plane.inputs["Size Y"])

    extrude = group.nodes.new("GeometryNodeExtrudeMesh"); extrude.location = (0, 0)
    group.links.new(plane.outputs["Mesh"], extrude.inputs["Mesh"])
    group.links.new(inp.outputs["厚度"], extrude.inputs["Offset"])

    rot = group.nodes.new("GeometryNodeRotate"); rot.location = (200, 0)
    rot.inputs["Rotation"].default_value = (0.5236, 0, 0)
    group.links.new(extrude.outputs["Mesh"], rot.inputs["Geometry"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (400, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(rot.outputs["Geometry"], out.inputs["Geometry"])
    print("✓ PSP_SolarPanel")

    # --- PSP_WindTurbine 风电机组 ---
    group = bpy.data.node_groups.new("PSP_WindTurbine", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "塔筒高度", "NodeSocketFloat", 'INPUT', 10000.0)
    _add_interface_socket(group, "塔筒直径", "NodeSocketFloat", 'INPUT', 400.0)
    _add_interface_socket(group, "叶片长度", "NodeSocketFloat", 'INPUT', 5500.0)

    cyl = group.nodes.new("GeometryNodeMeshPrimitiveCylinder"); cyl.location = (-200, 0)
    group.links.new(inp.outputs["塔筒直径"], cyl.inputs["Radius"])
    group.links.new(inp.outputs["塔筒高度"], cyl.inputs["Depth"])
    cyl.inputs["Vertices"].default_value = 32

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cyl.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_WindTurbine")

    # --- PSP_Substation 变电站 ---
    group = bpy.data.node_groups.new("PSP_Substation", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 15000.0)
    _add_interface_socket(group, "宽度", "NodeSocketFloat", 'INPUT', 12000.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 2500.0)

    cube = group.nodes.new("GeometryNodeMeshPrimitiveCube"); cube.location = (-200, 0)
    group.links.new(inp.outputs["长度"], cube.inputs["Size X"])
    group.links.new(inp.outputs["宽度"], cube.inputs["Size Y"])
    group.links.new(inp.outputs["高度"], cube.inputs["Size Z"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cube.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_Substation")

    # --- PSP_TransmissionTower 输电铁塔 ---
    group = bpy.data.node_groups.new("PSP_TransmissionTower", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 4000.0)

    cone = group.nodes.new("GeometryNodeMeshPrimitiveCone"); cone.location = (-200, 0)
    cone.inputs["Radius Top"].default_value = 200.0
    cone.inputs["Radius Bottom"].default_value = 800.0
    group.links.new(inp.outputs["高度"], cone.inputs["Depth"])
    cone.inputs["Vertices"].default_value = 4

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cone.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_TransmissionTower")

    # --- PSP_ResidentialBuilding 居民楼 ---
    group = bpy.data.node_groups.new("PSP_ResidentialBuilding", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-400, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 2000.0)
    _add_interface_socket(group, "宽度", "NodeSocketFloat", 'INPUT', 1500.0)
    _add_interface_socket(group, "高度", "NodeSocketFloat", 'INPUT', 2000.0)

    cube = group.nodes.new("GeometryNodeMeshPrimitiveCube"); cube.location = (-200, 0)
    group.links.new(inp.outputs["长度"], cube.inputs["Size X"])
    group.links.new(inp.outputs["宽度"], cube.inputs["Size Y"])
    group.links.new(inp.outputs["高度"], cube.inputs["Size Z"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(cube.outputs["Mesh"], out.inputs["Geometry"])
    print("✓ PSP_ResidentialBuilding")

    # --- PSP_MountainTerrain 山地地形 ---
    group = bpy.data.node_groups.new("PSP_MountainTerrain", "GeometryNodeTree")
    inp = group.nodes.new("NodeGroupInput"); inp.location = (-600, 0)
    _add_interface_socket(group, "长度", "NodeSocketFloat", 'INPUT', 500000.0)
    _add_interface_socket(group, "宽度", "NodeSocketFloat", 'INPUT', 500000.0)
    _add_interface_socket(group, "最大高度", "NodeSocketFloat", 'INPUT', 80000.0)
    _add_interface_socket(group, "粗糙度", "NodeSocketFloat", 'INPUT', 0.5)

    plane = group.nodes.new("GeometryNodeMeshPrimitivePlane"); plane.location = (-400, 0)
    group.links.new(inp.outputs["长度"], plane.inputs["Size X"])
    group.links.new(inp.outputs["宽度"], plane.inputs["Size Y"])
    plane.inputs["Vertices X"].default_value = 100; plane.inputs["Vertices Y"].default_value = 100

    noise = group.nodes.new("GeometryNodeDisplace"); noise.location = (-200, 0)
    group.links.new(plane.outputs["Mesh"], noise.inputs["Geometry"])

    tex = group.nodes.new("GeometryNodeTextureNoise"); tex.location = (-300, -100)
    tex.inputs["Scale"].default_value = 50000.0
    group.links.new(tex.outputs["Color"], noise.inputs["Displacement"])

    out = group.nodes.new("NodeGroupOutput"); out.location = (0, 0)
    _add_interface_socket(group, "Geometry", "NodeSocketGeometry", 'OUTPUT')
    group.links.new(noise.outputs["Geometry"], out.inputs["Geometry"])
    print("✓ PSP_MountainTerrain")

    print("=== 14个几何节点生成器全部创建完成 ===\n")


# ============================================================
# 阶段 4: 相机设置
# ============================================================
def setup_camera():
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            bpy.data.objects.remove(obj)

    bpy.ops.object.camera_add(location=(30000, -25000, 15000))
    camera = bpy.context.active_object
    camera.name = "主相机"
    camera.rotation_euler = (1.0, 0, 0.785)

    camera.data.type = 'PERSP'
    camera.data.lens = 35
    camera.data.clip_start = 100
    camera.data.clip_end = 1000000

    bpy.context.scene.camera = camera
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080

    print("✓ 相机已设置 (1920x1080, 35mm)")


# ============================================================
# 阶段 5: 光照设置
# ============================================================
def setup_lighting():
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj)

    # 太阳光
    bpy.ops.object.light_add(type='SUN', location=(50000, 50000, 80000))
    sun = bpy.context.active_object
    sun.name = "太阳光"
    sun.data.energy = 3
    sun.data.angle = 0.1
    sun.rotation_euler = (0.8, 0.3, 0.5)

    # 环境补光
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 100000))
    area = bpy.context.active_object
    area.name = "环境光"
    area.data.energy = 1000
    area.data.size = 100000

    # 世界环境
    world = bpy.context.scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.6, 0.7, 0.8, 1)
    bg.inputs['Strength'].default_value = 0.5

    print("✓ 光照已设置 (太阳光 + 环境光 + 世界背景)")


# ============================================================
# 阶段 6: 一键生成完整综合能源系统场景
# ============================================================
def generate_complete_system():
    """生成包含所有组件的完整场景"""

    # ---- 6.1 地形 ----
    bpy.ops.mesh.primitive_plane_add(size=500000, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "地形"
    apply_material(terrain, '地面')
    mod = terrain.modifiers.new(name="地形噪声", type='DISPLACE')
    tex = bpy.data.textures.new(name="地形纹理", type='CLOUDS')
    tex.noise_scale = 50000.0
    mod.texture = tex
    mod.strength = 80000.0

    # ---- 6.2 抽水蓄能电站 ----
    # 上水库
    bpy.ops.mesh.primitive_plane_add(size=80000, location=(0, -150000, 60000))
    upper_res = bpy.context.active_object
    upper_res.name = "上水库"
    apply_material(upper_res, '水')

    # 上水库大坝
    bpy.ops.mesh.primitive_cube_add(size=5000, location=(0, -150000, 45000))
    upper_dam = bpy.context.active_object
    upper_dam.name = "上水库大坝"
    upper_dam.scale = (30, 1, 12)
    apply_material(upper_dam, '混凝土')

    # 下水库
    bpy.ops.mesh.primitive_plane_add(size=60000, location=(0, 150000, 10000))
    lower_res = bpy.context.active_object
    lower_res.name = "下水库"
    apply_material(lower_res, '水')

    # 下水库大坝
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(0, 150000, 5000))
    lower_dam = bpy.context.active_object
    lower_dam.name = "下水库大坝"
    lower_dam.scale = (25, 1, 8)
    apply_material(lower_dam, '混凝土')

    # 地下厂房
    bpy.ops.mesh.primitive_cube_add(size=3000, location=(0, 0, -5000))
    ug_plant = bpy.context.active_object
    ug_plant.name = "地下厂房"
    ug_plant.scale = (67, 10, 17)
    apply_material(ug_plant, '混凝土')

    # 引水隧洞
    bpy.ops.mesh.primitive_cylinder_add(radius=400, depth=150000, location=(0, -75000, 35000))
    tunnel = bpy.context.active_object
    tunnel.name = "引水隧洞"
    tunnel.rotation_euler = (1.57, 0, 0)
    apply_material(tunnel, '隧洞材质')

    # ---- 6.3 火力发电厂 ----
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(-200000, 0, 15000))
    thermal = bpy.context.active_object
    thermal.name = "火力发电厂"
    thermal.scale = (30, 10, 7.5)
    apply_material(thermal, '工业建筑')

    # 冷却塔 x2
    for i in range(2):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=4000, depth=12000,
            location=(-200000, -20000 + i * 40000, 11000))
        ct = bpy.context.active_object
        ct.name = f"冷却塔_{i+1}"
        apply_material(ct, '混凝土')

    # 烟囱
    bpy.ops.mesh.primitive_cylinder_add(radius=500, depth=15000, location=(-185000, 0, 20000))
    chimney = bpy.context.active_object
    chimney.name = "烟囱"
    apply_material(chimney, '混凝土')

    # ---- 6.4 风电场 (5台完整机组: 塔筒 + 机舱 + 3叶片) ----
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

        # 3个叶片
        for j in range(3):
            angle = j * 2.0944
            bpy.ops.mesh.primitive_cone_add(
                radius1=50, radius2=10, depth=5500,
                location=(x, y, 15000))
            blade = bpy.context.active_object
            blade.name = f"风电机_{i+1}_叶片_{j+1}"
            blade.rotation_euler = (0, angle, 0.3)
            apply_material(blade, '风叶白')

    # ---- 6.5 光伏电站 (10x10阵列) ----
    for i in range(10):
        for j in range(10):
            x = 150000 + i * 3000
            y = -100000 + j * 2000
            bpy.ops.mesh.primitive_plane_add(size=200, location=(x, y, 3000))
            panel = bpy.context.active_object
            panel.name = f"光伏板_{i*10+j+1}"
            panel.rotation_euler = (0.5236, 0, 0)
            apply_material(panel, '光伏玻璃')

    # 逆变器房
    bpy.ops.mesh.primitive_cube_add(size=1000, location=(165000, -90000, 1500))
    inverter = bpy.context.active_object
    inverter.name = "逆变器房"
    inverter.scale = (6, 4, 3)
    apply_material(inverter, '金属')

    # ---- 6.6 电网系统 ----
    # 220kV枢纽变电站
    bpy.ops.mesh.primitive_cube_add(size=5000, location=(0, 0, 2500))
    sub220 = bpy.context.active_object
    sub220.name = "220kV枢纽变电站"
    sub220.scale = (30, 24, 5)
    apply_material(sub220, '金属')

    # 110kV区域变电站
    bpy.ops.mesh.primitive_cube_add(size=3000, location=(-100000, 50000, 2000))
    sub110 = bpy.context.active_object
    sub110.name = "110kV区域变电站"
    sub110.scale = (20, 16, 4)
    apply_material(sub110, '蓝色')

    # 10kV终端变电站
    bpy.ops.mesh.primitive_cube_add(size=2000, location=(100000, 100000, 1500))
    sub10 = bpy.context.active_object
    sub10.name = "10kV终端变电站"
    sub10.scale = (15, 12, 3)
    apply_material(sub10, '绿色')

    # 输电铁塔 (9座)
    tower_positions = [
        (-150000, 0), (-50000, 0), (50000, 0), (150000, 0),
        (-100000, 50000), (0, 50000), (100000, 50000),
        (50000, 100000), (150000, 100000)
    ]
    tower_colors = ['金属', '金属', '金属', '金属', '蓝色', '蓝色', '蓝色', '绿色', '绿色']

    for idx, (tx, ty) in enumerate(tower_positions):
        bpy.ops.mesh.primitive_cone_add(
            radius1=200, radius2=800, depth=4000,
            location=(tx, ty, 2000))
        tower = bpy.context.active_object
        tower.name = f"输电铁塔_{idx+1}"
        apply_material(tower, tower_colors[idx])

    # ---- 6.7 居民区 (5x5) ----
    building_colors = ['住宅外墙', '黄色', '橙色', '蓝色', '紫色']
    for i in range(5):
        for j in range(5):
            x = 150000 + i * 6000
            y = 150000 + j * 6000
            bpy.ops.mesh.primitive_cube_add(size=2000, location=(x, y, 6000))
            bld = bpy.context.active_object
            bld.name = f"居民楼_{i*5+j+1}"
            bld.scale = (1, 0.75, 2)
            apply_material(bld, building_colors[j % 5])

    # 小区配电箱 (4x4)
    for i in range(4):
        for j in range(4):
            x = 153000 + i * 6000
            y = 153000 + j * 6000
            bpy.ops.mesh.primitive_cube_add(size=200, location=(x, y, 2000))
            box = bpy.context.active_object
            box.name = f"配电箱_{i*4+j+1}"
            apply_material(box, '金属')

    print("\n=== 完整综合能源系统场景已生成！===")
    _print_scene_stats()


def _print_scene_stats():
    """统计场景对象"""
    counts = {}
    for obj in bpy.data.objects:
        t = obj.type
        counts[t] = counts.get(t, 0) + 1
    total = len(bpy.data.objects)
    print(f"  总对象数: {total}")
    for t, c in sorted(counts.items()):
        print(f"    {t}: {c}")


# ============================================================
# 阶段 7: 设置视图和渲染
# ============================================================
def setup_viewport():
    """设置视口显示"""
    # 确保3D视图存在
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'  # 材质预览模式
                    space.clip_end = 1000000
                    break
    print("✓ 视口已设置 (材质预览模式)")


# ============================================================
# 阶段 8: 保存文件
# ============================================================
def save_file():
    """保存为抽蓄电站2.blender"""
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_PATH)
    print(f"\n✓ 已保存: {OUTPUT_PATH}")
    print(f"  文件大小: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")


# ============================================================
# 主流程: 执行所有操作
# ============================================================
def main():
    print("=" * 60)
    print("  抽水蓄能电站 + 火电深度调峰 综合能源系统")
    print("  全操作一键生成")
    print("=" * 60)
    print()

    # 阶段1: 清空
    print(">>> 阶段 1/8: 清空场景")
    clear_scene()

    # 阶段2: 材质
    print("\n>>> 阶段 2/8: 创建PBR材质系统")
    # 预建所有材质
    for name, props in MATERIALS_DEF.items():
        create_pbr_material(f'PBR_{name}', props['base_color'], props['roughness'], props['metallic'])
    print(f"✓ {len(MATERIALS_DEF)} 种PBR材质已就绪")

    # 阶段3: 几何节点 (Blender 5.x API 已大幅变更，节点组生成器暂时跳过)
    print("\n>>> 阶段 3/8: 14个几何节点生成器")
    print("⚠ Blender 5.x 几何节点 API 已变更，节点组生成器暂时跳过")
    print("  场景生成使用 bpy.ops 原生操作，不受影响")
    # create_all_geometry_node_generators()  # Blender 5.x API 不兼容

    # 阶段4: 相机
    print("\n>>> 阶段 4/8: 设置相机")
    setup_camera()

    # 阶段5: 光照
    print("\n>>> 阶段 5/8: 设置光照")
    setup_lighting()

    # 阶段6: 生成场景
    print("\n>>> 阶段 6/8: 一键生成完整综合能源系统场景")
    generate_complete_system()

    # 阶段7: 视口
    print("\n>>> 阶段 7/8: 设置视口")
    setup_viewport()

    # 阶段8: 保存
    print("\n>>> 阶段 8/8: 保存文件")
    save_file()

    print("\n" + "=" * 60)
    print("  全部操作完成!")
    print(f"  输出文件: {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
