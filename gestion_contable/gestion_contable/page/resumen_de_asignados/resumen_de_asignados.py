import frappe
from frappe.utils import getdate, nowdate

@frappe.whitelist()
def get_user_stats():
    roles = ["Contador del Despacho", "Auxiliar Contable del Despacho"]
    
    # Obtener usuarios agrupados que tienen los roles
    users_with_roles = set(frappe.get_all("Has Role", filters={"role": ("in", roles)}, pluck="parent"))
    
    if not users_with_roles:
        return []
    
    # Filtrar solo usuarios activos
    users = frappe.get_all("User", 
                           filters={"name": ("in", list(users_with_roles)), "enabled": 1}, 
                           fields=["name", "full_name"])
    
    # Inicializar el diccionario de métricas
    user_map = {
        u.name: {
            "name": u.name,
            "full_name": u.full_name or u.name,
            "totales": 0,
            "pendientes": 0,
            "en_proceso": 0,
            "en_revision": 0,
            "completadas": 0,
            "atrasadas": 0
        } for u in users
    }
    
    # Obtener todas las tareas contables para procesarlas
    tasks = frappe.get_all("Tarea Contable", 
                           fields=["name", "asignado_a", "estado", "fecha_de_vencimiento"])
    
    today = getdate(nowdate())
    
    for task in tasks:
        # Solo procesamos si el usuario está en nuestro map (tiene rol del despacho y está activo)
        if task.asignado_a in user_map:
            u = user_map[task.asignado_a]
            u["totales"] += 1
            
            # Contar por estado
            if task.estado == "Pendiente":
                u["pendientes"] += 1
            elif task.estado == "En Proceso":
                u["en_proceso"] += 1
            elif task.estado == "En Revisión":
                u["en_revision"] += 1
            elif task.estado == "Completada":
                u["completadas"] += 1
                
            # Calcular atrasadas (que NO están completadas y la fecha ya pasó)
            if task.estado != "Completada" and task.fecha_de_vencimiento and getdate(task.fecha_de_vencimiento) < today:
                u["atrasadas"] += 1
                
    # Retornar como array ordenado por el nombre completo
    return sorted(user_map.values(), key=lambda x: x["full_name"])
