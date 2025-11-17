"use client";
import axios from "axios";
import { getToken, clearToken } from "@/lib/auth";

// 클라이언트에서 직접 백엔드로 요청 (CORS 기반)
const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL || "https://jsfamily2.myds.me:40041/api/v1";
let normalizedBase = rawBase.replace(/\/+$/, "");
if (!/\/api\/v1$/.test(normalizedBase)) {
  normalizedBase += "/api/v1";
}

export const api = axios.create({ baseURL: normalizedBase });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      clearToken();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export type Paginated<T> = {
  total: number;
  page: number;
  size: number;
  items: T[];
};
