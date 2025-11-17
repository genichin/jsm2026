"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import { useRouter } from "next/navigation";

// Backend enums
export type AssetType = "stock" | "crypto" | "bond" | "fund" | "etf" | "cash";

// Backend responses
type AccountBrief = { id: string; name: string; account_type: string };

type Asset = {
  id: string;
  user_id: string;
  account_id: string;
  name: string;
  asset_type: AssetType;
  symbol?: string | null;
  currency: string;
  asset_metadata?: any | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  balance?: number | null;
  price?: number | null;
  account?: AccountBrief | null;
};

type AssetListResponse = {
  items: Asset[];
  total: number;
  page: number;
  size: number;
  pages: number;
};

type AccountsListResponse = { total: number; accounts: { id: string; name: string }[] };

const assetTypeOptions: { value: AssetType; label: string }[] = [
  { value: "stock", label: "주식" },
  { value: "crypto", label: "암호화폐" },
  { value: "bond", label: "채권" },
  { value: "fund", label: "펀드" },
  { value: "etf", label: "ETF" },
  { value: "cash", label: "현금" },
];

export default function AssetsPage() {
  const qc = useQueryClient();
  const router = useRouter();

  // Filters & paging
  const [qText, setQText] = useState("");
  const [accountFilter, setAccountFilter] = useState<string | "">("");
  const [typeFilter, setTypeFilter] = useState<AssetType | "">("");
  const [activeOnly, setActiveOnly] = useState<boolean | "">(true);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);

  // Accounts for filter/create
  const accountsQuery = useQuery<AccountsListResponse>({
    queryKey: ["accounts", { for: "assets-filter" }],
    queryFn: async () => (await api.get("/accounts", { params: { is_active: true } })).data,
  });

  // List assets
  const listQuery = useQuery<AssetListResponse>({
    queryKey: ["assets", { qText, accountFilter, typeFilter, activeOnly, page, size }],
    queryFn: async () => {
      const params: any = { page, size };
      if (accountFilter) params.account_id = accountFilter;
      if (typeFilter) params.asset_type = typeFilter;
      if (activeOnly !== "") params.is_active = activeOnly;
      if (qText) params.search = qText;
      const res = await api.get("/assets", { params });
      return res.data as AssetListResponse;
    },
    placeholderData: (previousData) => previousData,
  });

  const assets = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);

  // Mutations
  const createMut = useMutation({
    mutationFn: async (payload: Partial<Asset> & { account_id: string; asset_type: AssetType }) =>
      (await api.post("/assets", payload)).data as Asset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
    },
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<Asset> }) =>
      (await api.put(`/assets/${id}`, payload)).data as Asset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/assets/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "자산 삭제 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  const recalcMut = useMutation({
    mutationFn: async (id: string) => (await api.post(`/assets/${id}/recalculate-balance`)).data as { asset_id: string; balance: number },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });

  // Inline create/edit state
  const [editing, setEditing] = useState<
    | (Partial<Asset> & { account_id?: string; asset_type?: AssetType })
    | null
  >(null);

  function startCreate() {
    setEditing({
      name: "",
      account_id: accountFilter || accountsQuery.data?.accounts?.[0]?.id || "",
      asset_type: (typeFilter || "stock") as AssetType,
      symbol: "",
      currency: "KRW",
      is_active: true,
      asset_metadata: null,
    });
  }

  function startEdit(row: Asset) {
    setEditing({
      id: row.id,
      name: row.name,
      symbol: row.symbol || "",
      currency: row.currency,
      is_active: row.is_active,
      asset_metadata: row.asset_metadata ?? null,
    });
  }

  function cancelEdit() {
    setEditing(null);
  }

  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editing) return;
    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);

    const metaText = fd.get("asset_metadata")?.toString().trim();
    let asset_metadata: any = null;
    if (metaText) {
      try {
        asset_metadata = JSON.parse(metaText);
      } catch {
        alert("asset_metadata JSON 형식이 올바르지 않습니다.");
        return;
      }
    }

    if (editing.id) {
      const payload: any = {
        name: fd.get("name")?.toString().trim(),
        symbol: fd.get("symbol")?.toString().trim() || null,
        currency: fd.get("currency")?.toString().trim() || "KRW",
        is_active: fd.get("is_active") === "on",
        asset_metadata,
      };
      await updateMut.mutateAsync({ id: editing.id as string, payload });
    } else {
      const account_id = fd.get("account_id")?.toString();
      const asset_type = fd.get("asset_type")?.toString() as AssetType;
      if (!account_id) return alert("계좌를 선택하세요.");
      const payload: any = {
        account_id,
        name: fd.get("name")?.toString().trim(),
        asset_type,
        symbol: fd.get("symbol")?.toString().trim() || null,
        currency: fd.get("currency")?.toString().trim() || "KRW",
        is_active: fd.get("is_active") === "on",
        asset_metadata,
      };
      await createMut.mutateAsync(payload);
    }
  }

  const columns: ColumnDef<Asset>[] = [
    {
      accessorKey: "name",
      header: "자산명",
      cell: ({ row }) => (
        <button
          onClick={() => router.push(`/assets/${row.original.id}`)}
          className="text-blue-600 hover:underline text-left"
        >
          {row.original.name}
        </button>
      ),
    },
    {
      accessorKey: "asset_type",
      header: "유형",
      cell: ({ getValue }) => assetTypeOptions.find((t) => t.value === getValue())?.label ?? String(getValue()),
    },
    { accessorKey: "symbol", header: "심볼", cell: ({ getValue }) => <span className="text-slate-600">{(getValue() as string) || "-"}</span> },
    { accessorKey: "currency", header: "통화" },
    { accessorKey: "balance", header: "수량", cell: ({ getValue }) => <span className="font-mono">{(getValue() as number ?? 0).toLocaleString()}</span> },
    { accessorKey: "price", header: "가격", cell: ({ getValue }) => <span className="font-mono">{(getValue() as number ?? 0).toLocaleString()}</span> },
    {
      accessorKey: "account.name",
      header: "계좌",
      cell: ({ row }) => <span>{row.original.account?.name || "-"}</span>,
    },
    {
      accessorKey: "is_active",
      header: "활성",
      cell: ({ row }) => (
        <button
          onClick={() => updateMut.mutate({ id: row.original.id, payload: { is_active: !row.original.is_active } })}
          className={`px-2 py-1 rounded text-xs ${row.original.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}
        >
          {row.original.is_active ? "활성" : "비활성"}
        </button>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="space-x-2">
          <button className="px-2 py-1 text-xs rounded bg-slate-100" onClick={() => startEdit(row.original)}>편집</button>
          <button className="px-2 py-1 text-xs rounded bg-indigo-100 text-indigo-800" onClick={() => recalcMut.mutate(row.original.id)}>잔고재계산</button>
          <button
            className="px-2 py-1 text-xs rounded bg-rose-100 text-rose-700"
            onClick={() => {
              if (confirm("정말 삭제하시겠습니까? 거래 내역이 있는 자산은 삭제할 수 없습니다.")) deleteMut.mutate(row.original.id);
            }}
          >
            삭제
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-end">
        <div>
          <label className="block text-xs text-slate-600 mb-1">검색</label>
          <input value={qText} onChange={(e) => setQText(e.target.value)} className="border rounded px-2 py-1" placeholder="이름/심볼/계좌" />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">계좌</label>
          <select value={accountFilter} onChange={(e) => { setAccountFilter(e.target.value); setPage(1); }} className="border rounded px-2 py-1 min-w-40">
            <option value="">전체</option>
            {(accountsQuery.data?.accounts || []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">유형</label>
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value as AssetType | ""); setPage(1); }} className="border rounded px-2 py-1">
            <option value="">전체</option>
            {assetTypeOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="block text-xs text-slate-600 mb-1">활성만</label>
          <input type="checkbox" checked={activeOnly === true} onChange={(e) => { setActiveOnly(e.target.checked ? true : ""); setPage(1); }} />
        </div>
        <div className="flex-1" />
        <button onClick={startCreate} className="px-3 py-2 rounded bg-emerald-600 text-white">새 자산</button>
      </div>

      {/* Inline Form */}
      {editing && (
        <form onSubmit={submitForm} className="border rounded p-3 space-y-2 bg-slate-50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-slate-600 mb-1">이름</label>
              <input name="name" defaultValue={editing.name || ""} className="w-full border rounded px-2 py-1" required />
            </div>
            {editing.id ? null : (
              <div>
                <label className="block text-xs text-slate-600 mb-1">계좌</label>
                <select name="account_id" defaultValue={editing.account_id || ""} className="w-full border rounded px-2 py-1">
                  <option value="">선택하세요</option>
                  {(accountsQuery.data?.accounts || []).map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            )}
            {editing.id ? null : (
              <div>
                <label className="block text-xs text-slate-600 mb-1">유형</label>
                <select name="asset_type" defaultValue={(editing.asset_type || "stock") as string} className="w-full border rounded px-2 py-1">
                  {assetTypeOptions.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="block text-xs text-slate-600 mb-1">심볼</label>
              <input name="symbol" defaultValue={editing.symbol || ""} className="w-full border rounded px-2 py-1" />
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">통화</label>
              <input name="currency" defaultValue={editing.currency || "KRW"} className="w-full border rounded px-2 py-1" />
            </div>
            <div className="flex items-center gap-2 pt-5">
              <input type="checkbox" name="is_active" defaultChecked={editing.is_active ?? true} />
              <span>활성</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">asset_metadata (JSON)</label>
            <textarea name="asset_metadata" defaultValue={editing.asset_metadata ? JSON.stringify(editing.asset_metadata, null, 2) : ""} className="w-full border rounded px-2 py-1 h-32 font-mono text-xs" />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-3 py-2 rounded bg-slate-800 text-white">{editing.id ? "수정" : "생성"}</button>
            <button type="button" onClick={cancelEdit} className="px-3 py-2 rounded bg-slate-200">취소</button>
          </div>
        </form>
      )}

      {/* Table */}
      {listQuery.isLoading ? (
        <div>로딩 중...</div>
      ) : (
        <DataTable columns={columns} data={assets} />
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm text-slate-600">
          총 {listQuery.data?.total ?? 0}개, 페이지 {listQuery.data?.page ?? page}/{listQuery.data?.pages ?? 1}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="px-2 py-1 rounded bg-slate-100 disabled:opacity-50"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            이전
          </button>
          <button
            className="px-2 py-1 rounded bg-slate-100 disabled:opacity-50"
            disabled={!!listQuery.data && page >= (listQuery.data.pages || 1)}
            onClick={() => setPage((p) => p + 1)}
          >
            다음
          </button>
          <select
            className="border rounded px-2 py-1"
            value={size}
            onChange={(e) => { setSize(parseInt(e.target.value, 10)); setPage(1); }}
          >
            {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n}/page</option>)}
          </select>
        </div>
      </div>
    </div>
  );
}
