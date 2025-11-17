import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import AppShellClient from "@/components/AppShellClient";

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const hasAuth = cookies().get("atm")?.value === "1";
  if (!hasAuth) {
    redirect("/login");
  }
  return <AppShellClient>{children}</AppShellClient>;
}
