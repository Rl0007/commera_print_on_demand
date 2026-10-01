"""A fake print provider standing in for the remote API (Printful-style)."""

import frappe
from frappe import _
from frappe.utils.data import cint

FAILURES_CACHE_KEY = "commera_print_on_demand:provider_failures"


class ProviderUnavailable(Exception):
	pass


def set_failures(count: int):
	# Kept in Redis, not the database: a failed Commera delivery rolls the database back, and the
	# countdown has to survive that the way a real outage would.
	frappe.cache.set_value(FAILURES_CACHE_KEY, cint(count))


def raise_if_down():
	remaining = cint(frappe.cache.get_value(FAILURES_CACHE_KEY))
	if remaining > 0:
		frappe.cache.set_value(FAILURES_CACHE_KEY, remaining - 1)
		raise ProviderUnavailable(f"Print provider unavailable (fails {remaining - 1} more calls)")


def create_order(external_id: str, product_id: str | None, qty: float) -> str:
	"""Idempotent on external_id, like Printful: a repeat returns the order already created."""
	raise_if_down()
	if existing_order := frappe.db.get_value("POD Provider Order", {"external_id": external_id}, "name"):
		return existing_order

	provider_order = frappe.new_doc("POD Provider Order")
	provider_order.update({"external_id": external_id, "product_id": product_id, "qty": qty})
	provider_order.insert(ignore_permissions=True)
	return provider_order.name


def cancel_order(provider_order_id: str):
	raise_if_down()
	status = frappe.db.get_value("POD Provider Order", provider_order_id, "status")
	if status in ("In Production", "Shipped"):
		frappe.throw(
			_("Print provider order {0} is {1} and can't be cancelled.").format(provider_order_id, status)
		)
	frappe.db.set_value("POD Provider Order", provider_order_id, "status", "Cancelled")


def start_production(provider_order_id: str):
	"""What the provider's "package in production" webhook would report."""
	frappe.db.set_value("POD Provider Order", provider_order_id, "status", "In Production")
	frappe.db.set_value("POD Job", {"provider_order_id": provider_order_id}, "status", "In Production")
