app_name = "commera_print_on_demand"
app_title = "Print on Demand"
app_publisher = "BWH Tech"
app_description = "Print-on-demand connector for Commera (example app)"
app_email = "dev@bwh.tech"
app_license = "mit"

required_apps = ["commera"]

after_install = "commera_print_on_demand.install.add_custom_fields"
after_migrate = "commera_print_on_demand.install.add_custom_fields"

commera_api_version = [1]

commera_order_placed = ["commera_print_on_demand.orders.on_order_placed"]
commera_order_cancelled = ["commera_print_on_demand.orders.on_order_cancelled"]
commera_order_fulfilled = ["commera_print_on_demand.orders.on_order_fulfilled"]
commera_order_delivered = ["commera_print_on_demand.orders.on_order_delivered"]

doc_events = {"Sales Order": {"before_cancel": "commera_print_on_demand.orders.before_order_cancel"}}
