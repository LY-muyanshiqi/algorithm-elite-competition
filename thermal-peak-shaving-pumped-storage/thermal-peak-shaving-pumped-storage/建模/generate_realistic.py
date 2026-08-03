"""
抽水蓄能电站 + 火电深度调峰 综合能源系统 — 真实尺度版
参考: 天荒坪抽水蓄能电站 (头570m, L/H≈2.5, 上库0.28km²)
基于 Blender 5.x | 单位: 厘米 (cm)

核心参数:
  上库台地 ~880m, 下库河谷 ~300m, 水头 ~575m
  水平距离 ~1200m, L/H ≈ 2.1
  上库坝 72m×500m, 下库坝 95m×230m
  地下厂房 200m×22m×48m
  压力钢管直径 7m

用法: blender --background --python generate_realistic.py
"""

import bpy
import math
import random
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "抽蓄电站2.blender")

# ============================================================
# PBR 材质库
# ============================================================
MATERIALS_DEF = {
    '混凝土':    ((0.52, 0.50, 0.48, 1), 0.82, 0.0),
    '水':        ((0.12, 0.35, 0.55, 0.78), 0.06, 0.05),
    '金属':      ((0.58, 0.58, 0.60, 1), 0.32, 0.88),
    '白色漆面':  ((0.92, 0.92, 0.93, 1), 0.22, 0.04),
    '光伏玻璃':  ((0.06, 0.18, 0.32, 0.88), 0.08, 0.35),
    '住宅外墙':  ((0.80, 0.74, 0.64, 1), 0.72, 0.0),
    '地面':      ((0.28, 0.42, 0.22, 1), 0.90, 0.0),
    '岩石':      ((0.48, 0.44, 0.40, 1), 0.88, 0.02),
    '工业建筑':  ((0.62, 0.62, 0.64, 1), 0.52, 0.18),
    '蓝色':      ((0.16, 0.32, 0.72, 1), 0.42, 0.28),
    '红色':      ((0.72, 0.16, 0.14, 1), 0.42, 0.22),
    '黄色':      ((0.78, 0.68, 0.16, 1), 0.48, 0.12),
    '绿色':      ((0.16, 0.52, 0.26, 1), 0.58, 0.0),
    '橙色':      ((0.86, 0.48, 0.16, 1), 0.48, 0.12),
    '紫色':      ((0.52, 0.26, 0.72, 1), 0.48, 0.22),
    '隧洞材质':  ((0.32, 0.42, 0.52, 0.50), 0.82, 0.08),
    '风叶白':    ((0.90, 0.90, 0.92, 1), 0.16, 0.02),
    '沥青道路':  ((0.22, 0.22, 0.24, 1), 0.86, 0.0),
    '钢材':      ((0.50, 0.50, 0.52, 1), 0.38, 0.92),
    '屋顶红':    ((0.62, 0.22, 0.18, 1), 0.62, 0.08),
    '玻璃窗':    ((0.28, 0.50, 0.65, 0.65), 0.06, 0.18),
    '树木':      ((0.20, 0.45, 0.18, 1), 0.82, 0.0),
    '树干':      ((0.32, 0.22, 0.12, 1), 0.88, 0.0),
    '草地':      ((0.30, 0.52, 0.24, 1), 0.85, 0.0),
    '坝体混凝土':((0.55, 0.53, 0.50, 1), 0.75, 0.0),
    '钢衬':      ((0.45, 0.45, 0.48, 1), 0.28, 0.95),
}

MAT_CACHE = {}

def create_terrain_material():
    """地形材质：根据坡度混合岩石/泥土/草地"""
    mat = bpy.data.materials.new(name="PBR_地形")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes; links = mat.node_tree.links
    for node in nodes: nodes.remove(node)

    out = nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    geom = nodes.new('ShaderNodeNewGeometry'); geom.location = (-400, 200)
    sep = nodes.new('ShaderNodeSeparateXYZ'); sep.location = (-200, 200)
    links.new(geom.outputs['Normal'], sep.inputs[0])

    # 岩石 (陡坡, low normal.z)
    rock_rgb = nodes.new('ShaderNodeRGB'); rock_rgb.location = (-200, 0)
    rock_rgb.outputs[0].default_value = (0.50, 0.46, 0.42, 1)
    # 泥土 (缓坡)
    dirt_rgb = nodes.new('ShaderNodeRGB'); dirt_rgb.location = (-200, 150)
    dirt_rgb.outputs[0].default_value = (0.38, 0.32, 0.22, 1)
    # 草地 (平地, high normal.z)
    grass_rgb = nodes.new('ShaderNodeRGB'); grass_rgb.location = (-200, 300)
    grass_rgb.outputs[0].default_value = (0.25, 0.48, 0.18, 1)

    # 岩石→泥土 (normal.z as factor)
    mix1 = nodes.new('ShaderNodeMix'); mix1.location = (0, 200)
    mix1.data_type = 'RGBA'
    links.new(rock_rgb.outputs[0], mix1.inputs[3])
    links.new(dirt_rgb.outputs[0], mix1.inputs[4])
    links.new(sep.outputs['Z'], mix1.inputs[1])

    # 泥土→草地 (higher z → grass)
    mix2 = nodes.new('ShaderNodeMix'); mix2.location = (150, 200)
    mix2.data_type = 'RGBA'
    links.new(mix1.outputs[2], mix2.inputs[4])
    links.new(grass_rgb.outputs[0], mix2.inputs[3])
    grass_factor = nodes.new('ShaderNodeMath'); grass_factor.location = (0, 350)
    grass_factor.operation = 'MULTIPLY_ADD'
    grass_factor.inputs[0].default_value = 2.0
    grass_factor.inputs[1].default_value = -1.5
    links.new(sep.outputs['Z'], grass_factor.inputs[2])
    clamp = nodes.new('ShaderNodeClamp'); clamp.location = (80, 350)
    links.new(grass_factor.outputs[0], clamp.inputs[0])
    links.new(clamp.outputs[0], mix2.inputs[1])

    links.new(mix2.outputs[2], bsdf.inputs['Base Color'])
    MAT_CACHE['PBR_地形'] = mat
    return mat

def create_pbr_material(name, base_color, roughness, metallic):
    mat = bpy.data.materials.new(name=name)
    nodes = mat.node_tree.nodes; links = mat.node_tree.links
    for node in nodes: nodes.remove(node)
    out = nodes.new('ShaderNodeOutputMaterial'); out.location = (400, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = base_color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if base_color[3] < 1.0:
        bsdf.inputs['Alpha'].default_value = base_color[3]
        mat.blend_method = 'BLEND'
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    MAT_CACHE[name] = mat
    return mat

def apply_material(obj, material_name):
    if material_name == '地形':
        if 'PBR_地形' not in MAT_CACHE:
            create_terrain_material()
        mat = MAT_CACHE['PBR_地形']
    else:
        mat_key = f'PBR_{material_name}'
        if mat_key not in MAT_CACHE:
            if material_name in MATERIALS_DEF:
                d = MATERIALS_DEF[material_name]
                create_pbr_material(mat_key, d[0], d[1], d[2])
            else: return
        mat = MAT_CACHE[mat_key]
    if obj.data.materials: obj.data.materials[0] = mat
    else: obj.data.materials.append(mat)

# ============================================================
# 真实地形生成 — 台地→陡坡→河谷 (天荒坪参考)
# ============================================================
def create_realistic_terrain():
    """
    台地-陡坡-河谷三段式地形:
    - 北侧 (y<0): 高山台地 ~880m, 上水库所在
    - 中部: 陡峭过渡坡 (山体面)
    - 南侧 (y>0): 河谷低地 ~280-320m, 下水库所在
    - 东西向山脊增加立体感
    """
    size = 800000   # 8km × 8km
    subdiv = 200    # 200×200 grid, 40m spacing

    bpy.ops.mesh.primitive_grid_add(x_subdivisions=subdiv, y_subdivisions=subdiv,
                                     size=size, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "地形"

    mesh = terrain.data
    verts = mesh.vertices

    # ---- 关键高程参数 (cm) ----
    upper_plateau_elev = 88000   # 上台地 ~880m
    lower_valley_elev  = 28000   # 下河谷 ~280m
    # 过渡带: 从台地到河谷的陡坡
    trans_center = -25000        # 过渡中心 (略偏北)
    trans_width  = 35000         # 过渡宽度

    # 上水库参数
    upper_cx, upper_cy = 0, -110000   # 上台地中央 (北侧1100m)
    upper_radius = 28000              # 半径 ~280m (约0.25km²)
    upper_bowl_depth = 3200           # 挖深 ~32m

    # 下水库参数
    lower_cx, lower_cy = 0, 25000     # 下河谷 (南侧250m)
    lower_radius = 20000              # 半径 ~200m
    lower_bowl_depth = 2800           # 挖深 ~28m

    random.seed(12345)
    # 预生成随机数以加速
    rand_vals = [random.random() for _ in range(len(verts))]

    for idx, v in enumerate(verts):
        x, y, _ = v.co

        # ---- 1. 基础高程: tanh 台地→河谷 ----
        t_norm = (y - trans_center) / trans_width
        blend = (1.0 - math.tanh(t_norm * 1.6)) / 2.0
        z = upper_plateau_elev * blend + lower_valley_elev * (1.0 - blend)

        # ---- 2. 主山脊 (东西走向, 在过渡带最高) ----
        # 山脊沿过渡带延伸, 中间高两侧低
        ridge_y_peak = -40000
        ridge_amp = 28000  # 山脊比台地高 280m
        ridge = ridge_amp * math.exp(-((y - ridge_y_peak) / 28000)**2)
        ridge *= math.exp(-(abs(x) / 320000)**3)
        # 中央山峰更高
        central_peak = 18000 * math.exp(-((y - (-55000)) / 35000)**2)
        central_peak *= math.exp(-(x / 100000)**2)
        ridge += central_peak

        # ---- 3. 两侧山脊 ----
        side_ridge = 12000 * math.exp(-((abs(x) - 250000) / 80000)**2)
        side_ridge *= math.exp(-((y - (-30000)) / 60000)**2) * blend

        # ---- 4. 上水库盆地 (台地上挖出洼地) ----
        dx_u = x - upper_cx
        dy_u = y - upper_cy
        dist_u = math.sqrt(dx_u * dx_u + dy_u * dy_u)
        upper_bowl = -upper_bowl_depth * math.exp(-(dist_u / upper_radius)**4)

        # 坝址隆起 (水库南缘, 对齐大坝位置)
        dam_ridge_y = upper_cy + upper_radius  # 水库南缘
        dy_dam = y - dam_ridge_y
        dam_abut = 7000 * math.exp(-(dy_dam / 10000)**2)
        dam_abut *= math.exp(-(x / 55000)**2)
        dam_abut *= (1.0 if -60000 < x < 60000 else 0.0)

        # ---- 5. 上台地压平 (消去山脊对库区的影响) ----
        plateau_radius = upper_radius * 2.0
        if dist_u < plateau_radius:
            plateau_target = upper_plateau_elev - 1800
            flatten = math.exp(-(dist_u / plateau_radius)**3)
            z = z * (1.0 - flatten) + plateau_target * flatten

        # ---- 6. 上台地洼地+坝址 (压平后再挖) ----
        z += upper_bowl + dam_abut

        # ---- 7. 下水库河谷洼地 ----
        dx_l = x - lower_cx
        dy_l = y - lower_cy
        dist_l = math.sqrt(dx_l * dx_l + dy_l * dy_l)
        lower_bowl = -lower_bowl_depth * math.exp(-(dist_l / lower_radius)**4)
        valley_rim = 1200 * math.exp(-(dist_l / (lower_radius * 1.5))**2)

        # 下库坝址隆起 (水库北缘, 对齐大坝)
        dam_ridge_l_y = lower_cy - lower_radius  # y = 5000 (北缘)
        dy_dam_l = y - dam_ridge_l_y
        lower_dam_abut = 6000 * math.exp(-(dy_dam_l / 8000)**2)
        lower_dam_abut *= math.exp(-(x / 30000)**2)
        lower_dam_abut *= (1.0 if -25000 < x < 25000 else 0.0)

        z += lower_bowl + valley_rim + lower_dam_abut

        # ---- 8. 河道 (连接上下库的天然溪谷) ----
        channel = 0.0
        if -120000 < y < 40000 and abs(x) < 20000:
            ch_width = 6000 + (y + 120000) / 160000 * 12000
            ch_factor = math.exp(-(x / ch_width)**2)
            channel = -z * 0.18 * ch_factor

        # ---- 9. 多层噪声 ----
        # 大尺度起伏
        n1 = (math.sin(x * 0.000022 + y * 0.000016)
              * math.cos(y * 0.000018 - x * 0.000011))
        n2 = math.sin(x * 0.000038 - y * 0.000032)
        noise_large = (n1 * 0.5 + n2 * 0.5) * 18000 * blend

        # 中尺度细节
        n3 = math.sin(x * 0.00008 + 1.3) * math.cos(y * 0.00007 + 0.7)
        noise_med = n3 * 6000 * blend

        # 微尺度
        noise_small = (rand_vals[idx] - 0.5) * 3500

        # ---- 10. 合成 ----
        z += ridge + side_ridge + channel + noise_large + noise_med + noise_small

        # 下限
        z = max(z, -3000)

        v.co = (x, y, z)

    mesh.update()

    # 平滑法线
    bpy.context.view_layer.objects.active = terrain
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.set_normals_from_faces()
    bpy.ops.object.mode_set(mode='OBJECT')

    apply_material(terrain, '地形')

    max_z = max(v.co.z for v in verts)
    print(f"✓ 地形: {size/100000:.0f}km², {subdiv}×{subdiv}, "
          f"最高{max_z/100:.0f}m, 台地~{upper_plateau_elev/100:.0f}m, 河谷~{lower_valley_elev/100:.0f}m")
    return terrain

# ============================================================
# 大坝 — 梯形截面挤出 (bmesh)
# ============================================================
def create_dam(name, location, length, height, base_w, top_w, rotation_z=0):
    """梯形截面大坝: 底宽base_w, 顶宽top_w, 高height, 长length"""
    import bmesh
    h2 = height / 2; bw2 = base_w / 2; tw2 = top_w / 2
    # XY平面梯形截面
    verts_2d = [(-bw2, -h2, 0), (bw2, -h2, 0), (tw2, h2, 0), (-tw2, h2, 0)]
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    for v in verts_2d: bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    bm.faces.new(bm.verts)
    bm.faces.ensure_lookup_table()
    geom = bmesh.ops.extrude_face_region(bm, geom=[bm.faces[0]])
    ev = [e for e in geom['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, length), verts=ev)
    bm.to_mesh(mesh); bm.free(); mesh.update()

    obj.location = location
    obj.rotation_euler = (1.5708, 0, rotation_z)
    apply_material(obj, '坝体混凝土')
    return obj

# ============================================================
# 双曲线冷却塔 (旋转体)
# ============================================================
def create_cooling_tower(name, location, base_r=3200, throat_r=1800, top_r=2200, height=9000, segs=48):
    """双曲线冷却塔: 底部宽→腰部窄→顶部微扩"""
    levels = 24; verts = []; faces = []
    for i in range(levels + 1):
        t = i / levels; zv = t * height - height / 2
        if t < 0.30:
            r = base_r - (base_r - throat_r) * (t / 0.30)
        elif t < 0.60:
            r = throat_r
        else:
            r = throat_r + (top_r - throat_r) * ((t - 0.60) / 0.40)
        for j in range(segs):
            ang = 2 * math.pi * j / segs
            verts.append((r * math.cos(ang), r * math.sin(ang), zv))
    for i in range(levels):
        for j in range(segs):
            a = i * segs + j; b = i * segs + (j + 1) % segs
            c = (i + 1) * segs + (j + 1) % segs; d = (i + 1) * segs + j
            faces.append((a, b, c, d))
    # 顶部封口
    tc = len(verts); verts.append((0, 0, height / 2))
    for j in range(segs):
        a = levels * segs + j; b = levels * segs + (j + 1) % segs
        faces.append((a, b, tc))
    # 底部封口
    bc = len(verts); verts.append((0, 0, -height / 2))
    for j in range(segs):
        a = (j + 1) % segs; b = j; faces.append((a, b, bc))

    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces); mesh.update()
    obj.location = location
    apply_material(obj, '混凝土')
    return obj

# ============================================================
# 风电机组
# ============================================================
def create_wind_turbine(name, location, tower_h=9000, base_r=300, top_r=160, blade_len=5500):
    """风电机组: 塔筒+机舱+轮毂+3叶片, 默认90m塔高55m叶片≈6MW级"""
    x, y, z = location
    bpy.ops.mesh.primitive_cone_add(radius1=base_r, radius2=top_r, depth=tower_h,
                                     location=(x, y, z + tower_h / 2), vertices=24)
    tw = bpy.context.active_object; tw.name = f"{name}_塔筒"; apply_material(tw, '白色漆面')

    bpy.ops.mesh.primitive_cube_add(size=1600, location=(x, y, z + tower_h))
    nc = bpy.context.active_object; nc.name = f"{name}_机舱"
    nc.scale = (4.0, 1.2, 1.0); apply_material(nc, '白色漆面')

    bpy.ops.mesh.primitive_uv_sphere_add(radius=300, location=(x + 3200, y, z + tower_h))
    hb = bpy.context.active_object; hb.name = f"{name}_轮毂"
    hb.scale = (1, 0.75, 0.75); apply_material(hb, '白色漆面')

    for j in range(3):
        ang = j * 2.0944
        bpy.ops.mesh.primitive_cube_add(size=450, location=(x + 3200, y, z + tower_h))
        bl = bpy.context.active_object; bl.name = f"{name}_叶片{j+1}"
        bl.scale = (blade_len / 225, 0.07, 0.55); bl.rotation_euler = (0.2, ang, 0)
        apply_material(bl, '风叶白')
    return tw

# ============================================================
# 光伏板
# ============================================================
def create_solar_panel(name, location, tilt=0.5236):
    x, y, z = location
    bpy.ops.mesh.primitive_plane_add(size=220, location=(x, y, z))
    pn = bpy.context.active_object; pn.name = name; pn.rotation_euler = (tilt, 0, 0)
    apply_material(pn, '光伏玻璃')

    bpy.ops.mesh.primitive_cube_add(size=210, location=(x, y, z + 55 * math.sin(tilt)))
    fr = bpy.context.active_object; fr.name = name + "_框"
    fr.scale = (1, 0.04, 0.02); fr.rotation_euler = (tilt, 0, 0)
    apply_material(fr, '金属')

    for s in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(radius=14, depth=350, location=(x + s * 70, y, z - 170))
        pl = bpy.context.active_object; pl.name = name + f"_柱{s+2}"; apply_material(pl, '金属')
    return pn

# ============================================================
# 建筑物 (带屋顶)
# ============================================================
def create_building(name, location, w=2500, d=1800, h=4000, body_mat='住宅外墙', roof_mat='屋顶红'):
    x, y, z = location
    bpy.ops.mesh.primitive_cube_add(size=w, location=(x, y, z + h / 2))
    bd = bpy.context.active_object; bd.name = name; bd.scale = (1, d / w, 1)
    apply_material(bd, body_mat)

    bpy.ops.mesh.primitive_cone_add(radius1=w * 0.65, radius2=0, depth=800,
                                     location=(x, y, z + h + 400), vertices=4)
    rf = bpy.context.active_object; rf.name = name + "_顶"
    rf.rotation_euler = (0, 0, 0.785); rf.scale = (1, d / w, 1)
    apply_material(rf, roof_mat)
    return bd

# ============================================================
# 树木
# ============================================================
def create_tree(name, location, h=750):
    x, y, z = location
    bpy.ops.mesh.primitive_cylinder_add(radius=35, depth=h * 0.45, location=(x, y, z + h * 0.22))
    tr = bpy.context.active_object; tr.name = name + "_干"; apply_material(tr, '树干')
    for i in range(3):
        cr = h * (0.30 - i * 0.06); cz = z + h * (0.42 + i * 0.2)
        bpy.ops.mesh.primitive_ico_sphere_add(radius=cr, subdivisions=2,
                                               location=(x + random.uniform(-cr * 0.3, cr * 0.3),
                                                        y + random.uniform(-cr * 0.3, cr * 0.3), cz))
        cn = bpy.context.active_object; cn.name = name + f"_冠{i+1}"
        cn.scale = (1, 1, 0.7 + random.uniform(0, 0.3)); apply_material(cn, '树木')
    return tr

# ============================================================
# 道路
# ============================================================
def create_road(name, start, end, width=900):
    dx = end[0] - start[0]; dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, max(start[2], end[2]))
    angle = math.atan2(dy, dx)
    bpy.ops.mesh.primitive_plane_add(size=width, location=mid)
    rd = bpy.context.active_object; rd.name = name
    rd.scale = (length / width, 1, 1); rd.rotation_euler = (0, 0, angle)
    apply_material(rd, '沥青道路')
    return rd

# ============================================================
# 场景生成
# ============================================================
def generate_scene():
    # ---- 关键坐标 ----
    upper_y, upper_z_surface = -110000, 86200   # 上库水面 ~862m
    lower_y, lower_z_surface = 25000, 30200      # 下库水面 ~302m
    upper_r = 28000  # 上库半径 280m
    lower_r = 20000  # 下库半径 200m
    head = (upper_z_surface - lower_z_surface) / 100  # ~560m

    # 1. 地形
    print(">>> 1/10 生成真实尺度地形 (台地→陡坡→河谷)...")
    create_realistic_terrain()

    # 2. 上水库 + 大坝
    print(">>> 2/10 生成上水库 (台地顶部, ~862m)...")
    bpy.ops.mesh.primitive_circle_add(radius=28000, vertices=72, location=(0, upper_y, upper_z_surface - 200))
    ures = bpy.context.active_object; ures.name = "上水库"; apply_material(ures, '水')

    # 上水库大坝 (南缘, y=-82000, 梯形截面: 高72m, 底宽50m, 顶宽10m, 长500m)
    create_dam("上水库大坝", (0, upper_y + upper_r, upper_z_surface - 3700),
               50000, 7200, 5000, 1000, 0)

    # 进水口 (水库北侧)
    bpy.ops.mesh.primitive_cube_add(size=2000, location=(0, upper_y - 26000, upper_z_surface - 3000))
    itk = bpy.context.active_object; itk.name = "上库进水塔"
    itk.scale = (1.5, 0.9, 5.5); apply_material(itk, '混凝土')

    # 3. 压力钢管 (直径7m, 沿陡坡下行)
    print(">>> 3/10 生成压力钢管 (Φ7m, 沿陡坡)...")
    pipe_segs = 10
    for i in range(pipe_segs):
        t = i / (pipe_segs - 1)
        pz = upper_z_surface - 4000 + t * (40000 - upper_z_surface + 4000)
        py = upper_y - 26000 + t * (-30000 - upper_y + 26000)
        px = 6000 * math.sin(t * 1.2)
        bpy.ops.mesh.primitive_cylinder_add(radius=350, depth=14000,
                                             location=(px, py, pz))
        seg = bpy.context.active_object; seg.name = f"压力钢管_{i+1}"
        seg.rotation_euler = (0.5, 0, 0); apply_material(seg, '钢衬')

    # 4. 地下厂房 (200m×22m×48m)
    print(">>> 4/10 生成地下厂房 (200m×22m×48m)...")
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(0, -45000, 32000))
    ug = bpy.context.active_object; ug.name = "地下厂房"
    ug.scale = (50, 5.5, 12); apply_material(ug, '混凝土')

    # 厂房附属洞室
    bpy.ops.mesh.primitive_cylinder_add(radius=700, depth=8000, location=(26000, -45000, 42000))
    at = bpy.context.active_object; at.name = "主变洞"; apply_material(at, '混凝土')

    # 5. 下水库 + 大坝
    print(">>> 5/10 生成下水库 (河谷, ~302m)...")
    bpy.ops.mesh.primitive_circle_add(radius=20000, vertices=64, location=(0, lower_y, lower_z_surface - 200))
    lres = bpy.context.active_object; lres.name = "下水库"; apply_material(lres, '水')

    # 下水库大坝 (北缘, y=5000, 梯形截面: 高95m, 底宽60m, 顶宽12m, 长230m)
    create_dam("下水库大坝", (0, lower_y - lower_r, lower_z_surface - 4800),
               23000, 9500, 6000, 1200, 0)

    # 尾水隧洞
    bpy.ops.mesh.primitive_cylinder_add(radius=500, depth=70000,
                                         location=(0, -10000, lower_z_surface - 1000))
    ttn = bpy.context.active_object; ttn.name = "尾水隧洞"
    ttn.rotation_euler = (1.57, 0, 0); apply_material(ttn, '隧洞材质')

    # 6. 火力发电厂 (放置在西侧河谷区)
    print(">>> 6/10 生成火力发电厂...")
    tx, ty, tz = -220000, -60000, 30000  # 河谷侧

    # 主厂房 (~180m×70m×40m)
    bpy.ops.mesh.primitive_cube_add(size=12000, location=(tx, ty, tz + 3500))
    tb = bpy.context.active_object; tb.name = "火电主厂房"
    tb.scale = (1, 0.38, 0.58); apply_material(tb, '工业建筑')

    # 锅炉房
    bpy.ops.mesh.primitive_cube_add(size=5000, location=(tx - 3000, ty, tz + 6000))
    tbr = bpy.context.active_object; tbr.name = "火电锅炉房"
    tbr.scale = (1, 0.38, 0.5); apply_material(tbr, '工业建筑')

    # 煤场
    bpy.ops.mesh.primitive_cube_add(size=6000, location=(tx - 15000, ty, tz + 1500))
    cy = bpy.context.active_object; cy.name = "煤场"
    cy.scale = (1, 0.5, 0.16); apply_material(cy, '地面')

    # 冷却塔 x2 (90m高, 64m底径, 36m喉径)
    create_cooling_tower("冷却塔_1", (tx, ty - 25000, tz - 2000), 3200, 1800, 2200, 9000)
    create_cooling_tower("冷却塔_2", (tx, ty + 25000, tz - 2000), 3200, 1800, 2200, 9000)

    # 烟囱 (150m)
    bpy.ops.mesh.primitive_cylinder_add(radius=450, depth=15000, location=(tx + 12000, ty, tz + 9500))
    chim = bpy.context.active_object; chim.name = "烟囱"; apply_material(chim, '混凝土')

    # 开关站
    bpy.ops.mesh.primitive_cube_add(size=4000, location=(tx + 20000, ty, tz + 1500))
    sw = bpy.context.active_object; sw.name = "火电开关站"
    sw.scale = (3, 2, 1.5); apply_material(sw, '金属')

    # 7. 风电场 (沿山脊布置)
    print(">>> 7/10 生成风电场 (山脊线, 8台×6MW级)...")
    wind_y = -65000
    for i in range(8):
        wx = -280000 + i * 80000
        wy = wind_y + random.uniform(-8000, 8000)
        create_wind_turbine(f"风电_{i+1}", (wx, wy, 35000 + random.uniform(-3000, 3000)),
                          9000 + random.uniform(-500, 500), 320, 170, 5500)

    # 8. 光伏电站 (东南侧平坦河谷)
    print(">>> 8/10 生成光伏电站 (12×15阵列)...")
    for i in range(12):
        for j in range(15):
            sx = 180000 + i * 3500; sy = 60000 + j * 2800
            create_solar_panel(f"光伏_{i*15+j+1}", (sx, sy, 29500 + random.uniform(-200, 200)))

    # 逆变器房
    bpy.ops.mesh.primitive_cube_add(size=1000, location=(198000, 80000, 30000))
    inv = bpy.context.active_object; inv.name = "逆变器房"
    inv.scale = (8, 5, 3); apply_material(inv, '金属')

    # 9. 电网系统
    print(">>> 9/10 生成电网系统...")
    # 500kV枢纽变电站 (下库附近)
    create_building("500kV枢纽变电站", (0, -20000, 29500), 16000, 12000, 4500, '金属', '蓝色')
    # 220kV区域变电站
    create_building("220kV区域变电站", (-90000, 40000, 29500), 11000, 8000, 3500, '蓝色', '白色漆面')
    # 110kV终端变电站
    create_building("110kV终端变电站", (100000, 100000, 29500), 8000, 6000, 2800, '绿色', '白色漆面')

    # 输电铁塔 (沿主要输电走廊)
    tower_pts = [
        (-160000, -20000), (-60000, -20000), (60000, -20000), (160000, -20000),
        (-100000, 50000), (0, 50000), (100000, 50000), (50000, 100000), (150000, 100000),
    ]
    for idx, (px, py) in enumerate(tower_pts):
        bpy.ops.mesh.primitive_cone_add(radius1=700, radius2=280, depth=5000,
                                         location=(px, py, 31000), vertices=4)
        twr = bpy.context.active_object; twr.name = f"铁塔_{idx+1}"; apply_material(twr, '钢材')

    # 10. 居民区 + 道路 + 植被
    print(">>> 10/10 生成居民区、道路、植被...")
    bld_colors = ['住宅外墙', '黄色', '橙色', '蓝色', '紫色']
    for i in range(5):
        for j in range(6):
            bx = 160000 + i * 7000; by = 140000 + j * 7000
            create_building(f"居民楼_{i*6+j+1}", (bx, by, 29500 + random.uniform(-300, 300)),
                          2500, 1800, random.uniform(3000, 6000),
                          bld_colors[j % 5], random.choice(['屋顶红', '蓝色', '绿色']))

    # 配电箱
    for i in range(4):
        for j in range(5):
            bx = 163000 + i * 7000; by = 143000 + j * 7000
            bpy.ops.mesh.primitive_cube_add(size=200, location=(bx, by, 29500))
            bx_obj = bpy.context.active_object; bx_obj.name = f"配电箱_{i*5+j+1}"
            apply_material(bx_obj, '金属')

    # 道路系统
    create_road("主路_南北", (0, -180000, 86000), (0, 180000, 29000), 1000)
    create_road("火电支路", (0, -30000, 40000), (-220000, -60000, 30000), 800)
    create_road("上库盘山路", (0, -80000, 50000), (0, -135000, 85000), 700)
    create_road("风电检修路", (-300000, -65000, 50000), (300000, -65000, 50000), 700)
    create_road("光伏支路", (50000, 80000, 29500), (200000, 80000, 29500), 800)
    create_road("居民路", (100000, 120000, 29500), (190000, 155000, 29500), 800)

    # 植被 (分区域: 山体密林 + 河谷散树 + 台地灌丛)
    random.seed(42)
    for i in range(400):
        tx = random.uniform(-350000, 350000)
        ty = random.uniform(-350000, 350000)
        # 避开建筑区
        if abs(tx) < 50000 and abs(ty) < 50000: continue
        if abs(tx - 190000) < 30000 and 55000 < ty < 95000: continue  # 光伏区
        if abs(tx + 220000) < 40000 and abs(ty + 60000) < 40000: continue  # 火电区
        if 155000 < tx < 200000 and 135000 < ty < 185000: continue  # 居民区
        if abs(tx) < 35000 and (-125000 < ty < -25000): continue  # 库区+厂房

        # 根据位置确定树高
        if ty < -60000:   # 台地区 — 较矮
            th = random.uniform(350, 900)
            tz = 85000 + random.uniform(0, 15000)
        elif ty < 20000:  # 山体陡坡 — 高树
            th = random.uniform(600, 1500)
            tz = 30000 + random.uniform(0, 60000)
        else:             # 河谷 — 中等
            th = random.uniform(400, 1100)
            tz = 29000 + random.uniform(0, 8000)

        create_tree(f"树_{i+1}", (tx, ty, tz), th)

    print(f"\n✓ 场景完成! 总对象: {len(bpy.data.objects)}, 水头: {head:.0f}m")

# ============================================================
# 主入口
# ============================================================
def main():
    print("=" * 60)
    print("  抽水蓄能+火电深度调峰 综合能源系统 (真实尺度版)")
    print("  参考: 天荒坪 头570m L/H≈2.5 上库0.28km²")
    print("=" * 60)

    # 清空
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for t in list(bpy.data.textures): bpy.data.textures.remove(t)
    MAT_CACHE.clear()

    # 预建材质
    for name, props in MATERIALS_DEF.items():
        create_pbr_material(f'PBR_{name}', props[0], props[1], props[2])
    print(f"✓ {len(MATERIALS_DEF)} 种PBR材质")

    # 相机 (从东南方俯瞰, 展示台地→河谷高差)
    bpy.ops.object.camera_add(location=(180000, 120000, 110000))
    cam = bpy.context.active_object; cam.name = "主相机"
    # 看向上水库—下水库中间的山体面
    cam.rotation_euler = (1.05, 0, 1.2)
    cam.data.type = 'PERSP'; cam.data.lens = 28
    cam.data.clip_start = 50; cam.data.clip_end = 3000000
    bpy.context.scene.camera = cam
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080

    # 光照 (午后阳光, 西北方向)
    bpy.ops.object.light_add(type='SUN', location=(100000, -80000, 180000))
    sun = bpy.context.active_object; sun.name = "太阳光"
    sun.data.energy = 4.5; sun.data.angle = 0.03
    sun.rotation_euler = (0.6, 0.2, 0.5)

    bpy.ops.object.light_add(type='AREA', location=(0, 0, 250000))
    area = bpy.context.active_object; area.name = "环境光"
    area.data.energy = 600; area.data.size = 250000

    # 世界环境 (Hosek-Wilkie天空 + 大气雾)
    world = bpy.context.scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes; links = world.node_tree.links
    for node in nodes: nodes.remove(node)
    sky_tex = nodes.new('ShaderNodeTexSky'); sky_tex.location = (-300, 0)
    sky_tex.sky_type = 'HOSEK_WILKIE'
    sky_tex.sun_direction = (0.25, -0.15, 0.9)
    sky_tex.turbidity = 2.5
    sky_tex.ground_albedo = 0.3
    bg_out = nodes.new('ShaderNodeBackground'); bg_out.location = (0, 0)
    bg_out.inputs['Strength'].default_value = 0.85
    out_w = nodes.new('ShaderNodeOutputWorld'); out_w.location = (300, 0)
    links.new(sky_tex.outputs['Color'], bg_out.inputs['Color'])
    links.new(bg_out.outputs['Background'], out_w.inputs['Surface'])

    # 大气雾效
    bpy.context.scene.world.mist_settings.use_mist = True
    bpy.context.scene.world.mist_settings.start = 2000
    bpy.context.scene.world.mist_settings.depth = 900000
    bpy.context.scene.world.mist_settings.height = 25000
    bpy.context.scene.world.mist_settings.intensity = 0.12

    # 生成场景
    generate_scene()

    # 视口设置
    for a in bpy.context.screen.areas:
        if a.type == 'VIEW_3D':
            for s in a.spaces:
                if s.type == 'VIEW_3D':
                    s.shading.type = 'MATERIAL'; s.clip_end = 2000000

    # 渲染预览图
    preview_path = os.path.join(OUTPUT_DIR, "抽蓄电站2_preview.png")
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.filepath = preview_path
    bpy.ops.render.render(write_still=True)
    print(f"✓ 预览图: {preview_path}")

    # 保存
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_PATH)
    print(f"\n✓ 保存: {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)/1024:.0f} KB)")
    print("=" * 60)

if __name__ == "__main__":
    main()
