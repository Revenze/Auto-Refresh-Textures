bl_info = {
    "name": "Auto Refresh Textures",
    "author": "Revenze",
    "version": (2, 5),
    "blender": (3, 0, 0),
    "location": "View3D > N-Panel > Auto Refresh",
    "description": "Auto-refresh textures when edited externally",
    "warning": "",
    "wiki_url": "",
    "category": "Material",
}

import bpy
import os
import subprocess
from bpy.app.handlers import persistent

last_mod_times = {}  # Stores the latest modifications
is_monitoring_enabled = False  # Controls whether monitoring is active


# Class for monitored textures
class MonitoredTextureItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Texture Name")
    filepath: bpy.props.StringProperty(name="File Path")
    monitor: bpy.props.BoolProperty(name="Monitor", default=False)


# Function to open the external editor
def open_external_editor(filepath):
    external_editor = bpy.context.preferences.filepaths.image_editor
    if external_editor:
        try:
            subprocess.Popen([external_editor, filepath])  # Opens the external editor asynchronously
            print(f"Open external editor for texture: {filepath}")
        except Exception as e:
            print(f"The external editor could not be opened: {e}")
    else:
        print("There is no external editor configured in Blender.")


# Refreshes selected textures
def refresh_images():
    for item in bpy.context.scene.monitored_textures:
        if item.monitor:  # Only textures enabled for monitoring
            try:
                mod_time = os.path.getmtime(item.filepath)
                if item.filepath in last_mod_times:
                    if mod_time != last_mod_times[item.filepath]:
                        for image in bpy.data.images:
                            if bpy.path.abspath(image.filepath) == item.filepath:
                                image.reload()
                                print(f"Texture refreshed: {item.name}")
                last_mod_times[item.filepath] = mod_time
            except FileNotFoundError:
                print(f"File not found: {item.filepath}")


# Timer for monitoring
def refresh_images_periodically():
    if is_monitoring_enabled:
        refresh_images()
        return bpy.context.scene.refresh_interval
    return None


# Updates the list of textures
def update_texture_list():
    bpy.context.scene.monitored_textures.clear()
    for material in bpy.data.materials:
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    file_path = bpy.path.abspath(node.image.filepath)
                    if file_path:  # Make sure you have a valid route
                        item = bpy.context.scene.monitored_textures.add()
                        item.name = node.image.name
                        item.filepath = file_path
                        item.monitor = False  # Starts as unmonitored


# Panel in the N-Panel
class AUTOREFRESH_PT_Panel(bpy.types.Panel):
    bl_label = "Auto Refresh Textures"
    bl_idname = "AUTOREFRESH_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Refresh"

    def draw(self, context):
        layout = self.layout        
        button_text = "Disable Auto Refresh" if is_monitoring_enabled else "Enable Auto Refresh"
        layout.operator("wm.toggle_refresh", text=button_text)
        layout.prop(context.scene, "refresh_interval", text="Refresh Interval (sec)")
        
        box = layout.box()
        box.label(text="Textures:")
        for item in context.scene.monitored_textures:
            row = box.row()
            row.prop(item, "monitor", text="")
            row.label(text=item.name)

            # Texture editing button
            edit_button = row.operator("wm.edit_texture", text="Edit")
            edit_button.filepath = item.filepath  # We pass the file path to the action
            edit_button.texture_name = item.name  # We also pass the name of the texture


# Operator to enable/disable monitoring
class WM_OT_ToggleRefresh(bpy.types.Operator):
    bl_idname = "wm.toggle_refresh"
    bl_label = "Toggle Texture Refresh"
    bl_description = "Enable or disable texture updates for external changes."

    def execute(self, context):
        global is_monitoring_enabled
        is_monitoring_enabled = not is_monitoring_enabled

        if is_monitoring_enabled:
            update_texture_list()
            bpy.app.timers.register(refresh_images_periodically)
            print("The texture update has started.")
        else:
            bpy.app.timers.unregister(refresh_images_periodically)
            print("The texture update has stopped.")

        return {'FINISHED'}


# Operator for texture editing (open in external editor)
class WM_OT_EditTexture(bpy.types.Operator):
    bl_idname = "wm.edit_texture"
    bl_label = "Edit Texture"
    bl_description = "Open the texture in an external editor."

    filepath: bpy.props.StringProperty(name="File Path")
    texture_name: bpy.props.StringProperty(name="Texture Name")

    def execute(self, context):
        open_external_editor(self.filepath)  # We call the function to open the editor
        return {'FINISHED'}


# Disable monitoring when loading a new file
@persistent
def disable_monitoring_on_load(_):
    global is_monitoring_enabled
    if is_monitoring_enabled:
        try:
            bpy.app.timers.unregister(refresh_images_periodically)
            print("Auto refresh disabled due to file load or new project creation.")
        except ValueError:
            print("Auto refresh was already disabled, no active timer to unregister.")
        is_monitoring_enabled = False


# Property registration
def register():
    bpy.utils.register_class(MonitoredTextureItem)
    bpy.types.Scene.monitored_textures = bpy.props.CollectionProperty(type=MonitoredTextureItem)
    bpy.types.Scene.refresh_interval = bpy.props.FloatProperty(
        name="Refresh Interval",
        description="Interval in seconds for texture updates.",
        default=1.0,
        min=0.5,
        max=10.0,
        step=0.1,
        precision=1,
    )
    bpy.utils.register_class(AUTOREFRESH_PT_Panel)
    bpy.utils.register_class(WM_OT_ToggleRefresh)
    bpy.utils.register_class(WM_OT_EditTexture)
    bpy.app.handlers.load_post.append(disable_monitoring_on_load)


def unregister():
    bpy.utils.unregister_class(MonitoredTextureItem)
    del bpy.types.Scene.monitored_textures
    del bpy.types.Scene.refresh_interval
    bpy.utils.unregister_class(AUTOREFRESH_PT_Panel)
    bpy.utils.unregister_class(WM_OT_ToggleRefresh)
    bpy.utils.unregister_class(WM_OT_EditTexture)
    bpy.app.handlers.load_post.remove(disable_monitoring_on_load)


if __name__ == "__main__":
    register()