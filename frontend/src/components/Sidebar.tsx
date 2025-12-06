"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import { useState } from "react";

// 메뉴 구조 최적화: 카테고리별 그룹핑
const navSections = [
  {
    title: "주요 메뉴",
    items: [
      { href: "/dashboard", label: "대시보드", icon: "dashboard" },
      { href: "/accounts", label: "계좌", icon: "account" },
      { href: "/assets", label: "자산", icon: "asset" },
      { href: "/transactions", label: "거래", icon: "transaction" },
    ]
  },
  {
    title: "관리",
    items: [
      { href: "/categories", label: "카테고리", icon: "category" },
      { href: "/tags", label: "태그", icon: "tag" },
      { href: "/reminders", label: "리마인더", icon: "reminder" },
      { href: "/activities", label: "액티비티", icon: "activity" },
    ]
  }
] as const;

const icons = {
  dashboard: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v12.5A1.75 1.75 0 0 1 14.25 16H1.75A1.75 1.75 0 0 1 0 14.25Zm1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25Z" />
      <path d="M2.5 3.5v6h3v-6Zm4.5 0v6h6v-6Z" />
    </svg>
  ),
  account: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z" />
    </svg>
  ),
  asset: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm7-3.25v2.992l2.028.812a.75.75 0 0 1-.557 1.392l-2.5-1A.751.751 0 0 1 7 8.25v-3.5a.75.75 0 0 1 1.5 0Z" />
    </svg>
  ),
  transaction: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M2.75 0h10.5C14.216 0 15 .784 15 1.75v10.5A1.75 1.75 0 0 1 13.25 14H2.75A1.75 1.75 0 0 1 1 12.25V1.75C1 .784 1.784 0 2.75 0Zm10.5 1.5H2.75a.25.25 0 0 0-.25.25v10.5c0 .138.112.25.25.25h10.5a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25ZM8 4a.75.75 0 0 1 .75.75v2.5h2.5a.75.75 0 0 1 0 1.5h-2.5v2.5a.75.75 0 0 1-1.5 0v-2.5h-2.5a.75.75 0 0 1 0-1.5h2.5v-2.5A.75.75 0 0 1 8 4Z" />
    </svg>
  ),
  category: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M1.75 1h12.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0 1 14.25 15H1.75A1.75 1.75 0 0 1 0 13.25V2.75C0 1.784.784 1 1.75 1ZM1.5 2.75v10.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V2.75a.25.25 0 0 0-.25-.25H1.75a.25.25 0 0 0-.25.25Z" />
    </svg>
  ),
  tag: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M1 7.775V2.75C1 1.784 1.784 1 2.75 1h5.025c.464 0 .91.184 1.238.513l6.25 6.25a1.75 1.75 0 0 1 0 2.474l-5.026 5.026a1.75 1.75 0 0 1-2.474 0l-6.25-6.25A1.752 1.752 0 0 1 1 7.775Zm1.5 0c0 .066.026.13.073.177l6.25 6.25a.25.25 0 0 0 .354 0l5.025-5.025a.25.25 0 0 0 0-.354l-6.25-6.25a.25.25 0 0 0-.177-.073H2.75a.25.25 0 0 0-.25.25ZM6 5a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z" />
    </svg>
  ),
  reminder: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M8 16a2 2 0 0 0 1.985-1.75c.017-.137-.097-.25-.235-.25h-3.5c-.138 0-.252.113-.235.25A2 2 0 0 0 8 16ZM3 5a5 5 0 0 1 10 0v2.947c0 .05.015.098.042.139l1.703 2.555A1.519 1.519 0 0 1 13.482 13H2.518a1.516 1.516 0 0 1-1.263-2.36l1.703-2.554A.255.255 0 0 0 3 7.947Zm5-3.5A3.5 3.5 0 0 0 4.5 5v2.947c0 .346-.102.683-.294.97l-1.703 2.556a.017.017 0 0 0-.003.01l.001.006c0 .002.002.004.004.006l.006.004.007.001h10.964l.007-.001.006-.004.004-.006.001-.007a.017.017 0 0 0-.003-.01l-1.703-2.554a1.745 1.745 0 0 1-.294-.97V5A3.5 3.5 0 0 0 8 1.5Z" />
    </svg>
  ),
  activity: (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
      <path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v9.5A1.75 1.75 0 0 1 14.25 13H8.06l-2.573 2.573A1.458 1.458 0 0 1 3 14.543V13H1.75A1.75 1.75 0 0 1 0 11.25Zm1.75-.25a.25.25 0 0 0-.25.25v9.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h6.5a.25.25 0 0 0 .25-.25v-9.5a.25.25 0 0 0-.25-.25Z" />
    </svg>
  ),
};

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
    <aside className="w-64 shrink-0 border-r border-gh-border-default bg-gh-canvas-default h-full flex flex-col">
      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        {navSections.map((section, idx) => (
          <div key={section.title} className={idx > 0 ? "mt-4" : ""}>
            <div className="px-4 mb-2">
              <h2 className="text-xs font-semibold text-gh-fg-muted uppercase tracking-wide">
                {section.title}
              </h2>
            </div>
            <div className="px-2 space-y-0.5">
              {section.items.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    className={clsx(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-gh-accent-subtle text-gh-accent-fg"
                        : "text-gh-fg-default hover:bg-gh-neutral-muted hover:text-gh-fg-default"
                    )}
                  >
                    {icons[item.icon as keyof typeof icons]}
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
        
        {/* Admin Section */}
        {isAdmin && (
          <div className="mt-4 pt-4 border-t border-gh-border-default">
            <div className="px-4 mb-2">
              <h2 className="text-xs font-semibold text-gh-fg-muted uppercase tracking-wide">
                관리자
              </h2>
            </div>
            <div className="px-2 space-y-0.5">
              <Link
                href="/admin/users"
                onClick={onNavigate}
                className={clsx(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  pathname.startsWith("/admin/users")
                    ? "bg-gh-accent-subtle text-gh-accent-fg"
                    : "text-gh-fg-default hover:bg-gh-neutral-muted"
                )}
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 0 1 1-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 0 0 1 3.102 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 5.018 5.01 5.01 0 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 1-.549-.514 3.507 3.507 0 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a.75.75 0 0 1 .416-.672A1.5 1.5 0 0 0 11 5.5.75.75 0 0 1 11 4Zm-5.5-.5a2 2 0 1 0-.001 3.999A2 2 0 0 0 5.5 3.5Z" />
                </svg>
                사용자 관리
              </Link>
            </div>
          </div>
        )}
      </nav>
      
      {/* User Info Section */}
      <div className="border-t border-gh-border-default p-3">
        {meQuery.isLoading ? (
          <div className="text-xs text-gh-fg-muted">로딩 중...</div>
        ) : meQuery.isError ? (
          <div className="text-xs text-gh-danger-fg">사용자 정보 로드 실패</div>
        ) : meQuery.data ? (
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-full flex items-center gap-3 p-2 rounded-md hover:bg-gh-neutral-muted text-left transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-gh-accent-emphasis flex items-center justify-center text-white font-semibold text-sm">
                {meQuery.data.username.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{meQuery.data.username}</div>
                {meQuery.data.email && (
                  <div className="text-xs text-gh-fg-muted truncate">{meQuery.data.email}</div>
                )}
              </div>
              <svg
                className={clsx("w-4 h-4 text-gh-fg-muted transition-transform", showUserMenu && "rotate-180")}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {showUserMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-gh-canvas-overlay border border-gh-border-default rounded-md shadow-lg overflow-hidden">
                {isAdmin && (
                  <div className="px-3 py-2 text-xs text-gh-accent-fg bg-gh-accent-subtle border-b border-gh-border-default">
                    관리자
                  </div>
                )}
                <button
                  onClick={handleLogout}
                  className="w-full px-3 py-2 text-sm text-left hover:bg-gh-danger-subtle text-gh-danger-fg flex items-center gap-2 transition-colors"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M2 2.75C2 1.784 2.784 1 3.75 1h2.5a.75.75 0 0 1 0 1.5h-2.5a.25.25 0 0 0-.25.25v10.5c0 .138.112.25.25.25h2.5a.75.75 0 0 1 0 1.5h-2.5A1.75 1.75 0 0 1 2 13.25Zm10.44 4.5-1.97-1.97a.749.749 0 0 1 .326-1.275.749.749 0 0 1 .734.215l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.749.749 0 0 1-1.275-.326.749.749 0 0 1 .215-.734l1.97-1.97H6.75a.75.75 0 0 1 0-1.5Z" />
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
