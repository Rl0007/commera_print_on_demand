from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "Commera Print On Demand"


def add_custom_fields():
	create_custom_fields(
		{
			"Item": [
				{
					"fieldname": "commera_print_on_demand_enabled",
					"label": "Print on Demand",
					"fieldtype": "Check",
					"insert_after": "stock_uom",
					"module": MODULE,
					"description": "Orders for this item are sent to the print provider.",
				},
				{
					"fieldname": "commera_print_on_demand_product_id",
					"label": "Print Provider Product ID",
					"fieldtype": "Data",
					"insert_after": "commera_print_on_demand_enabled",
					"depends_on": "commera_print_on_demand_enabled",
					"module": MODULE,
				},
			]
		},
		update=True,
	)
