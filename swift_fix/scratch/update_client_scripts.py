import frappe

RFQ_SCRIPT = """frappe.ui.form.on('Request for Quotation', {
    refresh(frm) {
        // Toggle the Create button layout when the form loads
        toggle_create_button(frm);
        // Load and render material request details
        load_material_request_details(frm);
        // Bind click listener for show-mr-detail button
        setup_detail_button_click(frm);
    },

    custom_recce_status(frm) {
        // Toggle the Create button layout instantly if the dropdown choice changes
        toggle_create_button(frm);
    },

    custom_recce_length(frm) {
        if (!frm.doc.custom_recced_timestamp) {
            frm.set_value(
                "custom_recced_timestamp",
                frappe.datetime.now_datetime()
            );
        }
    },

    validate(frm) {
        let missing_mr = false;
        if (!frm.doc.items || !frm.doc.items.length) {
            missing_mr = true;
        } else {
            for (let item of frm.doc.items) {
                if (!item.material_request) {
                    missing_mr = true;
                    break;
                }
            }
        }
        if (missing_mr) {
            frappe.throw(__("Please link a Material Request in the items table."));
        }
    }
});

function setup_detail_button_click(frm) {
    if (frm.fields_dict.custom_mr_html) {
        frm.fields_dict.custom_mr_html.$wrapper.off('click', '.show-mr-detail').on('click', '.show-mr-detail', function(e) {
            e.preventDefault();
            let mr_name = $(this).data('mr');
            if (mr_name) {
                window.show_mr_flow_details(mr_name);
            }
        });
    }
}

function load_material_request_details(frm) {
    if (frm.is_new()) {
        frm.set_df_property('custom_mr_html', 'options', '');
        frm.refresh_field('custom_mr_html');
        return;
    }

    frappe.call({
        method: 'swift_fix.setup.rfq_update.get_linked_mr_html',
        args: {
            doctype: frm.doc.doctype,
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.set_df_property('custom_mr_html', 'options', r.message);
            } else {
                frm.set_df_property('custom_mr_html', 'options', '');
            }
            frm.refresh_field('custom_mr_html');
        }
    });
}

function toggle_create_button(frm) {
    // Target the main 'Create' dropdown button element wrapper
    let $create_group = frm.page.get_inner_group_button(__("Create"));

    if (frm.doc.custom_recce_status === 'Validated') {
        if ($create_group) {
            $create_group.show();
        }
    } else {
        // First, strip the child elements safely to prevent core execution hooks from maintaining focus
        frm.remove_custom_button(__("Supplier Quotation"), __("Create"));
        
        // Hide the parent action button dropdown element completely
        if ($create_group) {
            $create_group.hide();
        }
    }
}

// Initialize the detail popup function globally if not already set
setup_global_mr_details_popup();
"""

SQ_SCRIPT = """frappe.ui.form.on('Supplier Quotation', {
    refresh(frm) {
        load_rfq_details(frm);
        load_material_request_details(frm);
        setup_detail_button_click(frm);
    },
    request_for_quotation(frm) {
        load_rfq_details(frm);
        load_material_request_details(frm);
    }
});

function setup_detail_button_click(frm) {
    if (frm.fields_dict.custom_mr_html) {
        frm.fields_dict.custom_mr_html.$wrapper.off('click', '.show-mr-detail').on('click', '.show-mr-detail', function(e) {
            e.preventDefault();
            let mr_name = $(this).data('mr');
            if (mr_name) {
                window.show_mr_flow_details(mr_name);
            }
        });
    }
}

function load_material_request_details(frm) {
    if (frm.is_new()) {
        frm.set_df_property('custom_mr_html', 'options', '');
        frm.refresh_field('custom_mr_html');
        return;
    }

    frappe.call({
        method: 'swift_fix.setup.rfq_update.get_linked_mr_html',
        args: {
            doctype: frm.doc.doctype,
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.set_df_property('custom_mr_html', 'options', r.message);
            } else {
                frm.set_df_property('custom_mr_html', 'options', '');
            }
            frm.refresh_field('custom_mr_html');
        }
    });
}

function load_rfq_details(frm) {
    let rfq = "";
    if (frm.doc.items && frm.doc.items.length) {
        for (let item of frm.doc.items) {
            if (item.request_for_quotation) {
                rfq = item.request_for_quotation;
                break;
            }
        }
    }
    if (rfq) {
        frappe.db.get_value("Request for Quotation", rfq, [
            "custom_recce_length",
            "custom_recce_height",
            "custom_recce_depth",
            "custom_recce_photo_1",
            "custom_recce_photo_2"
        ], function(r) {
            if (r) {
                let recce_html = `
                <div style="padding:10px">
                <b>Recce Details</b><br><br>
                Length : ${r.custom_recce_length || ""}<br>
                Height : ${r.custom_recce_height || ""}<br>
                Depth : ${r.custom_recce_depth || ""}<br><br>
                `;
                
                if (r.custom_recce_photo_1) {
                    recce_html += `<b>Photo 1:</b><br><img src="${r.custom_recce_photo_1}" style="max-width: 100%; max-height: 250px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; border: 1px solid #ddd;"><br>`;
                }
                if (r.custom_recce_photo_2) {
                    recce_html += `<b>Photo 2:</b><br><img src="${r.custom_recce_photo_2}" style="max-width: 100%; max-height: 250px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; border: 1px solid #ddd;"><br>`;
                }
                
                recce_html += `</div>`;
                
                if (frm.fields_dict.custom_recce_details) {
                    frm.fields_dict.custom_recce_details.$wrapper.html(recce_html);
                }
            }
        });
    }
}

// Initialize the detail popup function globally if not already set
setup_global_mr_details_popup();
"""

PO_SCRIPT = """frappe.ui.form.on('Purchase Order', {
    refresh(frm) {
        load_material_request_details(frm);
        setup_detail_button_click(frm);
    }
});

function setup_detail_button_click(frm) {
    if (frm.fields_dict.custom_mr_html) {
        frm.fields_dict.custom_mr_html.$wrapper.off('click', '.show-mr-detail').on('click', '.show-mr-detail', function(e) {
            e.preventDefault();
            let mr_name = $(this).data('mr');
            if (mr_name) {
                window.show_mr_flow_details(mr_name);
            }
        });
    }
}

function load_material_request_details(frm) {
    if (frm.is_new()) {
        frm.set_df_property('custom_mr_html', 'options', '');
        frm.refresh_field('custom_mr_html');
        return;
    }

    frappe.call({
        method: 'swift_fix.setup.rfq_update.get_linked_mr_html',
        args: {
            doctype: frm.doc.doctype,
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.set_df_property('custom_mr_html', 'options', r.message);
            } else {
                frm.set_df_property('custom_mr_html', 'options', '');
            }
            frm.refresh_field('custom_mr_html');
        }
    });
}

// Initialize the detail popup function globally if not already set
setup_global_mr_details_popup();
"""

ASSET_SCRIPT = """frappe.ui.form.on('Asset', {
    refresh(frm) {
        load_material_request_details(frm);
        setup_detail_button_click(frm);
    }
});

function setup_detail_button_click(frm) {
    if (frm.fields_dict.custom_procurement_html) {
        frm.fields_dict.custom_procurement_html.$wrapper.off('click', '.show-mr-detail').on('click', '.show-mr-detail', function(e) {
            e.preventDefault();
            let mr_name = $(this).data('mr');
            if (mr_name) {
                window.show_mr_flow_details(mr_name);
            }
        });
    }
}

function load_material_request_details(frm) {
    if (frm.is_new()) {
        frm.set_df_property('custom_procurement_html', 'options', '');
        frm.refresh_field('custom_procurement_html');
        return;
    }

    frappe.call({
        method: 'swift_fix.setup.rfq_update.get_linked_mr_html',
        args: {
            doctype: frm.doc.doctype,
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.set_df_property('custom_procurement_html', 'options', r.message);
            } else {
                frm.set_df_property('custom_procurement_html', 'options', '');
            }
            frm.refresh_field('custom_procurement_html');
        }
    });
}

// Initialize the detail popup function globally if not already set
setup_global_mr_details_popup();
"""

GLOBAL_POPUP_JS = """
function setup_global_mr_details_popup() {
    if (window.show_mr_flow_details) return;
    
    window.show_mr_flow_details = function(mr_name) {
        frappe.call({
            method: 'swift_fix.setup.rfq_update.get_mr_flow_details',
            args: { mr_name: mr_name },
            callback: function(r) {
                if (!r.message) return;
                let data = r.message;
                
                let d = new frappe.ui.Dialog({
                    title: __('Procurement Flow Details: {0}', [mr_name]),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'details_html'
                        }
                    ]
                });
                
                let html = `
                    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 10px; max-height: 70vh; overflow-y: auto;">
                        <style>
                            .detail-section {
                                margin-bottom: 20px;
                                border: 1px solid var(--border-color, #e2e8f0);
                                border-radius: 8px;
                                padding: 15px;
                                background-color: var(--card-bg, #ffffff);
                            }
                            .detail-title {
                                font-size: 14px;
                                font-weight: 600;
                                color: var(--text-color, #1e293b);
                                margin-bottom: 12px;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                border-bottom: 1px solid var(--border-color, #e2e8f0);
                                padding-bottom: 8px;
                            }
                            .detail-grid {
                                display: grid;
                                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                                gap: 12px;
                                font-size: 13px;
                            }
                            .detail-item {
                                margin-bottom: 4px;
                            }
                            .detail-label {
                                color: var(--text-muted, #64748b);
                                font-weight: 500;
                                font-size: 11px;
                                text-transform: uppercase;
                                letter-spacing: 0.5px;
                                margin-bottom: 2px;
                            }
                            .detail-value {
                                font-weight: 600;
                                color: var(--text-color, #334155);
                            }
                            .thumbnail-container {
                                display: flex;
                                flex-wrap: wrap;
                                gap: 10px;
                                margin-top: 10px;
                            }
                            .thumbnail-img {
                                max-width: 120px;
                                max-height: 120px;
                                border-radius: 6px;
                                border: 1px solid var(--border-color, #e2e8f0);
                                cursor: pointer;
                                transition: all 0.2s ease;
                            }
                            .thumbnail-img:hover {
                                transform: translateY(-2px);
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            }
                            .popup-table {
                                width: 100%;
                                font-size: 13px;
                                border-collapse: collapse;
                                margin-top: 5px;
                            }
                            .popup-table th {
                                color: var(--text-muted, #64748b);
                                font-weight: 600;
                                background-color: var(--fg-color, #f8fafc);
                                padding: 8px 12px;
                                border: 1px solid var(--border-color, #e2e8f0);
                                text-align: left;
                            }
                            .popup-table td {
                                padding: 8px 12px;
                                border: 1px solid var(--border-color, #e2e8f0);
                                color: var(--text-color, #334155);
                            }
                        </style>
                `;
                
                // 0. Requested Items
                if (data.mr_items && data.mr_items.length) {
                    html += `
                        <div class="detail-section" style="border-left: 4px solid var(--primary, #1b66ec);">
                            <div class="detail-title">
                                <span>Requested Items</span>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                    `;
                    data.mr_items.forEach(item => {
                        let item_quotes = data.sqs ? data.sqs.filter(q => q.item_code === item.item_code) : [];
                        let quotes_html = '';
                        if (item_quotes.length) {
                            quotes_html += `
                                <div style="margin-top: 8px; padding: 8px 12px; background: var(--fg-color, #f8fafc); border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0);">
                                    <div style="font-size: 11px; font-weight: 600; color: var(--text-muted, #64748b); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Supplier Quotes</div>
                                    <div style="display: flex; flex-direction: column; gap: 6px;">
                            `;
                            item_quotes.forEach(q => {
                                let sq_link = frappe.utils.get_form_link('Supplier Quotation', q.name);
                                quotes_html += `
                                    <div style="display: flex; justify-content: space-between; font-size: 12px; align-items: center;">
                                        <span>
                                            <a href="${sq_link}" target="_blank" style="color: var(--primary, #1b66ec); font-weight: 600; text-decoration: underline;">${q.supplier}</a>
                                            <span class="badge" style="background-color: #f1f5f9; color: #475569; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 6px;">${q.status}</span>
                                        </span>
                                        <span style="font-weight: 700; color: var(--text-color, #1e293b);">${frappe.format(q.rate, {fieldtype: 'Currency'})}</span>
                                    </div>
                                `;
                            });
                            quotes_html += `</div></div>`;
                        }

                        html += `
                            <div style="border-bottom: 1px dashed var(--border-color, #e2e8f0); padding-bottom: 8px; font-size: 13px;">
                                <div style="font-weight: 700; color: var(--text-color, #1e293b);">${item.item_name} <span style="font-weight: normal; color: var(--text-muted, #64748b);">(${item.item_code})</span></div>
                                <div style="margin-top: 4px; color: var(--text-color, #334155); white-space: pre-line; line-height: 1.4;">${item.custom_request_description || 'No description provided'}</div>
                                ${quotes_html}
                            </div>
                        `;
                    });
                    html += `</div></div>`;
                }

                // 1. RFQ Details
                if (data.rfq && data.rfq.length) {
                    data.rfq.forEach(rfq => {
                        let link = frappe.utils.get_form_link('Request for Quotation', rfq.name);
                        html += `
                            <div class="detail-section">
                                <div class="detail-title">
                                    <span>Request for Quotation: <a href="${link}" target="_blank" style="color: var(--primary, #1b66ec); font-weight: 700; text-decoration: underline;">${rfq.name}</a></span>
                                    <span class="badge" style="background-color: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 9999px;">${rfq.status}</span>
                                </div>
                                <div class="detail-grid">
                                    <div class="detail-item">
                                        <div class="detail-label">Recce Status</div>
                                        <div class="detail-value">${rfq.custom_recce_status || 'Pending'}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="detail-label">Dimensions</div>
                                        <div class="detail-value">${rfq.custom_recce_length || '0'}L x ${rfq.custom_recce_height || '0'}H x ${rfq.custom_recce_depth || '0'}D Ft</div>
                                    </div>
                                </div>
                        `;
                        if (rfq.custom_recce_photo_1 || rfq.custom_recce_photo_2) {
                            html += `
                                <div style="margin-top: 12px;">
                                    <div class="detail-label">Recce Photos</div>
                                    <div class="thumbnail-container">
                            `;
                            if (rfq.custom_recce_photo_1) {
                                html += `<a href="${rfq.custom_recce_photo_1}" target="_blank"><img src="${rfq.custom_recce_photo_1}" class="thumbnail-img"></a>`;
                            }
                            if (rfq.custom_recce_photo_2) {
                                html += `<a href="${rfq.custom_recce_photo_2}" target="_blank"><img src="${rfq.custom_recce_photo_2}" class="thumbnail-img"></a>`;
                            }
                            html += `</div></div>`;
                        }
                        html += `</div>`;
                    });
                } else {
                    html += `
                        <div class="detail-section" style="border-style: dashed; opacity: 0.6;">
                            <div class="detail-title" style="border-bottom: none; margin-bottom: 0; font-style: italic; font-weight: 500; color: var(--text-muted, #64748b);">No Request for Quotation linked yet.</div>
                        </div>
                    `;
                }

                // 2. Supplier Quotations
                if (data.sqs && data.sqs.length) {
                    html += `
                        <div class="detail-section">
                            <div class="detail-title">Supplier Quotations</div>
                            <table class="popup-table">
                                <thead>
                                    <tr>
                                        <th>Quotation</th>
                                        <th>Supplier</th>
                                        <th>Status</th>
                                        <th style="text-align: right;">Rate</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    data.sqs.forEach(sq => {
                        let link = frappe.utils.get_form_link('Supplier Quotation', sq.name);
                        html += `
                            <tr>
                                <td><a href="${link}" target="_blank" style="color: var(--primary, #1b66ec); font-weight: 700; text-decoration: underline;">${sq.name}</a></td>
                                <td>${sq.supplier}</td>
                                <td><span class="badge" style="background-color: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 9999px;">${sq.status}</span></td>
                                <td style="text-align: right; font-weight: 700; color: var(--primary, #1b66ec);">${frappe.format(sq.rate, {fieldtype: 'Currency'})}</td>
                            </tr>
                        `;
                    });
                    html += `</tbody></table></div>`;
                }

                // 2.5 Purchase Orders
                if (data.pos && data.pos.length) {
                    html += `
                        <div class="detail-section">
                            <div class="detail-title">Purchase Orders</div>
                            <table class="popup-table">
                                <thead>
                                    <tr>
                                        <th>Purchase Order</th>
                                        <th>Date</th>
                                        <th>Status</th>
                                        <th style="text-align: right;">Rate</th>
                                        <th style="text-align: right;">Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    data.pos.forEach(po => {
                        let link = frappe.utils.get_form_link('Purchase Order', po.name);
                        html += `
                            <tr>
                                <td><a href="${link}" target="_blank" style="color: var(--primary, #1b66ec); font-weight: 700; text-decoration: underline;">${po.name}</a></td>
                                <td>${po.date || '-'}</td>
                                <td><span class="badge" style="background-color: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 9999px;">${po.status}</span></td>
                                <td style="text-align: right; font-weight: 700; color: var(--text-color, #1e293b);">${frappe.format(po.rate, {fieldtype: 'Currency'})}</td>
                                <td style="text-align: right; font-weight: 700; color: var(--primary, #1b66ec);">${frappe.format(po.grand_total, {fieldtype: 'Currency'})}</td>
                            </tr>
                        `;
                    });
                    html += `</tbody></table></div>`;
                }

                // 3. Purchase Receipts
                if (data.prs && data.prs.length) {
                    data.prs.forEach(pr => {
                        let link = frappe.utils.get_form_link('Purchase Receipt', pr.name);
                        html += `
                            <div class="detail-section">
                                <div class="detail-title">
                                    <span>Purchase Receipt & QC: <a href="${link}" target="_blank" style="color: var(--primary, #1b66ec); font-weight: 700; text-decoration: underline;">${pr.name}</a></span>
                                    <span class="badge" style="background-color: #d1fae5; color: #065f46; padding: 4px 10px; border-radius: 9999px;">${pr.status}</span>
                                </div>
                                <div class="detail-grid">
                                    <div class="detail-item">
                                        <div class="detail-label">QC Dimensions</div>
                                        <div class="detail-value">${pr.custom_qc_length || '0'}L x ${pr.custom_qc_height || '0'}H x ${pr.custom_qc_depth || '0'}D Ft</div>
                                    </div>
                                </div>
                                <div style="margin-top: 10px;">
                                    <div class="detail-label">QC Notes</div>
                                    <div class="detail-value" style="font-weight: normal; background: var(--fg-color, #f8fafc); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0); margin-top: 4px; font-size: 13px;">${pr.custom_qc_notes || 'No notes added'}</div>
                                </div>
                        `;
                        if (pr.custom_qc_photo_1 || pr.custom_qc_photo_2) {
                            html += `
                                <div style="margin-top: 12px;">
                                    <div class="detail-label">QC Photos</div>
                                    <div class="thumbnail-container">
                            `;
                            if (pr.custom_qc_photo_1) {
                                html += `<a href="${pr.custom_qc_photo_1}" target="_blank"><img src="${pr.custom_qc_photo_1}" class="thumbnail-img"></a>`;
                            }
                            if (pr.custom_qc_photo_2) {
                                html += `<a href="${pr.custom_qc_photo_2}" target="_blank"><img src="${pr.custom_qc_photo_2}" class="thumbnail-img"></a>`;
                            }
                            html += `</div></div>`;
                        }
                        html += `</div>`;
                    });
                } else {
                    html += `
                        <div class="detail-section" style="border-style: dashed; opacity: 0.6;">
                            <div class="detail-title" style="border-bottom: none; margin-bottom: 0; font-style: italic; font-weight: 500; color: var(--text-muted, #64748b);">No Purchase Receipt (QC) recorded yet.</div>
                        </div>
                    `;
                }

                // 4. Asset Capitalizations
                if (data.capitalizations && data.capitalizations.length) {
                    data.capitalizations.forEach(ac => {
                        let link = frappe.utils.get_form_link('Asset Capitalization', ac.name);
                        html += `
                            <div class="detail-section">
                                <div class="detail-title">
                                    <span>Asset Capitalization: <a href="${link}" target="_blank" style="color: var(--primary, #1b66ec); font-weight: 700; text-decoration: underline;">${ac.name}</a></span>
                                    <span class="badge" style="background-color: #f3e8ff; color: #6b21a8; padding: 4px 10px; border-radius: 9999px;">${ac.status}</span>
                                </div>
                                <div class="detail-grid">
                                    <div class="detail-item">
                                        <div class="detail-label">Posting Date</div>
                                        <div class="detail-value">${ac.posting_date || '-'}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="detail-label">Installation Dimensions</div>
                                        <div class="detail-value">${ac.custom_installation_length || '0'}L x ${ac.custom_installation_height || '0'}H x ${ac.custom_installation_depth || '0'}D Ft</div>
                                    </div>
                                </div>
                                <div style="margin-top: 10px;">
                                    <div class="detail-label">Installation Notes</div>
                                    <div class="detail-value" style="font-weight: normal; background: var(--fg-color, #f8fafc); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0); margin-top: 4px; font-size: 13px;">${ac.custom_installation_notes || 'No installation notes added'}</div>
                                </div>
                        `;
                        if (ac.custom_installation_photo_1 || ac.custom_installation_photo_2) {
                            html += `
                                <div style="margin-top: 12px;">
                                    <div class="detail-label">Installation Photos</div>
                                    <div class="thumbnail-container">
                            `;
                            if (ac.custom_installation_photo_1) {
                                html += `<a href="${ac.custom_installation_photo_1}" target="_blank"><img src="${ac.custom_installation_photo_1}" class="thumbnail-img"></a>`;
                            }
                            if (ac.custom_installation_photo_2) {
                                html += `<a href="${ac.custom_installation_photo_2}" target="_blank"><img src="${ac.custom_installation_photo_2}" class="thumbnail-img"></a>`;
                            }
                            html += `</div></div>`;
                        }
                        html += `</div>`;
                    });
                }

                // 5. Assets Created
                if (data.assets && data.assets.length) {
                    html += `
                        <div class="detail-section">
                            <div class="detail-title">Assets Created</div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
                    `;
                    data.assets.forEach(asset => {
                        let link = frappe.utils.get_form_link('Asset', asset.name);
                        html += `
                            <div style="border: 1px solid var(--border-color, #e2e8f0); border-radius: 8px; padding: 12px; background: var(--fg-color, #f8fafc); display: flex; flex-direction: column; justify-content: space-between; gap: 8px;">
                                <div>
                                    <div style="font-size: 13px; font-weight: 700;"><a href="${link}" target="_blank" style="color: var(--primary, #1b66ec); text-decoration: underline;">${asset.name}</a></div>
                                    <div style="font-size: 12px; color: var(--text-muted, #64748b); font-weight: 500; margin-top: 2px;">${asset.asset_name}</div>
                                </div>
                                <div>
                                    <span class="badge" style="background-color: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Status: ${asset.status}</span>
                                </div>
                            </div>
                        `;
                    });
                    html += `</div></div>`;
                }

                html += `</div>`;
                
                d.fields_dict.details_html.$wrapper.html(html);
                d.show();
            }
        });
    };
}
"""

def update_client_scripts():
    # 1. Update Request for Quotation client script
    rfq_cs = frappe.get_doc("Client Script", "RFQ Recce Timestamp")
    rfq_cs.script = RFQ_SCRIPT + "\n" + GLOBAL_POPUP_JS
    rfq_cs.save(ignore_permissions=True)
    print("Updated RFQ Recce Timestamp Client Script")

    # 2. Update Supplier Quotation client script
    sq_cs = frappe.get_doc("Client Script", "Supplier Quotation Recce Fetch")
    sq_cs.script = SQ_SCRIPT + "\n" + GLOBAL_POPUP_JS
    sq_cs.save(ignore_permissions=True)
    print("Updated Supplier Quotation Recce Fetch Client Script")

    # 3. Create or update Purchase Order client script
    if frappe.db.exists("Client Script", "Purchase Order MR Details"):
        po_cs = frappe.get_doc("Client Script", "Purchase Order MR Details")
    else:
        po_cs = frappe.new_doc("Client Script")
        po_cs.name = "Purchase Order MR Details"
        po_cs.dt = "Purchase Order"
        po_cs.view = "Form"
        po_cs.enabled = 1
        po_cs.module = "Swift Fix"
        
    po_cs.script = PO_SCRIPT + "\n" + GLOBAL_POPUP_JS
    po_cs.save(ignore_permissions=True)
    print("Updated Purchase Order MR Details Client Script")
    
    # 4. Create or update Asset client script
    if frappe.db.exists("Client Script", "Asset Procurement HTML"):
        asset_cs = frappe.get_doc("Client Script", "Asset Procurement HTML")
    else:
        asset_cs = frappe.new_doc("Client Script")
        asset_cs.name = "Asset Procurement HTML"
        asset_cs.dt = "Asset"
        asset_cs.view = "Form"
        asset_cs.enabled = 1
        asset_cs.module = "Swift Fix"
        
    asset_cs.script = ASSET_SCRIPT + "\n" + GLOBAL_POPUP_JS
    asset_cs.save(ignore_permissions=True)
    print("Updated Asset Procurement HTML Client Script")
    
    frappe.db.commit()

if __name__ == "__main__":
    update_client_scripts()
