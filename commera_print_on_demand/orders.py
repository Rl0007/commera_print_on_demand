import frappe
from commera.sdk import STORE_ORDER_TYPE, orders
from frappe import _

from commera_print_on_demand import provider

CANCELLABLE_STATUSES = ("Queued", "Submitted")
RESENDABLE_STATUSES = ("Queued", "Submitted")


def on_order_placed(event):
	send_print_jobs(event.sales_order, ("Queued",), event_id=event.id)


def send_print_jobs(sales_order: str, statuses: tuple[str, ...], event_id: str | None = None) -> int:
	"""Sends each print line with no job yet, or whose job is in `statuses`. The provider is idempotent per
	line, so sending a job it already holds returns the same provider order."""
	order = orders.get_order(sales_order)
	if order["is_cancelled"]:
		return 0

	jobs_by_line = {
		job.sales_order_item: job
		for job in frappe.get_all(
			"POD Job",
			filters={"sales_order": sales_order},
			fields=["name", "sales_order_item", "status"],
		)
	}
	sent = 0
	for line in get_print_lines(order):
		job = jobs_by_line.get(line["line_id"])
		if job and job.status not in statuses:
			continue
		job_name = job.name if job else add_job(sales_order, line, event_id)
		provider_order_id = provider.create_order(line["line_id"], line["product_id"], line["qty"])
		frappe.db.set_value(
			"POD Job", job_name, {"status": "Submitted", "provider_order_id": provider_order_id}
		)
		# Each line's job is saved once the provider holds it, so a failure on a later line never orphans it.
		frappe.db.commit()
		sent += 1
	return sent


def get_print_lines(order) -> list[dict]:
	product_ids = dict(
		frappe.get_all(
			"Item",
			filters={
				"name": ["in", list({line["item_code"] for line in order["items"]})],
				"commera_print_on_demand_enabled": 1,
			},
			fields=["name", "commera_print_on_demand_product_id"],
			as_list=True,
		)
	)
	return [
		{**line, "product_id": product_ids[line["item_code"]]}
		for line in order["items"]
		if line["item_code"] in product_ids
	]


def add_job(sales_order: str, line: dict, event_id: str | None) -> str:
	job = frappe.new_doc("POD Job")
	job.update(
		{
			"sales_order": sales_order,
			"sales_order_item": line["line_id"],
			"item_code": line["item_code"],
			"product_id": line["product_id"],
			"qty": line["qty"],
			"event_id": event_id,
		}
	)
	job.insert()
	return job.name


def before_order_cancel(sales_order, method=None):
	if sales_order.order_type != STORE_ORDER_TYPE:
		return
	if frappe.db.exists("POD Job", {"sales_order": sales_order.name, "status": "In Production"}):
		frappe.throw(_("Your print is already in production, so this order can't be cancelled."))


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
