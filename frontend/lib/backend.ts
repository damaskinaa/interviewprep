import { createHmac, randomUUID, timingSafeEqual } from "crypto";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

type DaytonaPreviewResponse = {
  url?: string;
  token?: string;
  data?: { url?: string; token?: string };
};

type BackendTarget = { baseUrl: string; headers: Record<string, string> };

const USER_COOKIE = "nailit_uid";
const USER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
const PREVIEW_CACHE_MS = 5 * 60 * 1000;

let cachedPreview: { target: BackendTarget; expiresAt: number } | null = null;

function cookieSecret() {
  const secret = process.env.USER_COOKIE_SECRET || process.env.APP_API_KEY;
  if (!secret) throw new Error("USER_COOKIE_SECRET or APP_API_KEY must be configured on the server.");
  return secret;
}

function sign(value: string) {
  return createHmac("sha256", cookieSecret()).update(value).digest("base64url");
}

function verify(signed: string | undefined) {
  if (!signed) return "";
  const dot = signed.lastIndexOf(".");
  if (dot <= 0) return "";
  const value = signed.slice(0, dot);
  const expected = Buffer.from(sign(value));
  const actual = Buffer.from(signed.slice(dot + 1));
  if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) return "";
  return value;
}

// Anonymous per-browser identity until real auth is added; the backend scopes sessions to it.
export async function getOrCreateUserId() {
  const store = await cookies();
  const existing = verify(store.get(USER_COOKIE)?.value);
  if (existing) return existing;
  const userId = `anon_${randomUUID()}`;
  store.set(USER_COOKIE, `${userId}.${sign(userId)}`, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: USER_COOKIE_MAX_AGE,
  });
  return userId;
}

function getValue(response: DaytonaPreviewResponse, key: "url" | "token") {
  return response[key] || response.data?.[key] || "";
}

async function resolveBackend(): Promise<BackendTarget> {
  if (process.env.BACKEND_URL) return { baseUrl: process.env.BACKEND_URL, headers: {} };
  if (cachedPreview && cachedPreview.expiresAt > Date.now()) return cachedPreview.target;

  const apiKey = process.env.DAYTONA_API_KEY;
  const sandboxId = process.env.DAYTONA_SANDBOX_ID;
  const port = process.env.DAYTONA_PORT || "8000";
  if (!apiKey || !sandboxId) throw new Error("Set BACKEND_URL, or DAYTONA_API_KEY and DAYTONA_SANDBOX_ID.");

  const response = await fetch(`https://app.daytona.io/api/sandbox/${sandboxId}/ports/${port}/preview-url`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: "no-store",
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`Daytona preview lookup failed: ${response.status} ${text.slice(0, 500)}`);
  const data = JSON.parse(text) as DaytonaPreviewResponse;
  const previewUrl = getValue(data, "url");
  const previewToken = getValue(data, "token");
  if (!previewUrl || !previewToken) throw new Error("Daytona preview response did not include url and token.");

  const target = {
    baseUrl: previewUrl,
    headers: { "x-daytona-preview-token": previewToken, "X-Daytona-Skip-Preview-Warning": "true" },
  };
  cachedPreview = { target, expiresAt: Date.now() + PREVIEW_CACHE_MS };
  return target;
}

function buildUrl(baseUrl: string, endpoint: string) {
  const base = new URL(baseUrl.trim());
  const endpointUrl = new URL(endpoint, "http://internal.local");
  base.pathname = `${base.pathname.replace(/\/+$/, "")}${endpointUrl.pathname}`;
  base.search = endpointUrl.search;
  return base.toString();
}

type ProxyOptions = { method?: "GET" | "POST"; body?: unknown; label: string };

export async function proxyToBackend(endpoint: string, { method = "GET", body, label }: ProxyOptions) {
  try {
    const appApiKey = process.env.APP_API_KEY;
    if (!appApiKey) return NextResponse.json({ error: "Server is not configured" }, { status: 500 });
    const userId = await getOrCreateUserId();
    const target = await resolveBackend();
    const response = await fetch(buildUrl(target.baseUrl, endpoint), {
      method,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        "X-App-Key": appApiKey,
        "X-User-Id": userId,
        ...target.headers,
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      cache: "no-store",
    });
    const text = await response.text();
    if (!response.ok) {
      if (response.status === 401 || response.status === 404) cachedPreview = null;
      return NextResponse.json(
        { error: "Backend returned an error", status: response.status, body: text.slice(0, 2000) },
        { status: response.status },
      );
    }
    return NextResponse.json(JSON.parse(text));
  } catch (err: unknown) {
    cachedPreview = null;
    return NextResponse.json(
      { error: `${label} route crashed`, message: err instanceof Error ? err.message : "Unknown error" },
      { status: 500 },
    );
  }
}
