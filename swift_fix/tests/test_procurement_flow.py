# Copyright (c) 2026, Vinod Kumar K and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from swift_fix.setup.mr_utils import change_mr_status, get_mr_status_details, analyze_mr
from swift_fix.setup.popr_utils import on_po_submit, on_pr_submit, on_asset_capitalization_submit

class TestProcurementFlow(IntegrationTestCase):
	def setUp(self):
		# Setup prerequisites
		self.company = "Sravi Enterprises - Assets Kolapakkam"
		self.warehouse = "Stores - SE-AK"
		self.item_code = "MBLIT"
		self.supplier = "G & JC Signage"
		self.cost_center = "Main - SE-AK"
		self.expense_account = "Capital Equipment - SE-AK"
		self.location = "Test Location"
		self.raised_by = "Administrator"

		# Ensure Company exists
		if not frappe.db.exists("Company", self.company):
			frappe.get_doc({
				"doctype": "Company",
				"company_name": self.company,
				"default_currency": "INR",
				"country": "India"
			}).insert(ignore_permissions=True)

		# Ensure Warehouse exists
		if not frappe.db.exists("Warehouse", self.warehouse):
			parent_warehouse = frappe.db.get_value("Warehouse", {"is_group": 1, "company": self.company})
			frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": "Stores",
				"company": self.company,
				"parent_warehouse": parent_warehouse
			}).insert(ignore_permissions=True)

		# Ensure Asset Category exists
		self.asset_category = "Capital Equipment"
		if not frappe.db.exists("Asset Category", self.asset_category):
			frappe.get_doc({
				"doctype": "Asset Category",
				"asset_category_name": self.asset_category,
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 12,
				"enable_cwip_accounting": 0,
				"accounts": [{
					"company_name": self.company,
					"fixed_asset_account": "Capital Equipment - SE-AK",
					"accumulated_depreciation_account": "Accumulated Depreciations - SE-AK",
					"depreciation_expense_account": "Depreciation - SE-AK"
				}]
			}).insert(ignore_permissions=True)

		# Ensure Item exists
		if not frappe.db.exists("Item", self.item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": self.item_code,
				"item_name": "Mounting Backlit",
				"item_group": "Consumable",
				"stock_uom": "Square Foot",
				"is_fixed_asset": 1,
				"is_stock_item": 0,
				"auto_create_assets": 1,
				"asset_category": self.asset_category,
				"asset_naming_series": "ACC-ASS-.YYYY.-"
			}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Item", self.item_code, {
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": self.asset_category,
				"asset_naming_series": "ACC-ASS-.YYYY.-"
			})

		# Ensure Supplier exists
		if not frappe.db.exists("Supplier", self.supplier):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": self.supplier,
				"supplier_type": "Company"
			}).insert(ignore_permissions=True)

		# Ensure Location exists
		if not frappe.db.exists("Location", self.location):
			frappe.get_doc({
				"doctype": "Location",
				"location_name": self.location
			}).insert(ignore_permissions=True)

		# Ensure Asset Received But Not Billed account exists and is configured
		self.asset_received_account = "Asset Received But Not Billed - SE-AK"
		if not frappe.db.exists("Account", self.asset_received_account):
			frappe.get_doc({
				"doctype": "Account",
				"account_name": "Asset Received But Not Billed",
				"parent_account": "Stock Liabilities - SE-AK",
				"account_type": "Asset Received But Not Billed",
				"company": self.company,
				"is_group": 0
			}).insert(ignore_permissions=True)
		
		# Set it as default on Company
		frappe.db.set_value("Company", self.company, "asset_received_but_not_billed", self.asset_received_account)

		# Ensure Service Item exists
		self.service_item = "Installation Service"
		if not frappe.db.exists("Item", self.service_item):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": self.service_item,
				"item_name": "Installation Service",
				"item_group": "Consumable",
				"stock_uom": "Nos",
				"is_fixed_asset": 0,
				"is_stock_item": 0
			}).insert(ignore_permissions=True)

	def test_01_mr_fixed_asset_validation(self):
		# Set is_fixed_asset to 0 on Item, expect validation to fail when creating MR
		frappe.db.set_value("Item", self.item_code, "is_fixed_asset", 0)
		
		mr_invalid = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		
		self.assertRaises(frappe.ValidationError, mr_invalid.insert)
		
		# Set is_fixed_asset to 1 on Item, creation should succeed
		frappe.db.set_value("Item", self.item_code, "is_fixed_asset", 1)
		mr_valid = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr_valid.insert()
		mr_valid.submit()
		self.assertEqual(mr_valid.custom_processing_status, "Submitted")

	def test_02_rfq_submit_restriction_and_dimensions(self):
		frappe.db.set_value("Item", self.item_code, "is_fixed_asset", 1)
		
		# Create MR
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert()
		mr.submit()
		
		# Try to create RFQ when MR is in "Submitted" status (not Shortlisted).
		# RFQ submit/save validation should fail.
		rfq = frappe.get_doc({
			"doctype": "Request for Quotation",
			"company": self.company,
			"custom_request_details": mr.name,
			"suppliers": [{"supplier": self.supplier}],
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test request description"
			}]
		})
		self.assertRaises(frappe.ValidationError, rfq.insert)

		# Shortlist MR
		change_mr_status(mr.name, "Shortlisted")
		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Shortlisted")
		
		# Now RFQ insert/save should succeed
		rfq.insert()
		rfq.submit()
		
		# Check if comment is added to MR
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "Material Request",
			"reference_name": mr.name
		}, fields=["content"], order_by="creation desc")
		self.assertTrue(any("A Quotation is requested from Vendor and Recce Process is in Progress" in c.content for c in comments))

	def test_03_po_submit_flow(self):
		frappe.db.set_value("Item", self.item_code, "is_fixed_asset", 1)
		
		# Create & Shortlist MR
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert()
		mr.submit()
		change_mr_status(mr.name, "Shortlisted")
		
		# Create Purchase Order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": self.supplier,
			"company": self.company,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"material_request": mr.name,
				"warehouse": self.warehouse
			}]
		})
		po.insert()
		po.submit()
		
		# Verify MR status changed to "Under Process"
		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Under Process")
		
		# Verify comment added to MR
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "Material Request",
			"reference_name": mr.name
		}, fields=["content"], order_by="creation desc")
		self.assertTrue(any(f"Status updated to Under Process upon submission of Purchase Order {po.name}" in c.content for c in comments))

	def test_04_pr_and_asset_capitalization_flow(self):
		frappe.db.set_value("Item", self.item_code, "is_fixed_asset", 1)
		
		# Create & Shortlist MR
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert()
		mr.submit()
		change_mr_status(mr.name, "Shortlisted")
		
		# Create & Submit Purchase Order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": self.supplier,
			"company": self.company,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"material_request": mr.name,
				"warehouse": self.warehouse
			}]
		})
		po.insert()
		po.submit()
		
		# Create & Submit Purchase Receipt
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": po.name,
				"purchase_order_item": po.items[0].name,
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		pr.insert()
		pr.submit()
		
		# Verify Purchase Order status is now Completed
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "Completed")
		
		# Verify MR status is "Item Received"
		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Item Received")
		
		# Verify comment added
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "Material Request",
			"reference_name": mr.name
		}, fields=["content"], order_by="creation desc")
		self.assertTrue(any(f"Status updated to Item Received as Purchase Order {po.name} is completed via Purchase Receipt {pr.name}" in c.content for c in comments))

		# Find the asset created via PR
		assets = frappe.get_all("Asset", filters={"purchase_receipt": pr.name})
		self.assertTrue(len(assets) > 0)
		asset_name = assets[0].name

		# Mark the asset as composite so it can be capitalized
		frappe.db.set_value("Asset", asset_name, "asset_type", "Composite Asset")

		# Create & Submit Asset Capitalization
		ac = frappe.get_doc({
			"doctype": "Asset Capitalization",
			"company": self.company,
			"custom_purchase_order": po.name,
			"target_asset": asset_name,
			"target_item_code": self.item_code,
			"target_asset_location": self.location,
			"posting_date": frappe.utils.nowdate(),
			"service_items": [{
				"item_code": self.service_item,
				"qty": 1,
				"uom": "Nos",
				"rate": 100.0,
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		ac.insert()
		ac.submit()
		
		# Verify MR status is "Asset Capitalised"
		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Asset Capitalised")
		
		# Verify comment added
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "Material Request",
			"reference_name": mr.name
		}, fields=["content"], order_by="creation desc")
		self.assertTrue(any(f"Status updated to Asset Capitalised upon submission of Asset Capitalization {ac.name}" in c.content for c in comments))

		# Verify get_mr_status_details & analyze_mr
		status_details = get_mr_status_details(mr.name)
		self.assertFalse(status_details["has_active_po"])
		self.assertTrue(status_details["has_completed_po"])
		
		analysis = analyze_mr(mr.name)
		self.assertEqual(len(analysis["purchase_orders"]), 1)
		self.assertEqual(analysis["purchase_orders"][0]["name"], po.name)
		self.assertEqual(analysis["purchase_orders"][0]["status"], "Completed")

	def test_05_permission_checks(self):
		frappe.db.set_value("Item", self.item_code, "is_fixed_asset", 1)
		
		# Create a Material Request
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert()
		mr.submit()

		# Shortlist MR
		change_mr_status(mr.name, "Shortlisted")
		
		# Create RFQ
		rfq = frappe.get_doc({
			"doctype": "Request for Quotation",
			"company": self.company,
			"custom_request_details": mr.name,
			"suppliers": [{"supplier": self.supplier}],
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test request description"
			}]
		})
		rfq.insert()
		rfq.submit()

		# 1. Create a test user with no roles
		no_role_user = "test_norole@example.com"
		if not frappe.db.exists("User", no_role_user):
			u = frappe.get_doc({
				"doctype": "User",
				"email": no_role_user,
				"first_name": "No Role User",
				"send_welcome_email": 0
			})
			u.insert(ignore_permissions=True)

		# 2. Create a test user with Field User role
		field_user = "test_fielduser@example.com"
		if not frappe.db.exists("User", field_user):
			u = frappe.get_doc({
				"doctype": "User",
				"email": field_user,
				"first_name": "Field User",
				"send_welcome_email": 0,
				"roles": [{"role": "Field User"}]
			})
			u.insert(ignore_permissions=True)

		# 3. Create a test user with Vendor Technician role
		vendor_tech = "test_vendortech@example.com"
		if not frappe.db.exists("User", vendor_tech):
			u = frappe.get_doc({
				"doctype": "User",
				"email": vendor_tech,
				"first_name": "Vendor Tech User",
				"send_welcome_email": 0,
				"roles": [{"role": "Vendor Technician"}]
			})
			u.insert(ignore_permissions=True)

		# Save current user to restore later
		original_user = frappe.session.user

		try:
			# Test with Guest user
			frappe.set_user("Guest")
			
			from swift_fix.setup.rfq_update import rfq_change_recce_status, rfq_update_dimensions, rfq_update_dimensions_with_images

			# Guest should fail on MR APIs
			self.assertRaises(frappe.PermissionError, get_mr_status_details, mr.name)
			self.assertRaises(frappe.PermissionError, change_mr_status, mr.name, "Cancelled")
			self.assertRaises(frappe.PermissionError, analyze_mr, mr.name)

			# Guest should fail on RFQ APIs
			self.assertRaises(frappe.PermissionError, rfq_change_recce_status, rfq.name, "Validated")
			self.assertRaises(frappe.PermissionError, rfq_update_dimensions, rfq.name, "guest_user", 10.0, 10.0, 10.0)
			self.assertRaises(frappe.PermissionError, rfq_update_dimensions_with_images, rfq.name, "guest_user", 10.0, 10.0, 10.0)

			# Test with No-Role user
			frappe.set_user(no_role_user)
			self.assertRaises(frappe.PermissionError, get_mr_status_details, mr.name)
			self.assertRaises(frappe.PermissionError, change_mr_status, mr.name, "Cancelled")
			self.assertRaises(frappe.PermissionError, analyze_mr, mr.name)
			self.assertRaises(frappe.PermissionError, rfq_change_recce_status, rfq.name, "Validated")

			# Test with Field User
			frappe.set_user(field_user)
			# Field User has write access to MR, so MR status change should succeed
			change_mr_status(mr.name, "Held")
			mr.reload()
			self.assertEqual(mr.custom_processing_status, "Held")

			# Field User does not have write access to RFQ, so RFQ status change should fail
			self.assertRaises(frappe.PermissionError, rfq_change_recce_status, rfq.name, "Validated")

			# Test with Vendor Technician
			frappe.set_user(vendor_tech)
			# Vendor Technician has write access to RFQ, so RFQ status change and dimensions update should succeed
			rfq_change_recce_status(rfq.name, "Validated")
			rfq.reload()
			self.assertEqual(rfq.custom_recce_status, "Validated")

			rfq_update_dimensions(rfq.name, vendor_tech, 12.0, 14.0, 16.0)
			rfq.reload()
			self.assertEqual(rfq.custom_recce_length, 12.0)
			self.assertEqual(rfq.custom_recce_status, "Recced")

			# Vendor Technician does not have write access to MR, so MR status change should fail
			self.assertRaises(frappe.PermissionError, change_mr_status, mr.name, "Cancelled")

		finally:
			# Restore original user
			frappe.set_user(original_user)
