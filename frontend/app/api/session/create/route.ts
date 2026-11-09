import { proxyToBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function POST(request: Request) {
  const body = await request.json();
  delete body.user_id;
  return proxyToBackend("/session/create", { method: "POST", body, label: "Session create" });
}
