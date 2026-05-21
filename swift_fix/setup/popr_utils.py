import frappe
import qrcode
import io
from swift_fix.setup.mr_utils import _change_mr_status

def on_po_submit(doc, method):
	# Check if there are any Purchase Receipts generated for this PO
	pr_exists = frappe.db.exists("Purchase Receipt Item", {
		"purchase_order": doc.name,
		"docstatus": ["!=", 2]
	})
	# Check if there are any Assets generated for this PO
	asset_exists = frappe.db.exists("Asset", {
		"custom_purchase_order": doc.name,
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

def on_asset_capitalization_submit(doc, method):
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
			pr = frappe.db.get_value(
				"Purchase Receipt Item",
				item.pr_detail,
				"parent"
			)
			capitalization = frappe.db.exists(
				"Asset Capitalization",
				{"purchase_receipt": pr}
			)
			if not capitalization:
				frappe.throw(
					"Asset must be capitalized before creating Purchase Invoice."
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
	doc.db_set("asset_qr_code", file_doc.file_url)

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