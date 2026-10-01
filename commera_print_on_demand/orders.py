import frappe
from frappe import _
from frappe.query_builder import DocType

from commera_print_on_demand import provider

CANCELLABLE_STATUSES = ("Queued", "Submitted")


def on_order_placed(event):
	if frappe.db.get_value("Sales Order", event.sales_order, "docstatus") == 2:
		return

	jobs_by_line = {
		job.sales_order_item: job
		for job in frappe.get_all(
			"POD Job",
			filters={"sales_order": event.sales_order},
			fields=["name", "sales_order_item", "status"],
		)
	}
	for line in get_print_lines(event.sales_order):
		job = jobs_by_line.get(line.name)
		if job and job.status != "Queued":
			continue
		job_name = job.name if job else add_job(event, line)
		provider_order_id = provider.create_order(line.name, line.product_id, line.qty)
		frappe.db.set_value(
			"POD Job", job_name, {"status": "Submitted", "provider_order_id": provider_order_id}
		)
		# Each line's job is saved once the provider holds it, so a failure on a later line never orphans it.
		frappe.db.commit()


def get_print_lines(sales_order: str) -> list:
	sales_order_item = DocType("Sales Order Item")
	item = DocType("Item")
	return (
		frappe.qb.from_(sales_order_item)
		.join(item)
		.on(item.name == sales_order_item.item_code)
		.select(
			sales_order_item.name,
			sales_order_item.item_code,
			sales_order_item.qty,
			item.commera_print_on_demand_product_id.as_("product_id"),
		)
		.where((sales_order_item.parent == sales_order) & (item.commera_print_on_demand_enabled == 1))
		.orderby(sales_order_item.idx)
		.run(as_dict=True)
	)


def add_job(event, line) -> str:
	job = frappe.new_doc("POD Job")
	job.update(
		{
			"sales_order": event.sales_order,
			"sales_order_item": line.name,
			"item_code": line.item_code,
			"product_id": line.product_id,
			"qty": line.qty,
			"event_id": event.id,
		}
	)
	job.insert()
	return job.name


def before_order_cancel(sales_order):
	if frappe.db.exists("POD Job", {"sales_order": sales_order.name, "status": "In Production"}):
		return _("Your print is already in production, so this order can't be cancelled.")
	return None


def on_order_cancelled(event):
	jobs = frappe.get_all(
		"POD Job",
		filters={"sales_order": event.sales_order, "status": ["in", CANCELLABLE_STATUSES]},
		fields=["name", "provider_order_id"],
	)
	for job in jobs:
		if job.provider_order_id:
			provider.cancel_order(job.provider_order_id)
		frappe.db.set_value("POD Job", job.name, "status", "Cancelled")


def on_order_fulfilled(event):
	set_job_status(event.sales_order, "Shipped", ("Submitted", "In Production"))


def on_order_delivered(event):
	set_job_status(event.sales_order, "Delivered", ("Submitted", "In Production", "Shipped"))


def set_job_status(sales_order: str, status: str, from_statuses: tuple[str, ...]):
	frappe.db.set_value(
		"POD Job", {"sales_order": sales_order, "status": ["in", from_statuses]}, "status", status
	)
