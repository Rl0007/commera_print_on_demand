import frappe

from commera_print_on_demand.orders import RESENDABLE_STATUSES


def has_print_jobs(doctype: str, name: str) -> bool:
	return bool(frappe.db.exists("POD Job", {"sales_order": name}))


def has_resendable_jobs(doctype: str, name: str) -> bool:
	return frappe.has_permission("POD Job", "write") and bool(
		frappe.db.exists("POD Job", {"sales_order": name, "status": ["in", RESENDABLE_STATUSES]})
	)
