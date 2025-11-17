"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = getToken();

  useEffect(() => {
    if (!token) {
      router.replace("/login");
    }
  }, [token, router]);

  // SSR과 초기 클라이언트 렌더를 일치시키기 위해 래퍼를 유지
  // 토큰이 없더라도 일단 동일한 구조를 내보내고 즉시 리다이렉트

  return <>{children}</>;
}
