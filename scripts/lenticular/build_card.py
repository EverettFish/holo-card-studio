"""Build an editable Blender lenticular card. Run inside Blender: blender --background --factory-startup --python build_card.py -- <project> [--skip-render]"""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
R = Path(args[0]).resolve() if args else Path.cwd()
CFG = json.loads((R / 'card-config.json').read_text(encoding='utf-8-sig'))
FX=CFG.get('effects',{'particles':.65,'glow':.65})
L = {**{'flipAngle': 14, 'softness': .30, 'pitch': 120, 'stripe': .35, 'sweep': 6, 'refract': .3, 'ridge': .5, 'depth': .08, 'foil': .35, 'cycle': False}, **CFG.get('lenticular', {})}
(R / 'renders').mkdir(exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for g in list(bpy.data.node_groups):
    if g.bl_idname == 'ShaderNodeTree': bpy.data.node_groups.remove(g)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 48; scene.cycles.use_denoising = True; scene.cycles.transparent_max_bounces=32
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices(); gpu = False
    for dev in prefs.devices: dev.use = dev.type != 'CPU'; gpu = gpu or dev.use
    if gpu: scene.cycles.device = 'GPU'
except Exception as e: print('GPU fallback', e)
scene.render.resolution_x = 1080; scene.render.resolution_y = 1500; scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'; scene.render.film_transparent = True
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.fps = 24; scene.frame_start = 1; scene.frame_end = 96
world = bpy.data.worlds.new('深靛摄影棚'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.045, .065, .10, 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = .18


def node(tree, typ, name, x=0, y=0):
    n = tree.nodes.new(typ); n.name = name; n.label = name; n.location = (x, y); return n
def link(t, a, ao, b, bi): t.links.new(a.outputs[ao], b.inputs[bi])
def val(t, op, name, x, y, a=None, b=None):
    n = node(t, 'ShaderNodeMath', name, x, y); n.operation = op
    if a is not None: n.inputs[0].default_value = a
    if b is not None: n.inputs[1].default_value = b
    return n
def vec(t, op, name, x, y):
    n = node(t, 'ShaderNodeVectorMath', name, x, y); n.operation = op; return n
def socket(g, name, direction, kind, default=None, lo=None, hi=None):
    s = g.interface.new_socket(name=name, in_out=direction, socket_type=kind)
    if default is not None: s.default_value = default
    if lo is not None: s.min_value = lo
    if hi is not None: s.max_value = hi
    return s

# ---------------------------------------------------------------------------------------------
# Group 1: lenticular phase. Local view angle -> per-point mix factor, refraction offset, lens coordinate.
# Object space of the X=90° plane: local X across the card, local Z toward the viewer.
# ---------------------------------------------------------------------------------------------
LG = bpy.data.node_groups.new('光栅 · 视角相位 / Lenticular Phase', 'ShaderNodeTree')
socket(LG, 'UV', 'INPUT', 'NodeSocketVector')
socket(LG, '翻转角度', 'INPUT', 'NodeSocketFloat', L['flipAngle'], 3, 60)
socket(LG, '过渡柔和', 'INPUT', 'NodeSocketFloat', L['softness'], .02, .5)
socket(LG, '光栅密度', 'INPUT', 'NodeSocketFloat', L['pitch'], 10, 400)
socket(LG, '条纹显现', 'INPUT', 'NodeSocketFloat', L['stripe'], 0, 1)
socket(LG, '扫掠', 'INPUT', 'NodeSocketFloat', L['sweep'], 0, 30)
socket(LG, '柱镜折射', 'INPUT', 'NodeSocketFloat', L['refract'], 0, 3)
socket(LG, '循环', 'INPUT', 'NodeSocketFloat', 1.0 if L['cycle'] else 0.0, 0, 1)
socket(LG, '混合系数', 'OUTPUT', 'NodeSocketFloat'); socket(LG, '折射偏移', 'OUTPUT', 'NodeSocketVector'); socket(LG, '光栅坐标', 'OUTPUT', 'NodeSocketFloat')
gi = node(LG, 'NodeGroupInput', '光栅参数', -1500, 200); go = node(LG, 'NodeGroupOutput', '光栅输出', 1500, 100)
geo = node(LG, 'ShaderNodeNewGeometry', '几何 · 每点视线', -1500, -300)
view = node(LG, 'ShaderNodeVectorTransform', '视线 世界 → 物体', -1280, -300); view.vector_type = 'VECTOR'; view.convert_from = 'WORLD'; view.convert_to = 'OBJECT'; link(LG, geo, 'Incoming', view, 'Vector')
sep = node(LG, 'ShaderNodeSeparateXYZ', '拆分 X / Z', -1080, -300); link(LG, view, 0, sep, 0)
zc = val(LG, 'MAXIMUM', '法向分量下限 0.05', -880, -380, b=.05); link(LG, sep, 'Z', zc, 0)
at = val(LG, 'ARCTAN2', '水平视角 atan2(x,z)', -680, -300); link(LG, sep, 'X', at, 0); link(LG, zc, 0, at, 1)
deg = val(LG, 'DEGREES', '弧度 → 角度', -480, -300); link(LG, at, 0, deg, 0)
usep = node(LG, 'ShaderNodeSeparateXYZ', 'UV 拆分', -1280, 300); link(LG, gi, 'UV', usep, 0)
uc = val(LG, 'SUBTRACT', 'u − 0.5', -1080, 300, b=.5); link(LG, usep, 'X', uc, 0)
sw = val(LG, 'MULTIPLY', '× 扫掠', -880, 300); link(LG, uc, 0, sw, 0); link(LG, gi, '扫掠', sw, 1)
ang = val(LG, 'ADD', '角度 + 扫掠漂移', -280, -100); link(LG, deg, 0, ang, 0); link(LG, sw, 0, ang, 1)
absn = val(LG, 'ABSOLUTE', '|角度|', -80, -100); link(LG, ang, 0, absn, 0)
p = val(LG, 'DIVIDE', 'p = |角度| / 翻转角度', 120, -100); link(LG, absn, 0, p, 0); link(LG, gi, '翻转角度', p, 1)
mono = val(LG, 'MINIMUM', '单向 min(p,1)', 320, 40, b=1); link(LG, p, 0, mono, 0)
p1 = val(LG, 'ADD', 'p + 1', 320, -200, b=1); link(LG, p, 0, p1, 0)
md = val(LG, 'MODULO', 'mod 2', 500, -200, b=2); link(LG, p1, 0, md, 0)
m1 = val(LG, 'SUBTRACT', '− 1', 680, -200, b=1); link(LG, md, 0, m1, 0)
tri = val(LG, 'ABSOLUTE', '循环三角波', 860, -200); link(LG, m1, 0, tri, 0)
dif = val(LG, 'SUBTRACT', '三角 − 单向', 860, -40); link(LG, tri, 0, dif, 0); link(LG, mono, 0, dif, 1)
tsel = node(LG, 'ShaderNodeMath', '按循环开关混合', 1040, -40); tsel.operation = 'MULTIPLY_ADD'; link(LG, dif, 0, tsel, 0); link(LG, gi, '循环', tsel, 1); link(LG, mono, 0, tsel, 2)
lensm = val(LG, 'MULTIPLY', 'u × 光栅密度', -880, 520); link(LG, usep, 'X', lensm, 0); link(LG, gi, '光栅密度', lensm, 1)
lensf = val(LG, 'FRACT', '柱镜内位置', -680, 520); link(LG, lensm, 0, lensf, 0)
lensc = val(LG, 'SUBTRACT', '光栅坐标 −0.5…0.5', -480, 520, b=.5); link(LG, lensf, 0, lensc, 0); link(LG, lensc, 0, go, '光栅坐标')
sh = val(LG, 'MULTIPLY', '× 条纹显现', -280, 520); link(LG, lensc, 0, sh, 0); link(LG, gi, '条纹显现', sh, 1)
sh2 = val(LG, 'MULTIPLY', '× 0.5', -80, 520, b=.5); link(LG, sh, 0, sh2, 0)
tst = val(LG, 'ADD', 't + 条纹相位', 1200, 60); link(LG, tsel, 0, tst, 0); link(LG, sh2, 0, tst, 1)
lo = val(LG, 'SUBTRACT', '0.5 − 柔和', 1040, 280, a=.5); link(LG, gi, '过渡柔和', lo, 1)
hi = val(LG, 'ADD', '0.5 + 柔和', 1040, 440, a=.5); link(LG, gi, '过渡柔和', hi, 1)
mr = node(LG, 'ShaderNodeMapRange', '平滑阶跃 → 混合系数', 1320, 200); mr.interpolation_type = 'SMOOTHSTEP'; mr.clamp = True
link(LG, tst, 0, mr, 'Value'); link(LG, lo, 0, mr, 'From Min'); link(LG, hi, 0, mr, 'From Max'); link(LG, mr, 'Result', go, '混合系数')
rf = val(LG, 'MULTIPLY', '坐标 × 折射', -280, 720); link(LG, lensc, 0, rf, 0); link(LG, gi, '柱镜折射', rf, 1)
rd = val(LG, 'DIVIDE', '÷ 光栅密度', -80, 720); link(LG, rf, 0, rd, 0); link(LG, gi, '光栅密度', rd, 1)
rv = node(LG, 'ShaderNodeCombineXYZ', '折射偏移向量', 120, 720); link(LG, rd, 0, rv, 'X'); link(LG, rv, 0, go, '折射偏移')
LG['说明'] = '每个着色点用自己的视线求水平角，切换从卡的一侧扫过另一侧。混合系数 0 = 图 A，1 = 图 B。公式与网页 GLSL 完全一致，见 references/lenticular-model.md。'

# ---------------------------------------------------------------------------------------------
# Group 2: gentle float of the print behind the lens (same parallax formula as the web).
# ---------------------------------------------------------------------------------------------
PG = bpy.data.node_groups.new('视差 · 印刷层轻浮动 / Float', 'ShaderNodeTree')
socket(PG, '缩放', 'INPUT', 'NodeSocketFloat', 1.04); socket(PG, '深度', 'INPUT', 'NodeSocketFloat', L['depth'], -.5, .5); socket(PG, '视差效果', 'OUTPUT', 'NodeSocketVector')
pi_ = node(PG, 'NodeGroupInput', '缩放与深度', -1000, 320); po = node(PG, 'NodeGroupOutput', '视差效果', 920, 200)
puv = node(PG, 'ShaderNodeTexCoord', '纹理坐标 UV', -1000, 100)
psub = vec(PG, 'SUBTRACT', '中心归零', -800, 100); psub.inputs[1].default_value = (.5, .5, .5); link(PG, puv, 'UV', psub, 0)
pfma = vec(PG, 'MULTIPLY_ADD', '缩放后加回中心', -570, 100); pfma.inputs[2].default_value = (.5, .5, .5); link(PG, psub, 0, pfma, 0); link(PG, pi_, '缩放', pfma, 1)
pgeo = node(PG, 'ShaderNodeNewGeometry', '几何', -1000, -210)
pn = node(PG, 'ShaderNodeVectorTransform', '法向 世界 → 物体', -800, -220); pn.vector_type = 'NORMAL'; pn.convert_from = 'WORLD'; pn.convert_to = 'OBJECT'; link(PG, pgeo, 'Normal', pn, 'Vector')
pv = node(PG, 'ShaderNodeVectorTransform', '视线 世界 → 物体', -800, -450); pv.vector_type = 'VECTOR'; pv.convert_from = 'WORLD'; pv.convert_to = 'OBJECT'; link(PG, pgeo, 'Incoming', pv, 'Vector')
pdot = vec(PG, 'DOT_PRODUCT', '视线·法向', -550, -270); link(PG, pn, 0, pdot, 0); link(PG, pv, 0, pdot, 1)
pab = val(PG, 'ABSOLUTE', '正向', -330, -270); link(PG, pdot, 'Value', pab, 0)
pcl = val(PG, 'MAXIMUM', '掠射角下限 0.35', -130, -270, b=.35); link(PG, pab, 0, pcl, 0)
pdep = val(PG, 'MULTIPLY', '深度 × 0.14', -330, -530, b=.14); link(PG, pi_, '深度', pdep, 0)
pdiv = val(PG, 'DIVIDE', '深度 / 夹角', 80, -300); link(PG, pdep, 0, pdiv, 0); link(PG, pcl, 0, pdiv, 1)
pxy = vec(PG, 'MULTIPLY', '仅平面 XY', -320, -730); pxy.inputs[1].default_value = (1, 1, 0); link(PG, pv, 0, pxy, 0)
psc = vec(PG, 'SCALE', '缩放 · 深度', 310, -160); link(PG, pxy, 0, psc, 0); link(PG, pdiv, 0, psc, 'Scale')
padd = vec(PG, 'ADD', 'UV + 偏移', 650, 200); link(PG, pfma, 0, padd, 0); link(PG, psc, 0, padd, 1); link(PG, padd, 0, po, '视差效果')

# ---------------------------------------------------------------------------------------------
# Group 3: angle-dependent foil shared by face and edges.
# ---------------------------------------------------------------------------------------------
F = bpy.data.node_groups.new('镭射 · 条带与花纹', 'ShaderNodeTree'); socket(F, 'UV', 'INPUT', 'NodeSocketVector'); socket(F, '全息颜色', 'OUTPUT', 'NodeSocketColor'); socket(F, '条纹遮罩', 'OUTPUT', 'NodeSocketFloat')
fi = node(F, 'NodeGroupInput', '纹理输入', -1100, 250); fo = node(F, 'NodeGroupOutput', '镭射输出', 950, 180)
fg = node(F, 'ShaderNodeNewGeometry', '几何视线', -1100, -130)
fvt = node(F, 'ShaderNodeVectorTransform', '视线到卡牌局部', -900, -130); fvt.vector_type = 'VECTOR'; fvt.convert_from = 'WORLD'; fvt.convert_to = 'OBJECT'; link(F, fg, 'Incoming', fvt, 0)
fvs = vec(F, 'SCALE', '转卡驱动镭射位移', -710, -130); fvs.inputs['Scale'].default_value = 2.4; link(F, fvt, 0, fvs, 0)
fad = vec(F, 'ADD', 'UV + 角度', -520, 270); link(F, fi, 'UV', fad, 0); link(F, fvs, 0, fad, 1)
fmp = node(F, 'ShaderNodeMapping', '映射 · Y 32°', -330, 350); fmp.inputs['Rotation'].default_value[1] = math.radians(32); link(F, fad, 0, fmp, 0)
fwave = node(F, 'ShaderNodeTexWave', '条带 · 0.55 / 畸变 7', -80, 400); fwave.wave_type = 'BANDS'; fwave.bands_direction = 'X'; fwave.inputs['Scale'].default_value = .55; fwave.inputs['Distortion'].default_value = 7; fwave.inputs['Detail Scale'].default_value = 1.5; link(F, fmp, 0, fwave, 0)
fmp2 = node(F, 'ShaderNodeMapping', '映射副本 · 花纹 UV', -700, -420); link(F, fi, 'UV', fmp2, 0)
fpat = node(F, 'ShaderNodeTexNoise', '细颗粒花纹', -460, -420); fpat.inputs['Scale'].default_value = 94; fpat.inputs['Detail'].default_value = 2; link(F, fmp2, 0, fpat, 0)
fmul = node(F, 'ShaderNodeMixRGB', '正片叠底', 150, 250); fmul.blend_type = 'MULTIPLY'; fmul.inputs[0].default_value = .55; link(F, fwave, 'Color', fmul, 1); link(F, fpat, 'Color', fmul, 2)
fplus = node(F, 'ShaderNodeMixRGB', '相加 · 花纹', 350, 250); fplus.blend_type = 'ADD'; fplus.inputs[0].default_value = .12; link(F, fmul, 0, fplus, 1); link(F, fpat, 'Fac', fplus, 2)
framp = node(F, 'ShaderNodeValToRGB', '粉 → 黄 → 蓝 → 白', 560, 250)
framp.color_ramp.elements.remove(framp.color_ramp.elements[1]); framp.color_ramp.elements[0].position = 0; framp.color_ramp.elements[0].color = (.7, .10, .34, 1)
for pos, col in [(.35, (1, .68, .16, 1)), (.68, (.10, .48, 1, 1)), (1, (1, 1, 1, 1))]: framp.color_ramp.elements.new(pos).color = col
link(F, fplus, 0, framp, 0); link(F, framp, 0, fo, '全息颜色')
fmask = node(F, 'ShaderNodeValToRGB', '窄条纹发光遮罩', 370, -80); fmask.color_ramp.elements[0].position = .76; fmask.color_ramp.elements[1].position = .94; link(F, fwave, 'Fac', fmask, 0); link(F, fmask, 0, fo, '条纹遮罩')

# ---------------------------------------------------------------------------------------------
# Images and materials.
# ---------------------------------------------------------------------------------------------
images = {k: bpy.data.images.load(str(R / 'assets' / v), check_existing=True) for k, v in {'a': 'image_a.png', 'b': 'image_b.png', 'text': 'text.png'}.items()}
def material(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; m.node_tree.nodes.clear(); return m, m.node_tree
def bsdf(t, name, x, y):
    b = node(t, 'ShaderNodeBsdfPrincipled', name, x, y); b.inputs['Emission Color'].default_value = (0, 0, 0, 1); return b

main, t = material('01 · 光栅正面 / Lenticular Face')
out = node(t, 'ShaderNodeOutputMaterial', '最终表面', 2000, 300)
tc = node(t, 'ShaderNodeTexCoord', '原始 UV · 光栅片固定在这里', -1700, 700)
lens = node(t, 'ShaderNodeGroup', '光栅相位 · 调参数看这里', -1400, 700); lens.node_tree = LG; link(t, tc, 'UV', lens, 'UV')
for key, sock in [('flipAngle', '翻转角度'), ('softness', '过渡柔和'), ('pitch', '光栅密度'), ('stripe', '条纹显现'), ('sweep', '扫掠'), ('refract', '柱镜折射')]: lens.inputs[sock].default_value = L[key]
lens.inputs['循环'].default_value = 1.0 if L['cycle'] else 0.0
flt = node(t, 'ShaderNodeGroup', '印刷层浮动 · 1.04 / 深度', -1400, 250); flt.node_tree = PG; flt.inputs['深度'].default_value = L['depth']; flt.inputs['缩放'].default_value=1.0
auv = vec(t, 'ADD', '艺术 UV = 浮动 + 折射', -1100, 300); link(t, flt, '视差效果', auv, 0); link(t, lens, '折射偏移', auv, 1)
ta = node(t, 'ShaderNodeTexImage', '图 A · 正视形态 · 换卡替换这里', -850, 600); ta.image = images['a']; ta.extension = 'EXTEND'; link(t, auv, 0, ta, 'Vector')
tb = node(t, 'ShaderNodeTexImage', '图 B · 倾斜形态 · 换卡替换这里', -850, 250); tb.image = images['b']; tb.extension = 'EXTEND'; link(t, auv, 0, tb, 'Vector')
art = node(t, 'ShaderNodeMixRGB', 'A ⇄ B 光栅混合', -500, 450); art.blend_type = 'MIX'; link(t, lens, '混合系数', art, 0); link(t, ta, 'Color', art, 1); link(t, tb, 'Color', art, 2)
# Real lenticulars dim slightly where both frames are half visible.
gh = val(t, 'MULTIPLY_ADD', '2m − 1', -500, 150, b=2); gh.inputs[2].default_value = -1; link(t, lens, '混合系数', gh, 0)
gha = val(t, 'ABSOLUTE', '|2m − 1|', -320, 150); link(t, gh, 0, gha, 0)
ghd = val(t, 'MULTIPLY_ADD', '1 − 0.06·(1−|2m−1|)', -140, 150, b=.06); ghd.inputs[2].default_value = .94; link(t, gha, 0, ghd, 0)
artd = node(t, 'ShaderNodeMixRGB', '过渡带轻微变暗', 40, 400); artd.blend_type = 'MULTIPLY'; artd.inputs[0].default_value = 1; link(t, art, 0, artd, 1); link(t, ghd, 0, artd, 2)
foil = node(t, 'ShaderNodeGroup', '镭射条带', -850, -150); foil.node_tree = F; link(t, tc, 'UV', foil, 'UV')
over = node(t, 'ShaderNodeMixRGB', '叠加 · 镭射 (镭射强度 × 0.3)', 300, 400); over.blend_type = 'OVERLAY'; over.inputs[0].default_value = L['foil'] * .3; link(t, artd, 0, over, 1); link(t, foil, '全息颜色', over, 2)
# Lens sheet: parabolic ridge per lenticule, applied to the coat normal only.
lc2 = val(t, 'MULTIPLY', '光栅坐标²', -500, -450); link(t, lens, '光栅坐标', lc2, 0); link(t, lens, '光栅坐标', lc2, 1)
lh = val(t, 'MULTIPLY_ADD', '高度 1 − 4c²', -320, -450, b=-4); lh.inputs[2].default_value = 1; link(t, lc2, 0, lh, 0)
bump = node(t, 'ShaderNodeBump', '柱镜凹凸 · 仅清漆层', -100, -450); bump.inputs['Strength'].default_value = min(1.0, .5 * L['ridge']); bump.inputs['Distance'].default_value = .012; link(t, lh, 0, bump, 'Height')
face = bsdf(t, '原理化 · 印刷 + 塑料光栅片', 700, 400); face.inputs['Metallic'].default_value = .15; face.inputs['Roughness'].default_value = .38; face.inputs['Specular IOR Level'].default_value = .4
face.inputs['Coat Weight'].default_value = .3; face.inputs['Coat Roughness'].default_value = .12; face.inputs['Coat IOR'].default_value = 1.5
link(t, over, 0, face, 'Base Color'); link(t, bump, 'Normal', face, 'Coat Normal')
se = node(t, 'ShaderNodeEmission', '只让镭射扫光发光', 700, -50); link(t, foil, '全息颜色', se, 'Color')
sm = val(t, 'MULTIPLY', '扫光强度', 450, -50, b=.28 * L['foil']); link(t, foil, '条纹遮罩', sm, 0); link(t, sm, 0, se, 'Strength')
sa = node(t, 'ShaderNodeAddShader', '表面 + 扫光', 1200, 300); link(t, face, 0, sa, 0); link(t, se, 0, sa, 1)
# Sparse star flecks from the foil pattern, animated over the timeline.
v = node(t, 'ShaderNodeTexVoronoi', '闪星 · 距离到边缘', -850, -800); v.feature = 'DISTANCE_TO_EDGE'; v.inputs['Scale'].default_value = 105; link(t, tc, 'UV', v, 'Vector')
vr = node(t, 'ShaderNodeValToRGB', '细闪点阈值', -600, -800); vr.color_ramp.elements[0].position = .012; vr.color_ramp.elements[0].color = (1, 1, 1, 1); vr.color_ramp.elements[1].position = .04; vr.color_ramp.elements[1].color = (0, 0, 0, 1); link(t, v, 'Distance', vr, 0)
noise = node(t, 'ShaderNodeTexNoise', '闪烁 · 四维噪波', -850, -1100); noise.noise_dimensions = '4D'; noise.inputs['Scale'].default_value = 165; link(t, tc, 'UV', noise, 'Vector')
noise.inputs['W'].default_value = 0; noise.inputs['W'].keyframe_insert('default_value', frame=1); noise.inputs['W'].default_value = 2; noise.inputs['W'].keyframe_insert('default_value', frame=96)
nr = node(t, 'ShaderNodeValToRGB', '稀疏星点', -600, -1100); nr.color_ramp.elements[0].position = .70; nr.color_ramp.elements[1].position = .79; link(t, noise, 'Fac', nr, 0)
st = val(t, 'MULTIPLY', '星点 × 闪烁', -300, -900); link(t, vr, 0, st, 0); link(t, nr, 0, st, 1)
stren = val(t, 'MULTIPLY', '闪星亮度', -100, -900, b=3 * L['foil']); link(t, st, 0, stren, 0)
be = node(t, 'ShaderNodeEmission', '闪星自发光', 200, -900); be.inputs['Color'].default_value = (.72, .88, 1, 1); link(t, stren, 0, be, 'Strength')
ba = node(t, 'ShaderNodeAddShader', '+ 闪星', 1500, 300); link(t, sa, 0, ba, 0); link(t, be, 0, ba, 1); link(t, ba, 0, out, 'Surface')

link(t, face, 0, out, 'Surface'); over.inputs[0].default_value=0

textmat, tt = material('02 · 文字透明 / 深度0')
tp = node(tt, 'ShaderNodeGroup', '文字 · 1 / 0', -650, 250); tp.node_tree = PG; tp.inputs['缩放'].default_value = 1; tp.inputs['深度'].default_value = 0
tx = node(tt, 'ShaderNodeTexImage', '文字 PNG · 换卡替换这里', -420, 250); tx.image = images['text']; tx.extension = 'CLIP'; link(tt, tp, '视差效果', tx, 'Vector')
tbs = bsdf(tt, '文字原理化', -130, 300); tbs.inputs['Metallic'].default_value = 1; tbs.inputs['Roughness'].default_value = 1; link(tt, tx, 'Color', tbs, 'Base Color')
link(tt, tx, 'Color', tbs, 'Emission Color'); tbs.inputs['Emission Strength'].default_value = .35
trans = node(tt, 'ShaderNodeBsdfTransparent', '透明底', -130, 0); tm = node(tt, 'ShaderNodeMixShader', '文字 Alpha', 220, 220); link(tt, tx, 'Alpha', tm, 0); link(tt, trans, 0, tm, 1); link(tt, tbs, 0, tm, 2)
to = node(tt, 'ShaderNodeOutputMaterial', '文字表面', 460, 220); link(tt, tm, 0, to, 'Surface')

edge, et = material('03 · 卡边镭射 / 材质槽2')
eu = node(et, 'ShaderNodeTexCoord', '卡边坐标', -650, 0); ef = node(et, 'ShaderNodeGroup', '仅保留镭射', -430, 0); ef.node_tree = F; link(et, eu, 'UV', ef, 'UV')
eb = node(et, 'ShaderNodeBrightContrast', '亮度1', -180, 0); eb.inputs['Bright'].default_value = 1; link(et, ef, '全息颜色', eb, 'Color')
ep = bsdf(et, '卡边黑色金属', 50, 0); ep.inputs['Base Color'].default_value = (0, 0, 0, 1); ep.inputs['Metallic'].default_value = 1; ep.inputs['Roughness'].default_value = .32; link(et, eb, 0, ep, 'Emission Color'); ep.inputs['Emission Strength'].default_value = .42
eo = node(et, 'ShaderNodeOutputMaterial', '镭射卡边', 390, 0); link(et, ep, 0, eo, 'Surface')
gold, gt = material('04 · 古金压边'); gp = bsdf(gt, '古金金属', 0, 0); gp.inputs['Base Color'].default_value = (.63, .37, .10, 1); gp.inputs['Metallic'].default_value = 1; gp.inputs['Roughness'].default_value = .29; go2 = node(gt, 'ShaderNodeOutputMaterial', '金边', 360, 0); link(gt, gp, 0, go2, 0)
back, bt = material('05 · 背面靛蓝'); bp = bsdf(bt, '靛蓝背面', 0, 0); bp.inputs['Base Color'].default_value = (.009, .02, .036, 1); bp.inputs['Metallic'].default_value = 1; bp.inputs['Roughness'].default_value = .6; bo = node(bt, 'ShaderNodeOutputMaterial', '背面', 350, 0); link(bt, bp, 0, bo, 0)

# ---------------------------------------------------------------------------------------------
# Geometry: pivot, front plane (with thickness), text plane, edge rings. X=90° stays an object rotation.
# ---------------------------------------------------------------------------------------------
cardcol = bpy.data.collections.new('卡牌 · 光栅成品'); scene.collection.children.link(cardcol)
pivot = bpy.data.objects.new('转卡控制 · 播放时间线预览', None); cardcol.objects.link(pivot)
props = [('翻转角度', 'flipAngle', '翻转角度'), ('过渡柔和', 'softness', '过渡柔和'), ('光栅密度', 'pitch', '光栅密度'), ('条纹显现', 'stripe', '条纹显现'), ('扫掠', 'sweep', '扫掠'), ('柱镜折射', 'refract', '柱镜折射')]
for prop, key, _ in props: pivot[prop] = float(L[key])
pivot['景深'] = float(L['depth']); pivot['循环'] = 1.0 if L['cycle'] else 0.0
pivot['使用说明'] = '光栅参数通过驱动关联到此物体的自定义属性；绕 Z 轴旋转即水平倾斜。播放 1–96 帧：正视 = 图 A，倾斜 = 图 B。'
def drive(n, inp, prop):
    fc = n.inputs[inp].driver_add('default_value'); dr = fc.driver; dr.type = 'SCRIPTED'; var = dr.variables.new(); var.name = 'value'; var.targets[0].id = pivot; var.targets[0].data_path = '["' + prop + '"]'; dr.expression = 'value'
for prop, _, sock in props: drive(lens, sock, prop)
drive(lens, '循环', '循环'); drive(flt, '深度', '景深')

def perimeter(w, h, r, n=12):
    pts = []
    for cx, cy, start in [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]:
        for j in range(n + 1):
            a = math.radians(start + j * 90 / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def plane(name, w, h, mat, y=0, thickness=0):
    pts = perimeter(w, h, .20); N = len(pts); verts = [(x, z, 0) for x, z in pts]; faces = [tuple(range(N))]
    if thickness:
        verts += [(x, z, -thickness) for x, z in pts]; faces += [tuple(reversed(range(N, 2 * N)))]
        faces += [(i, (i + 1) % N, (i + 1) % N + N, i + N) for i in range(N)]
    me = bpy.data.meshes.new(name + '网格'); me.from_pydata(verts, [], faces); me.update(); o = bpy.data.objects.new(name, me); cardcol.objects.link(o)
    o.rotation_euler = (math.pi / 2, 0, 0); o.location = (0, y, 0); o.parent = pivot; me.materials.append(mat)
    if thickness:
        me.materials.append(edge); me.materials.append(back)
        for pol in me.polygons:
            if pol.index == 1: pol.material_index = 2
            elif pol.index > 1: pol.material_index = 1
    layer = me.uv_layers.new(name='UVMap')
    for pol in me.polygons:
        for li in pol.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co; layer.data[li].uv = (co.x / w + .5, co.y / h + .5)
    o['导入约定'] = 'Alt+G 清空位置；物体模式 X=90°，未应用旋转。局部 X 为卡面水平轴，局部 Z 为法向。'
    return o
card = plane('主体平面 · 光栅合成', 6.3, 9.45, main, 0, .045)
textob = plane('文字平面 · Alpha PNG', 6.3, 9.45, textmat, -.014)

def ring(name, w, h, width, mat, y):
    outer = perimeter(w, h, .20); inner = perimeter(w - width * 2, h - width * 2, max(.20 - width, .01)); N = len(outer)
    verts = [(x, z, 0) for x, z in outer + inner]; faces = [(i, (i + 1) % N, (i + 1) % N + N, i + N) for i in range(N)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); ob = bpy.data.objects.new(name, me); cardcol.objects.link(ob); ob.parent = pivot; ob.rotation_euler.x = math.pi / 2; ob.location.y = y; me.materials.append(mat)
    uv = me.uv_layers.new(name='UVMap')
    for pol in me.polygons:
        for li in pol.loop_indices:
            vv = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (vv.x / w + .5, vv.y / h + .5)
    return ob
# Full-bleed card: no decorative frame geometry.


# Independent optical layers; all pictorial content comes from the two generated full-card images.
pivot['镭射强度']=float(L['foil']);pivot['粒子强度']=float(FX.get('particles',.65));pivot['轮廓发光']=float(FX.get('glow',.65))
def fx_material(kind,prop):
    m,nt=material('特效 / '+kind);uv=node(nt,'ShaderNodeTexCoord','固定卡面 UV',-1200,500);ph=node(nt,'ShaderNodeGroup','相同光栅相位',-1000,500);ph.node_tree=LG;link(nt,uv,'UV',ph,'UV')
    for p,k,sock in props:ph.inputs[sock].default_value=L[k];drive(ph,sock,p)
    mask=None;color=None
    if kind=='foil':
        f=node(nt,'ShaderNodeGroup','随视角移动的镭射',-700,400);f.node_tree=F;link(nt,uv,'UV',f,'UV');mask=(f,'条纹遮罩');color=(f,'全息颜色')
    elif kind=='particles':
        v=node(nt,'ShaderNodeTexVoronoi','稀疏闪粒',-900,350);v.feature='DISTANCE_TO_EDGE';v.inputs['Scale'].default_value=105;link(nt,uv,'UV',v,'Vector');r=node(nt,'ShaderNodeValToRGB','窄边缘',-650,350);r.color_ramp.elements[0].position=.012;r.color_ramp.elements[0].color=(1,1,1,1);r.color_ramp.elements[1].position=.035;r.color_ramp.elements[1].color=(0,0,0,1);link(nt,v,'Distance',r,0)
        noise=node(nt,'ShaderNodeTexNoise','四维闪烁',-900,0);noise.noise_dimensions='4D';noise.inputs['Scale'].default_value=165;link(nt,uv,'UV',noise,'Vector');noise.inputs['W'].default_value=0;noise.inputs['W'].keyframe_insert('default_value',frame=1);noise.inputs['W'].default_value=3;noise.inputs['W'].keyframe_insert('default_value',frame=96)
        sparse=node(nt,'ShaderNodeValToRGB','稀疏阈值',-650,0);sparse.color_ramp.elements[0].position=.72;sparse.color_ramp.elements[1].position=.80;link(nt,noise,'Fac',sparse,0);mm=val(nt,'MULTIPLY','粒子遮罩',-400,200);link(nt,r,0,mm,0);link(nt,sparse,0,mm,1);mask=(mm,0)
    else:
        pg=node(nt,'ShaderNodeGroup','轮廓与原画同一 UV',-900,250);pg.node_tree=PG;pg.inputs['缩放'].default_value=1;pg.inputs['深度'].default_value=L['depth'];drive(pg,'深度','景深');av=vec(nt,'ADD','同一折射偏移',-690,250);link(nt,pg,'视差效果',av,0);link(nt,ph,'折射偏移',av,1)
        textures=[]
        for key in ['a','b']:
            im=bpy.data.images.load(str(R/'assets'/('line_'+key+'.png')),check_existing=True);images['line_'+key]=im;n=node(nt,'ShaderNodeTexImage','配准轮廓 '+key,-470,300 if key=='a' else 0);n.image=im;link(nt,av,0,n,'Vector');textures.append(n)
        mix=node(nt,'ShaderNodeMixRGB','轮廓随整卡切换',-200,300);link(nt,ph,'混合系数',mix,0);link(nt,textures[0],'Color',mix,1);link(nt,textures[1],'Color',mix,2);mask=(mix,0)
    atten=val(nt,'MULTIPLY','稀疏特效覆盖',-60,200,b={'foil':.06,'lines':.025,'particles':.16}[kind]);link(nt,mask[0],mask[1],atten,0);gain=val(nt,'MULTIPLY','独立强度',50,200,b=1);link(nt,atten,0,gain,0);drive(gain,1,prop)
    tr=node(nt,'ShaderNodeBsdfTransparent','透明光学膜',220,0);em=node(nt,'ShaderNodeEmission','局部发光',220,300);em.inputs['Color'].default_value=(1,.72,.28,1) if kind=='lines' else (.7,.9,1,1);em.inputs['Strength'].default_value={'foil':.72,'lines':2.4,'particles':3.5}[kind]
    if color:link(nt,color[0],color[1],em,'Color')
    mix=node(nt,'ShaderNodeMixShader','仅遮罩区域发光',470,200);link(nt,gain,0,mix,0);link(nt,tr,0,mix,1);link(nt,em,0,mix,2);out=node(nt,'ShaderNodeOutputMaterial','光学膜',700,200);link(nt,mix,0,out,'Surface');return m
for kind,prop,y in [('foil','镭射强度',-.008),('lines','轮廓发光',-.017),('particles','粒子强度',-.027)]:
    ob=plane('独立特效层 / '+kind,6.3,9.45,fx_material(kind,prop),y);ob['web_role']=kind
textob.location.y=-.038

# Timeline: horizontal tilt about Z sweeps A -> B -> A -> B. Frame 24 is frontal (A), frame 48 fully tilted (B).
tilt = max(L['flipAngle'] * 1.6, 18)
for frame, ang in [(1, (-2, 0, -tilt)), (24, (1.5, 0, 0)), (48, (3, 0, tilt)), (72, (-1.5, 0, 0)), (96, (-2, 0, -tilt))]:
    pivot.rotation_euler = [math.radians(x) for x in ang]; pivot.keyframe_insert('rotation_euler', frame=frame)
try:
    for fc in pivot.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'
except Exception as e: print('Keyframe easing skipped:', e)

# Perspective camera: a real lenticular sweeps because every point sees the lens from a slightly different angle.
def aim(o, p): o.rotation_euler = (Vector(p) - o.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add(location=(0, -24, 0)); cam = bpy.context.object; cam.name = '成品相机 · 透视'; aim(cam, (0, 0, 0)); cam.data.type = 'PERSP'; cam.data.lens = 75; cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 36; scene.camera = cam
for name, loc, energy, size, color in [('柔光主灯', (-3, -8, 4), 520, 9, (1, .90, .72)), ('正面均匀补光', (3, -7, -2), 360, 8, (.72, .85, 1)), ('顶部金光', (0, -4, 7), 180, 5, (1, .70, .32)), ('侧面高光 · 照亮柱镜纹', (7, -9, 1), 240, 2.5, (1, 1, 1))]:
    bpy.ops.object.light_add(type='AREA', location=loc); o = bpy.context.object; o.name = name; o.data.energy = energy; o.data.shape = 'DISK'; o.data.size = size; o.data.color = color; aim(o, (0, 0, 0))
def setopt(n, name, value):
    # Glare options are RNA properties in older 4.x and input sockets from 4.4 on.
    try: setattr(n, name, value); return
    except Exception: pass
    for s in n.inputs:
        if s.name.lower().replace(' ', '_') == name: s.default_value = value
try:
    scene.use_nodes = True; ct = scene.node_tree; ct.nodes.clear(); rl = node(ct, 'CompositorNodeRLayers', '渲染层', 0, 0); gl = node(ct, 'CompositorNodeGlare', '辉光 · 高质量', 250, 0); gl.glare_type = 'FOG_GLOW'
    setopt(gl, 'quality', 'HIGH'); setopt(gl, 'threshold', 1.5); setopt(gl, 'size', 8)
    co = node(ct, 'CompositorNodeComposite', '最终图像', 510, 0); link(ct, rl, 'Image', gl, 'Image'); link(ct, gl, 'Image', co, 'Image')
except Exception as e: print('Compositor glow skipped:', e)

try: bpy.context.preferences.view.language = 'zh_HANS'
except Exception: bpy.context.preferences.view.language = 'zh_CN'
bpy.context.preferences.view.use_translate_interface = True; bpy.context.preferences.view.use_translate_tooltips = True; bpy.context.preferences.view.use_translate_new_dataname = False; bpy.context.preferences.view.show_splash = False
bpy.ops.wm.save_userpref()
scene.frame_set(24)
bpy.ops.object.select_all(action='DESELECT'); card.select_set(True); bpy.context.view_layer.objects.active = card
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'; area.spaces.active.shading.type = 'MATERIAL'; area.spaces.active.overlay.show_overlays = False
for im in images.values(): im.pack()
states = CFG.get('states', {})
scene['制作说明'] = CFG.get('title', 'Card') + ' · ' + states.get('a', {}).get('label', 'A') + ' ⇄ ' + states.get('b', {}).get('label', 'B') + ' · 按空格播放转动查看光栅变幻'
scene['素材来源'] = '图 A / 图 B 为同构图双帧（上传或内置生图工具生成）；文字透明 PNG 使用精确字体排版。'
bpy.ops.wm.save_as_mainfile(filepath=str(R / 'card.blend'))
report = {'blender': bpy.app.version_string, 'language': bpy.context.preferences.view.language, 'interface_translation': bpy.context.preferences.view.use_translate_interface, 'config': bpy.utils.user_resource('CONFIG'),
          'render_engine': scene.render.engine, 'device': scene.cycles.device, 'images': {k: {'size': list(v.size), 'channels': v.channels, 'packed': bool(v.packed_file)} for k, v in images.items()},
          'planes': {o.name: {'rotation_degrees': [round(math.degrees(a), 2) for a in o.rotation_euler]} for o in [card, textob]}, 'parameters': {k: pivot[k] for k, _, _ in props}, 'depth': pivot['景深'], 'cycle': pivot['循环'], 'frames': {'front_A': 24, 'flip_B': 48}}
(R / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
if '--skip-render' not in args:
    for frame, name in [(24, 'front'), (48, 'flip'), (1, 'left')]:
        scene.frame_set(frame); scene.render.filepath = str(R / 'renders' / (name + '.png')); bpy.ops.render.render(write_still=True)
    scene.frame_set(24)
print('BUILD_AND_RENDER_COMPLETE')
