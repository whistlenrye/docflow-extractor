import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const res = await fetch(`${BACKEND}/extract`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  return NextResponse.json(data);
}
