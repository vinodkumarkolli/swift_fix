import frappe
import qrcode
import io
from swift_fix.setup.mr_utils import _change_mr_status

def validate_pr(doc, method):
	# Every Purchase Receipt Item must have a linked Purchase Order
	for item in doc.get("items", []):
		if not item.get("purchase_order"):
			frappe.throw(
				frappe._("Row #{0}: Purchase Order is mandatory for Purchase Receipt Item").format(item.idx)
			)

	# Quality Control validations on the parent Purchase Receipt
	if not doc.get("custom_qc_length") or not doc.get("custom_qc_height") or not doc.get("custom_qc_depth"):
		frappe.throw(frappe._("QC Dimensions are mandatory"))

	if not doc.get("custom_qc_photo_1"):
		frappe.throw(frappe._("QC Photos are mandatory"))

	if not doc.get("custom_qc_notes") or not doc.get("custom_qc_notes").strip():
		frappe.throw(frappe._("QC Notes are mandatory"))

@frappe.whitelist()
def create_pr(po_doc, warehouse=None, company=None, qc=None):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	po_name = po_doc
	if not isinstance(po_doc, str):
		po_name = po_doc.name

	# Make Purchase Receipt from Purchase Order
	pr = make_purchase_receipt(po_name)

	# Set company if provided
	if company:
		pr.company = company

	# Set warehouse on all items if provided, and map asset_location from linked Material Request
	for item in pr.get("items", []):
		if warehouse:
			item.warehouse = warehouse

		# Resolve asset_location from linked Material Request (if any)
		mr_name = item.get("material_request")
		if not mr_name and item.get("purchase_order_item"):
			mr_name = frappe.db.get_value("Purchase Order Item", item.get("purchase_order_item"), "material_request")

		mr_location = None
		if mr_name:
			mr_location = frappe.db.get_value("Material Request", mr_name, "custom_location")

		if mr_location:
			item.asset_location = mr_location
		else:
			# Fallback: use first available Location in the system
			item.asset_location = frappe.db.get_value("Location", {}, "name")

	# Load and set QC details
	import json
	if isinstance(qc, str):
		try:
			qc = json.loads(qc)
		except Exception:
			frappe.throw(frappe._("Invalid JSON format for qc"))

	if isinstance(qc, dict):
		for field in [
			"custom_qc_length",
			"custom_qc_height",
			"custom_qc_depth",
			"custom_qc_photo_1",
			"custom_qc_photo_2",
			"custom_qc_notes"
		]:
			if field in qc:
				pr.set(field, qc[field])

	# Save and submit the Purchase Receipt
	pr.insert()
	pr.submit()

	return pr.name

def on_po_submit(doc, method):
	# Check if there are any Purchase Receipts generated for this PO
	pr_exists = frappe.db.exists("Purchase Receipt Item", {
		"purchase_order": doc.name,
		"docstatus": ["!=", 2]
	})
	# Check if there are any Assets generated for this PO (via Purchase Receipt Items)
	pr_items = frappe.get_all(
		"Purchase Receipt Item",
		filters={"purchase_order": doc.name, "docstatus": ["!=", 2]},
		fields=["name"]
	)
	pr_item_names = [item.name for item in pr_items]
	asset_exists = False
	if pr_item_names:
		asset_exists = frappe.db.exists("Asset", {
			"purchase_receipt_item": ["in", pr_item_names],
			"docstatus": ["!=", 2]
		})

	if not pr_exists and not asset_exists:
		# Find unique linked Material Requests from PO items
		mr_names = {item.material_request for item in doc.items if item.material_request}
		for mr_name in mr_names:
			_change_mr_status(
				mr_name,
				"Under Process",
				reason=f"Status updated to Under Process upon submission of Purchase Order {doc.name}",
				ignore_permissions=True
			)

def on_pr_submit(doc, method):
	# Find unique Purchase Orders referenced in the Purchase Receipt items
	po_names = {item.purchase_order for item in doc.items if item.purchase_order}
	for po_name in po_names:
		# Force PO status to Completed
		frappe.db.set_value("Purchase Order", po_name, "status", "Completed")

		# Find unique linked Material Requests from PO items
		po_items = frappe.get_all(
			"Purchase Order Item",
			filters={"parent": po_name},
			fields=["material_request"]
		)
		mr_names = {item.material_request for item in po_items if item.material_request}
		for mr_name in mr_names:
			_change_mr_status(
				mr_name,
				"Item Received",
				reason=f"Status updated to Item Received as Purchase Order {po_name} is completed via Purchase Receipt {doc.name}",
				ignore_permissions=True
			)

	# Generate QR code for all auto-created assets linked to this Purchase Receipt
	assets = frappe.get_all("Asset", filters={"purchase_receipt": doc.name})
	for asset in assets:
		asset_doc = frappe.get_doc("Asset", asset.name)
		asset_doc.asset_type = "Composite Asset"
		asset_doc.save()
		generate_asset_qr(asset_doc)

def on_asset_capitalization_submit(doc, method):
	if doc.target_asset:
		asset = frappe.get_doc("Asset", doc.target_asset)
		if not asset.available_for_use_date:
			asset.available_for_use_date = doc.posting_date or frappe.utils.nowdate()
		for row in asset.finance_books:
			if not row.depreciation_start_date or frappe.utils.getdate(row.depreciation_start_date) < frappe.utils.getdate(asset.available_for_use_date):
				row.depreciation_start_date = frappe.utils.get_last_day(asset.available_for_use_date)
		if asset.docstatus == 0:
			asset.flags.ignore_permissions = True
			asset.save()

	if doc.custom_purchase_order:
		# Find unique linked Material Requests from PO items
		po_items = frappe.get_all(
			"Purchase Order Item",
			filters={"parent": doc.custom_purchase_order},
			fields=["material_request"]
		)
		mr_names = {item.material_request for item in po_items if item.material_request}
		for mr_name in mr_names:
			_change_mr_status(
				mr_name,
				"Asset Capitalised",
				reason=f"Status updated to Asset Capitalised upon submission of Asset Capitalization {doc.name}",
				ignore_permissions=True
			)

def check_purchase_invoice_capitalization(doc, method=None):
	for item in doc.items:
		if item.pr_detail:
			is_fixed_asset = frappe.db.get_value(
				"Purchase Receipt Item",
				item.pr_detail,
				"is_fixed_asset"
			)
			if is_fixed_asset:
				assets = frappe.get_all(
					"Asset",
					filters={"purchase_receipt_item": item.pr_detail, "docstatus": ["!=", 2]},
					fields=["name", "docstatus"]
				)
				if not assets:
					frappe.throw(
						f"Asset record not found for Purchase Receipt Item {item.pr_detail}. "
						"It must be created and capitalized before creating Purchase Invoice."
					)
				for asset in assets:
					if asset.docstatus != 1:
						frappe.throw(
							f"Asset {asset.name} must be capitalized before creating Purchase Invoice."
						)

def generate_asset_qr(doc, method=None):
	# Generate Maintenance Log URL with asset parameter
	qr_data = frappe.utils.get_url() + "/app/asset-maintenance-log/new-asset-maintenance-log?asset=" + doc.name

	# Create QR image
	img = qrcode.make(qr_data)

	buffer = io.BytesIO()
	img.save(buffer, format="PNG")

	# Create file attachment
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": f"{doc.name}_qr.png",
		"content": buffer.getvalue(),
		"attached_to_doctype": "Asset",
		"attached_to_name": doc.name
	})

	file_doc.insert(ignore_permissions=True)

	# Save QR image link to asset using db_set to avoid recursive save hooks
	doc.db_set("custom_asset_qr_code", file_doc.file_url)

def create_purchase_receipt_serial_nos(doc, method=None):
	for item in doc.items:
		if not item.serial_no:
			serial_no_val = f"{item.item_code}-{frappe.generate_hash(length=8).upper()}"
			serial = frappe.get_doc({
				"doctype": "Serial No",
				"serial_no": serial_no_val,
				"item_code": item.item_code,
				"company": doc.company,
				"status": "Active"
			})
			serial.insert(ignore_permissions=True)
			item.db_set("serial_no", serial.name)

def create_distribution_asset_shortcut(doc, method=None):
	# DEPRECATED: This shortcut is disabled as it causes circular dependencies with Asset Capitalization
	# which creates a Stock Entry "Material Issue" upon submission.
	pass

@frappe.whitelist()
def get_procurement_details(asset_name):
	# Fetch Asset
	if not frappe.db.exists("Asset", asset_name):
		return ""
	
	asset = frappe.get_doc("Asset", asset_name)
	
	# Fetch Purchase Receipt details
	pr_name = asset.purchase_receipt
	pr_item_name = asset.purchase_receipt_item
	
	pr_doc = None
	pr_item = None
	po_name = None
	po_doc = None
	mr_name = None
	mr_doc = None
	
	if pr_name:
		pr_doc = frappe.get_doc("Purchase Receipt", pr_name)
	if pr_item_name and frappe.db.exists("Purchase Receipt Item", pr_item_name):
		pr_item = frappe.get_doc("Purchase Receipt Item", pr_item_name)
		po_name = pr_item.purchase_order
		mr_name = pr_item.material_request
		# Fallback 1: Resolve Material Request via Purchase Order Item if not set directly on PR Item
		if not mr_name and pr_item.purchase_order_item:
			mr_name = frappe.db.get_value("Purchase Order Item", pr_item.purchase_order_item, "material_request")
	
	# Fallback 2: Resolve Material Request via Purchase Order items if po_name is set but mr_name is still missing
	if po_name and not mr_name:
		po_items = frappe.get_all(
			"Purchase Order Item",
			filters={"parent": po_name, "material_request": ["!=", ""]},
			fields=["material_request"],
			limit=1
		)
		if po_items:
			mr_name = po_items[0].material_request
			
	if po_name:
		po_doc = frappe.get_doc("Purchase Order", po_name)
	if mr_name:
		mr_doc = frappe.get_doc("Material Request", mr_name)
	
	# If none of MR, PO, PR are found, return a clean message
	if not pr_doc and not po_doc and not mr_doc:
		return f"""
			<div class="analysis-container">
				<div class="no-data">{frappe._("No procurement history found for this Asset.")}</div>
			</div>
		"""
	
	def get_form_link(doctype, name):
		return f"/app/{frappe.scrub(doctype).replace('_', '-')}/{name}"
	
	# Helper for badge rendering
	def get_badge_html(docstatus, status=None):
		if status:
			lbl = status
		else:
			lbl = "Draft" if docstatus == 0 else "Submitted" if docstatus == 1 else "Cancelled"
			
		bg = "#f1f5f9"
		fg = "#475569"
		if lbl in ["Shortlisted", "Completed", "Active", "Asset Capitalised", "Capitalized"]:
			bg = "#d1fae5"
			fg = "#065f46"
		elif lbl in ["Cancelled", "Closed"]:
			bg = "#fee2e2"
			fg = "#991b1b"
		elif lbl in ["Held"]:
			bg = "#fef3c7"
			fg = "#92400e"
		elif lbl in ["Submitted"]:
			bg = "#dbeafe"
			fg = "#1e40af"
		elif lbl in ["Under Process", "Item Received", "Received"]:
			bg = "#e0f2fe"
			fg = "#0369a1"
		elif lbl in ["Draft"]:
			bg = "#f1f5f9"
			fg = "#475569"
			
		return f'<span class="badge" style="background-color: {bg}; color: {fg}; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center;">{lbl}</span>'

	# Let's generate flow cards
	mr_html = ""
	if mr_doc:
		mr_link = get_form_link("Material Request", mr_doc.name)
		status_badge = get_badge_html(mr_doc.docstatus, mr_doc.get("custom_processing_status") or mr_doc.status)
		date_str = frappe.utils.format_date(mr_doc.transaction_date) if mr_doc.transaction_date else "-"
		mr_html = f"""
			<div class="summary-card">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">1. Material Request</div>
				<div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 6px;">
					<a href="{mr_link}" class="analysis-link">{mr_doc.name}</a>
				</div>
				<div style="font-size: 0.85rem; color: var(--text-color, #334155); margin-bottom: 8px;">
					<strong>{frappe._("Date")}:</strong> {date_str}
				</div>
				<div>{status_badge}</div>
			</div>
		"""
	else:
		mr_html = f"""
			<div class="summary-card" style="border-style: dashed; opacity: 0.6;">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">1. Material Request</div>
				<div style="font-size: 0.85rem; color: var(--text-muted, #64748b); font-style: italic;">
					{frappe._("Not linked to a Material Request")}
				</div>
			</div>
		"""

	po_html = ""
	if po_doc:
		po_link = get_form_link("Purchase Order", po_doc.name)
		status_badge = get_badge_html(po_doc.docstatus, po_doc.status)
		date_str = frappe.utils.format_date(po_doc.transaction_date) if po_doc.transaction_date else "-"
		amount_str = frappe.utils.fmt_money(po_doc.grand_total, currency=po_doc.currency)
		po_html = f"""
			<div class="summary-card">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">2. Purchase Order</div>
				<div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 6px;">
					<a href="{po_link}" class="analysis-link">{po_doc.name}</a>
				</div>
				<div style="font-size: 0.85rem; color: var(--text-color, #334155); margin-bottom: 4px;">
					<strong>{frappe._("Date")}:</strong> {date_str}
				</div>
				<div style="font-size: 0.85rem; color: var(--text-color, #334155); margin-bottom: 8px;">
					<strong>{frappe._("Total")}:</strong> {amount_str}
				</div>
				<div>{status_badge}</div>
			</div>
		"""
	else:
		po_html = f"""
			<div class="summary-card" style="border-style: dashed; opacity: 0.6;">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">2. Purchase Order</div>
				<div style="font-size: 0.85rem; color: var(--text-muted, #64748b); font-style: italic;">
					{frappe._("Not linked to a Purchase Order")}
				</div>
			</div>
		"""

	pr_html = ""
	if pr_doc:
		pr_link = get_form_link("Purchase Receipt", pr_doc.name)
		status_badge = get_badge_html(pr_doc.docstatus, pr_doc.status)
		date_str = frappe.utils.format_date(pr_doc.posting_date) if pr_doc.posting_date else "-"
		pr_html = f"""
			<div class="summary-card">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">3. Purchase Receipt</div>
				<div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 6px;">
					<a href="{pr_link}" class="analysis-link">{pr_doc.name}</a>
				</div>
				<div style="font-size: 0.85rem; color: var(--text-color, #334155); margin-bottom: 8px;">
					<strong>{frappe._("Date")}:</strong> {date_str}
				</div>
				<div>{status_badge}</div>
			</div>
		"""
	else:
		pr_html = f"""
			<div class="summary-card" style="border-style: dashed; opacity: 0.6;">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">3. Purchase Receipt</div>
				<div style="font-size: 0.85rem; color: var(--text-muted, #64748b); font-style: italic;">
					{frappe._("Not linked to a Purchase Receipt")}
				</div>
			</div>
		"""

	ac_docs = frappe.get_all(
		"Asset Capitalization",
		filters={"target_asset": asset.name, "docstatus": ["!=", 2]},
		fields=["name", "posting_date", "docstatus"]
	)
	ac_html = ""
	if ac_docs:
		ac_doc = ac_docs[0]
		ac_link = get_form_link("Asset Capitalization", ac_doc.name)
		status_badge = get_badge_html(ac_doc.docstatus, "Capitalized" if ac_doc.docstatus == 1 else "Draft")
		date_str = frappe.utils.format_date(ac_doc.posting_date) if ac_doc.posting_date else "-"
		ac_html = f"""
			<div class="summary-card">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">4. Asset Capitalization</div>
				<div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 6px;">
					<a href="{ac_link}" class="analysis-link">{ac_doc.name}</a>
				</div>
				<div style="font-size: 0.85rem; color: var(--text-color, #334155); margin-bottom: 8px;">
					<strong>{frappe._("Date")}:</strong> {date_str}
				</div>
				<div>{status_badge}</div>
			</div>
		"""
	else:
		ac_html = f"""
			<div class="summary-card" style="border-style: dashed; opacity: 0.6;">
				<div style="font-size: 0.75rem; color: var(--text-muted, #64748b); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">4. Asset Capitalization</div>
				<div style="font-size: 0.85rem; color: var(--text-muted, #64748b); font-style: italic;">
					{frappe._("Not Capitalized yet")}
				</div>
			</div>
		"""

	html = f"""
		<div class="analysis-container">
			<style>
				.analysis-container {{
					font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
					background-color: var(--card-bg, #ffffff);
					border: 1px solid var(--border-color, #e2e8f0);
					border-radius: 12px;
					padding: 24px;
					margin-top: 15px;
					margin-bottom: 30px;
					box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
				}}
				.analysis-header {{
					display: flex;
					justify-content: space-between;
					align-items: center;
					border-bottom: 2px solid var(--border-color, #e2e8f0);
					padding-bottom: 16px;
					margin-bottom: 20px;
				}}
				.analysis-title {{
					font-size: 1.25rem;
					font-weight: 600;
					color: var(--text-color, #1e293b);
					margin: 0;
				}}
				.analysis-summary {{
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 16px;
					margin-bottom: 24px;
				}}
				.summary-card {{
					background: linear-gradient(135deg, var(--card-bg, #ffffff) 0%, var(--fg-color, #f8fafc) 100%);
					border: 1px solid var(--border-color, #e2e8f0);
					border-radius: 12px;
					padding: 18px;
					text-align: left;
					box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
					transition: transform 0.2s ease, box-shadow 0.2s ease;
				}}
				.summary-card:hover {{
					transform: translateY(-2px);
					box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
				}}
				.analysis-link {{
					color: var(--primary, #1b66ec);
					font-weight: 600;
					text-decoration: none;
					border-bottom: 1px dashed var(--primary, #1b66ec);
					padding-bottom: 1px;
					transition: color 0.15s ease;
				}}
				.analysis-link:hover {{
					color: var(--primary-hover, #0843b8);
					border-bottom-style: solid;
					text-decoration: none;
				}}
			</style>
			
			<div class="analysis-header">
				<h3 class="analysis-title">{frappe._("Asset Procurement Reference Lifecycle")}</h3>
			</div>
			
			<div class="analysis-summary">
				{mr_html}
				{po_html}
				{pr_html}
				{ac_html}
			</div>
		</div>
	"""
	return html