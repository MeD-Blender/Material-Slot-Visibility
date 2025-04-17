bl_info = {
    "name": "Material Slot Visibility",
    "author": "MeD ChatGPT",
    "version": (1, 0),
    "location": "Properties > Material",
    "description": "Allows controlling and animating viewport/render visibility per material slot",
    "category": "Material",
}

import bpy
from bpy.app.handlers import frame_change_post, depsgraph_update_post, persistent

# ----------------------------------------------------------
# Property Groups
# ----------------------------------------------------------
class MaterialSlotState(bpy.types.PropertyGroup):
    render: bpy.props.BoolProperty(
        name="Render Visibility",
        default=True,
        options={'ANIMATABLE'},
        update=lambda s, c: update_visibility(c.object)
    )
    viewport: bpy.props.BoolProperty(
        name="Viewport Visibility",
        default=True,
        options={'ANIMATABLE'},
        update=lambda s, c: update_visibility(c.object)
    )

# ----------------------------------------------------------
# Core Logic
# ----------------------------------------------------------
def update_visibility(obj):
    if not obj.material_slots:
        return

    scene = bpy.context.scene
    current_frame = scene.frame_current
    is_rendering = bpy.context.screen is None

    if obj.type != 'MESH':
        return

    mesh = obj.data
    indices = []

    for poly in mesh.polygons:
        best_index = 0
        for i, state in enumerate(obj.material_slot_states):
            if i >= len(obj.material_slots):
                continue
            try:
                state_value = state.path_resolve('render' if is_rendering else 'viewport', frame=current_frame)
            except:
                state_value = state.render if is_rendering else state.viewport
            if state_value:
                best_index = i
                break
        indices.append(best_index)

    mesh.polygons.foreach_set('material_index', indices)
    mesh.update()

@persistent
def on_frame_change(scene):
    for obj in (o for o in scene.objects if hasattr(o, "material_slot_states")):
        update_visibility(obj)

@persistent
def sync_material_slot_states(scene):
    for obj in scene.objects:
        if not hasattr(obj, "material_slot_states") or obj.type != 'MESH':
            continue
        # Sync states
        slot_count = len(obj.material_slots)
        state_count = len(obj.material_slot_states)
        if state_count < slot_count:
            for _ in range(slot_count - state_count):
                obj.material_slot_states.add()
        elif state_count > slot_count:
            for _ in range(state_count - slot_count):
                obj.material_slot_states.remove(len(obj.material_slot_states) - 1)

# ----------------------------------------------------------
# UI Components
# ----------------------------------------------------------
class MATERIAL_UL_custom_slots(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = data
        if index >= len(obj.material_slot_states):
            return

        state = obj.material_slot_states[index]
        row = layout.row(align=True)
        row.label(text=item.material.name if item.material else "Empty")
        viewport_icon = 'HIDE_OFF' if state.viewport else 'HIDE_ON'
        row.prop(state, "viewport", text="", icon=viewport_icon, emboss=False)
        render_icon = 'RESTRICT_RENDER_OFF' if state.render else 'RESTRICT_RENDER_ON'
        row.prop(state, "render", text="", icon=render_icon, emboss=False)

class MATERIAL_PT_custom_panel(bpy.types.Panel):
    bl_label = "Material Slot Visibility"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        obj = context.object
        if not obj:
            return

        layout = self.layout
        layout.template_list("MATERIAL_UL_custom_slots", "", 
                             obj, "material_slots", 
                             obj, "active_material_index")

# ----------------------------------------------------------
# Registration
# ----------------------------------------------------------
classes = (
    MaterialSlotState,
    MATERIAL_UL_custom_slots,
    MATERIAL_PT_custom_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.material_slot_states = bpy.props.CollectionProperty(type=MaterialSlotState)
    frame_change_post.append(on_frame_change)
    depsgraph_update_post.append(sync_material_slot_states)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.material_slot_states
    frame_change_post.remove(on_frame_change)
    depsgraph_update_post.remove(sync_material_slot_states)

if __name__ == "__main__":
    register()
