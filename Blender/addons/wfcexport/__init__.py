from mathutils.geometry import distance_point_to_plane
from mathutils.geometry import intersect_point_tri_2d
from mathutils.geometry import intersect_point_quad_2d
from mathutils import Vector, Matrix
import math
import mathutils
import bmesh
import bpy

bl_info = {
    'name': 'WFC Export',
    'author': 'Martin Donald (Original Script), Martin Schmidli',
    'version': (1, 0, 0),
    'blender': (2, 80, 0),  # supports 2.8+
    "description": "WFC Export",
    'location': '',
    "warning": "",
    "tracker_url": "",
    'category': 'Development',
}


BOUNDARY_TOLERANCE = 0.001
MESH_NAME = "Triangle"
debug = False
addon_keymaps = []

PROTO_NAME = "mesh_name"
PROTO_ROTATION = "mesh_rotation"
PROTO_NEIGHBOURS = "valid_neighbours"
PROTO_A = "posA"
PROTO_B = "posB"
PROTO_C = "posC"
PROTO_TOP = "posTop"
PROTO_BOTTOM = "posBottom"
PROTO_FACES = [PROTO_A, PROTO_B, PROTO_C, PROTO_TOP, PROTO_BOTTOM]
PROTO_CONSTRAIN_TO = "constrain_to"
PROTO_CONSTRAIN_FROM = "constrain_from"
PROTO_WEIGHT = "weight"
PROTO_CUSTOM_ATTRIBUTES = {
    PROTO_CONSTRAIN_TO: "",
    PROTO_CONSTRAIN_FROM: "",
    PROTO_WEIGHT: 1
}

JSON_FILE = "prototype_data.json"
MODULES_FILE = "wfc_modules"

posA = 0
posB = 1
posC = 2
posTop = 3
posBot = 4

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


def compare_vertices(v1, v2):
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

    # Set the origin to the volumes center
    center = sum((v.co for v in mesh.vertices), Vector()) / len(mesh.vertices)

    # Move the object to the origin
    obj.location = center

    # Move the mesh data to the origin
    mesh.transform(Matrix.Translation(-center))

    # Set the origin of the object to the center of the mesh
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    # Move the object to the 0,0,0
    # Calculate the center of the mesh
    center = Vector((0.0, 0.0, 0.0))
    for v in mesh.vertices:
        center += obj.matrix_world @ v.co
    center /= len(mesh.vertices)

    # Set the origin to the center of the mesh
    obj.matrix_world.translation = -center

    # Debug_Only: Show in the scene
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


def rotate_mesh_120(bm):
    rot = Matrix.Rotation(math.radians(-120), 4, Vector([0.0, 0.0, 1.0]))
    bmesh.ops.rotate(bm, cent=Vector(
        [0.0, 0.0, 0.0]), matrix=rot, verts=bm.verts)


def find_connections_horizontal(obj):
    orientation = "up"
    boundaryY = -0.2887  # Triangle lowest part on Y Axis. Top down view.
    boundaries = [list(), list(), list()]

    field = bmesh.new()
    field.from_mesh(obj.data)

    # check orientation of triangle up/down
    if "orientation" in obj.keys():
        print("orientation", obj["orientation"])
        orientation = obj["orientation"]

    for i in range(3):
        for vert in field.verts:
            # We measure if the vertice y point is on or near the "reference" line
            if vert.co.y <= boundaryY + BOUNDARY_TOLERANCE:
                nice_pos = round_position(vert.co, 4)
                boundaries[i].append(nice_pos)
        # Rotate 120 degres so every side of the trianlge is aligned to the X Axis
        rotate_mesh_120(field)

    return boundaries


def hash_boundaries(allObjects):
    connectionDictionary = dict()
    modules = list()
    mi = 0  # Used to name meshes, incremented whenever we copy a module
    bi = 0  # Used to name boundaries, incremented whenever a new one is found

    # Loop through each selected object
    for obj in allObjects:

        # Output name of Triangle
        print("***** Handle Mesh:", obj.name)
        print("stored connections", connectionDictionary)

        copy = duplicateMesh(obj)

        move_to_origin(copy)  # move to center 0,0,0
        copy.name = MESH_NAME + str(mi)
        modules.append(copy)

        connections = find_connections_horizontal(copy)
        print("Found connections: ", len(connections))
        # print(connections)

        # All ConnectionNames are stored on the copy of the module 
        # this ensures that we can later access this informatio and know which side of the triangle modules has which conectionName assigned
        # copy.data => 0 (Rotation 0) = ConnectionName
        for i, connection in enumerate(connections):

            if len(connection) == 0:
                # no connection at all, we need the empty connection (-1) here
                copy.data[str(i)] = "-1"
                continue

            existingConnection = connectionExistsInDictionary(
                connection, connectionDictionary)
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

        # bpy.context.collection.objects.link(copy)  #  link to scene in case we want to see what we exported
        mi += 1

    print("final", connectionDictionary)
    return modules


def create_module_prototypes(modules):
    all_prototypes = dict()
    pi = 0

    for module in modules:
        prototypes = list()
        # we create a prototype of the main module for all rotations of the module
        # range(3) because we have 3 possible positions/rotations on the final field
        for i in range(3):
            prototype = dict()
            prototype[PROTO_NAME] = module.name
            prototype[PROTO_ROTATION] = i
            prototype[PROTO_A] = module.data[str((posA + (i * 2)) % 3)]
            prototype[PROTO_B] = module.data[str((posB + (i * 2)) % 3)]
            prototype[PROTO_C] = module.data[str((posC + (i * 2)) % 3)]

            # prototype = _add_custom_constraints(prototype, module)

            all_prototypes["{}{}".format("p", pi)] = prototype
            pi += 1

    all_prototypes["p-1"] = _blank_prototype()

    return all_prototypes


def _blank_prototype():
    proto = dict()
    proto[PROTO_NAME] = "-1"
    proto[PROTO_ROTATION] = 0
    proto[PROTO_A] = "-1f"
    proto[PROTO_B] = "-1f"
    proto[PROTO_C] = "-1f"
    proto[PROTO_TOP] = "-1f"
    proto[PROTO_BOTTOM] = "-1f"
    proto[PROTO_CONSTRAIN_TO] = "-1"
    proto[PROTO_CONSTRAIN_FROM] = "-1"
    proto[PROTO_WEIGHT] = 1
    return proto


class WFCExport(bpy.types.Operator):
    """WFC Export"""
    bl_idname = "wfc.export"
    bl_label = "WFC Export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Get a list of all selected objects in the scene
        allObjects = bpy.context.selected_objects
        module_meshes = hash_boundaries(allObjects)
        prototypes = create_module_prototypes(module_meshes)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(WFCExport)

    # handle the keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(
        name='Object Mode', space_type='EMPTY')

    kmi = km.keymap_items.new(WFCExport.bl_idname, 'T',
                              'PRESS', ctrl=True, shift=True)

    addon_keymaps.append((km, kmi))


def unregister():
    bpy.utils.unregister_class(WFCExport)

    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()
