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


def add_permission(doctype, role, perms, permlevel=0):
    # Only delete and manage Custom DocPerm to avoid corrupting standard system-level DocPerm entries
    if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": permlevel}):
        frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": permlevel})
        print(f"Deleted existing custom permissions for Role: '{role}' (Level {permlevel}) on DocType: '{doctype}'")

    perm = frappe.get_doc({
        "doctype": "Custom DocPerm",
        "parent": doctype,
        "parenttype": "DocType",
        "parentfield": "permissions",
        "role": role,
        "permlevel": permlevel
    })

    for p in perms:
        perm.set(p, 1)

    perm.insert(ignore_permissions=True)
    print(f"Inserted new permissions for Role: '{role}' (Level {permlevel}) on DocType: '{doctype}' with perms: {perms}")


def setup_permissions():
    permissions = [
        # Material Request
        ("Material Request", "Field User", ["read", "write", "create", "submit"], 0),
        ("Material Request", "Stock Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Material Request", "Stock User", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Material Request", "Purchase Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Material Request", "Purchase User", ["read", "write", "create", "submit", "cancel", "amend"], 0),

        # Request for Quotation
        ("Request for Quotation", "Purchase Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Request for Quotation", "Purchase Manager", ["read", "write"], 1),
        ("Request for Quotation", "Vendor Technician", ["read", "write"], 0),
        ("Request for Quotation", "Purchase User", ["read", "write", "create", "amend"], 0),
        ("Request for Quotation", "Stock User", ["read"], 0),
        ("Request for Quotation", "Manufacturing Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Request for Quotation", "All", ["read"], 1),

        # Supplier Quotation
        ("Supplier Quotation", "Purchase Manager", ["read", "write", "cancel", "submit", "create", "amend"], 0),
        ("Supplier Quotation", "Purchase Manager", ["read", "write"], 1),
        ("Supplier Quotation", "Vendor Admin", ["read", "write", "create", "cancel", "submit"], 0),
        ("Supplier Quotation", "Purchase User", ["read", "write", "create", "submit", "amend"], 0),
        ("Supplier Quotation", "Stock User", ["read"], 0),
        ("Supplier Quotation", "Manufacturing Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),

        # Purchase Order
        ("Purchase Order", "Purchase Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Purchase Order", "Purchase Manager", ["read", "write"], 1),
        ("Purchase Order", "Vendor Technician", ["read"], 0),
        ("Purchase Order", "Vendor Admin", ["read"], 0),
        ("Purchase Order", "Internal Technician", ["read"], 0),
        ("Purchase Order", "Purchase User", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Purchase Order", "Stock User", ["read"], 0),

        # Purchase Receipt
        ("Purchase Receipt", "Quality Manager", ["read", "write", "submit"], 0),
        ("Purchase Receipt", "Stock Manager", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Purchase Receipt", "Stock Manager", ["read", "write"], 1),
        ("Purchase Receipt", "Purchase User", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Purchase Receipt", "Stock User", ["read", "write", "create", "submit", "cancel", "amend"], 0),
        ("Purchase Receipt", "Accounts User", ["read"], 0),

        # Asset Capitalization
        ("Asset Capitalization", "Internal Technician", ["read", "write", "submit"], 0),
        ("Asset Capitalization", "Vendor Technician", ["read", "write", "create", "submit"], 0),

        # Asset Maintenance Log
        ("Asset Maintenance Log", "Internal Technician", ["read", "write", "create", "submit"], 0),
    ]

    for doctype, role, perms, level in permissions:
        add_permission(doctype, role, perms, level)

def after_install():
    create_roles()
    setup_permissions()

def after_migrate():
    create_roles()
    setup_permissions()