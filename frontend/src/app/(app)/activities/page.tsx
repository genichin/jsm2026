"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import { useEffect } from "react";
import { getToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

type Activity = { id: string; activity_type: string; target_type: string; created_at: string; content?: string };

export default function ActivitiesPage() {
  const router = useRouter();
  useEffect(() => { if (!getToken()) router.replace("/login"); }, [router]);
  const q = useQuery({ queryKey: ["activities"], queryFn: async () => (await api.get("/activities")).data });
  const items: Activity[] = q.data?.items ?? q.data ?? [];
  const columns: ColumnDef<Activity>[] = [
    { accessorKey: "created_at", header: "일시", cell: ({ getValue }) => new Date(getValue() as string).toLocaleString() },
    { accessorKey: "activity_type", header: "유형" },
    { accessorKey: "target_type", header: "대상" },
    { accessorKey: "content", header: "내용" },
  ];
  return (
    <div className="space-y-4">
      {q.isLoading ? <div>로딩 중...</div> : <DataTable columns={columns} data={items} />}
    </div>
  );
}
