"use client";
import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";

export default function AppShellClient({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const closeSidebar = () => setOpen(false);
  
  return (
    <div className="flex min-h-screen bg-gh-canvas-default">
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={closeSidebar}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 left-0 w-64 max-w-[80%] shadow-xl">
            <div className="h-full bg-gh-canvas-default">
              <Sidebar onNavigate={closeSidebar} />
            </div>
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar onMenuClick={() => setOpen((v) => !v)} />
        <main className="flex-1 px-4 md:px-6 py-4 md:py-6 max-w-[1280px] mx-auto w-full">{children}</main>
      </div>
    </div>
  );
}
