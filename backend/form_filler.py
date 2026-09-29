"""Playwright-based form filler.

Maps an ExtractionResult into a target web form using headless Chromium.
One browser per request, then closed.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from schemas import ExtractionResult
from url_safety import assert_safe_target

log = logging.getLogger("docflow.filler")

DEFAULT_TARGET_URL = os.getenv(
    "FORM_TARGET_URL", "http://localhost:3000/sample-form"
)


def _fmt_money(v: float | None) -> str:
    return f"{v:,.2f}" if v is not None else ""


def _party_block(prefix: str, party) -> dict[str, str]:
    if not party:
        return {}
    out: dict[str, str] = {}
    if party.name:
        out[f"{prefix}_name"] = party.name
    if party.address:
        out[f"{prefix}_address"] = party.address
    if party.country:
        out[f"{prefix}_country"] = party.country
    if party.tax_id:
        out[f"{prefix}_tax_id"] = party.tax_id
    return out


def result_to_fields(result: ExtractionResult) -> dict[str, str]:
    """Flatten an ExtractionResult into name->value pairs matching the sample form."""
    fields: dict[str, str] = {}
    fields.update(_party_block("shipper", result.shipper))
    fields.update(_party_block("consignee", result.consignee))
    if result.invoice_number:
        fields["invoice_number"] = result.invoice_number
    if result.invoice_date:
        fields["invoice_date"] = result.invoice_date
    if result.incoterms:
        fields["incoterms"] = result.incoterms
    if result.currency:
        fields["currency"] = result.currency
    if result.subtotal is not None:
        fields["subtotal"] = _fmt_money(result.subtotal)
    if result.freight is not None:
        fields["freight"] = _fmt_money(result.freight)
    if result.insurance is not None:
        fields["insurance"] = _fmt_money(result.insurance)
    if result.total is not None:
        fields["total"] = _fmt_money(result.total)
    for i, item in enumerate(result.line_items[:5]):
        n = i + 1
        if item.description:
            fields[f"item_{n}_desc"] = item.description
        if item.quantity is not None:
            fields[f"item_{n}_qty"] = str(item.quantity)
        if item.unit:
            fields[f"item_{n}_unit"] = item.unit
        if item.unit_price is not None:
            fields[f"item_{n}_price"] = _fmt_money(item.unit_price)
        if item.amount is not None:
            fields[f"item_{n}_amount"] = _fmt_money(item.amount)
        if item.hs_code:
            fields[f"item_{n}_hs"] = item.hs_code
    return fields


async def fill_form(
    result: ExtractionResult,
    target_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    fields = result_to_fields(result)
    url = target_url or DEFAULT_TARGET_URL
    if dry_run:
        return {"dry_run": True, "target_url": url, "fields": fields}

    assert_safe_target(url)

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed; pip install playwright && playwright install chromium"
        ) from exc

    filled: list[str] = []
    skipped: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            assert_safe_target(page.url)
            for name, value in fields.items():
                loc = page.locator(f"[name='{name}']")
                if await loc.count() == 0:
                    skipped.append(name)
                    continue
                tag = await loc.first.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    await loc.first.select_option(value=value)
                elif tag in ("input", "textarea"):
                    itype = await loc.first.get_attribute("type") or "text"
                    if itype in ("checkbox", "radio"):
                        await loc.first.set_checked(value.lower() in ("1", "true", "yes", "on"))
                    else:
                        await loc.first.fill(value)
                else:
                    await loc.first.fill(value)
                filled.append(name)
            submit = page.locator("button[type='submit'], input[type='submit']")
            if await submit.count():
                await submit.first.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                assert_safe_target(page.url)
        finally:
            await browser.close()

    return {
        "dry_run": False,
        "target_url": url,
        "filled": filled,
        "skipped": skipped,
        "field_count": len(fields),
    }
