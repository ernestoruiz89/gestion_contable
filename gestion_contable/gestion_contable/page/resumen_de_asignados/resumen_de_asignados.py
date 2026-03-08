import json

import frappe
from frappe.utils import getdate, nowdate


@frappe.whitelist()
def get_user_stats():
    roles = ["Contador del Despacho", "Auxiliar Contable del Despacho"]

    users_with_roles = set(frappe.get_all("Has Role", filters={"role": ("in", roles)}, pluck="parent"))
    if not users_with_roles:
        return []

    users = frappe.get_all(
        "User",
        filters={"name": ("in", list(users_with_roles)), "enabled": 1},
        fields=["name", "full_name"],
    )

    user_map = {
        user.name: {
            "name": user.name,
            "full_name": user.full_name or user.name,
            "totales": 0,
            "pendientes": 0,
            "en_proceso": 0,
            "en_revision": 0,
            "completadas": 0,
            "atrasadas": 0,
        }
        for user in users
    }

    tasks = frappe.get_all("Task", fields=["name", "_assign", "status", "exp_end_date"])
    today = getdate(nowdate())

    for task in tasks:
        assignees = []
        if task._assign:
            try:
                assignees = json.loads(task._assign)
            except Exception:
                assignees = []

        for assigned_user in assignees:
            if assigned_user not in user_map:
                continue

            metrics = user_map[assigned_user]
            metrics["totales"] += 1

            if task.status == "Open":
                metrics["pendientes"] += 1
            elif task.status == "Working":
                metrics["en_proceso"] += 1
            elif task.status == "Pending Review":
                metrics["en_revision"] += 1
            elif task.status == "Completed":
                metrics["completadas"] += 1

            if task.status != "Completed" and task.exp_end_date and getdate(task.exp_end_date) < today:
                metrics["atrasadas"] += 1

    return sorted(user_map.values(), key=lambda row: row["full_name"])
