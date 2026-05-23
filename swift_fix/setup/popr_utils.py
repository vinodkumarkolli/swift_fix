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

def validate_asset_capitalization(doc, method=None):
	if not doc.get("target_asset") and doc.get("target_item_code"):
		is_fixed_asset = frappe.db.get_value("Item", doc.get("target_item_code"), "is_fixed_asset")
		if is_fixed_asset:
			if not doc.get("target_asset_location"):
				frappe.throw(frappe._("Target Asset Location is mandatory for Asset Capitalization."))
			
			# Create draft asset
			asset = frappe.get_doc({
				"doctype": "Asset",
				"item_code": doc.get("target_item_code"),
				"asset_name": doc.get("target_asset_name") or doc.get("target_item_code"),
				"company": doc.company,
				"location": doc.get("target_asset_location"),
				"purchase_date": doc.posting_date or frappe.utils.nowdate(),
				"available_for_use_date": doc.posting_date or frappe.utils.nowdate(),
				"asset_type": "Composite Asset",
				"asset_quantity": 1,
				"purchase_amount": 0,
				"net_purchase_amount": 0,
			})
			asset.flags.ignore_permissions = True
			asset.insert()
			doc.target_asset = asset.name
			doc.target_asset_name = asset.asset_name

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
			asset.submit()

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

def on_asset_capitalization_cancel(doc, method):
	if doc.target_asset:
		asset = frappe.get_doc("Asset", doc.target_asset)
		if asset.docstatus == 1:
			asset.flags.ignore_permissions = True
			asset.cancel()

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
	from swift_fix.setup.utils import get_procurement_details as utils_get_procurement_details
	return utils_get_procurement_details(asset_name)