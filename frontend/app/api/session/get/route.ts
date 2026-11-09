import { NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function GET(request: Request) {
  const sessionId = new URL(request.url).searchParams.get("session_id") || "";
  if (!sessionId) return NextResponse.json({ error: "session_id is required" }, { status: 400 });
  return proxyToBackend(`/session/get?session_id=${encodeURIComponent(sessionId)}`, { label: "Session get" });
}
