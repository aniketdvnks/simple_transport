from __future__ import annotations


def get_vehicle_dashboard_data(data=None):
	return {
		"fieldname": "license_plate",
		"non_standard_fieldnames": {
			"Trip": "vehicle",
			"Lorry Receipt": "vehicle",
			"GPS Webhook Log": "vehicle",
		},
		"transactions": [
			{"items": ["Vehicle Log"]},
			{"items": ["Trip", "Lorry Receipt"]},
			{"items": ["GPS Webhook Log"]},
		],
	}
