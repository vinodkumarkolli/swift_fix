import frappe

def clean_val(val):
    if isinstance(val, str):
        return val.strip('"').strip("'")
    return val

def has_active_po(mr_name):
    # Find all POs linked to this MR
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"material_request": mr_name},
        fields=["parent"]
    )
    po_names = [item.parent for item in po_items]
    if not po_names:
        return False
        
    # Check if any of these POs is submitted (docstatus == 1) and status is not Closed
    active_pos = frappe.get_all(
        "Purchase Order",
        filters={
            "name": ["in", po_names],
            "docstatus": 1,
            "status": ["not in", ["Closed", "Completed"]]
        },
        limit=1
    )
    return len(active_pos) > 0

def has_completed_po(mr_name):
    # Find all POs linked to this MR
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"material_request": mr_name},
        fields=["parent"]
    )
    po_names = [item.parent for item in po_items if item.parent]
    if not po_names:
        return False
        
    # Check if any of these POs is submitted (docstatus == 1) and status is Completed
    completed_pos = frappe.get_all(
        "Purchase Order",
        filters={
            "name": ["in", po_names],
            "docstatus": 1,
            "status": "Completed"
        },
        limit=1
    )
    return len(completed_pos) > 0

@frappe.whitelist()
def get_mr_status_details(mr_name):
    mr_name = clean_val(mr_name)
    frappe.get_doc("Material Request", mr_name).check_permission("read")
    return {
        "has_active_po": has_active_po(mr_name),
        "has_completed_po": has_completed_po(mr_name)
    }

def _change_mr_status(mr_name, status, reason=None, ignore_permissions=False):
    mr_name = clean_val(mr_name)
    status = clean_val(status)
    reason = clean_val(reason) if reason else None
    
    # Validation: Cancel & Hold are disabled if there is an active PO
    if status in ["Cancelled", "Held"] and has_active_po(mr_name):
        frappe.throw(
            frappe._("Cannot change status to {0} because there is an active Purchase Order linked to this Material Request.").format(status)
        )
        
    mr = frappe.get_doc("Material Request", mr_name)
    if not ignore_permissions:
        mr.check_permission("write")

    mr.db_set("custom_processing_status", status)
    
    if reason:
        comment = frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Material Request",
            "reference_name": mr_name,
            "content": reason
        })
        comment.insert(ignore_permissions=True)
        
    return {"status": "success"}

@frappe.whitelist()
def change_mr_status(mr_name, status, reason=None):
    return _change_mr_status(mr_name, status, reason, ignore_permissions=False)

@frappe.whitelist()
def analyze_mr(mr_name):
    mr_name = clean_val(mr_name)
    mr = frappe.get_doc("Material Request", mr_name)
    mr.check_permission("read")
    location = mr.custom_location
    
    # Fetch Purchase Orders linked to this Material Request
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"material_request": mr_name},
        fields=["parent"]
    )
    po_names = list(set(item.parent for item in po_items if item.parent))
    purchase_orders = []
    if po_names:
        purchase_orders = frappe.get_all(
            "Purchase Order",
            filters={"name": ["in", po_names]},
            fields=["name", "status", "transaction_date", "grand_total"]
        )

    if not location:
        return {
            "material_requests": [],
            "assets": [],
            "purchase_orders": purchase_orders
        }
        
    # Fetch other Material Requests for the same location
    other_mrs = frappe.get_all(
        "Material Request",
        filters={
            "custom_location": location,
            "name": ["!=", mr_name]
        },
        fields=["name", "custom_processing_status"]
    )
    
    mr_names = [mr.name for mr in other_mrs]
    mr_to_caps = get_asset_capitalizations_for_mrs(mr_names)
    
    for mr in other_mrs:
        mr["asset_capitalizations"] = mr_to_caps.get(mr.name, [])
        
    # Fetch Assets associated with the location
    assets = frappe.get_all(
        "Asset",
        filters={
            "location": location
        },
        fields=["name", "asset_name", "status"]
    )
    
    return {
        "material_requests": other_mrs,
        "assets": assets,
        "purchase_orders": purchase_orders
    }

def get_asset_capitalizations_for_mrs(mr_names):
    if not mr_names:
        return {}
    
    # Get Purchase Orders linked to these Material Requests
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"material_request": ["in", mr_names]},
        fields=["parent", "material_request"]
    )
    
    po_to_mr = {}
    for item in po_items:
        po_to_mr.setdefault(item.parent, []).append(item.material_request)
        
    po_names = list(po_to_mr.keys())
    if not po_names:
        return {}
        
    # Get Asset Capitalizations linked to these Purchase Orders
    asset_caps = frappe.get_all(
        "Asset Capitalization",
        filters={"custom_purchase_order": ["in", po_names]},
        fields=["name", "custom_purchase_order"]
    )
    
    mr_to_caps = {}
    for cap in asset_caps:
        mrs = po_to_mr.get(cap.custom_purchase_order, [])
        for mr in mrs:
            mr_to_caps.setdefault(mr, []).append(cap.name)
            
    return mr_to_caps

def validate_mr(doc, method):
    for item in doc.get("items") or []:
        if not item.item_code:
            continue
        is_fixed_asset = frappe.db.get_value("Item", item.item_code, "is_fixed_asset")
        if not is_fixed_asset:
            frappe.throw(
                frappe._("Item {0} must be a Fixed Asset item to be added to a Material Request.").format(item.item_code)
            )