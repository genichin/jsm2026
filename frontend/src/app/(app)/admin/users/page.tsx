"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/DataTable";

type User = {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
};

export default function AdminUsersPage() {
  const qc = useQueryClient();

  const meQuery = useQuery<User>({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/auth/users/me")).data,
    staleTime: 60 * 1000,
  });

  const listQuery = useQuery<User[]>({
    queryKey: ["admin-users"],
    queryFn: async () => (await api.get("/auth/users")).data,
    enabled: !!meQuery.data?.is_superuser,
  });

  const toggleActiveMut = useMutation({
    mutationFn: async (user: User) => (await api.patch(`/auth/users/${user.id}/toggle-active`)).data as User,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const toggleSuperuserMut = useMutation({
    mutationFn: async (user: User) => (await api.patch(`/auth/users/${user.id}/toggle-superuser`)).data as User,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const deleteMut = useMutation({
    mutationFn: async (user: User) => (await api.delete(`/auth/users/${user.id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const me = meQuery.data;
  const rows: User[] = listQuery.data ?? [];

  const columns: ColumnDef<User>[] = [
    { accessorKey: "email", header: "이메일" },
    { accessorKey: "username", header: "사용자명" },
    { accessorKey: "full_name", header: "이름", cell: ({ getValue }) => <span className="text-slate-600">{(getValue() as string) || "-"}</span> },
    { accessorKey: "created_at", header: "생성일", cell: ({ getValue }) => new Date(String(getValue())).toLocaleString() },
    {
      accessorKey: "is_active",
      header: "활성",
      cell: ({ row }) => {
        const u = row.original;
        const disabled = me?.id === u.id; // 자기자신 제한
        const onClick = () => !disabled && toggleActiveMut.mutate(u);
        return (
          <button
            onClick={onClick}
            disabled={disabled || toggleActiveMut.isPending}
            className={`px-2 py-1 rounded text-xs ${u.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            {u.is_active ? "활성" : "비활성"}
          </button>
        );
      },
    },
    {
      accessorKey: "is_superuser",
      header: "관리자",
      cell: ({ row }) => {
        const u = row.original;
        const disabled = me?.id === u.id; // 자기자신 제한
        const onClick = () => !disabled && toggleSuperuserMut.mutate(u);
        return (
          <button
            onClick={onClick}
            disabled={disabled || toggleSuperuserMut.isPending}
            className={`px-2 py-1 rounded text-xs ${u.is_superuser ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            {u.is_superuser ? "관리자" : "일반"}
          </button>
        );
      },
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const u = row.original;
        const disabled = me?.id === u.id; // 자기자신 삭제 금지
        const onDelete = () => {
          if (disabled) return;
          if (confirm(`사용자 ${u.email} 을(를) 삭제하시겠습니까?`)) {
            deleteMut.mutate(u);
          }
        };
        return (
          <div className="space-x-2">
            <button
              onClick={onDelete}
              disabled={disabled || deleteMut.isPending}
              className={`px-2 py-1 text-xs rounded bg-rose-100 text-rose-700 ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              삭제
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">관리자만 접근 가능한 사용자 목록/권한 관리 화면입니다.</p>

      {meQuery.isLoading ? (
        <div>권한 확인 중...</div>
      ) : meQuery.data && !meQuery.data.is_superuser ? (
        <div className="text-rose-600">접근 권한이 없습니다.</div>
      ) : null}

      {listQuery.isLoading ? (
        <div>로딩 중...</div>
      ) : listQuery.isError ? (
        <div className="text-rose-600">사용자 목록을 불러오지 못했습니다.</div>
      ) : (
        <DataTable columns={columns} data={rows} />
      )}
    </div>
  );
}
