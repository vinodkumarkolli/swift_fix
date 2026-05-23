# Swift Fix

A premium Computerized Maintenance Management System (CMMS) custom Frappe application designed for **Sravi Enterprises**.

---

## 1. Overview of the Application

Swift Fix automates the lifecycle of capital equipment and fixed assets through a custom business flow called **Procurement-based Asset Deployment**. This workflow spans initial procurement intent, vendor quotes and Recce processing, contract terms commitments, receipt serialization, asset generation, and final field deployment (capitalization).

Additionally, Swift Fix supports a **Stock-led Asset Flow (Non-procurement Flow)** to fast-track the creation and deployment of assets using existing warehouse stock without going through the purchasing pipeline.

### The Procurement-based Asset Deployment Lifecycle

```mermaid
flowchart TD
    subgraph Procurement Lifecycle
        MR[Material Request<br><b>Intent of Procuring</b>] --> RFQ[Request for Quotation]
        RFQ --> SQ[Sales Quotation<br><i>Supplier Quotation</i>]
        SQ --> PO[Purchase Order<br><b>Terms of Procuring</b>]
    end

    subgraph Receipt & Serialization
        PO --> PR[Purchase Receipt<br><i>Completion of Mfg</i>]
        PR -->|Simultaneous Creation<br>PR/Item Link| Asset[Asset<br><b>Completion of Procurement</b>]
    end

    subgraph Deployment
        PR & Asset --> AC[Asset Capitalisation<br><b>Deployment of Item</b>]
    end

    style MR fill:#f9f,stroke:#333,stroke-width:2px
    style PO fill:#bbf,stroke:#333,stroke-width:2px
    style Asset fill:#bfb,stroke:#333,stroke-width:2px
    style AC fill:#fbb,stroke:#333,stroke-width:2px
```

---

## 2. Core Features & Business Logic

### 1. Material Request (MR)
- **Fixed Asset Enforcement**: Validates that only items marked as `is_fixed_asset = 1` are permitted in Material Requests.
- **Button Hiding Rules**: Standard "Purchase Order" and "Supplier Quotation" buttons are hidden on the MR form to prevent direct creation bypassing the RFQ stage.
- **Status Banner**: Displays the custom processing status (`Draft`, `Shortlisted`, `Under Process`, `Item Received`, `Asset Capitalised`, `Cancelled`, `Held`) dynamically in the UI without modifying the document state.

### 2. Request for Quotation (RFQ) & Supplier Quotation (SQ)
- **Pre-requisite Validation**: An RFQ can only be saved and submitted if all unique linked Material Requests (referenced in the `items` child table) have a custom processing status of **Shortlisted**.
- **Dynamic HTML Banner**: Displays linked Material Request details dynamically in a premium HTML field (`custom_mr_html`) on both RFQ and SQ forms, supporting multiple MR cards if needed.
- **Timeline Commenting**: Automatically logs a comment on all unique linked MR timelines: *"A Quotation is requested from Vendor and Recce Process is in Progress"*.

### 3. Purchase Order (PO)
- **Under Process Transition**: Submission of the PO automatically transitions the linked Material Request status to **Under Process** (unless Purchase Receipts or Assets already exist for it).
- **Status Locks**: Active POs prevent the linked Material Request from being cancelled or placed on hold.

### 4. Purchase Receipt (PR) & Asset Generation
- **Automatic Serialization**: Submission of a Purchase Receipt automatically generates a unique serial number (`[Item Code]-[Hash]`) for the item and updates the row.
- **Simultaneous Asset Creation**: Automatically generates and saves the corresponding **Asset** linked to the Purchase Receipt.
- **Procurement Details View**: Displays the linked Material Request, Purchase Order, Purchase Receipt, and Asset Capitalization details dynamically in a premium HTML field (`custom_procurement_html`) on the Asset form.
- **Completion Hook**: Completes the Purchase Order status and transitions the linked Material Request status to **Item Received**.

### 5. Asset QR Code Generation
- Automatically generates a QR code URL (`/app/asset-maintenance-log/new-asset-maintenance-log?asset=[Asset_Name]`) and attaches the PNG image to the Asset document upon creation (`after_insert`).

### 6. Asset Capitalization & Purchase Invoice Validation
- **Purchase Invoice Constraint**: Submission of a Purchase Invoice is blocked if the corresponding Purchase Receipt items haven't been capitalized through an `Asset Capitalization` document first.
- **Capitalization Hook**: Submission of an `Asset Capitalization` document transitions the linked Material Request status to **Asset Capitalised**.

### 7. Stock-led Asset Flow (Non-Procurement)
- **Simplified Workflow**: Allows creating Fixed Assets directly from regular stocked items (`maintain_stock = 1`, `is_fixed_asset = 0`) via `Asset Capitalization` (consuming items from a specified Warehouse using the `stock_items` child table).
- **Target Location Validation**: Enforces that a `target_asset_location` is supplied before the capitalization can be saved or submitted.
- **Automated Lifecycle Hooks**:
  - Automatically generates a draft **Asset** at the specified location upon saving.
  - Automatically submits the target Asset when the Asset Capitalization is submitted.
  - Automatically cancels the target Asset if the Asset Capitalization is cancelled.
- **Context-Aware Global UI**: The global detail popup widget detects stock-led assets and hides all procurement-specific timeline cards (RFQ, SQ, PO, PR) to focus exclusively on Stock Consumption, Capitalization details, and Asset information.

---

## 3. Architecture & File Structure

The application's backend architecture is designed around a single, consolidated utility module to maximize code reuse, stability, and maintainability.

```
swift_fix/
├── fixtures/
│   ├── client_script.json   # Client-side scripts for forms (RFQ, SQ, PO, Asset, etc.)
│   └── custom_field.json    # Custom fields registered for ERPNext/Frappe DocTypes
├── scratch/
│   └── update_client_scripts.py # Helper script to patch/update client scripts in database
└── setup/
    ├── utils.py             # Single Source of Truth for core procurement/asset utility logic
    ├── popr_utils.py        # Lifecycle hooks & validations delegate for PO, PR, and AC
    ├── rfq_utils.py         # RFQ-specific workflows & Recce updates
    └── mr_utils.py          # Material Request validation & transition rules
```

### Key Modules:
* **`setup/utils.py`**: The unified code repository for document-agnostic history generation (`get_asset_html`, `get_historic_flow_details`) and core state verification. All legacy formatting methods have been refactored and consolidated here.
* **`setup/popr_utils.py`**: Intercepts document events for Purchase Order, Purchase Receipt, Asset Capitalization, and Purchase Invoice. Uses backend helpers from `utils.py`.
* **`setup/rfq_utils.py`**: Manages RFQ state checks, Supplier Quotation mappings, and Recce updates.
* **`setup/mr_utils.py`**: Enforces strict validation rules and status updates for Material Requests.

---

## 4. Installation

Install Swift Fix using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd /path/to/your/frappe-bench
bench get-app https://github.com/vinodkumarkolli/swift_fix.git --branch develop
bench --site [your-site-name] install-app swift_fix
```

---

## 5. Developer Utilities & Test Execution

### Running Automated Integration Tests

Swift Fix includes a comprehensive test suite covering the entire procurement flow, security and permissions checks, status transitions, and data validations.

To run the entire test suite:

```bash
bench --site cmms.localhost run-tests --app swift_fix
```

To run a specific test step/module individually (e.g. MR or PO):

```bash
bench --site cmms.localhost run-tests --app swift_fix --class Test06MR
```

### Database Migration & Clearing Cache

When pulls or modifications are made to hook structures, custom fields, client scripts, or role configurations, apply them by running:

```bash
bench --site [your-site-name] migrate
bench --site [your-site-name] clear-cache
```

### Exporting App Fixtures

If custom fields, role permissions, or client scripts are updated in the desk, export them to git-trackable fixtures using:

```bash
bench --site [your-site-name] export-fixtures
```

---

## 6. Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/swift_fix
pre-commit install
```

Code quality and formatting checks are governed by:
- **Ruff** (Python formatting and linting)
- **ESLint & Prettier** (JS structure and styling)
- **Pyupgrade** (Python syntax upgrades)

---

## 7. License

This project is licensed under the [MIT License](license.txt).
