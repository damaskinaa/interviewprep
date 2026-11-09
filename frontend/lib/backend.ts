import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

function buildUrl(endpoint: string) {
  const base = new URL(BACKEND_URL.trim());
  const endpointUrl = new URL(endpoint, "http://internal.local");
  base.pathname = `${base.pathname.replace(/\/+$/, "")}${endpointUrl.pathname}`;
  base.search = endpointUrl.search;
  return base.toString();
}

type ProxyOptions = { method?: "GET" | "POST"; body?: unknown; label: string };

export async function proxyToBackend(endpoint: string, { method = "GET", body, label }: ProxyOptions) {
  try {
    const response = await fetch(buildUrl(endpoint), {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : {},
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      cache: "no-store",
    });
    const text = await response.text();
    if (!response.ok) {
      return NextResponse.json(
        { error: "Backend returned an error", status: response.status, body: text.slice(0, 2000) },
        { status: response.status },
      );
    }
    return NextResponse.json(JSON.parse(text));
  } catch (err: unknown) {
    return NextResponse.json(
      { error: `${label} route crashed`, message: err instanceof Error ? err.message : "Unknown error" },
      { status: 500 },
    );
  }
}
