export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

async function requestStatus(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    credentials: "omit",
    signal: AbortSignal.timeout(30000),
  });
  const payload = await response.json().catch(() => ({}));
  return { ok: response.ok, statusCode: response.status, payload };
}

export async function checkPlatformStatus() {
  if (!API_BASE_URL) {
    return { configured: false, api: "not-configured", database: "not-checked" };
  }

  const [healthResult, readinessResult] = await Promise.allSettled([
    requestStatus("/api/health/"),
    requestStatus("/api/ready/"),
  ]);

  const api = healthResult.status === "fulfilled" && healthResult.value.ok
    ? "online" : "unavailable";
  const database = readinessResult.status === "fulfilled"
    && readinessResult.value.ok
    && readinessResult.value.payload.database === "connected"
    ? "connected" : "unavailable";

  return {
    configured: true,
    api,
    database,
    apiPayload: healthResult.status === "fulfilled" ? healthResult.value.payload : null,
  };
}
