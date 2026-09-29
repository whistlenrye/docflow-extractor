"use client";
import { useState } from "react";

const DOC_TYPES = [
  "shipping.commercial_invoice",
  "shipping.packing_list",
  "shipping.bill_of_lading",
  "generic.invoice",
  "generic.claim",
];

type Party = { name?: string | null; address?: string | null; country?: string | null; tax_id?: string | null };
type Item = { description?: string; quantity?: number | null; unit?: string | null; unit_price?: number | null; amount?: number | null; hs_code?: string | null };
type Result = {
  invoice_number?: string | null;
  invoice_date?: string | null;
  incoterms?: string | null;
  currency?: string | null;
  subtotal?: number | null;
  freight?: number | null;
  insurance?: number | null;
  total?: number | null;
  shipper?: Party | null;
  consignee?: Party | null;
  line_items?: Item[];
  warnings?: string[];
  confidence?: number;
  model_used?: string | null;
};

function money(v: number | null | undefined) {
  if (v == null) return "";
  const [w, f] = v.toFixed(2).split(".");
  return `${w.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${f}`;
}

function toFields(result: Result): Record<string, string> {
  const fields: Record<string, string> = {};
  const party = (prefix: string, value?: Party | null) => {
    if (!value) return;
    if (value.name) fields[`${prefix}_name`] = value.name;
    if (value.address) fields[`${prefix}_address`] = value.address;
    if (value.country) fields[`${prefix}_country`] = value.country;
    if (value.tax_id) fields[`${prefix}_tax_id`] = value.tax_id;
  };
  party("shipper", result.shipper);
  party("consignee", result.consignee);
  if (result.invoice_number) fields.invoice_number = result.invoice_number;
  if (result.invoice_date) fields.invoice_date = result.invoice_date;
  if (result.incoterms) fields.incoterms = result.incoterms;
  if (result.currency) fields.currency = result.currency;
  if (result.subtotal != null) fields.subtotal = money(result.subtotal);
  if (result.freight != null) fields.freight = money(result.freight);
  if (result.insurance != null) fields.insurance = money(result.insurance);
  if (result.total != null) fields.total = money(result.total);
  (result.line_items || []).slice(0, 5).forEach((item, i) => {
    const n = i + 1;
    if (item.description) fields[`item_${n}_desc`] = item.description;
    if (item.quantity != null) fields[`item_${n}_qty`] = String(item.quantity);
    if (item.unit) fields[`item_${n}_unit`] = item.unit;
    if (item.unit_price != null) fields[`item_${n}_price`] = money(item.unit_price);
    if (item.amount != null) fields[`item_${n}_amount`] = money(item.amount);
    if (item.hs_code) fields[`item_${n}_hs`] = item.hs_code;
  });
  return fields;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [result, setResult] = useState<Result | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [held, setHeld] = useState<string | null>(null);

  async function loadSample() {
    const res = await fetch("/commercial_invoice_sample.txt");
    setText(await res.text());
    setDocType("shipping.commercial_invoice");
    setFile(null);
    setError(null);
  }

  async function handleExtract() {
    if (!file && !text.trim()) {
      setError("Paste text or choose a file.");
      return;
    }
    setLoading(true);
    setError(null);
    setHeld(null);
    const form = new FormData();
    form.append("doc_type", docType);
    if (text.trim()) form.append("text", text);
    if (file) form.append("file", file);
    try {
      const res = await fetch("/api/extract", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setResult(data);
      setFields(toFields(data));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "extraction failed");
    } finally {
      setLoading(false);
    }
  }

  function confirm() {
    if (!fields.invoice_number || !fields.total) {
      setError("Invoice number and total are required.");
      return;
    }
    setError(null);
    setHeld(`${fields.invoice_number} held for review. Nothing was filed.`);
  }

  return (
    <main className="max-w-3xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">DocFlow Extractor</h1>
      <p className="text-gray-600">Paste or upload a document. Review the fields. Map them onto the entry form.</p>
      <div className="space-y-3">
        <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,application/pdf,text/plain,image/*"
               onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <select value={docType} onChange={(e) => setDocType(e.target.value)} className="border p-2 rounded block">
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8}
                  placeholder="Paste invoice text, or load the sample."
                  className="w-full border p-2 rounded font-mono text-sm" />
        <div className="flex gap-2">
          <button onClick={loadSample} className="border px-4 py-2 rounded">Load sample</button>
          <button onClick={handleExtract} disabled={loading} className="bg-black text-white px-4 py-2 rounded disabled:opacity-50">
            {loading ? "Extracting…" : "Extract"}
          </button>
        </div>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {result && (
        <p className="text-sm text-gray-600">
          {result.model_used || "parser"} · confidence {Math.round((result.confidence || 0) * 100)}%
          {result.warnings?.length ? ` · ${result.warnings.join(" ")}` : ""}
        </p>
      )}
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Entry form</h2>
        {["shipper_name","shipper_address","consignee_name","invoice_number","invoice_date","incoterms","currency","subtotal","freight","insurance","total","item_1_desc","item_1_hs","item_1_qty","item_1_amount"].map((name) => (
          <label key={name} className="block text-sm">
            {name}
            <input className="border rounded w-full p-2" name={name} value={fields[name] || ""}
                   onChange={(e) => setFields({ ...fields, [name]: e.target.value })} />
          </label>
        ))}
        <button onClick={confirm} className="bg-blue-600 text-white px-4 py-2 rounded">Confirm entry</button>
        {held && <p className="text-green-700 text-sm">{held}</p>}
      </section>
    </main>
  );
}
