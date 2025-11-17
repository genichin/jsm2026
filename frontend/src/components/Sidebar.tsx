"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import { useState } from "react";

const nav = [
  { href: "/dashboard", label: "대시보드" },
  { href: "/accounts", label: "계좌" },
  { href: "/assets", label: "자산" },
  { href: "/transactions", label: "거래" },
  { href: "/categories", label: "카테고리" },
  { href: "/tags", label: "태그" },
  { href: "/reminders", label: "리마인더" },
  { href: "/activities", label: "액티비티" }
 ] as const;

export default function Sidebar({ onNavigate }: { onNavigate?: () => void } = {}) {
  const pathname = usePathname();
  const router = useRouter();
  const [showUserMenu, setShowUserMenu] = useState(false);
  
  const meQuery = useQuery<{ id: string; username: string; email?: string; is_superuser: boolean }>({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/auth/users/me")).data,
    staleTime: 60 * 1000,
  });
  
  const isAdmin = !!meQuery.data?.is_superuser;
  
  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };
  
  return (
    <aside className="w-64 md:w-56 shrink-0 border-r bg-white h-full flex flex-col">
      <div className="p-4 text-xl font-semibold">J&apos;s Money</div>
      <nav className="px-2 space-y-1 flex-1">{nav.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            onClick={onNavigate}
            className={clsx(
              "block rounded px-3 py-2 text-sm hover:bg-slate-100",
              pathname.startsWith(n.href) && "bg-slate-100 font-medium"
            )}
          >
            {n.label}
          </Link>
        ))}
        {isAdmin && (
          <>
            <div className="pt-3 border-t mx-2" />
            <div className="px-3 text-xs uppercase tracking-wide text-slate-500">관리자</div>
            <Link
              href="/admin/users"
              onClick={onNavigate}
              className={clsx(
                "block rounded px-3 py-2 text-sm hover:bg-slate-100",
                pathname.startsWith("/admin/users") && "bg-slate-100 font-medium"
              )}
            >
              사용자 관리
            </Link>
          </>
        )}
      </nav>
      
      {/* User Info Section */}
      <div className="border-t p-3">
        {meQuery.isLoading ? (
          <div className="text-xs text-gray-500">로딩 중...</div>
        ) : meQuery.isError ? (
          <div className="text-xs text-red-500">사용자 정보 로드 실패</div>
        ) : meQuery.data ? (
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-full flex items-center gap-3 p-2 rounded hover:bg-slate-100 text-left"
            >
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-semibold text-sm">
                {meQuery.data.username.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{meQuery.data.username}</div>
                {meQuery.data.email && (
                  <div className="text-xs text-gray-500 truncate">{meQuery.data.email}</div>
                )}
              </div>
              <svg
                className={clsx("w-4 h-4 text-gray-400 transition-transform", showUserMenu && "rotate-180")}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {showUserMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border rounded-lg shadow-lg overflow-hidden">
                {isAdmin && (
                  <div className="px-3 py-2 text-xs text-blue-600 bg-blue-50 border-b">
                    관리자
                  </div>
                )}
                <button
                  onClick={handleLogout}
                  className="w-full px-3 py-2 text-sm text-left hover:bg-red-50 text-red-600 flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  로그아웃
                </button>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </aside>
  );
}
