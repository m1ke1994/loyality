const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
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
