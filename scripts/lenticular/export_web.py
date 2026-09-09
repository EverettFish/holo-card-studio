"""Export the card geometry with browser material-role names. Run inside Blender after build_card.py."""
import bpy, sys
from pathlib import Path
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
root = Path(args[0]) if args else Path(__file__).resolve().parent
blend = root / 'card.blend'
if not blend.exists(): raise FileNotFoundError('Missing card.blend')
bpy.ops.wm.open_mainfile(filepath=str(blend))
pivot = bpy.data.objects['转卡控制 · 播放时间线预览']; pivot.animation_data_clear(); pivot.rotation_euler = (0, 0, 0)
materials = {}
for role in ['front', 'edge', 'back', 'text', 'gold', 'foil', 'lines', 'particles']:
    m = bpy.data.materials.new('web_' + role); m.diffuse_color = (.7, .5, .2, 1); m.use_nodes = True; materials[role] = m
bpy.ops.object.select_all(action='DESELECT')
for ob in list(bpy.data.collections['卡牌 · 光栅成品'].objects):
    if ob.type != 'MESH': continue
    if '文字平面' in ob.name: ob.hide_render = True; continue
    ob.select_set(True)
    if ob.get('web_role'):
        ob.data.materials.clear(); ob.data.materials.append(materials[ob['web_role']])
    elif '主体平面' in ob.name:
        old = [p.material_index for p in ob.data.polygons]; ob.data.materials.clear()
        for role in ['front', 'edge', 'back']: ob.data.materials.append(materials[role])
        for p, i in zip(ob.data.polygons, old): p.material_index = i
    else:
        role = 'gold' if '古金' in ob.name else 'edge'; ob.data.materials.clear(); ob.data.materials.append(materials[role])
pivot.select_set(True)
output = root / 'web' / 'assets' / 'card.glb'; output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True, export_materials='EXPORT', export_animations=False, export_cameras=False, export_lights=False, export_yup=True)
print('EXPORTED', output)
