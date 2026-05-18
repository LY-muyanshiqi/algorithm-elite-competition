"""Analyze the current Blender scene"""
from mcp_tools import execute_code

code = '''
import bpy

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
total_verts = sum(len(o.data.vertices) for o in meshes)
total_faces = sum(len(o.data.polygons) for o in meshes)

print(f"Total meshes: {len(meshes)}")
print(f"Total vertices: {total_verts:,}")
print(f"Total faces: {total_faces:,}")
print(f"Materials: {[m.name for m in bpy.data.materials]}")

min_bound = [float("inf")] * 3
max_bound = [float("-inf")] * 3
for o in meshes:
    for v in o.data.vertices:
        wv = o.matrix_world @ v.co
        for i in range(3):
            min_bound[i] = min(min_bound[i], wv[i])
            max_bound[i] = max(max_bound[i], wv[i])

size = [max_bound[i] - min_bound[i] for i in range(3)]
print(f"BBox: {[round(v,1) for v in min_bound]} to {[round(v,1) for v in max_bound]}")
print(f"Size: {[round(s,1) for s in size]} m")

sizes = [(o.name, len(o.data.vertices), len(o.data.polygons)) for o in meshes]
sizes.sort(key=lambda x: x[1], reverse=True)
print("\\nTop 10 largest meshes:")
for n,v,f in sizes[:10]:
    print(f"  {n}: {v:,} verts, {f:,} faces")
'''

r = execute_code(code)
print(r['result']['result'])
