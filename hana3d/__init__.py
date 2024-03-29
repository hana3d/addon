# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
import bpy
import bpy.utils.previews
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences

from . import (  # noqa: WPS235
    addon_updater_ops,
    append_link,
    asset,
    bg_blender,
    hana3d_oauth,
    hana3d_types,
    libraries,
    paths,
    tags,
    tasks_queue,
    thread_tools,
    ui,
    utils,
)
from .config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from .src import async_loop, autothumb, download, upload
from .src.application.application import Application
from .src.authentication.authentication import Authentication
from .src.edit_asset import operators as edit_ops
from .src.logs import logger, send_logs
from .src.panels import panel_builder
from .src.search import operator as search_op

bl_info = {
    'name': 'Hana3D',
    'author': 'Vilem Duha, Petr Dlouhy, R2U',
    'version': (1, 3, 2),
    'blender': (2, 91, 0),
    'location': 'View3D > Properties > Hana3D',
    'description': 'Online Hana3D library (materials, models, scenes and more). Connects to the internet.',  # noqa: E501
    'warning': '',
    'category': '3D View',
}


@ persistent
def scene_load(context):
    """Load scene and initialize classes and menus.

    Parameters:
        context: Blender context
    """
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
    ui_props.assetbar_on = False
    ui_props.turn_off = False
    preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
    preferences.login_attempt = False
    preferences.refresh_in_progress = False

    application = Application()
    authentication = Authentication()
    if not application.background():
        if not bpy.app.timers.is_registered(authentication.refresh_token_timer):
            bpy.app.timers.register(authentication.refresh_token_timer)


@ persistent
def thumbnail_load(context):
    """Force thumbnails to load when opening a scene.

    Parameters:
        context: Blender context
    """
    for scene_obj in bpy.data.objects:
        props = getattr(scene_obj, HANA3D_NAME)
        if props.thumbnail != '':
            props.force_preview_reload = True


@ bpy.app.handlers.persistent
def check_timers_timer():
    """Check if all timers are registered regularly.

    Prevents possible bugs from stopping the addon.

    Returns:
        float: time between executions
    """
    if not bpy.app.timers.is_registered(download.timer_update):
        bpy.app.timers.register(download.timer_update)
    if not bpy.app.timers.is_registered(download.execute_append_tasks):
        bpy.app.timers.register(download.execute_append_tasks)
    if not bpy.app.timers.is_registered(tasks_queue.queue_worker):
        bpy.app.timers.register(tasks_queue.queue_worker)
    if not bpy.app.timers.is_registered(bg_blender.bg_update):
        bpy.app.timers.register(bg_blender.bg_update)
    if not bpy.app.timers.is_registered(thread_tools.threads_state_update):
        bpy.app.timers.register(thread_tools.threads_state_update)
    if not bpy.app.timers.is_registered(ui.redraw_regions):
        bpy.app.timers.register(ui.redraw_regions)
    return 5.0


class Hana3DAddonPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = HANA3D_NAME

    default_global_dict = paths.default_global_dict()

    api_key: StringProperty(
        name=f"{HANA3D_DESCRIPTION} API Key",
        description=f"Your {HANA3D_DESCRIPTION} API Key. Get it from your page on the website",
        default="",
        subtype="PASSWORD",
        update=utils.save_prefs,
    )

    api_key_refresh: StringProperty(
        name=f"{HANA3D_DESCRIPTION} refresh API Key",
        description="API key used to refresh the token regularly.",
        default="",
        subtype="PASSWORD",
    )

    api_key_timeout: IntProperty(
        name='api key timeout',
        description='time where the api key will need to be refreshed',
        default=0,
        update=utils.save_prefs,
    )

    api_key_life: IntProperty(
        name='api key life time',
        description='maximum lifetime of the api key, in seconds',
        default=3600,
        update=utils.save_prefs,
    )

    id_token: StringProperty(
        name=f"{HANA3D_DESCRIPTION} ID Token",
        default="",
        subtype="PASSWORD",
        update=utils.save_prefs,
    )

    refresh_in_progress: BoolProperty(
        name="Api key refresh in progress",
        description="Api key is currently being refreshed. Don't refresh it again.",
        default=False,
    )

    login_attempt: BoolProperty(
        name="Login/Signup attempt",
        description=f"When this is on, {HANA3D_DESCRIPTION} is trying to connect and login",
        default=False,
    )

    show_on_start: BoolProperty(
        name="Show assetbar when starting blender",
        description="Show assetbar when starting blender",
        default=False,
    )

    search_in_header: BoolProperty(
        name="Show 3D view header",
        description="Show 3D view header",
        default=True
    )

    global_dir: StringProperty(
        name="Global Files Directory",
        description="Global storage for your assets, will use subdirectories for the contents",
        subtype='DIR_PATH',
        default=default_global_dict,
        update=utils.save_prefs,
    )

    project_subdir: StringProperty(
        name="Project Assets Subdirectory",
        description="where data will be stored for individual projects",
        subtype='DIR_PATH',
        default="//assets",
    )

    directory_behaviour: EnumProperty(
        name="Use Directories",
        items=(
            (
                'BOTH',
                'Global and subdir',
                'store files both in global lib and subdirectory of current project. '
                'Warning - each file can be many times on your harddrive, '
                'but helps you keep your projects in one piece',
            ),
            (
                'GLOBAL',
                'Global',
                "store downloaded files only in global directory. \n "
                "This can bring problems when moving your projects, \n"
                "since assets won't be in subdirectory of current project",
            ),
            (
                'LOCAL',
                'Local',
                'store downloaded files only in local directory.\n'
                ' This can use more bandwidth when you reuse assets in different projects. ',
            ),
        ),
        description="Which directories will be used for storing downloaded data",
        default="BOTH",
    )
    thumbnail_use_gpu: BoolProperty(
        name="Use GPU for Thumbnails Rendering",
        description="By default this is off so you can continue your work without any lag",
        default=False,
    )

    max_assetbar_rows: IntProperty(
        name="Max Assetbar Rows",
        description="max rows of assetbar in the 3D view",
        default=1,
        min=0,
        max=20,
    )

    thumb_size: IntProperty(name="Assetbar thumbnail Size", default=96, min=-1, max=256)

    asset_counter: IntProperty(
        name="Usage Counter",
        description="Counts usages so it asks for registration only after reaching a limit",
        default=0,
        min=0,
        max=20000,
    )

    first_run: BoolProperty(
        name="First run",
        description="Detects if addon was already registered/run.",
        default=True,
        update=utils.save_prefs,
    )

    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_intrval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31,
    )
    updater_intrval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )
    updater_intrval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "show_on_start")

        if self.api_key.strip() == '':
            panel_builder.draw_login_buttons(layout)
        else:
            layout.operator(f"wm.{HANA3D_NAME}_logout", text="Logout", icon='URL')

        layout.prop(self, "api_key", text='Your API Key')
        layout.prop(self, "global_dir")
        layout.prop(self, "project_subdir")
        # layout.prop(self, "temp_dir")
        layout.prop(self, "directory_behaviour")
        layout.prop(self, "thumbnail_use_gpu")
        layout.prop(self, "thumb_size")
        layout.prop(self, "max_assetbar_rows")
        layout.prop(self, "search_in_header")

        addon_updater_ops.update_settings_ui(self, context)


modules = (
    async_loop,
    append_link,
    asset,
    autothumb,
    bg_blender,
    download,
    hana3d_oauth,
    libraries,
    logger,
    search_op,
    send_logs,
    tags,
    tasks_queue,
    thread_tools,
    hana3d_types,
    ui,
    panel_builder,
    upload,
    edit_ops,
)


def register():
    addon_updater_ops.register(bl_info)
    bpy.utils.register_class(Hana3DAddonPreferences)
    for module in modules:
        module.register()

    utils.load_prefs()

    bpy.app.timers.register(check_timers_timer, persistent=True)
    bpy.app.handlers.load_post.append(scene_load)
    bpy.app.handlers.load_post.append(thumbnail_load)


def unregister():
    for module in reversed(modules):
        module.unregister()

    bpy.app.timers.unregister(check_timers_timer)
    bpy.app.handlers.load_post.remove(thumbnail_load)
    bpy.app.handlers.load_post.remove(scene_load)
    bpy.utils.unregister_class(Hana3DAddonPreferences)
    addon_updater_ops.unregister()


logger.setup_logger()
