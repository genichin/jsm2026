"use client";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ThemeToggle } from "./ThemeToggle";
import { useState } from "react";

const pageTitles: Record<string, string> = {
  "/dashboard": "대시보드",
  "/accounts": "계좌",
  "/assets": "자산",
  "/transactions": "거래",
  "/categories": "카테고리",
  "/tags": "태그",
  "/reminders": "리마인더",
  "/activities": "액티비티",
  "/admin/users": "사용자 관리",
};

export default function Topbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const pageTitle = pageTitles[pathname] || "J's Money";
  const [showSearch, setShowSearch] = useState(false);
  
  const meQuery = useQuery<{ id: string; username: string; email?: string; is_superuser: boolean }>({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/auth/users/me")).data,
    staleTime: 60 * 1000,
  });
  
  return (
    <header className="sticky top-0 z-20 border-b border-gh-border-default bg-gh-canvas-default">
      <div className="flex h-16 items-center gap-3 px-4 md:px-6">
        {/* Mobile Menu Button */}
        <button
          type="button"
          aria-label="Open menu"
          className="md:hidden inline-flex items-center justify-center p-2 rounded-md hover:bg-gh-neutral-muted"
          onClick={onMenuClick}
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Logo & Title */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <svg className="w-8 h-8 text-gh-fg-default" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="hidden sm:block text-base font-semibold">J&apos;s Money</span>
          </button>
          
          <span className="hidden md:block text-gh-fg-muted">/</span>
          <span className="hidden md:block text-sm font-semibold">{pageTitle}</span>
        </div>

        {/* Search */}
        <div className="hidden md:flex items-center flex-1 max-w-md">
          <div className="relative w-full">
            <input
              type="text"
              placeholder="Search or jump to..."
              className="w-full px-3 py-1.5 text-sm bg-gh-canvas-inset border border-gh-border-default rounded-md focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis focus:border-transparent"
              onFocus={() => setShowSearch(true)}
              onBlur={() => setTimeout(() => setShowSearch(false), 200)}
            />
            <kbd className="absolute right-2 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-xs bg-gh-canvas-subtle border border-gh-border-default rounded">
              /
            </kbd>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          {/* Search Icon (Mobile) */}
          <button className="md:hidden p-2 rounded-md hover:bg-gh-neutral-muted">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
              <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-8.997.01A4.5 4.5 0 0 0 11.5 7Z" />
            </svg>
          </button>

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* User Menu */}
          {meQuery.data && (
            <div className="flex items-center gap-2 pl-2 border-l border-gh-border-default">
              <button className="flex items-center gap-2 p-1.5 rounded-md hover:bg-gh-neutral-muted">
                <div className="w-6 h-6 rounded-full bg-gh-accent-emphasis flex items-center justify-center text-white text-xs font-semibold">
                  {meQuery.data.username.charAt(0).toUpperCase()}
                </div>
                <span className="hidden sm:block text-sm font-medium">{meQuery.data.username}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
