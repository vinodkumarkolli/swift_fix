# Copyright (c) 2026, Vinod Kumar K and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from swift_fix.setup.mr_utils import change_mr_status, get_mr_status_details, analyze_mr
from swift_fix.setup.popr_utils import on_po_submit, on_pr_submit, on_asset_capitalization_submit

class ProcurementFlowBase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		import erpnext.setup.setup_wizard.operations.install_fixtures as install_fixtures
		if not frappe.db.exists("Warehouse Type", "Transit"):
			install_fixtures.install("India")
			frappe.db.commit()

	def setUp(self):

		super().setUp()
		# Setup prerequisites
		self.company = "Sravi Enterprises - Assets Kolapakkam"
		self.warehouse = "Stores - SE-AK"
		self.item_code = "MBLIT"
		self.supplier = "G & JC Signage"
		self.cost_center = "Main - SE-AK"
		self.expense_account = "Capital Equipment - SE-AK"
		self.location = "Test Location"
		self.raised_by = "Administrator"
		self.asset_category = "Capital Equipment"
		self.asset_received_account = "Asset Received But Not Billed - SE-AK"
		self.service_item = "Installation Service"

		# Ensure prerequisites are created
		self.ensure_company()
		self.ensure_fiscal_year()
		self.ensure_warehouse()
		self.ensure_asset_category()
		self.ensure_item()
		self.ensure_supplier()
		self.ensure_location()
		self.ensure_accounts()
		self.ensure_service_item()

	def ensure_company(self):
		if not frappe.db.exists("Company", self.company):
			frappe.get_doc({
				"doctype": "Company",
				"company_name": self.company,
				"default_currency": "INR",
				"country": "India"
			}).insert(ignore_permissions=True)

	def ensure_fiscal_year(self):
		year_name = "2026-2027"
		if not frappe.db.exists("Fiscal Year", year_name):
			frappe.get_doc({
				"doctype": "Fiscal Year",
				"year": year_name,
				"year_start_date": "2026-04-01",
				"year_end_date": "2027-03-31"
			}).insert(ignore_permissions=True)

	def ensure_warehouse(self):
		if not frappe.db.exists("Warehouse", self.warehouse):
			parent_warehouse = frappe.db.get_value("Warehouse", {"is_group": 1, "company": self.company})
			frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": "Stores",
				"company": self.company,
				"parent_warehouse": parent_warehouse
			}).insert(ignore_permissions=True)

	def ensure_asset_category(self):
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
					"accumulated_depreciation_account": "Accumulated Depreciation - SE-AK",
					"depreciation_expense_account": "Depreciation - SE-AK"
				}]
			}).insert(ignore_permissions=True)

	def ensure_item(self):
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

	def ensure_supplier(self):
		if not frappe.db.exists("Supplier", self.supplier):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": self.supplier,
				"supplier_type": "Company"
			}).insert(ignore_permissions=True)

	def ensure_location(self):
		if not frappe.db.exists("Location", self.location):
			frappe.get_doc({
				"doctype": "Location",
				"location_name": self.location
			}).insert(ignore_permissions=True)

	def ensure_accounts(self):
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

	def ensure_service_item(self):
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


class Test01Company(ProcurementFlowBase):
	def test_company_creation(self):
		self.assertTrue(frappe.db.exists("Company", self.company))
		company_doc = frappe.get_doc("Company", self.company)
		self.assertEqual(company_doc.default_currency, "INR")
		# Verify Warehouse creation/setup
		self.assertTrue(frappe.db.exists("Warehouse", self.warehouse))


class Test02Accounts(ProcurementFlowBase):
	def test_accounts_setup(self):
		self.assertTrue(frappe.db.exists("Account", self.asset_received_account))
		self.assertTrue(frappe.db.exists("Account", self.expense_account))


class Test03CostCenter(ProcurementFlowBase):
	def test_cost_center_setup(self):
		cost_centers = frappe.get_all("Cost Center", filters={"company": self.company})
		self.assertTrue(len(cost_centers) > 0)


class Test04Location(ProcurementFlowBase):
	def test_location_creation(self):
		self.assertTrue(frappe.db.exists("Location", self.location))


class Test05StockItem(ProcurementFlowBase):
	"""
	Represents the 'Stock Item (with Serial Number)' step.
	Verifies the creation, configuration, and constraints of our target fixed asset item.
	"""
	def test_stock_item_properties(self):
		self.assertTrue(frappe.db.exists("Item", self.item_code))
		item_doc = frappe.get_doc("Item", self.item_code)
		self.assertEqual(item_doc.is_fixed_asset, 1)
		self.assertEqual(item_doc.is_stock_item, 0)
		self.assertEqual(item_doc.auto_create_assets, 1)


class Test06MR(ProcurementFlowBase):
	def test_mr_validation_and_creation(self):
		# Set is_fixed_asset to 0 on Item, expect validation to fail
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
		
		# Reset is_fixed_asset to 1 and verify success
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


class Test07SQ(ProcurementFlowBase):
	def test_rfq_and_sq_lifecycle(self):
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
		mr.insert().submit()

		# Try creating RFQ when MR is in "Submitted" status (validation should fail)
		rfq = frappe.get_doc({
			"doctype": "Request for Quotation",
			"company": self.company,
			"suppliers": [{"supplier": self.supplier}],
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"stock_uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test request description",
				"material_request": mr.name
			}]
		})
		self.assertRaises(frappe.ValidationError, rfq.insert)

		# Shortlist MR
		change_mr_status(mr.name, "Shortlisted")
		mr.reload()

		# RFQ creation should now succeed
		rfq.insert().submit()

		# Verify comment added to MR
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "Material Request",
			"reference_name": mr.name
		}, fields=["content"], order_by="creation desc")
		self.assertTrue(any("A Quotation is requested from Vendor and Recce Process is in Progress" in c.content for c in comments))

		# Test get_linked_mr_html for RFQ
		from swift_fix.setup.rfq_update import get_linked_mr_html
		rfq_html = get_linked_mr_html("Request for Quotation", rfq.name)
		self.assertIn(mr.name, rfq_html)
		self.assertIn("Shortlisted", rfq_html)
		self.assertIn(self.location, rfq_html)
		self.assertIn("Location", rfq_html)
		self.assertIn("/location/", rfq_html.lower())

		# Create Supplier Quotation linked to RFQ
		sq = frappe.get_doc({
			"doctype": "Supplier Quotation",
			"company": self.company,
			"supplier": self.supplier,
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"rate": 150.0,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"warehouse": self.warehouse,
				"request_for_quotation": rfq.name
			}]
		})
		sq.insert().submit()

		# Test get_linked_mr_html for Supplier Quotation
		sq_html = get_linked_mr_html("Supplier Quotation", sq.name)
		self.assertIn(mr.name, sq_html)
		self.assertIn("Shortlisted", sq_html)
		self.assertIn(self.location, sq_html)
		self.assertIn("Location", sq_html)
		self.assertIn("/location/", sq_html.lower())


class Test08PO(ProcurementFlowBase):
	def test_po_submission_flow(self):
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
		mr.insert().submit()
		change_mr_status(mr.name, "Shortlisted")

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
		po.insert().submit()

		# Verify MR status changed to "Under Process"
		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Under Process")

		# Verify timeline comments
		comments = frappe.get_all("Comment", filters={
			"reference_doctype": "Material Request",
			"reference_name": mr.name
		}, fields=["content"], order_by="creation desc")
		self.assertTrue(any(f"Status updated to Under Process upon submission of Purchase Order {po.name}" in c.content for c in comments))

		# Test get_linked_mr_html for Purchase Order
		from swift_fix.setup.rfq_update import get_linked_mr_html
		po_html = get_linked_mr_html("Purchase Order", po.name)
		self.assertIn(mr.name, po_html)
		self.assertIn(self.location, po_html)


class Test09PR(ProcurementFlowBase):
	def test_pr_submission_flow(self):
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert().submit()
		change_mr_status(mr.name, "Shortlisted")

		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": self.supplier,
			"company": self.company,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"material_request": mr.name,
				"warehouse": self.warehouse
			}]
		})
		po.insert().submit()

		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_length": 10.0,
			"custom_qc_height": 12.0,
			"custom_qc_depth": 14.0,
			"custom_qc_photo_1": "/files/qc1.png",
			"custom_qc_photo_2": "/files/qc2.png",
			"custom_qc_notes": "All items inspected and cleared.",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": po.name,
				"purchase_order_item": po.items[0].name,
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		pr.insert().submit()

		# Verify PO is Completed and MR is Item Received
		po_status = frappe.db.get_value("Purchase Order", po.name, "status")
		self.assertEqual(po_status, "Completed")

		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Item Received")

		# Verify serialization was done (serial number updated in items)
		pr.reload()
		self.assertTrue(bool(pr.items[0].serial_no))

	def test_pr_validation_rules(self):
		# 1. Test PR Item without PO throws ValidationError
		pr_no_po = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_length": 10.0,
			"custom_qc_height": 12.0,
			"custom_qc_depth": 14.0,
			"custom_qc_photo_1": "/files/qc1.png",
			"custom_qc_photo_2": "/files/qc2.png",
			"custom_qc_notes": "Valid notes",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"warehouse": self.warehouse,
				"asset_location": self.location
				# purchase_order is intentionally omitted
			}]
		})
		self.assertRaises(frappe.ValidationError, pr_no_po.insert)

		# 2. Test missing QC dimensions throws ValidationError
		pr_no_qc_dim = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_photo_1": "/files/qc1.png",
			"custom_qc_photo_2": "/files/qc2.png",
			"custom_qc_notes": "Valid notes",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": "DummyPO",
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		self.assertRaises(frappe.ValidationError, pr_no_qc_dim.insert)

		# 3. Test missing QC photos throws ValidationError
		pr_no_qc_photo = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_length": 10.0,
			"custom_qc_height": 12.0,
			"custom_qc_depth": 14.0,
			"custom_qc_notes": "Valid notes",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": "DummyPO",
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		self.assertRaises(frappe.ValidationError, pr_no_qc_photo.insert)

		# 4. Test missing QC notes throws ValidationError
		pr_no_qc_notes = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_length": 10.0,
			"custom_qc_height": 12.0,
			"custom_qc_depth": 14.0,
			"custom_qc_photo_1": "/files/qc1.png",
			"custom_qc_photo_2": "/files/qc2.png",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": "DummyPO",
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		self.assertRaises(frappe.ValidationError, pr_no_qc_notes.insert)

	def test_create_pr_helper(self):
		from swift_fix.setup.popr_utils import create_pr

		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert().submit()
		change_mr_status(mr.name, "Shortlisted")

		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": self.supplier,
			"company": self.company,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"material_request": mr.name,
				"warehouse": self.warehouse
			}]
		})
		po.insert().submit()

		qc_details = {
			"custom_qc_length": 8,
			"custom_qc_height": 5,
			"custom_qc_depth": 0.6,
			"custom_qc_photo_1": "https://photos.app.goo.gl/UkR9rNajG3HYYECF8",
			"custom_qc_photo_2": "https://photos.app.goo.gl/UkR9rNajG3HYYECF8",
			"custom_qc_notes": "All items inspected and cleared.",
		}

		pr_name = create_pr(po_doc=po.name, qc=qc_details, warehouse=self.warehouse, company=self.company)
		self.assertTrue(frappe.db.exists("Purchase Receipt", pr_name))

		pr = frappe.get_doc("Purchase Receipt", pr_name)
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.custom_qc_length, 8)
		self.assertEqual(pr.custom_qc_height, 5)
		self.assertEqual(pr.custom_qc_depth, 0.6)
		self.assertEqual(pr.custom_qc_notes, "All items inspected and cleared.")

		# Test passing qc_details as JSON string
		po2 = frappe.copy_doc(po)
		po2.name = None
		po2.insert().submit()
		
		import json
		qc_details_json = json.dumps(qc_details)
		pr_name2 = create_pr(po_doc=po2.name, qc=qc_details_json, warehouse=self.warehouse, company=self.company)
		self.assertTrue(frappe.db.exists("Purchase Receipt", pr_name2))


class Test10AssetCapitalization(ProcurementFlowBase):
	def test_asset_capitalization_flow(self):
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert().submit()
		change_mr_status(mr.name, "Shortlisted")

		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": self.supplier,
			"company": self.company,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"material_request": mr.name,
				"warehouse": self.warehouse
			}]
		})
		po.insert().submit()

		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_length": 10.0,
			"custom_qc_height": 12.0,
			"custom_qc_depth": 14.0,
			"custom_qc_photo_1": "/files/qc1.png",
			"custom_qc_photo_2": "/files/qc2.png",
			"custom_qc_notes": "All items inspected and cleared.",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": po.name,
				"purchase_order_item": po.items[0].name,
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		pr.insert().submit()

		# Find the asset created
		assets = frappe.get_all("Asset", filters={"purchase_receipt": pr.name})
		self.assertTrue(len(assets) > 0)
		asset_name = assets[0].name

		# Mark the asset as composite so it can be capitalized
		frappe.db.set_value("Asset", asset_name, "asset_type", "Composite Asset")

		# Create Purchase Invoice before capitalization (should throw ValidationError)
		pi_invalid = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": self.company,
			"supplier": self.supplier,
			"posting_date": frappe.utils.nowdate(),
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_receipt": pr.name,
				"pr_detail": pr.items[0].name,
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		pi_invalid.insert()
		self.assertRaises(frappe.ValidationError, pi_invalid.submit)

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
		ac.insert().submit()

		# Manually submit the asset (docstatus -> 1) as required before Purchase Invoice submission
		asset_doc = frappe.get_doc("Asset", asset_name)
		asset_doc.submit()

		# Submit purchase invoice (should succeed now because asset capitalization has been submitted)
		pi_valid = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": self.company,
			"supplier": self.supplier,
			"posting_date": frappe.utils.nowdate(),
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_receipt": pr.name,
				"pr_detail": pr.items[0].name,
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		pi_valid.insert().submit()
		self.assertEqual(pi_valid.docstatus, 1)

		# Verify MR status is Asset Capitalised
		mr.reload()
		self.assertEqual(mr.custom_processing_status, "Asset Capitalised")


class Test11Asset(ProcurementFlowBase):
	def test_asset_lifecycle(self):
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": self.company,
			"custom_location": self.location,
			"custom_raised_by": self.raised_by,
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test description",
				"expense_account": self.expense_account,
				"cost_center": self.cost_center
			}]
		})
		mr.insert().submit()
		change_mr_status(mr.name, "Shortlisted")

		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": self.supplier,
			"company": self.company,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 5),
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"material_request": mr.name,
				"warehouse": self.warehouse
			}]
		})
		po.insert().submit()

		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": self.supplier,
			"company": self.company,
			"custom_qc_length": 10.0,
			"custom_qc_height": 12.0,
			"custom_qc_depth": 14.0,
			"custom_qc_photo_1": "/files/qc1.png",
			"custom_qc_photo_2": "/files/qc2.png",
			"custom_qc_notes": "All items inspected and cleared.",
			"items": [{
				"item_code": self.item_code,
				"qty": 1,
				"rate": 150,
				"uom": "Square Foot",
				"conversion_factor": 1.0,
				"purchase_order": po.name,
				"purchase_order_item": po.items[0].name,
				"warehouse": self.warehouse,
				"asset_location": self.location
			}]
		})
		pr.insert().submit()

		# Find the asset created
		assets = frappe.get_all("Asset", filters={"purchase_receipt": pr.name})
		self.assertTrue(len(assets) > 0)
		asset_name = assets[0].name

		# Verify Asset is created as Draft (docstatus = 0)
		asset_doc = frappe.get_doc("Asset", asset_name)
		self.assertEqual(asset_doc.docstatus, 0)
		# Verify QR code is generated and attached
		self.assertTrue(bool(asset_doc.custom_asset_qr_code))

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
		ac.insert().submit()

		# Verify asset is still in Draft state (docstatus = 0) and can be manually submitted
		asset_doc.reload()
		self.assertEqual(asset_doc.docstatus, 0)
		asset_doc.submit()
		self.assertEqual(asset_doc.docstatus, 1)

		# Verify procurement HTML contents
		from swift_fix.setup.popr_utils import get_procurement_details
		html_details = get_procurement_details(asset_name)
		self.assertIn(po.name, html_details)
		self.assertIn(mr.name, html_details)
		self.assertIn(pr.name, html_details)
		self.assertIn(ac.name, html_details)


class Test12PermissionChecks(ProcurementFlowBase):
	def test_permission_checks(self):
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
		mr.insert().submit()
		change_mr_status(mr.name, "Shortlisted")
		
		# Create RFQ
		rfq = frappe.get_doc({
			"doctype": "Request for Quotation",
			"company": self.company,
			"suppliers": [{"supplier": self.supplier}],
			"items": [{
				"item_code": self.item_code,
				"qty": 2,
				"warehouse": self.warehouse,
				"uom": "Square Foot",
				"stock_uom": "Square Foot",
				"conversion_factor": 1.0,
				"custom_request_description": "Test request description",
				"material_request": mr.name
			}]
		})
		rfq.insert().submit()

		# Create users for checks
		no_role_user = "test_norole@example.com"
		if not frappe.db.exists("User", no_role_user):
			u = frappe.get_doc({
				"doctype": "User",
				"email": no_role_user,
				"first_name": "No Role User",
				"send_welcome_email": 0
			})
			u.insert(ignore_permissions=True)

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

		original_user = frappe.session.user

		try:
			# Guest user check
			frappe.set_user("Guest")
			from swift_fix.setup.rfq_update import rfq_change_recce_status, rfq_update_dimensions, rfq_update_dimensions_with_images
			self.assertRaises(frappe.PermissionError, get_mr_status_details, mr.name)
			self.assertRaises(frappe.PermissionError, change_mr_status, mr.name, "Cancelled")
			self.assertRaises(frappe.PermissionError, analyze_mr, mr.name)
			self.assertRaises(frappe.PermissionError, rfq_change_recce_status, rfq.name, "Validated")
			self.assertRaises(frappe.PermissionError, rfq_update_dimensions, rfq.name, "guest_user", 10.0, 10.0, 10.0)
			self.assertRaises(frappe.PermissionError, rfq_update_dimensions_with_images, rfq.name, "guest_user", 10.0, 10.0, 10.0)

			# No-Role check
			frappe.set_user(no_role_user)
			self.assertRaises(frappe.PermissionError, get_mr_status_details, mr.name)
			self.assertRaises(frappe.PermissionError, change_mr_status, mr.name, "Cancelled")
			self.assertRaises(frappe.PermissionError, rfq_change_recce_status, rfq.name, "Validated")

			# Field User check (can write to MR, not to RFQ)
			frappe.set_user(field_user)
			change_mr_status(mr.name, "Held")
			mr.reload()
			self.assertEqual(mr.custom_processing_status, "Held")
			self.assertRaises(frappe.PermissionError, rfq_change_recce_status, rfq.name, "Validated")

			# Vendor Technician check (can write to RFQ, not to MR)
			frappe.set_user(vendor_tech)
			rfq_change_recce_status(rfq.name, "Validated")
			rfq.reload()
			self.assertEqual(rfq.custom_recce_status, "Validated")

			rfq_update_dimensions(rfq.name, vendor_tech, 12.0, 14.0, 16.0)
			rfq.reload()
			self.assertEqual(rfq.custom_recce_length, 12.0)
			self.assertEqual(rfq.custom_recce_status, "Recced")
			self.assertRaises(frappe.PermissionError, change_mr_status, mr.name, "Cancelled")

		finally:
			frappe.set_user(original_user)
