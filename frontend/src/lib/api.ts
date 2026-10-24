export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "famchop_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Private mode / blocked storage: the user just stays signed out
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type FastApiDetail = string | { msg: string; loc?: (string | number)[] }[];

function messageFrom(detail: FastApiDetail | undefined, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // Pydantic validation errors: "Value error, Provide either..." -> "Provide either..."
    return detail.map((d) => d.msg.replace(/^Value error, /, "")).join(". ");
  }
  return fallback;
}

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const token = getToken();
  const { json, ...rest } = init ?? {};
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...rest,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...rest.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Can't reach the FamChop server. Is the backend running?");
  }

  if (res.status === 401 && token) {
    // Token expired or invalid: sign out and go to login
    setToken(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(res.status, messageFrom(body?.detail, `Something went wrong (${res.status})`));
  }
  return body as T;
}

/** For "get latest X" endpoints where 404 just means "none yet". */
export async function apiOrNull<T>(path: string): Promise<T | null> {
  try {
    return await api<T>(path);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}
