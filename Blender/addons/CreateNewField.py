import bpy
import bmesh
from mathutils import Vector, Matrix

# Create a new mesh data block
mesh = bpy.data.meshes.new("TriangleMesh")

# Create a new bmesh to add geometry
bm = bmesh.new()

# Create the vertices for the bottom triangle
v1 = bm.verts.new((0.0, 0.0, 0.0))
v2 = bm.verts.new((1.0, 0.0, 0.0))
v3 = bm.verts.new((0.5, 0.866, 0.0))

# Create the bottom triangle face
f1 = bm.faces.new((v1, v2, v3))

# Update the bmesh and create a new object from the mesh data
bm.to_mesh(mesh)
mesh.update()
obj = bpy.data.objects.new("TriangleMesh", mesh)

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

# Link the object to the scene and make it active
scene = bpy.context.scene
scene.collection.objects.link(obj)