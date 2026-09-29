import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

// Serves the bundled sample target form so Playwright has something to fill
// during local demos without standing up a separate server.
export async function GET() {
  const html = readFileSync(
    join(process.cwd(), "..", "backend", "sample_form.html"),
    "utf-8"
  );
  return new NextResponse(html, {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
