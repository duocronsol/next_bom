"""Carry the BOM Scrap Item formula fields over to BOM Secondary Item.

ERPNext v16 replaced the BOM Scrap Item table with BOM Secondary Item and copies each scrap row across
(`erpnext.patches.v16_0.co_by_product_patch`), but only its own fields. The four custom fields that
drive formula-based quantities live on the old table and would otherwise be lost with it.
"""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.modules.patch_handler import run_single

OLD_DOCTYPE = "BOM Scrap Item"
NEW_DOCTYPE = "BOM Secondary Item"
FORMULA_FIELDS = ("custom__is_custom_calculation", "custom_type", "custom_reference_row_", "custom_formula")


def execute():
	if not frappe.db.has_table(OLD_DOCTYPE):
		return

	# The old table is only readable until ERPNext's own migration drops it, and the copy below needs
	# the rows ERPNext creates. Running it here, once, makes the order independent of the app order.
	run_single(patchmodule="erpnext.patches.v16_0.co_by_product_patch")

	create_custom_fields({NEW_DOCTYPE: load_custom_field_definitions()}, ignore_validate=True)

	old_fields = [fieldname for fieldname in FORMULA_FIELDS if frappe.db.has_column(OLD_DOCTYPE, fieldname)]
	if old_fields:
		copy_formula_values(old_fields)

	# these point at a doctype that no longer exists
	frappe.db.delete("Custom Field", {"dt": OLD_DOCTYPE})
	frappe.clear_cache(doctype=NEW_DOCTYPE)


EXPORT_METADATA = (
	"_assign",
	"_comments",
	"_liked_by",
	"_user_tags",
	"creation",
	"docstatus",
	"idx",
	"modified",
	"modified_by",
	"name",
	"owner",
)


def load_custom_field_definitions() -> list[dict]:
	path = frappe.get_app_path("next_bom", "next_bom", "custom", "bom_secondary_item.json")
	with open(path) as f:
		fields = json.load(f)["custom_fields"]

	return [{k: v for k, v in field.items() if k not in EXPORT_METADATA} for field in fields]


def copy_formula_values(old_fields: list[str]):
	old_rows = frappe.get_all(
		OLD_DOCTYPE,
		filters={"parenttype": "BOM", "docstatus": ("<", 2)},
		fields=["parent", "idx", "item_code", *old_fields],
	)

	for old in old_rows:
		if not any(old.get(fieldname) for fieldname in old_fields):
			continue

		new_rows = frappe.get_all(
			NEW_DOCTYPE,
			filters={
				"parent": old.parent,
				"parenttype": "BOM",
				"secondary_item_type": "Scrap",
				"item_code": old.item_code,
				"idx": old.idx,
			},
			pluck="name",
		)
		if len(new_rows) != 1:
			print(f"next_bom: no unique {NEW_DOCTYPE} row for {old.parent} row {old.idx}; formula not copied")
			continue

		frappe.db.set_value(
			NEW_DOCTYPE,
			new_rows[0],
			{fieldname: old.get(fieldname) for fieldname in old_fields},
			update_modified=False,
		)
