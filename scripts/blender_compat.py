"""Blender compositor compatibility shared by the holographic builders."""
import sys
import bpy


def configure_cycles_device(scene):
    """Use Metal on macOS, keeping the existing OptiX/CPU path elsewhere."""
    scene.cycles.device = 'CPU'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL' if sys.platform == 'darwin' else 'OPTIX'
        prefs.get_devices()
        gpu = False
        for device in prefs.devices:
            device.use = device.type != 'CPU'
            gpu = gpu or device.use
        if gpu:
            scene.cycles.device = 'GPU'
    except Exception as error:
        print('GPU fallback', error)


def configure_compositor(scene):
    """Connect render layers through fog glow using the available Blender API."""
    if hasattr(scene, 'compositing_node_group'):
        tree = bpy.data.node_groups.new('闪卡辉光', 'CompositorNodeTree')
        scene.compositing_node_group = tree
        tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        output_type = 'NodeGroupOutput'
    else:
        scene.use_nodes = True
        tree = scene.node_tree
        tree.nodes.clear()
        output_type = 'CompositorNodeComposite'

    def node(kind, name, x):
        result = tree.nodes.new(kind)
        result.name = result.label = name
        result.location = (x, 0)
        return result

    layers = node('CompositorNodeRLayers', '渲染层', 0)
    glare = node('CompositorNodeGlare', '辉光 · 高质量', 250)
    if glare.inputs.get('Type') is not None:
        glare.inputs['Type'].default_value = 'Fog Glow'
        glare.inputs['Quality'].default_value = 'High'
        glare.inputs['Threshold'].default_value = 1.5
        glare.inputs['Size'].default_value = 0.5
    else:
        glare.glare_type = 'FOG_GLOW'
        glare.quality = 'HIGH'
        glare.threshold = 1.5
        glare.size = 8
    output = node(output_type, '最终图像', 510)
    tree.links.new(layers.outputs['Image'], glare.inputs['Image'])
    tree.links.new(glare.outputs['Image'], output.inputs['Image'])
    return tree
