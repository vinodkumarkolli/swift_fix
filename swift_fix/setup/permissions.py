import frappe


def add_permission(doctype, role, perms):
    meta = frappe.get_meta(doctype)

    # check if permission already exists
    for p in meta.permissions:
        if p.role == role:
            return

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