import { NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function GET(request: Request) {
  const jobId = new URL(request.url).searchParams.get("job_id") || "";
  if (!jobId) return NextResponse.json({ error: "job_id is required" }, { status: 400 });
  return proxyToBackend(`/module/status?job_id=${encodeURIComponent(jobId)}`, { label: "Module status" });
}
