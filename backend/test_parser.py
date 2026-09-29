import unittest
from pathlib import Path

from parser import parse_document

SAMPLE = (Path(__file__).resolve().parents[1] / "samples" / "commercial_invoice_sample.txt")
# When run from a checkout the sample sits next to backend/. Tests also embed
# a copy so they pass from a flat copy of the backend.
EMBEDDED = """COMMERCIAL INVOICE

Shipper / Exporter:
Shenzhen Apex Microelectronics Co., Ltd.
High-Tech Industrial Park, Nanshan, Shenzhen, Guangdong, China
Tax ID: 91440300MA5XXXXXXX

Consignee / Buyer:
LES SCHWAB WAREHOUSE CENTER
20900 COOLEY RD, BEND OR 97701-3406, USA

Invoice Number: INV-2026-0042
Invoice Date: 18/02/2026
Country of Origin: CN
Incoterms: FOB Shenzhen
Currency: USD

Item | Description | HS Code | Qty | Unit | Unit Price | Amount
1 | Automotive Grade Microcontroller ICs for ADAS Systems (Model: APX-904) | 8542.31 | 50000 | PCE | 4.92 | 245800.00
2 | Evaluation Board Kit | 8471.80 | 200 | PCE | 85.00 | 17000.00

Subtotal: 262800.00
Freight: 4200.00
Insurance: 1200.00
Total: 268200.00

Declaration: We certify this invoice is true and correct, goods are of Chinese origin, and prices are actual.
"""


class ParserTests(unittest.TestCase):
    def text(self) -> str:
        if SAMPLE.exists():
            return SAMPLE.read_text()
        return EMBEDDED

    def test_commercial_invoice_sample(self):
        result = parse_document(self.text(), "shipping.commercial_invoice")
        self.assertEqual(result.invoice_number, "INV-2026-0042")
        self.assertEqual(result.invoice_date, "18/02/2026")
        self.assertEqual(result.incoterms, "FOB Shenzhen")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.subtotal, 262800.0)
        self.assertEqual(result.freight, 4200.0)
        self.assertEqual(result.insurance, 1200.0)
        self.assertEqual(result.total, 268200.0)
        self.assertIsNotNone(result.shipper)
        self.assertEqual(result.shipper.name, "Shenzhen Apex Microelectronics Co., Ltd.")
        self.assertEqual(result.shipper.tax_id, "91440300MA5XXXXXXX")
        self.assertEqual(result.shipper.country, "China")
        self.assertEqual(result.consignee.name, "LES SCHWAB WAREHOUSE CENTER")
        self.assertEqual(result.consignee.country, "USA")
        self.assertEqual(len(result.line_items), 2)
        self.assertEqual(result.line_items[0].hs_code, "8542.31")
        self.assertEqual(result.line_items[0].quantity, 50000)
        self.assertEqual(result.line_items[0].unit, "PCE")
        self.assertEqual(result.line_items[0].unit_price, 4.92)
        self.assertEqual(result.line_items[0].amount, 245800.0)
        self.assertEqual(result.line_items[0].country_of_origin, "CN")
        self.assertEqual(result.line_items[1].description, "Evaluation Board Kit")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertFalse(any("Partial parse" in w for w in result.warnings))

    def test_subtotal_is_not_the_total(self):
        result = parse_document("Subtotal: 10.00\nTotal: 12.50\n", "generic.invoice")
        self.assertEqual(result.subtotal, 10.0)
        self.assertEqual(result.total, 12.5)

    def test_empty_text(self):
        result = parse_document("   ", "generic.invoice")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.line_items, [])


if __name__ == "__main__":
    unittest.main()
