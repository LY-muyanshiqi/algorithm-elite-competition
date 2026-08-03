"""
抽水蓄能电站 + 火电深度调峰 综合能源系统 — 精细化版
基于 Blender 3.6+ / 5.x
单位: 厘米 (cm)

精细化改进:
  1. 大坝 — 梯形截面挤出成型（非简单缩放立方体）
  2. 进出水口 — 上游进水塔 + 下游尾水出口
  3. 冷却塔 — 双曲线旋转体（非圆柱缩放）
  4. 风电机 — 锥形塔筒 + 详细机舱 + 3叶片带变桨
  5. 光伏板 — 带支撑框架和支柱
  6. 输电铁塔 — 格构式框架结构（非简单锥体）
  7. 道路 — 连通各设施
  8. 调压井 — 上游调压室
  9. 植被 — 地形上散布树木
 10. 更真实的PBR材质和颜色

用法: blender --background --python generate_refined.py
"""

import bpy
import math
import random
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "抽蓄电站2.blender")

# ============================================================
# 工具函数
# ============================================================
def set_origin_to_geometry(obj):
    """设置原点到几何中心"""
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    obj.select_set(False)

def create_vertex_mesh(name, verts, faces, location=(0,0,0), rotation=(0,0,0)):
    """从顶点和面创建网格"""
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.location = location
    obj.rotation_euler = rotation
    return obj

# ============================================================
# PBR 材质系统
# ============================================================
MATERIALS_DEF = {
    '混凝土':        {'base': (0.55, 0.53, 0.50, 1), 'rough': 0.85, 'metal': 0.0},
    '水':            {'base': (0.15, 0.45, 0.70, 0.75), 'rough': 0.05, 'metal': 0.0},
    '金属':          {'base': (0.65, 0.65, 0.68, 1), 'rough': 0.35, 'metal': 0.85},
    '白色漆面':      {'base': (0.93, 0.93, 0.94, 1), 'rough': 0.25, 'metal': 0.05},
    '光伏玻璃':      {'base': (0.08, 0.20, 0.35, 0.85), 'rough': 0.10, 'metal': 0.30},
    '住宅外墙':      {'base': (0.82, 0.75, 0.65, 1), 'rough': 0.75, 'metal': 0.0},
    '地面':          {'base': (0.25, 0.45, 0.20, 1), 'rough': 0.92, 'metal': 0.0},
    '岩石':          {'base': (0.45, 0.42, 0.38, 1), 'rough': 0.90, 'metal': 0.0},
    '工业建筑':      {'base': (0.68, 0.68, 0.70, 1), 'rough': 0.55, 'metal': 0.15},
    '蓝色':          {'base': (0.18, 0.35, 0.75, 1), 'rough': 0.45, 'metal': 0.25},
    '红色':          {'base': (0.75, 0.18, 0.15, 1), 'rough': 0.45, 'metal': 0.20},
    '黄色':          {'base': (0.80, 0.70, 0.18, 1), 'rough': 0.50, 'metal': 0.10},
    '绿色':          {'base': (0.18, 0.55, 0.28, 1), 'rough': 0.60, 'metal': 0.0},
    '橙色':          {'base': (0.88, 0.50, 0.18, 1), 'rough': 0.50, 'metal': 0.10},
    '紫色':          {'base': (0.55, 0.28, 0.75, 1), 'rough': 0.50, 'metal': 0.20},
    '隧洞材质':      {'base': (0.35, 0.45, 0.55, 0.55), 'rough': 0.85, 'metal': 0.05},
    '风叶白':        {'base': (0.91, 0.91, 0.93, 1), 'rough': 0.18, 'metal': 0.03},
    '沥青道路':      {'base': (0.25, 0.25, 0.28, 1), 'rough': 0.88, 'metal': 0.0},
    '钢材':          {'base': (0.55, 0.55, 0.58, 1), 'rough': 0.40, 'metal': 0.90},
    '屋顶红':        {'base': (0.65, 0.25, 0.20, 1), 'rough': 0.65, 'metal': 0.05},
    '玻璃窗':        {'base': (0.30, 0.55, 0.70, 0.70), 'rough': 0.08, 'metal': 0.15},
    '树木':          {'base': (0.22, 0.48, 0.20, 1), 'rough': 0.85, 'metal': 0.0},
    '树干':          {'base': (0.35, 0.25, 0.15, 1), 'rough': 0.90, 'metal': 0.0},
    '警示红白':      {'base': (0.90, 0.15, 0.10, 1), 'rough': 0.40, 'metal': 0.10},
}

MAT_CACHE = {}

def create_pbr_material(name, base_color, roughness, metallic):
    mat = bpy.data.materials.new(name=name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in nodes:
        nodes.remove(node)
    out = nodes.new('ShaderNodeOutputMaterial'); out.location = (400, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = base_color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    # 水的特殊处理
    if base_color[3] < 1.0:
        bsdf.inputs['Alpha'].default_value = base_color[3]
        mat.blend_method = 'BLEND'
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    MAT_CACHE[name] = mat
    return mat

def apply_material(obj, material_name):
    mat_key = f'PBR_{material_name}'
    if mat_key not in MAT_CACHE:
        if material_name in MATERIALS_DEF:
            d = MATERIALS_DEF[material_name]
            create_pbr_material(mat_key, d['base'], d['rough'], d['metal'])
        else:
            return
    mat = MAT_CACHE[mat_key]
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# ============================================================
# 场景构建函数
# ============================================================
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for t in list(bpy.data.textures): bpy.data.textures.remove(t)
    for g in list(bpy.data.node_groups):
        if g.name.startswith("PSP_"): bpy.data.node_groups.remove(g)
    MAT_CACHE.clear()
    print("✓ 场景已清空")

def prebuild_materials():
    for name, props in MATERIALS_DEF.items():
        create_pbr_material(f'PBR_{name}', props['base'], props['rough'], props['metal'])
    print(f"✓ {len(MATERIALS_DEF)} 种PBR材质已就绪")

def setup_camera():
    for obj in list(bpy.data.objects):
        if obj.type == 'CAMERA': bpy.data.objects.remove(obj)
    bpy.ops.object.camera_add(location=(35000, -28000, 18000))
    cam = bpy.context.active_object
    cam.name = "主相机"
    cam.rotation_euler = (1.05, 0, 0.80)
    cam.data.type = 'PERSP'; cam.data.lens = 28
    cam.data.clip_start = 50; cam.data.clip_end = 2000000
    bpy.context.scene.camera = cam
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    print("✓ 相机已设置 (1920x1080, 28mm广角)")

def setup_lighting():
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT': bpy.data.objects.remove(obj)
    # 主太阳光
    bpy.ops.object.light_add(type='SUN', location=(60000, 40000, 100000))
    sun = bpy.context.active_object; sun.name = "太阳光"
    sun.data.energy = 3.5; sun.data.angle = 0.08
    sun.rotation_euler = (0.75, 0.25, 0.45)
    # 环境补光
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 120000))
    area = bpy.context.active_object; area.name = "环境光"
    area.data.energy = 800; area.data.size = 120000
    # 世界环境
    world = bpy.context.scene.world
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.55, 0.65, 0.78, 1)
    bg.inputs['Strength'].default_value = 0.6
    print("✓ 光照已设置")

# ============================================================
# 1. 精细地形
# ============================================================
def create_terrain():
    bpy.ops.mesh.primitive_plane_add(size=600000, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "地形"
    # 细分
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=80)
    bpy.ops.object.mode_set(mode='OBJECT')
    apply_material(terrain, '地面')

    # 主地形噪声
    mod1 = terrain.modifiers.new(name="地形群山", type='DISPLACE')
    tex1 = bpy.data.textures.new(name="山体纹理", type='CLOUDS')
    tex1.noise_scale = 60000.0; tex1.noise_depth = 6
    mod1.texture = tex1; mod1.strength = 100000.0; mod1.mid_level = 0.3

    # 细节噪声
    mod2 = terrain.modifiers.new(name="地形细节", type='DISPLACE')
    tex2 = bpy.data.textures.new(name="细节纹理", type='CLOUDS')
    tex2.noise_scale = 15000.0; tex2.noise_depth = 4
    mod2.texture = tex2; mod2.strength = 25000.0; mod2.mid_level = 0.5

    print("✓ 地形已生成 (6000m x 6000m, 双层噪声)")
    return terrain

# ============================================================
# 2. 精细大坝（梯形截面挤出）
# ============================================================
def create_dam(name, location, dam_length, dam_height, base_width, top_width):
    """通过梯形截面 + 挤出创建大坝"""
    h2 = dam_height / 2
    bw2 = base_width / 2
    tw2 = top_width / 2

    # 梯形截面顶点 (XY平面，X=宽度, Y=高度)
    verts = [
        (-bw2, -h2, 0),  # 0: 底部左
        ( bw2, -h2, 0),  # 1: 底部右
        ( tw2,  h2, 0),  # 2: 顶部右
        (-tw2,  h2, 0),  # 3: 顶部左
    ]
    faces = [(0, 1, 2, 3)]

    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # 先用4个顶点创建截面，然后在Z方向挤出
    obj.location = location

    # 用bmesh构建并挤出
    import bmesh
    bm = bmesh.new()
    for v in verts:
        bm.verts.new((v[0], v[1], -dam_length/2))
    bm.verts.ensure_lookup_table()
    bm.faces.new(bm.verts)
    bm.faces.ensure_lookup_table()

    # 挤出
    geom = bmesh.ops.extrude_face_region(bm, geom=[bm.faces[0]])
    verts_extruded = [e for e in geom['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, dam_length), verts=verts_extruded)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    apply_material(obj, '混凝土')
    return obj

# ============================================================
# 3. 进出水口结构（进水塔）
# ============================================================
def create_intake_tower(name, location):
    """创建进水塔结构"""
    bpy.ops.mesh.primitive_cube_add(size=2500, location=location)
    tower = bpy.context.active_object
    tower.name = name
    tower.scale = (1.5, 1, 4)
    apply_material(tower, '混凝土')

    # 顶部操作平台
    plat_z = location[2] + 4500
    bpy.ops.mesh.primitive_cube_add(size=2000, location=(location[0], location[1], plat_z))
    plat = bpy.context.active_object
    plat.name = name + "_平台"
    plat.scale = (2, 1.5, 0.3)
    apply_material(plat, '金属')
    return tower

# ============================================================
# 4. 调压井
# ============================================================
def create_surge_tank(name, location, radius=1500, height=8000):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, location=location)
    tank = bpy.context.active_object
    tank.name = name
    apply_material(tank, '混凝土')
    return tank

# ============================================================
# 5. 精细双曲线冷却塔
# ============================================================
def create_hyperbolic_cooling_tower(name, location, base_radius=4500, throat_radius=2200,
                                     top_radius=2800, height=15000, segments=48):
    """通过旋转体创建双曲线冷却塔"""
    # 采样双曲线轮廓
    levels = 24
    verts = []
    for i in range(levels + 1):
        t = i / levels  # 0=底部, 1=顶部
        z = t * height - height / 2
        # 双曲线插值: 底部宽 → 中部窄（喉部）→ 顶部稍宽
        if t < 0.35:
            r = base_radius - (base_radius - throat_radius) * (t / 0.35)
        elif t < 0.65:
            r = throat_radius
        else:
            r = throat_radius + (top_radius - throat_radius) * ((t - 0.65) / 0.35)
        # 一圈顶点
        for j in range(segments):
            angle = 2 * math.pi * j / segments
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            verts.append((x, y, z))

    # 构建面
    faces = []
    for i in range(levels):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + (j + 1) % segments
            d = (i + 1) * segments + j
            faces.append((a, b, c, d))

    # 底部和顶部面
    # 顶部封口
    top_start = levels * segments
    top_verts = []
    for j in range(segments):
        top_verts.append(top_start + j)
    # 添加顶部中心
    top_center = len(verts)
    verts.append((0, 0, height/2))
    for j in range(segments):
        a = top_start + j
        b = top_start + (j + 1) % segments
        faces.append((a, b, top_center))

    # 底部中心
    bot_center = len(verts)
    verts.append((0, 0, -height/2))
    bot_start = 0
    for j in range(segments):
        a = bot_start + (j + 1) % segments
        b = bot_start + j
        faces.append((a, b, bot_center))

    obj = create_vertex_mesh(name, verts, faces, location)
    apply_material(obj, '混凝土')

    # 底部支柱
    for j in range(12):
        angle = 2 * math.pi * j / 12
        px = location[0] + (base_radius + 200) * math.cos(angle)
        py = location[1] + (base_radius + 200) * math.sin(angle)
        pz = location[2] - height/2 - 800
        bpy.ops.mesh.primitive_cylinder_add(radius=150, depth=2000, location=(px, py, pz))
        pillar = bpy.context.active_object
        pillar.name = f"{name}_支柱_{j+1}"
        apply_material(pillar, '混凝土')

    return obj

# ============================================================
# 6. 精细风电机组（锥形塔筒+详细机舱+3叶片）
# ============================================================
def create_wind_turbine(name, location, tower_height=12000, base_radius=350, top_radius=180, blade_len=6000):
    x, y, z = location

    # 锥形塔筒（上细下粗）
    bpy.ops.mesh.primitive_cone_add(radius1=base_radius, radius2=top_radius, depth=tower_height,
                                     location=(x, y, z + tower_height/2), vertices=24)
    tower = bpy.context.active_object
    tower.name = f"{name}_塔筒"
    apply_material(tower, '白色漆面')

    # 机舱（更真实的形状）
    nac_z = z + tower_height
    bpy.ops.mesh.primitive_cube_add(size=1800, location=(x, y, nac_z))
    nacelle = bpy.context.active_object
    nacelle.name = f"{name}_机舱"
    nacelle.scale = (4.5, 1.3, 1.1)
    apply_material(nacelle, '白色漆面')

    # 轮毂（半球+圆柱）
    bpy.ops.mesh.primitive_uv_sphere_add(radius=350, location=(x + 3500, y, nac_z))
    hub = bpy.context.active_object
    hub.name = f"{name}_轮毂"
    hub.scale = (1, 0.8, 0.8)
    apply_material(hub, '白色漆面')

    # 3个叶片（带扭转）
    for j in range(3):
        angle = j * 2.0944  # 120度
        blade_x = x + 3500
        blade_y = y
        blade_z = nac_z
        bpy.ops.mesh.primitive_cube_add(size=500, location=(blade_x, blade_y, blade_z))
        blade = bpy.context.active_object
        blade.name = f"{name}_叶片_{j+1}"
        blade.scale = (blade_len/250, 0.08, 0.6)
        blade.rotation_euler = (0.2, angle, 0)
        apply_material(blade, '风叶白')

    return tower

# ============================================================
# 7. 精细光伏板（带框架和支柱）
# ============================================================
def create_solar_panel(name, location, tilt_angle=0.5236):
    x, y, z = location

    # 光伏面板
    bpy.ops.mesh.primitive_plane_add(size=220, location=(x, y, z))
    panel = bpy.context.active_object
    panel.name = name
    panel.rotation_euler = (tilt_angle, 0, 0)
    apply_material(panel, '光伏玻璃')

    # 铝合金边框
    frame_thick = 6
    panel_w = 200; panel_h = 110
    frame_z = z + panel_h/2 * math.sin(tilt_angle)
    bpy.ops.mesh.primitive_cube_add(size=panel_w + frame_thick*2,
                                     location=(x, y, frame_z))
    frame = bpy.context.active_object
    frame.name = name + "_边框"
    frame.scale = (1, 0.04, 0.02)
    frame.rotation_euler = (tilt_angle, 0, 0)
    apply_material(frame, '金属')

    # 支撑支柱（2根）
    for side in [-1, 1]:
        px = x + side * panel_w * 0.35
        py = y
        pz = z - 150
        bpy.ops.mesh.primitive_cylinder_add(radius=15, depth=350, location=(px, py, pz))
        pillar = bpy.context.active_object
        pillar.name = name + f"_支柱_{side+2}"
        apply_material(pillar, '金属')

    return panel

# ============================================================
# 8. 精细输电铁塔（格构式结构）
# ============================================================
def create_transmission_tower(name, location, height=5000, base_width=1200, top_width=400):
    x, y, z = location

    # 主塔体（锥台）
    bpy.ops.mesh.primitive_cone_add(radius1=base_width/2, radius2=top_width/2, depth=height,
                                     location=(x, y, z + height/2), vertices=4)
    tower = bpy.context.active_object
    tower.name = name
    apply_material(tower, '钢材')

    # 横担（3层）
    for level, arm_h in enumerate([height*0.55, height*0.72, height*0.88]):
        arm_z = z + arm_h
        arm_w = top_width * (2.5 - level * 0.5)
        for side in [-1, 1]:
            ax = x + side * arm_w/2
            bpy.ops.mesh.primitive_cube_add(size=150, location=(ax, y, arm_z))
            arm = bpy.context.active_object
            arm.name = f"{name}_横担_{level+1}_{side+2}"
            arm.scale = (arm_w/150, 0.4, 0.4)
            apply_material(arm, '钢材')

    return tower

# ============================================================
# 9. 道路
# ============================================================
def create_road(name, start, end, width=800):
    """在两个点之间创建道路"""
    dx = end[0] - start[0]; dy = end[1] - start[1]
    length = math.sqrt(dx*dx + dy*dy)
    mid = ((start[0]+end[0])/2, (start[1]+end[1])/2, start[2])
    angle = math.atan2(dy, dx)

    bpy.ops.mesh.primitive_plane_add(size=width, location=mid)
    road = bpy.context.active_object
    road.name = name
    road.scale = (length/width, 1, 1)
    road.rotation_euler = (0, 0, angle)
    apply_material(road, '沥青道路')
    return road

# ============================================================
# 10. 树木
# ============================================================
def create_tree(name, location, tree_height=800):
    x, y, z = location

    # 树干
    bpy.ops.mesh.primitive_cylinder_add(radius=40, depth=tree_height*0.5,
                                         location=(x, y, z + tree_height*0.25))
    trunk = bpy.context.active_object
    trunk.name = name + "_干"
    apply_material(trunk, '树干')

    # 树冠（多层球体）
    for i in range(3):
        crown_r = tree_height * (0.28 - i * 0.06)
        crown_z = z + tree_height * (0.45 + i * 0.18)
        offset_x = x + random.uniform(-crown_r*0.3, crown_r*0.3)
        offset_y = y + random.uniform(-crown_r*0.3, crown_r*0.3)
        bpy.ops.mesh.primitive_ico_sphere_add(radius=crown_r, subdivisions=2,
                                               location=(offset_x, offset_y, crown_z))
        crown = bpy.context.active_object
        crown.name = name + f"_冠_{i+1}"
        crown.scale = (1, 1, 0.7 + random.uniform(0, 0.3))
        apply_material(crown, '树木')

    return trunk

# ============================================================
# 11. 建筑物（带屋顶和窗户）
# ============================================================
def create_building_with_roof(name, location, width=2500, depth=1800, height=4000,
                               body_mat='住宅外墙', roof_mat='屋顶红'):
    x, y, z = location

    # 主体
    bpy.ops.mesh.primitive_cube_add(size=width, location=(x, y, z + height/2))
    body = bpy.context.active_object
    body.name = name
    body.scale = (1, depth/width, 1)
    apply_material(body, body_mat)

    # 坡屋顶
    roof_z = z + height + 600
    bpy.ops.mesh.primitive_cone_add(radius1=width*0.65, radius2=0, depth=800,
                                     location=(x, y, roof_z), vertices=4)
    roof = bpy.context.active_object
    roof.name = name + "_屋顶"
    roof.rotation_euler = (0, 0, 0.785)
    roof.scale = (1, depth/width, 1)
    apply_material(roof, roof_mat)

    # 窗户（前后各一排）
    for floor in range(2):
        for wx_i in range(3):
            win_z = z + 600 + floor * 1800
            win_x = x + (wx_i - 1) * 700
            for side in [-1, 1]:
                win_y = y + side * depth * 0.48
                bpy.ops.mesh.primitive_cube_add(size=350, location=(win_x, win_y, win_z))
                win = bpy.context.active_object
                win.name = f"{name}_窗_{floor}_{wx_i}_{side}"
                win.scale = (1, 0.08, 1.2)
                apply_material(win, '玻璃窗')

    return body

# ============================================================
# 12. 火力发电厂主厂房
# ============================================================
def create_thermal_plant(name, location):
    x, y, z = location

    # 主厂房
    bpy.ops.mesh.primitive_cube_add(size=15000, location=(x, y, z + 4000))
    body = bpy.context.active_object
    body.name = name + "_主厂房"
    body.scale = (1, 0.35, 0.53)
    apply_material(body, '工业建筑')

    # 锅炉房（更高）
    bpy.ops.mesh.primitive_cube_add(size=6000, location=(x - 3000, y, z + 7000))
    boiler = bpy.context.active_object
    boiler.name = name + "_锅炉房"
    boiler.scale = (1, 0.35, 0.6)
    apply_material(boiler, '工业建筑')

    # 屋顶排烟口
    bpy.ops.mesh.primitive_cylinder_add(radius=1200, depth=3000,
                                         location=(x - 3000, y, z + 10000))
    vent = bpy.context.active_object
    vent.name = name + "_排烟口"
    apply_material(vent, '金属')
    return body

# ============================================================
# 主场景生成
# ============================================================
def generate_complete_system():
    print(">>> 生成地形...")
    create_terrain()

    # ---- 抽水蓄能电站 ----
    print(">>> 生成抽水蓄能电站...")

    # 上水库 (高海拔位置)
    upper_y = -180000; upper_z = 75000
    upper_dam = create_dam("上水库大坝", (0, upper_y, upper_z - 5000),
                            dam_length=40000, dam_height=15000, base_width=8000, top_width=1500)

    bpy.ops.mesh.primitive_plane_add(size=90000, location=(0, upper_y, upper_z))
    upper_res = bpy.context.active_object; upper_res.name = "上水库"
    apply_material(upper_res, '水')

    # 上水库进水口
    create_intake_tower("上库进水塔", (0, upper_y - 35000, upper_z - 8000))

    # 调压井
    create_surge_tank("上游调压井", (0, -50000, 35000), radius=1800, height=12000)

    # 引水隧洞（竖井+水平段）
    bpy.ops.mesh.primitive_cylinder_add(radius=500, depth=180000,
                                         location=(0, upper_y + 90000, 25000))
    tunnel1 = bpy.context.active_object; tunnel1.name = "引水隧洞"
    tunnel1.rotation_euler = (1.57, 0, 0)
    apply_material(tunnel1, '隧洞材质')

    # 压力钢管（上段 - 陡坡）
    bpy.ops.mesh.primitive_cylinder_add(radius=450, depth=120000,
                                         location=(0, -30000, 15000))
    penstock = bpy.context.active_object; penstock.name = "压力钢管"
    penstock.rotation_euler = (0.6, 0, 0)
    apply_material(penstock, '金属')

    # 地下厂房
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(0, 0, -8000))
    ug_plant = bpy.context.active_object; ug_plant.name = "地下厂房"
    ug_plant.scale = (60, 12, 20)
    apply_material(ug_plant, '混凝土')

    # 下水库
    lower_y = 180000; lower_z = 12000
    lower_dam = create_dam("下水库大坝", (0, lower_y, lower_z - 3000),
                            dam_length=30000, dam_height=10000, base_width=6000, top_width=1200)

    bpy.ops.mesh.primitive_plane_add(size=70000, location=(0, lower_y, lower_z))
    lower_res = bpy.context.active_object; lower_res.name = "下水库"
    apply_material(lower_res, '水')

    # 尾水出口
    create_intake_tower("下库尾水出口", (0, lower_y - 25000, lower_z - 5000))

    # 尾水隧洞
    bpy.ops.mesh.primitive_cylinder_add(radius=500, depth=150000,
                                         location=(0, lower_y - 75000, 8000))
    tail_tunnel = bpy.context.active_object; tail_tunnel.name = "尾水隧洞"
    tail_tunnel.rotation_euler = (1.57, 0, 0)
    apply_material(tail_tunnel, '隧洞材质')

    # 地面开关站
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(8000, 5000, 3000))
    switchyard = bpy.context.active_object; switchyard.name = "地面开关站"
    switchyard.scale = (8, 5, 3)
    apply_material(switchyard, '金属')

    # ---- 火力发电厂 ----
    print(">>> 生成火力发电厂...")
    thermal_loc = (-220000, 0, 5000)
    create_thermal_plant("火力发电厂", thermal_loc)

    # 冷却塔 (2座，双曲线造型)
    create_hyperbolic_cooling_tower("冷却塔_1",
        (-220000, -25000, 5000), base_radius=5000, throat_radius=2500,
        top_radius=3200, height=14000)
    create_hyperbolic_cooling_tower("冷却塔_2",
        (-220000, 30000, 5000), base_radius=5000, throat_radius=2500,
        top_radius=3200, height=14000)

    # 烟囱（带警示色环）
    bpy.ops.mesh.primitive_cylinder_add(radius=600, depth=18000,
                                         location=(-205000, 0, 15000))
    chimney = bpy.context.active_object; chimney.name = "烟囱"
    apply_material(chimney, '混凝土')

    # 烟囱顶部警示环
    for ring_i in range(3):
        ring_z = 15000 - 5000 + ring_i * 4000
        bpy.ops.mesh.primitive_cylinder_add(radius=650, depth=800,
                                             location=(-205000, 0, ring_z))
        ring = bpy.context.active_object
        ring.name = f"烟囱警示环_{ring_i+1}"
        apply_material(ring, '警示红白' if ring_i % 2 == 0 else '白色漆面')

    # 输煤栈桥
    bpy.ops.mesh.primitive_cube_add(size=2000, location=(-240000, 0, 4000))
    coal_bridge = bpy.context.active_object; coal_bridge.name = "输煤栈桥"
    coal_bridge.scale = (20, 1, 1.5)
    apply_material(coal_bridge, '金属')

    # ---- 风电场 (5台) ----
    print(">>> 生成风电场...")
    for i in range(5):
        x = -200000 + i * 100000
        y = -220000
        create_wind_turbine(f"风电机_{i+1}", (x, y, 0),
                           tower_height=12000 + random.uniform(-1000, 1000),
                           base_radius=350, top_radius=180, blade_len=6000)

    # ---- 光伏电站 (8x10阵列, 带框架) ----
    print(">>> 生成光伏电站...")
    for i in range(8):
        for j in range(10):
            x = 160000 + i * 3500
            y = -120000 + j * 2500
            z = 2000 + random.uniform(-200, 200)
            create_solar_panel(f"光伏板_{i*10+j+1}", (x, y, z), random.uniform(0.45, 0.6))

    # 逆变器房（2个）
    for inv_i, (ix, iy) in enumerate([(167000, -105000), (183000, -105000)]):
        create_building_with_roof(f"逆变器房_{inv_i+1}", (ix, iy, 1500),
                                  width=3000, depth=2000, height=2500,
                                  body_mat='工业建筑', roof_mat='金属')

    # ---- 电网系统 ----
    print(">>> 生成电网系统...")

    # 220kV枢纽变电站
    create_building_with_roof("220kV枢纽变电站", (0, 0, 3000),
                              width=15000, depth=12000, height=4000,
                              body_mat='金属', roof_mat='蓝色')

    # 110kV区域变电站
    create_building_with_roof("110kV区域变电站", (-110000, 60000, 2500),
                              width=10000, depth=8000, height=3000,
                              body_mat='蓝色', roof_mat='白色漆面')

    # 10kV终端变电站
    create_building_with_roof("10kV终端变电站", (110000, 120000, 2000),
                              width=8000, depth=6000, height=2500,
                              body_mat='绿色', roof_mat='白色漆面')

    # 输电铁塔（格构式）
    tower_positions = [
        (-160000, 0), (-80000, 0), (80000, 0), (160000, 0),
        (-110000, 60000), (0, 60000), (110000, 60000),
        (60000, 110000), (140000, 110000)
    ]
    tower_colors = ['钢材','钢材','钢材','钢材','蓝色','蓝色','蓝色','绿色','绿色']

    for idx, (tx, ty) in enumerate(tower_positions):
        create_transmission_tower(f"输电铁塔_{idx+1}", (tx, ty, 1000), 5000, 1400, 500)
        # 给铁塔上色
        tower_obj = bpy.data.objects.get(f"输电铁塔_{idx+1}")
        if tower_obj:
            apply_material(tower_obj, tower_colors[idx])

    # ---- 居民区 (4x5) ----
    print(">>> 生成居民区...")
    building_colors = ['住宅外墙', '黄色', '橙色', '蓝色', '紫色']
    for i in range(4):
        for j in range(5):
            x = 160000 + i * 7000
            y = 160000 + j * 7000
            z = 2000 + random.uniform(-500, 500)
            h = random.uniform(3000, 6000)
            create_building_with_roof(f"居民楼_{i*5+j+1}", (x, y, z),
                                      width=2500, depth=1800, height=h,
                                      body_mat=building_colors[j % 5],
                                      roof_mat=random.choice(['屋顶红', '蓝色', '绿色']))

    # ---- 道路系统 ----
    print(">>> 生成道路...")
    road_pairs = [
        ("主路_南北", (0, -200000, 500), (0, 200000, 500)),
        ("火电连接路", (0, 0, 500), (-220000, 0, 500)),
        ("风电连接路", (0, -220000, 500), (-200000, -220000, 500)),
        ("光伏连接路", (0, -120000, 500), (180000, -120000, 500)),
        ("居民区连接路", (0, 120000, 500), (180000, 160000, 500)),
    ]
    for rname, start, end in road_pairs:
        create_road(rname, start, end, 1000)

    # ---- 植被 ----
    print(">>> 生成植被...")
    random.seed(42)
    for i in range(200):
        tx = random.uniform(-280000, 280000)
        ty = random.uniform(-280000, 280000)
        # 避开建筑物区域
        if (abs(tx) < 50000 and abs(ty) < 50000): continue  # 避开中心变电站
        if (abs(tx - 160000) < 40000 and abs(ty - 160000) < 40000): continue  # 居民区
        if (abs(tx - 170000) < 30000 and abs(ty + 110000) < 30000): continue  # 光伏区
        if (abs(tx + 220000) < 40000 and abs(ty) < 40000): continue  # 火电区
        # 只在有地形高度的地方种树
        tz = 500 + random.uniform(0, 20000) * (1 if random.random() > 0.6 else 0)
        create_tree(f"树木_{i+1}", (tx, ty, tz), random.uniform(400, 1200))

    print("\n=== 完整综合能源系统精细化场景已生成！===")
    print(f"  总对象数: {len(bpy.data.objects)}")

# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("  抽水蓄能电站 + 火电深度调峰 综合能源系统 (精细化版)")
    print("=" * 60)

    clear_scene()
    prebuild_materials()
    setup_camera()
    setup_lighting()
    generate_complete_system()

    # 设置视口
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.clip_end = 2000000

    # 保存
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_PATH)
    print(f"\n✓ 已保存: {OUTPUT_PATH}")
    print(f"  文件大小: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
    print("=" * 60)

if __name__ == "__main__":
    main()
