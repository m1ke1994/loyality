const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || "Request failed";
    throw new Error(msg);
  }
  return data;
}
