const API_BASE = import.meta.env.VITE_API_BASE ?? "https://mytonprovider.org";
const TIMEOUT_MS = 15000;

export class HttpError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    signal: AbortSignal.timeout?.(TIMEOUT_MS),
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new HttpError(response.status, `Request to ${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const http = {
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};
