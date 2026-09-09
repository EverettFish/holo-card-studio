"""Derive registered sparse VFX masks from full card art with Blender compositor."""
import bpy,sys,json
from pathlib import Path
R=Path(sys.argv[sys.argv.index('--')+1]);C=json.loads((R/'card-config.json').read_text(encoding='utf-8-sig'));bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=1;s.render.resolution_x=1024;s.render.resolution_y=1536;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.view_settings.view_transform='Standard';s.view_settings.look='None';s.use_nodes=True;bpy.ops.object.camera_add(location=(0,0,2));s.camera=bpy.context.object
for state in ['a','b']:
 t=s.node_tree;t.nodes.clear();im=t.nodes.new('CompositorNodeImage');im.image=bpy.data.images.load(str(R/'assets'/f'image_{state}.png'));s.render.resolution_x=int(im.image.size[0]);s.render.resolution_y=int(im.image.size[1]);f=t.nodes.new('CompositorNodeFilter');f.filter_type='SOBEL';t.links.new(im.outputs['Image'],f.inputs['Image']);bw=t.nodes.new('CompositorNodeRGBToBW');t.links.new(f.outputs['Image'],bw.inputs[0]);r=t.nodes.new('CompositorNodeValToRGB');r.color_ramp.elements[0].position=.24;r.color_ramp.elements[1].position=.65;t.links.new(bw.outputs[0],r.inputs[0]);source=r.outputs[0]
 box=C.get('identity',{}).get('face_box')
 if box:
  x0,y0,x1,y1=box;mask=t.nodes.new('CompositorNodeEllipseMask');mask.x=(x0+x1)/2/s.render.resolution_x;mask.y=1-(y0+y1)/2/s.render.resolution_y;mask.width=(x1-x0)/s.render.resolution_x*1.2;mask.height=(y1-y0)/s.render.resolution_y*1.25;inv=t.nodes.new('CompositorNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;t.links.new(mask.outputs['Mask'],inv.inputs[1]);mul=t.nodes.new('CompositorNodeMath');mul.operation='MULTIPLY';t.links.new(source,mul.inputs[0]);t.links.new(inv.outputs[0],mul.inputs[1]);source=mul.outputs[0]
 out=t.nodes.new('CompositorNodeComposite');t.links.new(source,out.inputs[0]);s.render.filepath=str(R/'assets'/f'line_{state}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'sources/fx-mask-compositor.blend'))
