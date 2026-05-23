import frappe

def clean_val(val):
    if isinstance(val, str):
        return val.strip('"').strip("'")
    return val

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
    doc = frappe.get_doc(doctype, docname)
    mrs = []
    
    for item in doc.get("items", []):
        if item.get("material_request"):
            mrs.append(item.material_request)
            
    if not mrs and doctype == "Supplier Quotation":
        rfq_names = set()
        for item in doc.get("items", []):
            if item.get("request_for_quotation"):
                rfq_names.add(item.request_for_quotation)
        for rfq_name in rfq_names:
            rfq_items = frappe.get_all(
                "Request for Quotation Item",
                filters={"parent": rfq_name},
                fields=["material_request"]
            )
            for rfq_item in rfq_items:
                if rfq_item.material_request:
                    mrs.append(rfq_item.material_request)
                    
    unique_mrs = []
    for mr in mrs:
        if mr and mr not in unique_mrs:
            unique_mrs.append(mr)
            
    if not unique_mrs:
        return ""
        
    html_cards = []
    for mr_name in unique_mrs:
        mr_doc = frappe.db.get_value("Material Request", mr_name, ["custom_processing_status", "transaction_date"], as_dict=True)
        if not mr_doc:
            continue
            
        status = mr_doc.custom_processing_status or "Submitted"
        tx_date = mr_doc.transaction_date
        
        badge_bg = '#f1f5f9'
        badge_color = '#475569'
        
        if status == 'Shortlisted':
            badge_bg = '#d1fae5'
            badge_color = '#065f46'
        elif status == 'Cancelled':
            badge_bg = '#fee2e2'
            badge_color = '#991b1b'
        elif status == 'Held':
            badge_bg = '#fef3c7'
            badge_color = '#92400e'
        elif status in ['Submitted', 'Draft']:
            badge_bg = '#dbeafe'
            badge_color = '#1e40af'
        elif status in ['Under Process', 'Item Received']:
            badge_bg = '#e0f2fe'
            badge_color = '#0369a1'
        elif status == 'Asset Capitalised':
            badge_bg = '#f3e8ff'
            badge_color = '#6b21a8'
            
        mr_link = frappe.utils.get_url_to_form('Material Request', mr_name)
        formatted_date = frappe.utils.format_date(tx_date) if tx_date else "-"
        
        card = f"""
        <div class="mr-status-card" style="
            flex: 1 1 calc(50% - 16px);
            min-width: 280px;
            background: linear-gradient(135deg, var(--card-bg, #ffffff) 0%, var(--fg-color, #f8fafc) 100%);
            border: 1px solid var(--border-color, #e2e8f0);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="
                    background-color: var(--primary-light, #e0f2fe);
                    color: var(--primary, #1b66ec);
                    width: 40px;
                    height: 40px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                ">
                    <i class="fa fa-file-text-o"></i>
                </div>
                <div>
                    <div style="font-size: 11px; color: var(--text-muted, #64748b); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Linked Material Request</div>
                    <div style="font-size: 15px; font-weight: 600; margin-bottom: 2px;">
                        <a href="{mr_link}" style="color: var(--primary, #1b66ec); text-decoration: none; border-bottom: 1px dashed var(--primary, #1b66ec); padding-bottom: 1px; transition: color 0.15s ease;">{mr_name}</a>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted, #64748b);">Date: {formatted_date}</div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 11px; color: var(--text-muted, #64748b); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Status</div>
                <span class="badge" style="
                    display: inline-flex;
                    align-items: center;
                    padding: 6px 12px;
                    border-radius: 9999px;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: {badge_bg};
                    color: {badge_color};
                ">{status}</span>
            </div>
        </div>
        """
        html_cards.append(card)
        
    container_html = f"""
    <div class="mr-cards-container" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        gap: 16px;
        margin-top: 10px;
        margin-bottom: 20px;
        width: 100%;
    ">
        {"".join(html_cards)}
    </div>
    """
    return container_html

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