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

bl_info = {
    "name": "Bisect plus",
    "author": "Patrick Busch",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bisect plus",
    "description": "Bisect with object selection for the cutting plane",
    "warning": "",
    "wiki_url": "",
    "category": "All",
}

import bpy
import bmesh
import mathutils.geometry

from bpy.props import PointerProperty

from bpy.types import (
        Operator,
        Panel,
        PropertyGroup,
        )

#OPERATOR class
class bisectplus(Operator):
    bl_idname = 'mesh.bisectplus'
    bl_label = 'Bisect Plus'
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "MESH"

    def execute(self, context):
        objectselection_props = context.window_manager.objectselection_props
        obj = context.active_object
        mode = obj.mode
        #go in EDIT MODE to see the results as it's a mesh operation
        bpy.ops.object.mode_set(mode='EDIT')
        cpobj = None
        cpobj = objectselection_props.cuttingplane

        #only accept mesh
        if cpobj.type != 'MESH':
            return {'FINISHED'}
        
        bm = bmesh.new()
        bm.from_mesh(cpobj.data)

        bm.faces.ensure_lookup_table()
        bm.faces[0].select = True
        
        if len(bm.faces) > 1:
            return {'FINISHED'}

        bm.verts.ensure_lookup_table()
        v1 = cpobj.matrix_world @ bm.verts[0].co
        v2 = cpobj.matrix_world @ bm.verts[1].co
        v3 = cpobj.matrix_world @ bm.verts[2].co
        v4 = cpobj.matrix_world @ bm.verts[3].co

        nv2 = v4 - v3
        nv3 = v3 - v2
        vn = nv2.cross(nv3)
        vn.normalize()
        face = bm.faces[0]

        origin =  cpobj.matrix_world @ face.calc_center_median()
        normal = vn
        
        #call bisect with the selected plane
        bpy.ops.mesh.bisect(plane_co=origin, plane_no=normal)

        obj.vertex_groups.new(name="bisectionloop")
        bpy.ops.object.vertex_group_assign()
        mat = obj.matrix_world
        
        sideA = obj.vertex_groups["bisectionloop"]
        sideA = obj.vertex_groups.new(name="SideA")
        sideB = obj.vertex_groups["bisectionloop"]
        sideB = obj.vertex_groups.new(name="SideB")
        
        indexarrayA = []
        for vertex in obj.data.vertices:
            pos = mat@vertex.co
            distance = mathutils.geometry.distance_point_to_plane(pos, origin, normal)
            if distance > 0.01:
                indexarrayA.append(vertex.index)
        
        indexarrayB = []
        for vertex in obj.data.vertices:
            pos = mat@vertex.co
            distance = mathutils.geometry.distance_point_to_plane(pos, origin, normal)
            if distance < 0.01:
                indexarrayB.append(vertex.index)

        bpy.ops.object.mode_set(mode='OBJECT')
        sideA.add( indexarrayA, 1.0, 'REPLACE' )
        sideB.add( indexarrayB, 1.0, 'REPLACE' )
        bpy.ops.object.mode_set(mode='EDIT')

        
        bpy.ops.object.vertex_group_set_active(group='bisectionloop')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_set_active(group='SideA')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()
        
        bpy.ops.object.vertex_group_set_active(group='bisectionloop')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_set_active(group='SideB')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()
        
        #clean up
        bm.free()
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=300)

    def draw(self, context):
        cell_props = context.window_manager.objectselection_props
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.label(text="Cutting Plane:")
        row = col.row()
        #row.prop(cell_props, "source")
        row.prop(cell_props, "cuttingplane")

#ui class
class OBJECTSELECTION_Panel(Panel):
    bl_idname = 'OBJECTSELECTION_Panel'
    bl_label = 'Bisect Plus'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Create'
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.bisectplus", icon='OBJECT_DATA', text="Select Cutting Plane")

class ObjectSelectionProperties(PropertyGroup):
    cuttingplane: PointerProperty(
            name="",
            description="Must be a single face Plane Object to cut",
            type=bpy.types.Object
            )

classes = (
    ObjectSelectionProperties,
    bisectplus,
    OBJECTSELECTION_Panel,
    )

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.WindowManager.objectselection_props = PointerProperty(
        type=ObjectSelectionProperties
    )

def unregister():
    del bpy.types.WindowManager.objectselectionprops

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__" :
    register()