import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "로그인 - J's Money",
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
      {children}
    </main>
  );
}
