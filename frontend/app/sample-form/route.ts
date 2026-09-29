import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

export async function GET() {
  const candidates = [
    join(process.cwd(), "public", "sample-form.html"),
    join(process.cwd(), "..", "backend", "sample_form.html"),
  ];
  for (const path of candidates) {
    try {
      const html = readFileSync(path, "utf-8");
      return new NextResponse(html, { headers: { "content-type": "text/html; charset=utf-8" } });
    } catch {
      /* try the next location */
    }
  }
  return NextResponse.json({ detail: "sample form missing" }, { status: 500 });
}
