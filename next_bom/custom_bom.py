from datetime import date

import frappe
from frappe import _
from frappe.utils import ceil, floor, flt, get_link_to_form, getdate
from frappe.utils.safe_exec import safe_eval

CALCULATED_TABLES = ("items", "secondary_items")


def before_validate(doc, method=None):
	"""Work out formula-based quantities before ERPNext's own validate derives stock qty, amounts and costs from them."""
	for table in CALCULATED_TABLES:
		rows = doc.get(table) or []
		for row in rows:
			if row.get("custom_type") == "Actual" and row.get("custom_formula"):
				row.qty = calculate_formula(row.custom_formula, doc, row)
			elif row.get("custom_type") == "On Previous Row Qty":
				row.qty = calculate_formula(row.custom_formula, doc, previous_row(rows, row))


def previous_row(rows, row):
	index = reference_index(row.get("custom_reference_row_"))
	if not 0 <= index < len(rows):
		frappe.throw(
			_("Row {0}: Reference Row # {1} does not exist").format(row.idx, row.get("custom_reference_row_"))
		)
	return rows[index]


def reference_index(reference_row) -> int:
	try:
		return int(reference_row) - 1
	except TypeError, ValueError:
		return -1


def throw_error_message(row, error, title, description=None):
	data = frappe._dict(
		{
			"doctype": row.parenttype,
			"name": row.parent,
			"doclink": get_link_to_form(row.parenttype, row.parent),
			"row_id": row.idx,
			"error": error,
			"title": title,
			"description": description or "",
		}
	)

	message = _(
		"Error while evaluating the {doctype} {doclink} at row {row_id}. <br><br> <b>Error:</b> {error} <br><br> <b>Hint:</b> {description}"
	).format(**data)

	frappe.throw(message, title=title)


def calculate_formula(formula, doc, row):
	whitelisted_globals = {
		"int": int,
		"float": float,
		"long": int,
		"round": round,
		"date": date,
		"getdate": getdate,
		"ceil": ceil,
		"floor": floor,
	}

	data = frappe._dict()
	data.update(row.as_dict())
	data.update(doc.as_dict())

	try:
		formula = sanitize_expression(formula)
		if not formula:
			raise ValueError("empty formula")

		return flt(safe_eval(formula, whitelisted_globals, data))
	except Exception:
		frappe.throw(
			title=_("Raw Materials Formula Error"),
			msg=_("<b>Row {0}#:</b> Please check the Formula").format(row.idx),
		)


def sanitize_expression(string: str | None = None) -> str | None:
	if not string:
		return None

	parts = string.strip().splitlines()
	return " ".join(parts)
