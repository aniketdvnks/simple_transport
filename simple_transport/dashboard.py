from __future__ import annotations


def get_vehicle_dashboard_data(data=None):
	return {
		"fieldname": "license_plate",
		"non_standard_fieldnames": {
			"Driver Assignment": "vehicle",
			"Trip": "vehicle",
			"Lorry Receipt": "vehicle",
			"GPS Webhook Log": "vehicle",
		},
		"transactions": [
			{"items": ["Vehicle Log"]},
			{"items": ["Driver Assignment", "Trip", "Lorry Receipt"]},
			{"items": ["GPS Webhook Log"]},
		],
	}
