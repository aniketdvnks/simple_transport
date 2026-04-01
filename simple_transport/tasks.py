from __future__ import annotations

from frappe.utils import getdate

from simple_transport.simple_transport.doctype.transport_order.transport_order import (
	ensure_transport_order_for_date,
)


def create_daily_transport_order():
	ensure_transport_order_for_date(getdate())
