import "./globals.css";
import { ReactQueryProvider } from "@/lib/queryClient";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "J's Money",
  description: "개인 자산관리 프론트엔드",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </body>
    </html>
  );
}
