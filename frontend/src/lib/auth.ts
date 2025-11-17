"use client";

export const TOKEN_KEY = "jsm_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  try {
    const maxAge = 60 * 60 * 24 * 30; // 30 days
    document.cookie = `atm=1; Path=/; Max-Age=${maxAge}; SameSite=Lax; ${location.protocol === 'https:' ? 'Secure' : ''}`.trim();
  } catch {}
}

export function clearToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  try {
    document.cookie = `atm=; Path=/; Max-Age=0; SameSite=Lax; ${location.protocol === 'https:' ? 'Secure' : ''}`.trim();
  } catch {}
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
