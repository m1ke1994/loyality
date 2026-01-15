import { useAuthStore } from "./stores/auth";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

function getStoredAuth() {
  const raw = localStorage.getItem("auth");
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getAccessToken() {
  const auth = useAuthStore();
  return auth.tokens?.access || getStoredAuth()?.tokens?.access || "";
}

async function refreshTokens() {
  const auth = useAuthStore();
  const refresh = auth.tokens?.refresh || getStoredAuth()?.tokens?.refresh;
  if (!refresh) {
    return false;
  }
  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    auth.logout();
    return false;
  }
  const tokens = await res.json().catch(() => null);
  if (!tokens?.access) {
    auth.logout();
    return false;
  }
  auth.updateTokens(tokens);
  return true;
}

export async function apiFetch(path: string, options: RequestInit = {}, allowRetry = true) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Authorization")) {
    const access = getAccessToken();
    if (access) {
      headers.set("Authorization", `Bearer ${access}`);
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && allowRetry) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiFetch(path, options, false);
    }
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg = data.message || data.detail || "Request failed";
    const err: Error & { code?: string } = new Error(msg);
    if (data.code || data.detail) {
      err.code = data.code || data.detail;
    }
    throw err;
  }

  return data;
}
