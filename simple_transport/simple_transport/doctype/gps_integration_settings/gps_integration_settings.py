from __future__ import annotations

from frappe.model.document import Document

from simple_transport.gps_integration import get_relative_endpoint_paths


class GPSIntegrationSettings(Document):
	def validate(self):
		for fieldname, value in get_relative_endpoint_paths().items():
			self.set(fieldname, value)

