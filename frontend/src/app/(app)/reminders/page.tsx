"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import { useEffect } from "react";
import { getToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

type Reminder = { id: string; title: string; reminder_type: string; remind_at: string; is_active: boolean };

export default function RemindersPage() {
  const router = useRouter();
  useEffect(() => { if (!getToken()) router.replace("/login"); }, [router]);
  const q = useQuery({ queryKey: ["reminders"], queryFn: async () => (await api.get("/reminders")).data });
  const items: Reminder[] = q.data?.items ?? q.data ?? [];
  const columns: ColumnDef<Reminder>[] = [
    { accessorKey: "title", header: "제목" },
    { accessorKey: "reminder_type", header: "유형" },
    { accessorKey: "remind_at", header: "알림시각", cell: ({ getValue }) => new Date(getValue() as string).toLocaleString() },
    { accessorKey: "is_active", header: "활성", cell: ({ getValue }) => (getValue() ? "✓" : "-") },
  ];
  return (
    <div className="space-y-4">
      {q.isLoading ? <div>로딩 중...</div> : <DataTable columns={columns} data={items} />}
    </div>
  );
}
