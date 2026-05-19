import frappe
ROLES = [
    "Field User",
    "Purchase Manager",
    "Quality Manager",
    "Vendor Technician",
    "Internal Technician",
    "Vendor Admin"
]

def create_roles():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role
            }).insert(ignore_permissions=True)
            print(f"Created Role: '{role}'")


def add_permission(doctype, role, perms):
    meta = frappe.get_meta(doctype)

    # check if permission already exists
    permission_exists = False
    for p in meta.permissions:
        if p.role == role:
            permission_exists = True
            break

    if permission_exists:
        frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role})
        frappe.db.delete("DocPerm", {"parent": doctype, "role": role})
        print(f"Deleted existing permissions for Role: '{role}' on DocType: '{doctype}'")

    perm = frappe.get_doc({
        "doctype": "Custom DocPerm",
        "parent": doctype,
        "parenttype": "DocType",
        "parentfield": "permissions",
        "role": role
    })

    for p in perms:
        perm.set(p, 1)

    perm.insert(ignore_permissions=True)
    print(f"Inserted new permissions for Role: '{role}' on DocType: '{doctype}' with perms: {perms}")


def setup_permissions():

    permissions = {

        "Material Request": {
            "Field User": ["read", "write", "create", "submit"]
        },

        "Request for Quotation": {
            "Purchase Manager": ["read", "write", "create", "submit"],
            "Vendor Technician": ["read", "write"]
        },

        "Supplier Quotation": {
            "Purchase Manager": ["read", "write","cancel", "submit"],
            "Vendor Admin": ["read","write","create","cancel", "submit"]
        },

        "Purchase Order": {
            "Purchase Manager": ["read", "write","create", "submit"]
        },

        "Purchase Receipt": {
            "Quality Manager": ["read", "write", "submit"]
        },

        "Asset Capitalization": {
            "Internal Technician": ["read", "write", "submit"],
            "Vendor Technician": ["read", "write","create","submit"]
        },

        "Asset Maintenance Log": {
            "Internal Technician": ["read", "write","create","submit"]
        }

    }

    for doctype, roles in permissions.items():
        for role, perms in roles.items():
            add_permission(doctype, role, perms)

def after_install():
    create_roles()
    setup_permissions()

def after_migrate():
    create_roles()
    setup_permissions() 