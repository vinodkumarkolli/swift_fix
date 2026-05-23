import frappe
from swift_fix.setup.utils import clean_val

@frappe.whitelist()
def rfq_change_recce_status(doc,to_state):
    doc = clean_val(doc)
    to_state = clean_val(to_state)
    ## fetch the request for quotation document
    rfq = frappe.get_doc("Request for Quotation", doc)
    rfq.check_permission("write")
    ## check the docstatus =1. if yes, modify the custom_recce_status to `to_state` and validate if `to_state` is any of following
    ## ["Recced","Validated","Invalidated","Not_Recced"]
    if rfq.docstatus == 1 and to_state in ["Validated","Invalidated"]:
        rfq.set("custom_recce_status", to_state)
        rfq.save(ignore_permissions=True)
        frappe.db.commit()
        # Return Success message
    else:
        frappe.throw("Invalid state")

@frappe.whitelist()
def rfq_update_dimensions(doc,user,length,height,depth):
    doc = clean_val(doc)
    length = clean_val(length)
    height = clean_val(height)
    depth = clean_val(depth)
    ## fetch the request for quotation document
    rfq = frappe.get_doc("Request for Quotation", doc)
    rfq.check_permission("write")
    ## check the docstatus =1. if yes, modify the custom_recce_length, custom_recce_height, custom_recce_depth to `length`,`height`,`depth` and validate if 
    if rfq.docstatus == 1:
        rfq.set("custom_recce_length", frappe.utils.flt(length))
        rfq.set("custom_recce_height", frappe.utils.flt(height))
        rfq.set("custom_recce_depth", frappe.utils.flt(depth))
        rfq.set("custom_recced_timestamp", frappe.utils.now_datetime())
        rfq.set("custom_recce_done_by", user)
        rfq.set("custom_recce_status","Recced")
        rfq.save(ignore_permissions=True)
        frappe.db.commit()
    else:
        frappe.throw("Invalid state")

def save_image_from_url(image_url, doctype, docname, fieldname):
    if not image_url:
        return None

    # If it is already a local path, just return it
    if image_url.startswith("/files/") or image_url.startswith("/private/files/"):
        return image_url

    # Check if a File record for this URL and document already exists to prevent duplicate attachments
    existing_file = frappe.db.get_value("File", {
        "file_url": image_url,
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "attached_to_field": fieldname
    }, "file_url")

    if existing_file:
        return existing_file

    # Create a new File document pointing to the S3 / remote URL
    file_name = image_url.split("/")[-1].split("?")[0]
    if not file_name:
        file_name = f"recce_{fieldname}"

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_url": image_url,
        "file_name": file_name,
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "attached_to_field": fieldname
    })
    file_doc.insert(ignore_permissions=True)

    return file_doc.file_url

@frappe.whitelist()
def rfq_update_dimensions_with_images(doc, user, length, height, depth, image1_url=None, image2_url=None):
    doc = clean_val(doc)
    length = clean_val(length)
    height = clean_val(height)
    depth = clean_val(depth)
    image1_url = clean_val(image1_url)
    image2_url = clean_val(image2_url)
    ## fetch the request for quotation document
    rfq = frappe.get_doc("Request for Quotation", doc)
    rfq.check_permission("write")

    ## check the docstatus = 1. if yes, modify dimensions and photos
    if rfq.docstatus == 1:
        # Save S3 image URLs to Frappe File attachments and get file URLs
        #convert length, height, depth to float before pushing
        rfq.set("custom_recce_length", frappe.utils.flt(length))
        rfq.set("custom_recce_height", frappe.utils.flt(height))
        rfq.set("custom_recce_depth", frappe.utils.flt(depth))
        rfq.set("custom_recced_timestamp", frappe.utils.now_datetime())
        rfq.set("custom_recce_done_by", user)
        if image1_url:
            saved_image1_url = save_image_from_url(image1_url, "Request for Quotation", doc, "custom_recce_photo_1")
            rfq.set("custom_recce_photo_1", saved_image1_url)
        if image2_url:
            saved_image2_url = save_image_from_url(image2_url, "Request for Quotation", doc, "custom_recce_photo_2")
            rfq.set("custom_recce_photo_2", saved_image2_url)
        rfq.set("custom_recce_status", "Recced")
        rfq.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": "success",
            "message": "RFQ dimensions and images updated successfully"
        }
    else:
        frappe.throw("Invalid state")

@frappe.whitelist()
def get_linked_mr_html(doctype, docname):
    from swift_fix.setup.utils import get_asset_html
    return get_asset_html(doctype, docname)

def validate_rfq(doc, method):
    unique_mrs = []
    for item in doc.get("items", []):
        if item.get("material_request") and item.material_request not in unique_mrs:
            unique_mrs.append(item.material_request)
            
    if not unique_mrs:
        frappe.throw(frappe._("Please link at least one Material Request in the items table."))
        
    for mr_name in unique_mrs:
        mr_status = frappe.db.get_value("Material Request", mr_name, "custom_processing_status")
        if mr_status != "Shortlisted":
            frappe.throw(
                frappe._("Request for Quotation cannot be saved. The linked Material Request {0} must be in 'Shortlisted' status (current status: {1}).").format(
                    mr_name, mr_status or "None"
                )
            )

def on_rfq_submit(doc, method):
    unique_mrs = []
    for item in doc.get("items", []):
        if item.get("material_request") and item.material_request not in unique_mrs:
            unique_mrs.append(item.material_request)
            
    for mr_name in unique_mrs:
        mr = frappe.get_doc("Material Request", mr_name)
        mr.add_comment("Comment", text="A Quotation is requested from Vendor and Recce Process is in Progress")

@frappe.whitelist()
def get_mr_flow_details(mr_name):
    from swift_fix.setup.utils import get_historic_flow_details
    return get_historic_flow_details(mr_name)