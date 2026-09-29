"use client";
import { useState } from "react";

const DOC_TYPES = [
  "shipping.commercial_invoice",
  "shipping.packing_list",
  "shipping.bill_of_lading",
  "generic.invoice",
  "generic.claim",
];

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExtract() {
    if (!file) return;
    setLoading(true); setError(null); setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    try {
      const res = await fetch("/api/extract", { method: "POST", body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message || "extraction failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-3xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">DocFlow Extractor</h1>
      <p className="text-gray-600">Upload a messy PDF. Get structured fields. Map them into a form.</p>

      <div className="space-y-3">
        <input type="file" accept="application/pdf,image/*"
               onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <select value={docType} onChange={(e) => setDocType(e.target.value)}
                className="border p-2 rounded">
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button onClick={handleExtract} disabled={!file || loading}
                className="bg-black text-white px-4 py-2 rounded disabled:opacity-50">
          {loading ? "Extracting…" : "Extract"}
        </button>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      {result && (
        <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </main>
  );
}
