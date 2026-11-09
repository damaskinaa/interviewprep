import { proxyToBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  return proxyToBackend("/lua-coach", { method: "POST", body: await request.json(), label: "Lua" });
}
