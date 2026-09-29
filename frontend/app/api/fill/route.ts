import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (process.env.EXTRACT_API_KEY) headers["X-API-Key"] = process.env.EXTRACT_API_KEY;
  const res = await fetch(`${BACKEND}/fill`, { method: "POST", headers, body });
  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") || "application/json" },
  });
}
