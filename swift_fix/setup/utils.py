import frappe

def clean_val(val):
	if isinstance(val, str):
		return val.strip('"').strip("'")
	return val

@frappe.whitelist()
def get_asset_html(doctype, docname):
	doc = frappe.get_doc(doctype, docname)
	mrs = []
	
	if doctype == "Asset":
		mr_name = None
		if doc.purchase_receipt_item:
			mr_name = frappe.db.get_value("Purchase Receipt Item", doc.purchase_receipt_item, "material_request")
		if not mr_name:
			ac_info = frappe.db.get_value(
				"Asset Capitalization",
				{"target_asset": docname, "docstatus": ["!=", 2]},
				["name", "custom_purchase_order", "posting_date", "docstatus"],
				as_dict=True
			)
			if ac_info:
				if ac_info.custom_purchase_order:
					po_items = frappe.get_all(
						"Purchase Order Item",
						filters={"parent": ac_info.custom_purchase_order, "material_request": ["!=", ""]},
						fields=["material_request"],
						limit=1
					)
					if po_items:
						mr_name = po_items[0].material_request
				else:
					ac_link = frappe.utils.get_url_to_form('Asset Capitalization', ac_info.name)
					formatted_date = frappe.utils.format_date(ac_info.posting_date) if ac_info.posting_date else "-"
					status = "Capitalized" if ac_info.docstatus == 1 else "Draft"
					badge_bg = '#f3e8ff' if status == "Capitalized" else '#dbeafe'
					badge_color = '#6b21a8' if status == "Capitalized" else '#1e40af'
					
					stock_items = frappe.get_all(
						"Asset Capitalization Stock Item",
						filters={"parent": ac_info.name},
						fields=["warehouse"]
					)
					warehouses = list(set(d.warehouse for d in stock_items if d.warehouse))
					warehouses_str = ", ".join(warehouses) if warehouses else "Not Specified"
					
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
								<i class="fa fa-cubes"></i>
							</div>
							<div>
								<div style="font-size: 11px; color: var(--text-muted, #64748b); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Stock-led Capitalization</div>
								<div style="font-size: 15px; font-weight: 600; margin-bottom: 2px;">
									<a href="{ac_link}" style="color: var(--primary, #1b66ec); text-decoration: none; border-bottom: 1px dashed var(--primary, #1b66ec); padding-bottom: 1px; transition: color 0.15s ease;">{ac_info.name}</a>
								</div>
								<div style="font-size: 12px; color: var(--text-muted, #64748b);">Date: {formatted_date}</div>
								<div style="font-size: 12px; color: var(--text-muted, #64748b);">Warehouse: {warehouses_str}</div>
							</div>
						</div>
						<div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; justify-content: center; gap: 8px;">
							<div>
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
							<button class="btn btn-xs btn-default show-mr-detail" data-mr="{ac_info.name}" style="font-size: 11px; padding: 3px 8px; font-weight: 500;">Detail</button>
						</div>
					</div>
					"""
					container_html = f"""
					<div class="mr-cards-container" style="
						font-family: -apple-system, BlinkMacSystemFont, sans-serif;
						display: flex;
						flex-direction: row;
						flex-wrap: wrap;
						gap: 16px;
						margin-top: 10px;
						margin-bottom: 20px;
						width: 100%;
					">
						{card}
					</div>
					"""
					return container_html
		if mr_name:
			mrs.append(mr_name)
	
	for item in (doc.get("items") or []):
		if item.get("material_request"):
			mrs.append(item.material_request)
			
	if not mrs and doctype == "Supplier Quotation":
		rfq_names = set()
		for item in (doc.get("items") or []):
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
		mr_doc = frappe.db.get_value("Material Request", mr_name, ["custom_processing_status", "transaction_date", "custom_location"], as_dict=True)
		if not mr_doc:
			continue
			
		status = mr_doc.custom_processing_status or "Submitted"
		tx_date = mr_doc.transaction_date
		location = mr_doc.custom_location or "Not Specified"
		if location and location != "Not Specified":
			loc_link = frappe.utils.get_url_to_form('Location', location)
			location_html = f'<a href="{loc_link}" style="color: var(--primary, #1b66ec); font-weight: 600; text-decoration: none; border-bottom: 1px dashed var(--primary, #1b66ec); padding-bottom: 1px; transition: color 0.15s ease;">{location}</a>'
		else:
			location_html = '<span style="font-weight: 600;">Not Specified</span>'
		
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
					<div style="font-size: 12px; color: var(--text-muted, #64748b);">Location: {location_html}</div>
				</div>
			</div>
			<div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; justify-content: center; gap: 8px;">
				<div>
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
				<button class="btn btn-xs btn-default show-mr-detail" data-mr="{mr_name}" style="font-size: 11px; padding: 3px 8px; font-weight: 500;">Detail</button>
			</div>
		</div>
		"""
		html_cards.append(card)
		
	container_html = f"""
	<div class="mr-cards-container" style="
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
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

@frappe.whitelist()
def get_historic_flow_details(mr_name):
	mr_name = clean_val(mr_name)
	details = {
		"mr_name": mr_name,
		"mr_items": [],
		"rfq": None,
		"sqs": [],
		"pos": [],
		"prs": [],
		"capitalizations": [],
		"assets": [],
		"is_stock_led": False
	}

	if mr_name.startswith("ACC-ASC-"):
		details["is_stock_led"] = True
		stock_items = frappe.get_all(
			"Asset Capitalization Stock Item",
			filters={"parent": mr_name},
			fields=["item_code", "item_name", "stock_qty", "warehouse"]
		)
		details["mr_items"] = [{
			"item_code": d.item_code,
			"item_name": d.item_name,
			"custom_request_description": f"Quantity: {d.stock_qty} | Source Warehouse: {d.warehouse}"
		} for d in stock_items]

		ac = frappe.get_doc("Asset Capitalization", mr_name)
		details["capitalizations"] = [{
			"name": ac.name,
			"posting_date": frappe.utils.format_date(ac.posting_date) if ac.posting_date else None,
			"status": "Capitalized" if ac.docstatus == 1 else "Draft",
			"custom_installation_notes": ac.custom_installation_notes,
			"custom_installation_photo_1": ac.custom_installation_photo_1,
			"custom_installation_photo_2": ac.custom_installation_photo_2,
			"custom_installation_length": ac.custom_installation_length,
			"custom_installation_height": ac.custom_installation_height,
			"custom_installation_depth": ac.custom_installation_depth
		}]

		if ac.target_asset:
			asset = frappe.db.get_value("Asset", ac.target_asset, ["name", "asset_name", "status"], as_dict=True)
			if asset:
				details["assets"] = [asset]
		return details

	# Fetch MR Items details
	details["mr_items"] = frappe.get_all(
		"Material Request Item",
		filters={"parent": mr_name},
		fields=["item_code", "item_name", "custom_request_description"]
	)

	# 1. Fetch RFQ
	rfq_items = frappe.get_all(
		"Request for Quotation Item",
		filters={"material_request": mr_name},
		fields=["parent"]
	)
	if rfq_items:
		rfq_names = list(set(d.parent for d in rfq_items))
		rfqs = []
		for rfq_name in rfq_names:
			rfq_doc = frappe.get_doc("Request for Quotation", rfq_name)
			rfqs.append({
				"name": rfq_doc.name,
				"status": rfq_doc.status,
				"custom_recce_status": rfq_doc.custom_recce_status,
				"custom_recce_length": rfq_doc.custom_recce_length,
				"custom_recce_height": rfq_doc.custom_recce_height,
				"custom_recce_depth": rfq_doc.custom_recce_depth,
				"custom_recce_photo_1": rfq_doc.custom_recce_photo_1,
				"custom_recce_photo_2": rfq_doc.custom_recce_photo_2,
				"custom_recced_timestamp": frappe.utils.format_datetime(rfq_doc.custom_recced_timestamp) if rfq_doc.custom_recced_timestamp else None
			})
		details["rfq"] = rfqs

	# 2. Fetch SQ details
	sq_items = frappe.get_all(
		"Supplier Quotation Item",
		filters={"material_request": mr_name},
		fields=["parent", "rate", "item_code"]
	)
	# Fallback to fetching via RFQ if direct MR link is empty
	rfq_items_for_fallback = frappe.get_all(
		"Request for Quotation Item",
		filters={"material_request": mr_name},
		fields=["parent", "item_code"]
	)
	if rfq_items_for_fallback:
		rfq_names = list(set(d.parent for d in rfq_items_for_fallback))
		item_codes = list(set(d.item_code for d in rfq_items_for_fallback))
		sq_items_via_rfq = frappe.get_all(
			"Supplier Quotation Item",
			filters={
				"request_for_quotation": ["in", rfq_names],
				"item_code": ["in", item_codes],
				"docstatus": ["<", 2]
			},
			fields=["parent", "rate", "item_code"]
		)
		existing_keys = set((d.parent, d.item_code) for d in sq_items)
		for d in sq_items_via_rfq:
			if (d.parent, d.item_code) not in existing_keys:
				sq_items.append(d)
	if sq_items:
		sq_parents = list(set(d.parent for d in sq_items))
		sq_parent_details = {}
		for parent in sq_parents:
			sq_parent_details[parent] = frappe.db.get_value("Supplier Quotation", parent, ["supplier", "status", "grand_total"], as_dict=True)

		sqs = []
		for d in sq_items:
			parent_info = sq_parent_details.get(d.parent)
			if parent_info:
				sqs.append({
					"name": d.parent,
					"supplier": parent_info.supplier,
					"status": parent_info.status,
					"rate": d.rate,
					"grand_total": parent_info.grand_total,
					"item_code": d.item_code
				})
		details["sqs"] = sqs

	# 2.5 Fetch PO details
	po_items = frappe.get_all(
		"Purchase Order Item",
		filters={"material_request": mr_name},
		fields=["parent", "rate", "item_code"]
	)
	if po_items:
		po_parents = list(set(d.parent for d in po_items))
		po_parent_details = {}
		for parent in po_parents:
			po_parent_details[parent] = frappe.db.get_value("Purchase Order", parent, ["status", "grand_total", "transaction_date"], as_dict=True)
			
		pos = []
		for d in po_items:
			parent_info = po_parent_details.get(d.parent)
			if parent_info:
				pos.append({
					"name": d.parent,
					"status": parent_info.status,
					"date": frappe.utils.format_date(parent_info.transaction_date) if parent_info.transaction_date else None,
					"rate": d.rate,
					"grand_total": parent_info.grand_total,
					"item_code": d.item_code
				})
		details["pos"] = pos

	# 3. Fetch PR & QC
	pr_items = frappe.get_all(
		"Purchase Receipt Item",
		filters={"material_request": mr_name},
		fields=["name", "parent"]
	)
	if not pr_items:
		po_items = frappe.get_all("Purchase Order Item", filters={"material_request": mr_name}, fields=["name"])
		po_item_names = [d.name for d in po_items]
		if po_item_names:
			pr_items = frappe.get_all(
				"Purchase Receipt Item",
				filters={"purchase_order_item": ["in", po_item_names]},
				fields=["name", "parent"]
			)
			
	if pr_items:
		pr_names = list(set(d.parent for d in pr_items))
		prs = []
		for pr_name in pr_names:
			pr_doc = frappe.get_doc("Purchase Receipt", pr_name)
			prs.append({
				"name": pr_doc.name,
				"status": pr_doc.status,
				"custom_qc_length": pr_doc.custom_qc_length,
				"custom_qc_height": pr_doc.custom_qc_height,
				"custom_qc_depth": pr_doc.custom_qc_depth,
				"custom_qc_photo_1": pr_doc.custom_qc_photo_1,
				"custom_qc_photo_2": pr_doc.custom_qc_photo_2,
				"custom_qc_notes": pr_doc.custom_qc_notes
			})
		details["prs"] = prs

	# 4. Fetch Assets and 5. Fetch Asset Capitalizations
	pr_item_names = [d.name for d in pr_items] if pr_items else []
	
	# Get POs linked to this MR
	po_items = frappe.get_all(
		"Purchase Order Item",
		filters={"material_request": mr_name},
		fields=["parent"]
	)
	po_names = list(set(d.parent for d in po_items))

	# Find target assets from Asset Capitalizations linked to these POs
	ac_target_assets = []
	capitalizations = []
	ac_docs = []
	if po_names:
		ac_docs = frappe.get_all(
			"Asset Capitalization",
			filters={"custom_purchase_order": ["in", po_names], "docstatus": ["!=", 2]},
			fields=[
				"name", "posting_date", "docstatus", "target_asset",
				"custom_installation_notes", "custom_installation_photo_1",
				"custom_installation_photo_2", "custom_installation_length",
				"custom_installation_height", "custom_installation_depth"
			]
		)
		for ac in ac_docs:
			if ac.target_asset:
				ac_target_assets.append(ac.target_asset)
			capitalizations.append({
				"name": ac.name,
				"posting_date": frappe.utils.format_date(ac.posting_date) if ac.posting_date else None,
				"status": "Capitalized" if ac.docstatus == 1 else "Draft",
				"custom_installation_notes": ac.custom_installation_notes,
				"custom_installation_photo_1": ac.custom_installation_photo_1,
				"custom_installation_photo_2": ac.custom_installation_photo_2,
				"custom_installation_length": ac.custom_installation_length,
				"custom_installation_height": ac.custom_installation_height,
				"custom_installation_depth": ac.custom_installation_depth
			})
	details["capitalizations"] = capitalizations

	# Fetch Assets
	assets = []
	or_filters = []
	if pr_item_names:
		or_filters.append(["purchase_receipt_item", "in", pr_item_names])
	if ac_target_assets:
		or_filters.append(["name", "in", ac_target_assets])

	if or_filters:
		assets = frappe.get_all(
			"Asset",
			or_filters=or_filters,
			fields=["name", "asset_name", "status"]
		)
	details["assets"] = assets

	return details

@frappe.whitelist()
def get_procurement_details(asset_name):
	# Fetch Asset
	if not frappe.db.exists("Asset", asset_name):
		return ""
	
	asset = frappe.get_doc("Asset", asset_name)
	
	# Fetch Purchase Receipt details
	pr_name = asset.purchase_receipt
	pr_item_name = asset.purchase_receipt_item
	
	if not pr_name:
		ac_info = frappe.db.get_value(
			"Asset Capitalization",
			{"target_asset": asset_name, "docstatus": ["!=", 2]},
			["name", "custom_purchase_order"],
			as_dict=True
		)
		if ac_info and ac_info.custom_purchase_order:
			po_name = ac_info.custom_purchase_order
			pr_item_info = frappe.db.get_value(
				"Purchase Receipt Item",
				{"purchase_order": po_name, "item_code": asset.item_code, "docstatus": ["!=", 2]},
				["parent", "name"],
				as_dict=True
			)
			if pr_item_info:
				pr_name = pr_item_info.parent
				pr_item_name = pr_item_info.name
	
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
