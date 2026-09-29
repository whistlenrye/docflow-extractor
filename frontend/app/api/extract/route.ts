import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const headers: Record<string, string> = {};
  if (process.env.EXTRACT_API_KEY) headers["X-API-Key"] = process.env.EXTRACT_API_KEY;
  const res = await fetch(`${BACKEND}/extract`, { method: "POST", body: formData, headers });
  const data = await res.json().catch(() => ({ detail: "backend unavailable" }));
  return NextResponse.json(data, { status: res.status });
}
