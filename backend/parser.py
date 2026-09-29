"""Deterministic document parser.

Used when Gemini is unset, errors, or returns an empty payload. Tuned for
commercial invoices, packing lists, and bills of lading without inventing
values that are not on the page.
"""
from __future__ import annotations

import re

from schemas import ExtractionResult, LineItem, Party

UNITS = {
    "PCS", "PCE", "PC", "KG", "KGS", "EA", "CTN", "CTNS",
    "UNIT", "UNITS", "SET", "SETS", "BOX", "BOXES", "MT", "LTR",
}
KNOWN_COUNTRIES = {
    "china", "usa", "u.s.a.", "u.s.a", "united states", "australia",
    "united kingdom", "uk", "japan", "germany", "vietnam", "india",
    "singapore", "new zealand", "hong kong", "taiwan", "korea",
    "south korea", "canada", "mexico", "indonesia", "thailand",
    "malaysia", "united arab emirates", "uae",
}

_SHIP_ONLY = re.compile(
    r"^(?:shipper|exporter|seller)(?:\s*/\s*(?:exporter|seller|shipper))?\s*:?\s*$",
    re.I,
)
_SHIP_INLINE = re.compile(
    r"^(?:shipper|exporter|seller)(?:\s*/\s*(?:exporter|seller|shipper))?\s*:\s*(.+)$",
    re.I,
)
_CONS_ONLY = re.compile(
    r"^(?:consignee|buyer|importer)(?:\s*/\s*(?:buyer|importer|consignee))?\s*:?\s*$",
    re.I,
)
_CONS_INLINE = re.compile(
    r"^(?:consignee|buyer|importer)(?:\s*/\s*(?:buyer|importer|consignee))?\s*:\s*(.+)$",
    re.I,
)
_STOP = re.compile(
    r"^(?:invoice\b|country of origin\b|incoterms?\b|currency\b|item\s*\||"
    r"declaration\b|subtotal\b|freight\b|insurance\b|total\b)",
    re.I,
)
_TAX = re.compile(r"^(?:tax\s*id|vat(?:\s*no\.?)?|abn|ein|gst(?:\s*no\.?)?)\s*[:#\-]?\s*(.+)$", re.I)
_MONEY = r"(?<![A-Za-z]){label}\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)"
_LOOSE_ROW = re.compile(
    r"^(.+?)\s+([0-9]+(?:\.[0-9]+)?)\s+([A-Za-z]{1,6})\s+([0-9]+(?:\.[0-9]+)?)"
    r"(?:\s+([0-9]+(?:\.[0-9]+)?))?\s*$"
)


def _num(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = raw.replace(",", "").strip()
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", cleaned):
        return None
    return float(cleaned)


def _line_value(text: str, pattern: re.Pattern[str]) -> str | None:
    for line in text.splitlines():
        match = pattern.search(line.strip())
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _money(label: str, text: str) -> float | None:
    found = re.search(_MONEY.format(label=label), text, re.I)
    if not found:
        return None
    return _num(found.group(1))


def _clean_id(value: str) -> str:
    token = value.strip().split()[0].strip(",;")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./\-]{1,40}", token):
        return token
    return value.strip()[:60]


def _country_from(address_lines: list[str]) -> str | None:
    if not address_lines:
        return None
    tail = address_lines[-1]
    parts = [part.strip() for part in tail.split(",") if part.strip()]
    if not parts:
        return None
    cand = parts[-1]
    if cand.lower().rstrip(".") in KNOWN_COUNTRIES or re.fullmatch(r"[A-Z]{2,3}", cand):
        return cand
    return None


def _party(lines: list[str]) -> Party | None:
    cleaned = [line.strip() for line in lines if line.strip()]
    if not cleaned:
        return None
    tax_id = None
    rest: list[str] = []
    for line in cleaned:
        tax = _TAX.match(line)
        if tax:
            tax_id = tax.group(1).strip()
        else:
            rest.append(line)
    if not rest and not tax_id:
        return None
    name = rest[0] if rest else None
    address_lines = rest[1:]
    address = ", ".join(address_lines) if address_lines else None
    return Party(
        name=name,
        address=address,
        country=_country_from(address_lines),
        tax_id=tax_id,
    )


def _parties(text: str) -> tuple[Party | None, Party | None]:
    ship: list[str] = []
    cons: list[str] = []
    mode: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        inline_ship = _SHIP_INLINE.match(line)
        if _SHIP_ONLY.match(line) or inline_ship:
            mode = "ship"
            if inline_ship:
                ship.append(inline_ship.group(1))
            continue
        inline_cons = _CONS_INLINE.match(line)
        if _CONS_ONLY.match(line) or inline_cons:
            mode = "cons"
            if inline_cons:
                cons.append(inline_cons.group(1))
            continue
        if mode and _STOP.match(line):
            mode = None
            continue
        if mode == "ship":
            ship.append(line)
        elif mode == "cons":
            cons.append(line)
    return _party(ship), _party(cons)


def _col(header: list[str], *keys: str) -> int | None:
    for index, cell in enumerate(header):
        if any(key in cell for key in keys):
            return index
    return None


def _cell(cells: list[str], index: int | None) -> str:
    if index is None or index >= len(cells):
        return ""
    return cells[index].strip()


def _pipe_items(text: str, origin: str | None) -> list[LineItem]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.split("|")]
        cells = [cell for cell in cells if cell != ""]
        if len(cells) >= 3:
            rows.append(cells)
    if len(rows) < 2:
        return []
    header = [cell.lower() for cell in rows[0]]
    desc_i = _col(header, "desc")
    if desc_i is None:
        return []
    hs_i = _col(header, "hs")
    qty_i = _col(header, "qty", "quantity")
    unit_i = _col(header, "unit")
    # "unit" also sits inside "unit price" — prefer the shorter header.
    if unit_i is not None and "price" in header[unit_i]:
        unit_i = next((i for i, cell in enumerate(header) if cell.strip() in {"unit", "uom"}), None)
    price_i = _col(header, "unit price", "price")
    amount_i = _col(header, "amount", "extended")
    items: list[LineItem] = []
    for cells in rows[1:]:
        description = _cell(cells, desc_i)
        if not description or description.lower() in {"description", "item"}:
            continue
        if re.fullmatch(r"\d+", description):
            continue
        unit = _cell(cells, unit_i) or None
        hs = _cell(cells, hs_i) or None
        if hs and not re.search(r"\d", hs):
            hs = None
        quantity = _num(_cell(cells, qty_i))
        unit_price = _num(_cell(cells, price_i))
        amount = _num(_cell(cells, amount_i))
        if amount is None and quantity is not None and unit_price is not None:
            amount = round(quantity * unit_price, 2)
        items.append(LineItem(
            description=description[:200],
            quantity=quantity,
            unit=unit[:12] if unit else None,
            unit_price=unit_price,
            amount=amount,
            hs_code=hs,
            country_of_origin=origin,
        ))
        if len(items) >= 30:
            break
    return items


def _loose_items(text: str, origin: str | None) -> list[LineItem]:
    items: list[LineItem] = []
    for line in text.splitlines():
        match = _LOOSE_ROW.match(line.strip())
        if not match:
            continue
        unit = match.group(3).upper()
        if unit not in UNITS:
            continue
        description = match.group(1).strip(" |-")
        if len(description) < 3 or not re.search(r"[A-Za-z]", description):
            continue
        quantity = _num(match.group(2))
        unit_price = _num(match.group(4))
        amount = _num(match.group(5))
        if amount is None and quantity is not None and unit_price is not None:
            amount = round(quantity * unit_price, 2)
        items.append(LineItem(
            description=description[:200],
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            amount=amount,
            country_of_origin=origin,
        ))
        if len(items) >= 30:
            break
    return items


def _score(result: ExtractionResult) -> float:
    score = 0.0
    if result.invoice_number:
        score += 0.15
    if result.invoice_date:
        score += 0.10
    if result.currency:
        score += 0.10
    if result.total is not None:
        score += 0.15
    if result.shipper and result.shipper.name:
        score += 0.15
    if result.consignee and result.consignee.name:
        score += 0.10
    if result.line_items:
        score += 0.15
    if result.subtotal is not None:
        score += 0.05
    if result.freight is not None:
        score += 0.025
    if result.insurance is not None:
        score += 0.025
    return min(score, 0.92)


def useful(result: ExtractionResult) -> bool:
    return bool(
        result.invoice_number
        or result.total is not None
        or result.line_items
        or (result.shipper and result.shipper.name)
    )


def parse_document(text: str, doc_type: str) -> ExtractionResult:
    if not text or not text.strip():
        return ExtractionResult(
            doc_type=doc_type,
            confidence=0.0,
            warnings=["No text to parse."],
            model_used="parser",
        )

    origin = _line_value(text, re.compile(r"^country of origin\s*[:\-]?\s*(.+)$", re.I))
    invoice_number = _line_value(
        text, re.compile(r"^invoice\s*(?:number|no\.?|#)\s*[:#\-]?\s*(.+)$", re.I)
    )
    bl_number = _line_value(
        text,
        re.compile(r"^(?:b/?l|bill of lading)\s*(?:no\.?|number|#)?\s*[:#\-]?\s*(.+)$", re.I),
    )
    warnings: list[str] = []
    if invoice_number:
        invoice_number = _clean_id(invoice_number)
    elif bl_number:
        invoice_number = _clean_id(bl_number)
        warnings.append("No invoice number; stored the bill of lading number.")

    invoice_date = _line_value(text, re.compile(r"^invoice\s+date\s*[:\-]?\s*(.+)$", re.I))
    if not invoice_date:
        invoice_date = _line_value(
            text,
            re.compile(r"^date\s*[:\-]?\s*([0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{2,4})\b", re.I),
        )
    if invoice_date:
        found = re.search(r"[0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{2,4}", invoice_date)
        invoice_date = found.group(0) if found else invoice_date[:32]

    incoterms = _line_value(text, re.compile(r"^incoterms?\s*[:\-]?\s*(.+)$", re.I))
    if incoterms:
        incoterms = incoterms.strip()[:80]

    currency = _line_value(text, re.compile(r"^currency\s*[:\-]?\s*([A-Za-z]{3})\b", re.I))
    if currency:
        currency = currency.upper()
    else:
        found = re.search(r"\b(USD|AUD|EUR|GBP|CNY|NZD|JPY|CAD)\b", text)
        currency = found.group(1) if found else None

    shipper, consignee = _parties(text)
    items = _pipe_items(text, origin)
    if not items:
        items = _loose_items(text, origin)

    result = ExtractionResult(
        doc_type=doc_type,
        confidence=0.0,
        shipper=shipper,
        consignee=consignee,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        incoterms=incoterms,
        currency=currency,
        line_items=items,
        subtotal=_money("subtotal", text),
        freight=_money("freight", text),
        insurance=_money("insurance", text),
        total=_money("total", text),
        warnings=warnings,
        model_used="parser",
    )
    result.confidence = _score(result)
    if result.confidence < 0.55:
        result.warnings.append("Partial parse — confirm every field before submitting.")
    return result


def merge_extractions(primary: ExtractionResult, fallback: ExtractionResult) -> ExtractionResult:
    """Prefer model fields, fill gaps from the parser. Never invent new values."""

    def pick_str(a: str | None, b: str | None) -> str | None:
        return a if a else b

    def pick_num(a: float | None, b: float | None) -> float | None:
        return a if a is not None else b

    def pick_party(a: Party | None, b: Party | None) -> Party | None:
        if a is None:
            return b
        if b is None:
            return a
        return Party(
            name=pick_str(a.name, b.name),
            address=pick_str(a.address, b.address),
            country=pick_str(a.country, b.country),
            tax_id=pick_str(a.tax_id, b.tax_id),
        )

    if not useful(primary):
        merged = fallback.model_copy(deep=True)
        merged.warnings = list(dict.fromkeys([
            *fallback.warnings,
            "Model output was empty; parser result used.",
        ]))
        merged.model_used = primary.model_used or fallback.model_used
        return merged

    warnings = list(dict.fromkeys([*primary.warnings, *fallback.warnings]))
    items = primary.line_items or fallback.line_items
    return ExtractionResult(
        doc_type=primary.doc_type or fallback.doc_type,
        confidence=max(primary.confidence, fallback.confidence if not primary.line_items else primary.confidence),
        shipper=pick_party(primary.shipper, fallback.shipper),
        consignee=pick_party(primary.consignee, fallback.consignee),
        invoice_number=pick_str(primary.invoice_number, fallback.invoice_number),
        invoice_date=pick_str(primary.invoice_date, fallback.invoice_date),
        incoterms=pick_str(primary.incoterms, fallback.incoterms),
        currency=pick_str(primary.currency, fallback.currency),
        line_items=items,
        subtotal=pick_num(primary.subtotal, fallback.subtotal),
        freight=pick_num(primary.freight, fallback.freight),
        insurance=pick_num(primary.insurance, fallback.insurance),
        total=pick_num(primary.total, fallback.total),
        warnings=warnings,
        model_used=primary.model_used or fallback.model_used,
    )
