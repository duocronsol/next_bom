from frappe import _dict
from frappe.tests import UnitTestCase

from next_bom.custom_bom import before_validate, calculate_formula


class Row(_dict):
	def as_dict(self):
		return dict(self)


class Document(_dict):
	def as_dict(self):
		return dict(self)


class TestCustomBOM(UnitTestCase):
	def test_formula_uses_the_row_and_the_document(self):
		row = Row(idx=1, qty=5)
		doc = Document(quantity=10)

		self.assertEqual(calculate_formula("qty * 2 + quantity", doc, row), 20)

	def test_formula_may_span_lines(self):
		self.assertEqual(calculate_formula("quantity *\n 3", Document(quantity=10), Row(idx=1)), 30)

	def test_quantities_are_set_on_raw_materials_and_secondary_items(self):
		doc = Document(
			quantity=4,
			items=[
				Row(idx=1, qty=0, custom_type="Actual", custom_formula="quantity * 2"),
				Row(
					idx=2,
					qty=0,
					custom_type="On Previous Row Qty",
					custom_formula="qty * 3",
					custom_reference_row_="1",
				),
			],
			secondary_items=[Row(idx=1, qty=0, custom_type="Actual", custom_formula="quantity + 1")],
		)

		before_validate(doc)

		self.assertEqual([row.qty for row in doc.get("items")], [8, 24])
		self.assertEqual(doc.get("secondary_items")[0].qty, 5)

	def test_rows_without_a_formula_are_untouched(self):
		doc = Document(items=[Row(idx=1, qty=7)], secondary_items=[])

		before_validate(doc)

		self.assertEqual(doc.get("items")[0].qty, 7)
