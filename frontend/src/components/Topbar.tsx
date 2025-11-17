"use client";
import { usePathname, useRouter } from "next/navigation";

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
  
  return (
    <header className="sticky top-0 z-10 border-b bg-white/80 backdrop-blur">
      <div className="container flex h-14 items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Open menu"
            className="md:hidden inline-flex items-center justify-center rounded p-2 hover:bg-slate-100"
            onClick={onMenuClick}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
              <path fillRule="evenodd" d="M3.75 6.75A.75.75 0 0 1 4.5 6h15a.75.75 0 0 1 0 1.5h-15a.75.75 0 0 1-.75-.75Zm0 5.25a.75.75 0 0 1 .75-.75h15a.75.75 0 0 1 0 1.5h-15a.75.75 0 0 1-.75-.75Zm.75 4.5a.75.75 0 0 0 0 1.5h15a.75.75 0 0 0 0-1.5h-15Z" clipRule="evenodd" />
            </svg>
          </button>
          {/* Mobile: Show "J's Money" as home button + page title */}
          <div className="md:hidden flex items-center gap-2">
            <button
              onClick={() => router.push("/dashboard")}
              className="text-sm font-bold text-blue-600 hover:text-blue-700"
            >
              J's Money
            </button>
            <span className="text-slate-400">›</span>
            <span className="text-sm font-medium text-slate-700">{pageTitle}</span>
          </div>
          {/* Desktop: Show only page title */}
          <div className="hidden md:block text-sm font-medium text-slate-700">{pageTitle}</div>
        </div>
      </div>
    </header>
  );
}
