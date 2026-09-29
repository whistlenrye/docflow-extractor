import re
from schemas import ExtractionResult, Party, LineItem


class BaseExtractor:
    def extract(self, text: str, doc_type: str) -> ExtractionResult:
        raise NotImplementedError


class GenericInvoiceExtractor(BaseExtractor):
    def extract(self, text: str, doc_type: str) -> ExtractionResult:
        return ExtractionResult(
            doc_type=doc_type,
            confidence=0.5,
            raw_text=text[:2000],
            warnings=["Generic extractor — add a typed extractor for better accuracy."],
        )


class ShippingCommercialInvoiceExtractor(BaseExtractor):
    """Regex-based extractor for commercial invoices. Replace with LLM or
    layout-aware parsing for production accuracy."""

    def extract(self, text: str, doc_type: str) -> ExtractionResult:
        inv_no = self._find(r"Invoice\s*(?:No|Number|#)[:\s]*([A-Z0-9-]+)", text)
        date = self._find(r"Date[:\s]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})", text)
        incoterms = self._find(r"Incoterms?[:\s]*([A-Z]{3}(?:\s+[A-Za-z ]+)?)", text)
        currency = self._find(r"\b(USD|AUD|EUR|GBP|CNY)\b", text)
        total = self._find(r"Total[:\s]*([0-9,]+\.?[0-9]*)", text)
        items = []
        for m in re.finditer(r"([A-Za-z][A-Za-z0-9 ]{2,40})\s+([0-9]+)\s+([A-Z]{2,4})?\s*([0-9.]+)?", text):
            items.append(LineItem(description=m.group(1).strip(), quantity=float(m.group(2)) if m.group(2) else None,
                                  unit=m.group(3), unit_price=float(m.group(4)) if m.group(4) else None))
        return ExtractionResult(
            doc_type=doc_type,
            confidence=0.7,
            invoice_number=inv_no,
            invoice_date=date,
            incoterms=incoterms,
            currency=currency,
            total=float(total.replace(",", "")) if total else None,
            line_items=items[:20],
            raw_text=text[:2000],
        )

    @staticmethod
    def _find(pattern, text):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None


REGISTRY = {
    "generic.invoice": GenericInvoiceExtractor(),
    "shipping.commercial_invoice": ShippingCommercialInvoiceExtractor(),
    "shipping.packing_list": GenericInvoiceExtractor(),
    "shipping.bill_of_lading": GenericInvoiceExtractor(),
    "generic.claim": GenericInvoiceExtractor(),
}


def get_extractor(doc_type: str) -> BaseExtractor:
    return REGISTRY.get(doc_type, GenericInvoiceExtractor())
