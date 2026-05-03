import frappe

ROLES = [
    "Field User",
    "Manager",
    "Quality Manager",
    "Vendor Technician",
    "Technician",
    "Vendor Admin"
]

def create_roles():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role
            }).insert(ignore_permissions=True)