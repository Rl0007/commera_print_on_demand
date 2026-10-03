import frappe
from frappe import _
from frappe.utils.data import cint

from commera_print_on_demand.orders import RESENDABLE_STATUSES, send_print_jobs

JOB_STATUSES = ("Queued", "Submitted", "In Production", "Shipped", "Delivered", "Cancelled")
PROVIDER_ORDER_STATUSES = ("Received", "In Production", "Shipped", "Cancelled")
JOB_FIELDS = [
	"name",
	"sales_order",
	"item_code",
	"product_id",
	"qty",
	"status",
	"provider_order_id",
	"creation",
]


@frappe.whitelist(methods=["GET"])
def get_jobs(status: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	if status and status not in JOB_STATUSES:
		frappe.throw(_("Status must be one of {0}.").format(", ".join(JOB_STATUSES)))

	rows = frappe.get_list(
		"POD Job",
		filters={"status": status} if status else {},
		fields=JOB_FIELDS,
		order_by="creation desc",
		start=cint(start),
		page_length=cint(page_length),
	)
	counts = {
		row.status: cint(row.count)
		for row in frappe.get_list(
			"POD Job",
			fields=["status", {"COUNT": "*", "as": "count"}],
			group_by="status",
			order_by="status asc",
		)
	}
	return {
		"rows": rows,
		"total": counts.get(status, 0) if status else sum(counts.values()),
		"counts": {job_status: counts.get(job_status, 0) for job_status in JOB_STATUSES},
	}


@frappe.whitelist(methods=["GET"])
def get_job(name: str) -> dict:
	jobs = frappe.get_list("POD Job", filters={"name": name}, fields=JOB_FIELDS, limit=1)
	if not jobs:
		frappe.throw(_("POD Job {0} not found.").format(name), frappe.DoesNotExistError)

	job = jobs[0]
	provider_orders = job.provider_order_id and frappe.get_list(
		"POD Provider Order",
		filters={"name": job.provider_order_id},
		fields=["name", "external_id", "product_id", "qty", "status", "creation"],
		limit=1,
	)
	job.provider_order = provider_orders[0] if provider_orders else None
	return job


@frappe.whitelist(methods=["GET"])
def get_order_print_jobs(sales_order: str) -> list[dict]:
	frappe.has_permission("Sales Order", "read", sales_order, throw=True)
	return frappe.get_list(
		"POD Job",
		filters={"sales_order": sales_order},
		fields=["name", "item_code", "qty", "status", "provider_order_id"],
		order_by="creation asc",
	)


@frappe.whitelist(methods=["POST"])
def resend_order(name: str) -> str:
	frappe.has_permission("POD Job", "write", throw=True)
	sent = send_print_jobs(name, RESENDABLE_STATUSES)
	if not sent:
		frappe.throw(_("Order {0} has no print jobs waiting for the printer.").format(name))
	if sent == 1:
		return _("Sent 1 print job to the printer.")
	return _("Sent {0} print jobs to the printer.").format(sent)


@frappe.whitelist(methods=["GET"])
def get_provider_orders(status: str | None = None, start: int = 0, page_length: int = 20) -> dict:
	if status and status not in PROVIDER_ORDER_STATUSES:
		frappe.throw(_("Status must be one of {0}.").format(", ".join(PROVIDER_ORDER_STATUSES)))

	rows = frappe.get_list(
		"POD Provider Order",
		filters={"status": status} if status else {},
		fields=["name", "external_id", "product_id", "qty", "status", "creation"],
		order_by="creation desc",
		start=cint(start),
		page_length=cint(page_length),
	)
	jobs = get_jobs_by_provider_order([row.name for row in rows])
	for row in rows:
		row.job = jobs.get(row.name)

	counts = {
		row.status: cint(row.count)
		for row in frappe.get_list(
			"POD Provider Order",
			fields=["status", {"COUNT": "*", "as": "count"}],
			group_by="status",
			order_by="status asc",
		)
	}
	return {
		"rows": rows,
		"total": counts.get(status, 0) if status else sum(counts.values()),
		"counts": {order_status: counts.get(order_status, 0) for order_status in PROVIDER_ORDER_STATUSES},
	}


def get_jobs_by_provider_order(provider_orders: list[str]) -> dict[str, str]:
	if not provider_orders:
		return {}
	return dict(
		frappe.get_list(
			"POD Job",
			filters={"provider_order_id": ["in", provider_orders]},
			fields=["provider_order_id", "name"],
			as_list=True,
		)
	)
