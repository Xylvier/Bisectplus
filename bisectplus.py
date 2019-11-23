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
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bisect plus",
    "description": "Bisect plus object selection for the cutting plane",
    "warning": "",
    "wiki_url": "https://github.com/Xylvier/Bisectplus/wiki",
    "category": "All",
}

import bpy
import bmesh
import mathutils.geometry

from bpy.props import (
        PointerProperty,
        StringProperty,
        FloatProperty,
        BoolProperty,
        )

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
        objs = context.selected_objects
        return objs != [] and objs[0].type == "MESH"

    def execute(self, context):
        objectselection_props = context.window_manager.objectselection_props
        obj = context.active_object

        #go in EDIT MODE to see the results as it's a mesh operation
        bpy.ops.object.mode_set(mode='EDIT')
        cpobj = objectselection_props.cuttingplane

        #only accept mesh
        if cpobj.type != 'MESH':
            return {'CANCELED'}
        
        bm = bmesh.new()
        bm.from_mesh(cpobj.data)

        bm.faces.ensure_lookup_table()
        bm.faces[0].select = True
        
        if len(bm.faces) > 1:
            return {'CANCELED'}

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
        
        #keep the manual selection saved in a vertex group
        if objectselection_props.rememberselection:
            obj.vertex_groups.new(name="prebisectselection")
            bpy.ops.object.vertex_group_assign()
        
        #only works in Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        if objectselection_props.selectionoverride:
            #all vertices need to be selected
            for v in obj.data.vertices:
                v.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        
        
        #call bisect with the selected plane
        bpy.ops.mesh.bisect(
            plane_co = origin,
            plane_no = normal,
            use_fill = objectselection_props.fill,
            clear_inner = objectselection_props.clearinner,
            clear_outer = objectselection_props.clearouter,
            threshold = objectselection_props.axisthreshold,
            )

        obj.vertex_groups.new(name="bisectionloop")
        bpy.ops.object.vertex_group_assign()
        mat = obj.matrix_world
        
        sideA = obj.vertex_groups["bisectionloop"]
        sideA = obj.vertex_groups.new(name="FrontSide")
        sideB = obj.vertex_groups["bisectionloop"]
        sideB = obj.vertex_groups.new(name="BackSide")

        indexarrayA = []
        for vertex in obj.data.vertices:
            pos = mat@vertex.co
            distance = mathutils.geometry.distance_point_to_plane(pos, origin, normal)
            if distance > objectselection_props.axisthreshold:
                indexarrayA.append(vertex.index)
    
        indexarrayB = []
        for vertex in obj.data.vertices:
            pos = mat@vertex.co
            distance = mathutils.geometry.distance_point_to_plane(pos, origin, normal)
            if distance < objectselection_props.axisthreshold:
                indexarrayB.append(vertex.index)

        #only works in Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        sideA.add( indexarrayA, 1.0, 'REPLACE' )
        sideB.add( indexarrayB, 1.0, 'REPLACE' )
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.object.vertex_group_set_active(group='bisectionloop')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_set_active(group='FrontSide')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()
        
        bpy.ops.object.vertex_group_set_active(group='bisectionloop')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_set_active(group='BackSide')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_deselect()
    
        if objectselection_props.rememberselection:
            bpy.ops.object.vertex_group_set_active(group='prebisectselection')
            bpy.ops.object.vertex_group_select()
            bpy.ops.object.vertex_group_set_active(group='bisectionloop')
            bpy.ops.object.vertex_group_deselect()
            bpy.ops.object.vertex_group_set_active(group='prebisectselection')
            bpy.ops.object.vertex_group_remove()
         
        
        if objectselection_props.clearouter:
            bpy.ops.object.vertex_group_set_active(group='FrontSide')
            bpy.ops.object.vertex_group_remove()
            bpy.ops.object.vertex_group_set_active(group='BackSide')
            #Object Mode needed for the selection of the vertices
            bpy.ops.object.mode_set(mode='OBJECT')
            for v in obj.data.vertices:
                v.select = True
            bpy.ops.object.mode_set(mode='EDIT')

            bpy.ops.object.vertex_group_assign()
        if objectselection_props.clearinner:
            bpy.ops.object.vertex_group_set_active(group='BackSide')
            bpy.ops.object.vertex_group_remove()
            bpy.ops.object.vertex_group_set_active(group='FrontSide')
            #Object Mode needed for the selection of the vertices
            bpy.ops.object.mode_set(mode='OBJECT')
            for v in obj.data.vertices:
                v.select = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.vertex_group_assign()


        #clean up
        bm.free()
        return {'FINISHED'}


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
        column = layout.column(align=True)
        
        box = column.box()
        
        cell_props = context.window_manager.objectselection_props
        
        obj = context.active_object
        cell_props.bisecttarget = obj.name
        label = box.label(text="Currently selected target:")

        box1 = box.box()
        box1.label(text=obj.name,icon='OBJECT_DATAMODE')

        cell_props = context.window_manager.objectselection_props
        cplabeltxt = "Select a cutting plane:"
        if cell_props.cuttingplane:
            cplabeltxt = "Selected cutting plane:"

        box.label(text=cplabeltxt)
        box.prop(cell_props, "cuttingplane")
        box.prop(cell_props, "rememberselection")
        box.prop(cell_props, "selectionoverride")
        column.separator()
        box.prop(cell_props, "fill")
        box.prop(cell_props, "clearinner")
        box.prop(cell_props, "clearouter")
        box.prop(cell_props, "axisthreshold")
        
        if cell_props.cuttingplane:
            column.separator()
            column.operator("mesh.bisectplus", icon='NONE', text="Ready to bisect")

    @classmethod
    def poll(cls, context):
        #using selected_objects to only show the ui if the object is a mesh
        #and the operation can be done on it
        objs = context.selected_objects
        return objs != [] and objs[0].type == "MESH"


class ObjectSelectionProperties(PropertyGroup):
    bisecttarget: StringProperty(
            name="",
            description="Selected Object to be bisected with the cutting plane,\nhas to be a 'Mesh'",
            )
    
    cuttingplane: PointerProperty(
            name="",
            description="Must be a single face Plane Object to cut.",
            type=bpy.types.Object,
            )
    rememberselection: BoolProperty(
            name="Remember manual selection",
            description="Your selection before the operation will be restored,\nafter the operation is done.",
            default=True,
            )   
    
    selectionoverride: BoolProperty(
            name="Override selection",
            description="Overrides your eventual selection and selects all vertices,\nthat way the bisection will go through the entire object.\n\nDon't activate if you have a manual selection!",
            default=False,
            )

    fill: BoolProperty(
            name="Fill",
            description="Fill in the cut\nbeware of new faces if used without clear inner or outer",
            default=False,
            )
    clearinner: BoolProperty(
            name="Clear Inner",
            description="Remove geometry behind the plane",
            default=False,
            )
    clearouter: BoolProperty(
            name="Clear Outer",
            description="Remove geometry in front of the plane",
            default=False,
            )
    axisthreshold: FloatProperty(
            name="Axisthreshold:",
            description="Preserves the geometry along the cutline",
            default=0.0001,
            min=0.00001,
            max=1.0,
            precision=4,
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
    del bpy.types.WindowManager.objectselection_props

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__" :
    register()