app_name = "swift_fix"
app_title = "Swift Fix"
app_publisher = "Vinod Kumar K"
app_description = "A CMMS solution for Sravi Enterprises"
app_email = "vinodkumarkolli@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "swift_fix",
# 		"logo": "/assets/swift_fix/logo.png",
# 		"title": "Swift Fix",
# 		"route": "/swift_fix",
# 		"has_permission": "swift_fix.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/swift_fix/css/swift_fix.css"
# app_include_js = "/assets/swift_fix/js/swift_fix.js"

# include js, css files in header of web template
# web_include_css = "/assets/swift_fix/css/swift_fix.css"
# web_include_js = "/assets/swift_fix/js/swift_fix.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "swift_fix/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "swift_fix/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "swift_fix.utils.jinja_methods",
# 	"filters": "swift_fix.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "swift_fix.install.before_install"
# after_install = "swift_fix.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "swift_fix.uninstall.before_uninstall"
# after_uninstall = "swift_fix.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "swift_fix.utils.before_app_install"
# after_app_install = "swift_fix.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "swift_fix.utils.before_app_uninstall"
# after_app_uninstall = "swift_fix.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "swift_fix.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "swift_fix.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Material Request": {
		"validate": "swift_fix.setup.mr_utils.validate_mr"
	},
	"Request for Quotation": {
		"validate": "swift_fix.setup.rfq_update.validate_rfq",
		"on_submit": "swift_fix.setup.rfq_update.on_rfq_submit"
	},
	"Purchase Order": {
		"on_submit": "swift_fix.setup.popr_utils.on_po_submit"
	},
	"Purchase Receipt": {
		"on_submit": [
			"swift_fix.setup.popr_utils.on_pr_submit",
			"swift_fix.setup.popr_utils.create_purchase_receipt_serial_nos"
		]
	},
	"Asset Capitalization": {
		"on_submit": "swift_fix.setup.popr_utils.on_asset_capitalization_submit"
	},
	"Asset": {
		"after_insert": "swift_fix.setup.popr_utils.generate_asset_qr"
	},
	"Purchase Invoice": {
		"before_submit": "swift_fix.setup.popr_utils.check_purchase_invoice_capitalization"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"swift_fix.tasks.all"
# 	],
# 	"daily": [
# 		"swift_fix.tasks.daily"
# 	],
# 	"hourly": [
# 		"swift_fix.tasks.hourly"
# 	],
# 	"weekly": [
# 		"swift_fix.tasks.weekly"
# 	],
# 	"monthly": [
# 		"swift_fix.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "swift_fix.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "swift_fix.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "swift_fix.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "swift_fix.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["swift_fix.utils.before_request"]
# after_request = ["swift_fix.utils.after_request"]

# Job Events
# ----------
# before_job = ["swift_fix.utils.before_job"]
# after_job = ["swift_fix.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"swift_fix.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

fixtures = [
    {"doctype": "Custom Field", "filters":{"module":["in",["Swift Fix"]]}},
    {"doctype": "Client Script"},
    {"doctype": "Role"},
    # {"doctype": "Custom DocPerm"}
]

after_install = "swift_fix.setup.install.after_install"
after_migrate = "swift_fix.setup.install.after_migrate"