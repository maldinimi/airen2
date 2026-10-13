/** Klien API: cookie sesi HttpOnly + header CSRF untuk metode yang mengubah data. */
let csrf = "";
export const setCsrf = (t: string) => { csrf = t; };

export class GalatApi extends Error {
  constructor(public status: number, pesan: string, public traceId?: string) { super(pesan); }
}

async function minta<T>(metode: string, url: string, badan?: unknown): Promise<T> {
  const form = badan instanceof FormData;
  const r = await fetch(url, {
    method: metode,
    credentials: "same-origin",
    headers: {
      ...(metode !== "GET" ? { "X-CSRF-Token": csrf } : {}),
      ...(badan !== undefined && !form ? { "Content-Type": "application/json" } : {}),
    },
    body: badan === undefined ? undefined : form ? (badan as FormData) : JSON.stringify(badan),
  });
  if (!r.ok) {
    let data: { pesan?: string; trace_id?: string } = {};
    try { data = await r.json(); } catch { /* bukan JSON */ }
    if (r.status === 401 && !url.endsWith("/login") && location.pathname !== "/login") {
      location.href = "/login";
    }
    const pesan = data.pesan ?? (r.status === 413 ? "File terlalu besar." : "Terjadi kesalahan. Coba lagi.");
    throw new GalatApi(r.status, data.trace_id ? `${pesan} (ID: ${data.trace_id})` : pesan, data.trace_id);
  }
  return r.json() as Promise<T>;
}

export const api = {
  get: <T,>(url: string) => minta<T>("GET", url),
  post: <T,>(url: string, badan?: unknown) => minta<T>("POST", url, badan ?? {}),
  put: <T,>(url: string, badan?: unknown) => minta<T>("PUT", url, badan ?? {}),
  del: <T,>(url: string) => minta<T>("DELETE", url),
};

export const urlFile = (fileId: string) => `/api/file/${fileId}`;

export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}
