import { proxyToBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function POST(request: Request) {
  return proxyToBackend("/module/run", { method: "POST", body: await request.json(), label: "Module run" });
}
