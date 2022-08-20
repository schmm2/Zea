extends Spatial

var mesh : ArrayMesh setget _set_mesh
var prototype : Dictionary
var debug_text

var text


func _set_mesh(new_mesh):
	mesh = new_mesh
	$mesh_instance.mesh = mesh
	

func _on_col_area_mouse_entered():
	if debug_text:
		debug_text.text = str(prototype)


func _on_col_area_mouse_exited():
	if debug_text.text:
		debug_text.text = ""
