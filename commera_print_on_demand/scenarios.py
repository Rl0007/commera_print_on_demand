"""Devbox scenarios: bench --site dev.localhost execute commera_print_on_demand.scenarios.run --kwargs "{'only': [1]}" """

import time

import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.utils import now_datetime

from commera_print_on_demand import provider

COMPANY = "Lifestyle Demo"
CUSTOMER = "ZZ POD Customer"
CONTACT_EMAIL = "pod.shopper@example.com"
ITEM = "ZZ-POD-MUG"
PLAIN_ITEM = "ZZ-HOOKS-DEMO-TEE"
PRICE_LIST = "Standard Selling"
APP = "commera_print_on_demand"


def run(only=None):
	frappe.set_user("Administrator")
	scenarios = {
		1: placed_once,
		2: provider_down_then_retried,
		3: cancel_refused_in_production,
		4: cancel_goes_through,
		5: fulfil_with_delivery_note,
		6: fulfil_with_shipping_request,
	}
	for number in only or scenarios:
		print(f"\n=== scenario {number}: {scenarios[number].__name__}")
		try:
			scenarios[number]()
		except Exception:
			frappe.db.rollback()
			print("SCENARIO ERROR", frappe.get_traceback())


def placed_once():
	sales_order = new_cod_order()
	delivery = wait_for_delivery(sales_order, "order_placed", "Done")
	print("first delivery", delivery)
	print("jobs", get_jobs(sales_order))

	# Re-deliver the same event, the way at-least-once delivery may.
	frappe.db.set_value(
		"Commera Event Delivery", delivery.name, {"status": "Queued", "next_retry_at": now_datetime()}
	)
	frappe.db.commit()
	trigger_due_deliveries()
	print("re-delivery", wait_for_delivery(sales_order, "order_placed", "Done", min_attempts=2))
	print("jobs after re-delivery", get_jobs(sales_order))
	print("provider orders", get_provider_orders(sales_order))


def provider_down_then_retried():
	provider.set_failures(2)
	sales_order = new_cod_order()
	for attempt in (1, 2):
		delivery = wait_for_delivery(sales_order, "order_placed", "Queued", min_attempts=attempt)
		print(f"after attempt {attempt}:", delivery, "| now", now_datetime())
		print("  jobs", get_jobs(sales_order), "| error", get_error_title(delivery.last_error))
		frappe.db.set_value("Commera Event Delivery", delivery.name, "next_retry_at", now_datetime())
		frappe.db.commit()
		trigger_due_deliveries()
	print("after attempt 3:", wait_for_delivery(sales_order, "order_placed", "Done", min_attempts=3))
	print("jobs", get_jobs(sales_order))
	print("provider orders", get_provider_orders(sales_order))


def cancel_refused_in_production():
	from commera.api.orders import cancel_order

	sales_order = new_cod_order()
	wait_for_delivery(sales_order, "order_placed", "Done")
	job = get_jobs(sales_order)[0]
	provider.start_production(job.provider_order_id)
	frappe.db.commit()
	print("before cancel", get_jobs(sales_order), get_provider_orders(sales_order))

	owner = frappe.db.get_value("Sales Order", sales_order, "owner")
	frappe.set_user(owner)
	try:
		cancel_order(sales_order)
		print("UNEXPECTED: cancel went through")
	except frappe.ValidationError as exception:
		print("refused:", type(exception).__name__, "|", exception)
	frappe.db.rollback()
	frappe.set_user("Administrator")
	frappe.local.message_log = []

	time.sleep(5)
	frappe.db.rollback()
	print("docstatus", frappe.db.get_value("Sales Order", sales_order, "docstatus"))
	print("after refusal", get_jobs(sales_order), get_provider_orders(sales_order))
	print("events", get_events(sales_order))


def cancel_goes_through():
	from commera.api.orders import cancel_order

	sales_order = new_cod_order()
	wait_for_delivery(sales_order, "order_placed", "Done")
	print("before cancel", get_jobs(sales_order))
	frappe.set_user(frappe.db.get_value("Sales Order", sales_order, "owner"))
	cancel_order(sales_order)
	frappe.db.commit()
	frappe.set_user("Administrator")
	print("docstatus", frappe.db.get_value("Sales Order", sales_order, "docstatus"))
	print("cancelled delivery", wait_for_delivery(sales_order, "order_cancelled", "Done"))
	print("after cancel", get_jobs(sales_order), get_provider_orders(sales_order))


def fulfil_with_delivery_note():
	sales_order = new_cod_order()
	wait_for_delivery(sales_order, "order_placed", "Done")
	submit_order(sales_order)
	delivery_note = make_delivery_note(sales_order)
	delivery_note.insert()
	delivery_note.submit()
	frappe.db.commit()
	print("delivery note", delivery_note.name)
	wait_for_delivery(sales_order, "order_delivered", "Done")
	print("ecommerce status", frappe.db.get_value("Sales Order", sales_order, "custom_ecommerce_status"))
	print("events", get_events(sales_order))
	print("jobs", get_jobs(sales_order))


def fulfil_with_shipping_request():
	sales_order = new_cod_order()
	wait_for_delivery(sales_order, "order_placed", "Done")
	submit_order(sales_order)
	delivery_note = make_delivery_note(sales_order)
	delivery_note.insert()
	delivery_note.submit()
	# No carrier is configured on the devbox, so validate() can't run: insert the carrier's row directly
	# and fire the same on_update a tracking webhook would.
	shipping_request = frappe.new_doc("Shipping Request")
	shipping_request.update(
		{
			"status": "In Transit",
			"ref_doctype": "Sales Order",
			"ref_docname": sales_order,
			"delivery_note": delivery_note.name,
			"company": COMPANY,
		}
	)
	shipping_request.set_new_name()
	shipping_request.db_insert()
	shipping_request.run_method("on_update")
	frappe.db.commit()
	wait_for_delivery(sales_order, "order_fulfilled", "Done")
	print("after In Transit", get_jobs(sales_order), "| events", get_events(sales_order))
	shipping_request.db_set("status", "Delivered")
	shipping_request.run_method("on_update")
	frappe.db.commit()
	wait_for_delivery(sales_order, "order_delivered", "Done")
	print("after Delivered", get_jobs(sales_order), "| events", get_events(sales_order))


def submit_order(sales_order: str):
	order = frappe.get_doc("Sales Order", sales_order)
	order.submit()
	frappe.db.commit()


def ensure_data() -> str:
	if not frappe.db.exists("Customer", CUSTOMER):
		customer = frappe.new_doc("Customer")
		customer.update({"customer_name": CUSTOMER, "customer_type": "Individual"})
		customer.insert()
	contact = frappe.db.get_value("Contact", {"email_id": CONTACT_EMAIL}, "name")
	if not contact:
		contact_doc = frappe.new_doc("Contact")
		contact_doc.first_name = "POD Shopper"
		contact_doc.append("email_ids", {"email_id": CONTACT_EMAIL, "is_primary": 1})
		contact_doc.append("links", {"link_doctype": "Customer", "link_name": CUSTOMER})
		contact_doc.insert()
		contact = contact_doc.name
	if not frappe.db.exists("Item", ITEM):
		item = frappe.new_doc("Item")
		item.update(
			{
				"item_code": ITEM,
				"item_name": "POD Photo Mug",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"commera_print_on_demand_enabled": 1,
				"commera_print_on_demand_product_id": "printful-mug-11oz",
			}
		)
		item.insert()
	if not frappe.db.exists("Item Price", {"item_code": ITEM, "price_list": PRICE_LIST}):
		item_price = frappe.new_doc("Item Price")
		item_price.update({"item_code": ITEM, "price_list": PRICE_LIST, "price_list_rate": 400})
		item_price.insert()
	frappe.db.commit()
	return contact


def new_cod_order() -> str:
	from commera.api.payments import place_cod_order

	contact = ensure_data()
	items = [{"item_code": ITEM, "qty": 1}]
	if frappe.db.exists("Item Price", {"item_code": PLAIN_ITEM, "price_list": PRICE_LIST}):
		items.append({"item_code": PLAIN_ITEM, "qty": 1})
	quotation = frappe.new_doc("Quotation")
	quotation.update(
		{
			"quotation_to": "Customer",
			"party_name": CUSTOMER,
			"company": COMPANY,
			"order_type": "Shopping Cart",
			"contact_person": contact,
			"contact_email": CONTACT_EMAIL,
			"currency": "INR",
			"conversion_rate": 1,
			"selling_price_list": PRICE_LIST,
			"price_list_currency": "INR",
			"plc_conversion_rate": 1,
			"items": items,
		}
	)
	quotation.flags.ignore_permissions = True
	quotation.insert()
	sales_order = place_cod_order(quotation.name)
	frappe.db.commit()
	print("placed COD order", sales_order.name, "lines", [row.item_code for row in sales_order.items])
	return sales_order.name


def trigger_due_deliveries():
	from commera.plugin_events import run_due_deliveries

	run_due_deliveries()
	# run_due_deliveries enqueues after commit.
	frappe.db.commit()


def wait_for_delivery(sales_order: str, event: str, status: str, min_attempts: int = 1, timeout: int = 60):
	started = time.time()
	delivery = None
	while time.time() - started < timeout:
		frappe.db.rollback()
		delivery = get_delivery(sales_order, event)
		if delivery and delivery.status == status and delivery.attempts >= min_attempts:
			delivery.waited_seconds = round(time.time() - started, 1)
			return delivery
		time.sleep(1)
	raise TimeoutError(f"{event} delivery for {sales_order} never reached {status}: {delivery}")


def get_delivery(sales_order: str, event: str):
	deliveries = frappe.get_all(
		"Commera Event Delivery",
		filters={"parent": f"{sales_order}-{event}", "app": APP},
		fields=["name", "status", "attempts", "next_retry_at", "last_error", "finished_at"],
	)
	return deliveries[0] if deliveries else None


def get_jobs(sales_order: str) -> list:
	return frappe.get_all(
		"POD Job",
		filters={"sales_order": sales_order},
		fields=["name", "status", "provider_order_id", "event_id"],
		order_by="creation",
	)


def get_provider_orders(sales_order: str) -> list:
	return frappe.get_all(
		"POD Provider Order",
		filters={"external_id": ["in", [job.sales_order_item for job in get_job_lines(sales_order)]]},
		fields=["name", "status"],
	)


def get_job_lines(sales_order: str) -> list:
	return frappe.get_all(
		"Sales Order Item", filters={"parent": sales_order}, fields=["name as sales_order_item"]
	)


def get_events(sales_order: str) -> list:
	events = frappe.get_all(
		"Commera Event",
		filters={"reference_doctype": "Sales Order", "reference_name": sales_order},
		pluck="event",
		order_by="creation",
	)
	return events


def get_error_title(error_log: str | None) -> str | None:
	return frappe.db.get_value("Error Log", error_log, "method") if error_log else None
