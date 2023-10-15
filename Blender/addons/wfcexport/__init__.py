bl_info = {
   'name': 'WFC Export',
   'author': 'Martin Donald (Original Script), Martin Schmidli',
   'version': (1, 0, 0),
   'blender': (2, 80, 0), # supports 2.8+
   "description": "WFC Export",
   'location': '',
   "warning": "",
   "tracker_url": "",
   'category': 'Development',
}

import bpy
import bmesh
import mathutils
import math
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_quad_2d
from mathutils.geometry import intersect_point_tri_2d
from mathutils.geometry import distance_point_to_plane

MESH_NAME = "Triangle"
debug = False
addon_keymaps = []

print("****************")
print("******START*********")
print("******Version 1.1*********")
print("****************")

def duplicateMesh(obj):
    dup = obj.copy()
    dup.data = obj.data.copy()
    return dup

def create_redmarker(co, name):
    # Create a new sphere mesh
    mesh = bpy.data.meshes.new("Sphere")
    sphere = bpy.data.objects.new((name + "Sphere"), mesh)

    # Set the sphere's location
    sphere.location = (co)

    # Add the sphere to the scene
    scene = bpy.context.scene
    scene.collection.objects.link(sphere)

    # Create a new material and set its color to red
    material = bpy.data.materials.new(name="Red")
    material.diffuse_color = (1.0, 0.0, 0.0, 1.0)  # (R, G, B, A)

    # Assign the material to the sphere
    sphere.data.materials.append(material)

    # Add a subdivision surface modifier to make the sphere smoother
    subsurf_modifier = sphere.modifiers.new(name="Subdivision", type="SUBSURF")
    subsurf_modifier.levels = 2  # Increase the number of subdivisions

    # Set the sphere's radius
    sphere.scale = (0.1, 0.1, 0.1)  # Set the scale to adjust the sphere's size

def compare_vertices(v1,v2):
    if v1.x != v2.x:
        return False
    if v1.y != v2.y:
        return False
    if v1.z != v2.z:
        return False
    return True

def move_to_origin(obj):
    loc = obj.location
    obj.location = Vector([0.0, 0.0, 0.0])
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.translate(bm, vec=[-loc.x, -loc.y, -loc.z], verts=bm.verts)
    bm.to_mesh(obj.data)
    
def create_referenceobject():
    # Create a new mesh data block
    mesh = bpy.data.meshes.new("ReferenceMesh")

    # Create a new bmesh to add geometry
    bm = bmesh.new()

    # Create the vertices for the bottom triangle
    v1 = bm.verts.new((0.0, 0.0, 0.0))
    v2 = bm.verts.new((1.0, 0.0, 0.0))
    v3 = bm.verts.new((0.5, 0.866, 0.0))

    # Create the vertices for the top triangle
    v4 = bm.verts.new((0.0, 0.0, 1.0))
    v5 = bm.verts.new((1.0, 0.0, 1.0))
    v6 = bm.verts.new((0.5, 0.866, 1.0))

    # Create the bottom triangle face
    f1 = bm.faces.new((v1, v2, v3))

    # Create the top triangle face
    f2 = bm.faces.new((v4, v5, v6))

    # Create the side faces
    f3 = bm.faces.new((v1, v4, v6, v3))
    f4 = bm.faces.new((v6, v3, v2, v5))
    f5 = bm.faces.new((v1, v2, v5, v4))
    
    # Update the bmesh and create a new object from the mesh data
    bm.to_mesh(mesh)
    mesh.update()
    obj = bpy.data.objects.new("ReferenceObject", mesh)
    
    # Get the mesh data
    mesh = obj.data

    ### Set the origin to the volumes center
    center = sum((v.co for v in mesh.vertices), Vector()) / len(mesh.vertices)

    # Move the object to the origin
    obj.location = center

    # Move the mesh data to the origin
    mesh.transform(Matrix.Translation(-center))

    # Set the origin of the object to the center of the mesh
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    
    ### Move the object to the 0,0,0
    # Calculate the center of the mesh
    center = Vector((0.0, 0.0, 0.0))
    for v in mesh.vertices:
        center += obj.matrix_world @ v.co
    center /= len(mesh.vertices)

    # Set the origin to the center of the mesh
    obj.matrix_world.translation = -center 
      
    ### Debug_Only: Show in the scene  
    # Link the object to the scene and make it active
    if debug == True:
        scene = bpy.context.scene
        scene.collection.objects.link(obj)
    
    return obj

def compareConnections(b1, b2):
    # Compare two boundaries and return True if they're the same
    if len(b1) == len(b2):
        for v in b1:
            if v in b2:
                continue
            else:
                return False
        return True
    
    # It's okay if the lengths don't match, in this case we check if the larger array
    # contains all members of the smaller, and consider it a match if so
    elif len(b1) > len(b2):
        
        for v in b2:
            if v in b1:
                continue
            else:
                return False
        return True
    else:
        for v in b1:
            if v in b2:
                continue
            else:
                return False
        return True

def round_position(vec, i):
    result = Vector([0.0, 0.0, 0.0])
    result.x = round(vec.x, i)
    result.y = round(vec.y, i)
    result.z = round(vec.z, i)
    return result

def connectionExistsInDictionary(connection, connectionDictionary):
    if len(connectionDictionary.keys()) == 0:
        return False
    for connectionName, existingConnection in connectionDictionary.items():
        if compareConnections(connection, existingConnection):
            return connectionName
    return False

def flipConnection(connection):
    newConnection = list()
    for vert in connection:
        newVert = vert.copy()
        newVert.y *= -1.0
        newConnection.append(newVert)
    return newConnection    
 
def find_connections(obj):
    orientation = "up"

    field = bmesh.new()
    field.from_mesh(obj.data)
    
    # print(field.verts)    
    # print(reference.verts)
    
    # check orientation of triangle up/down
    if "orientation" in obj.keys():
        print("orientation",obj["orientation"])
        orientation = obj["orientation"]
    
    foundCollisionPoints = list()
    
    for face in reference.faces:
        collision_points = list()
             
        #print(len(field.verts))  
          
        for vertOfField in field.verts:
            #print("Check Vertex {}", vertOfField.co)
                        
            # first check, calculate distance to plane         
            distancePointToPlane = distance_point_to_plane(vertOfField.co, face.verts[0].co, face.normal)
            #print(distancePointToPlane)


            # distance must be 0 or within a certain range -0.1 to +0.1
            if (distancePointToPlane < 0.1 and distancePointToPlane > -0.1): # find a better value for this          
                insideFace = 0
                
                # second check, check if point is within face
                if len(face.verts) == 4:
                    insideFace = intersect_point_quad_2d(vertOfField.co, face.verts[0].co,face.verts[1].co,face.verts[2].co,face.verts[3].co)
                             
                if len(face.verts) == 3:
                    insideFace = intersect_point_tri_2d(vertOfField.co,face.verts[0].co,face.verts[1].co,face.verts[2].co)
                
                if (insideFace == 1) and (vertOfField.co not in collision_points):
                    roundedPosition = round_position(vertOfField.co, 4)
                    collision_points.append(roundedPosition)
                
        # debug only: Print the collision points
        if debug == True:
            for point in collision_points:
                create_redmarker(point, "face"+str(face.index))
                print(point)
        
        # add the found connections to the collection 
        if len(collision_points) > 0:
            print("collisionspoints",collision_points)
            foundCollisionPoints.append(collision_points)  
    
    # return connections
    return foundCollisionPoints          
        

def export_selection():
    connectionDictionary = dict()
    modules = list() 
    
    mi = 0  # Used to name meshes, incremented whenever we copy a module
    bi = 0  # Used to name boundaries, incremented whenever a new one is found

    # Get a list of all selected objects in the scene
    allObjects = bpy.context.selected_objects
        
    referenceObject = create_referenceobject()

    # Loop through each selected object
    for obj in allObjects:

        # Output name of Triangle
        print("***** Handle Mesh:", obj.name)
        print("stored connections", connectionDictionary) 
            
        copy = duplicateMesh(obj) 
        move_to_origin(copy) # move to center 0,0,0
        copy.name = MESH_NAME + str(mi)
        modules.append(copy)
        
        connections = find_connections(copy)
        print("Found connections: ",len(connections))
        # print(connections)
        
        for i, connection in enumerate(connections):
            
            if len(connection) == 0:
                # no connection at all, we need the empty connection (-1) here
                copy.data[str(i)] = "-1"
                continue

            existingConnection = connectionExistsInDictionary(connection, connectionDictionary) 
            print("found existing connection", existingConnection)
            
            if existingConnection:
                print("existing connection")
                copy.data[str(i)] = existingConnection
            else:
                print("new connection")
                # Create new Connection entry and name it
                new_name = str(bi)
                if compareConnections(connection, flipConnection(connection)):  # if symmetrical
                    new_name += "s"
                    connectionDictionary[new_name] = connection
                else:
                    newConnection = connection.copy()
                    connectionDictionary[new_name] = newConnection
                    connectionDictionary[new_name + "f"] = flipConnection(newConnection)
                copy.data[str(i)] = new_name
                bi += 1

        #bpy.context.collection.objects.link(copy)  #  link to scene in case we want to see what we exported
        mi += 1
    
    print("final",connectionDictionary)
    return modules 


class WFCExport(bpy.types.Operator):
    """WFC Export"""
    bl_idname = "wfc.export"
    bl_label = "WFC Export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        export_selection()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(WFCExport)

     # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')

    kmi = km.keymap_items.new(WFCExport.bl_idname, 'T', 'PRESS', ctrl=True, shift=True)

    addon_keymaps.append((km, kmi))


def unregister():
    bpy.utils.unregister_class(WFCExport)

     # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()