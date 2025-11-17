"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";

// Backend enums
export type TransactionType =
  | "buy" | "sell" | "deposit" | "withdraw" | "dividend" | "interest"
  | "fee" | "transfer_in" | "transfer_out" | "adjustment" | "invest"
  | "redeem" | "internal_transfer" | "card_payment" | "promotion_deposit"
  | "auto_transfer" | "remittance" | "exchange";

// Backend responses
type AssetBrief = {
  id: string;
  name: string;
  asset_type: string;
  symbol?: string;
  currency: string;
  is_active: boolean;
};

type CategoryBrief = {
  id: string;
  name: string;
  flow_type: string;
};

type Transaction = {
  id: string;
  asset_id: string;
  related_transaction_id?: string | null;
  category_id?: string | null;
  category?: CategoryBrief | null;
  type: TransactionType;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  realized_profit?: number | null;
  transaction_date: string;
  description?: string | null;
  memo?: string | null;
  is_confirmed: boolean;
  external_id?: string | null;
  created_at: string;
  updated_at: string;
  asset?: AssetBrief | null;
};

type TransactionListResponse = {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
};

type AssetsListResponse = { items: { id: string; name: string; asset_type: string }[] };
type AccountsListResponse = { total: number; accounts: { id: string; name: string }[] };
type CategoriesTreeResponse = { id: string; name: string; flow_type: string }[];

const txTypeOptions: { value: TransactionType; label: string }[] = [
  { value: "buy", label: "매수" },
  { value: "sell", label: "매도" },
  { value: "deposit", label: "입금" },
  { value: "withdraw", label: "출금" },
  { value: "dividend", label: "배당" },
  { value: "interest", label: "이자" },
  { value: "fee", label: "수수료" },
  { value: "transfer_in", label: "이체입금" },
  { value: "transfer_out", label: "이체출금" },
  { value: "adjustment", label: "수량조정" },
  { value: "invest", label: "투자" },
  { value: "redeem", label: "해지" },
  { value: "exchange", label: "환전" },
];

export default function TransactionsPage() {
  const qc = useQueryClient();

  // Filters & paging
  const [assetFilter, setAssetFilter] = useState<string | "">("");
  const [accountFilter, setAccountFilter] = useState<string | "">("");
  const [typeFilter, setTypeFilter] = useState<TransactionType | "">("");
  const [categoryFilter, setCategoryFilter] = useState<string | "">("");
  const [confirmedOnly, setConfirmedOnly] = useState<boolean | "">(true);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);

  // Assets, Accounts, Categories for filters/create
  const assetsQuery = useQuery<AssetsListResponse>({
    queryKey: ["assets", { for: "tx-filter" }],
    queryFn: async () => (await api.get("/assets", { params: { page: 1, size: 100 } })).data,
  });

  const accountsQuery = useQuery<AccountsListResponse>({
    queryKey: ["accounts", { for: "tx-filter" }],
    queryFn: async () => (await api.get("/accounts", { params: { is_active: true } })).data,
  });

  const categoriesQuery = useQuery<CategoriesTreeResponse>({
    queryKey: ["categories-tree"],
    queryFn: async () => (await api.get("/categories/tree")).data,
  });

  // List transactions
  const listQuery = useQuery<TransactionListResponse>({
    queryKey: ["transactions", { assetFilter, accountFilter, typeFilter, categoryFilter, confirmedOnly, page, size }],
    queryFn: async () => {
      const params: any = { page, size };
      if (assetFilter) params.asset_id = assetFilter;
      if (accountFilter) params.account_id = accountFilter;
      if (typeFilter) params.type = typeFilter;
      if (categoryFilter) params.category_id = categoryFilter;
      if (confirmedOnly !== "") params.is_confirmed = confirmedOnly;
      const res = await api.get("/transactions/recent", { params });
      return res.data as TransactionListResponse;
    },
    placeholderData: (previousData) => previousData,
  });

  const transactions = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);

  // Mutations
  const createMut = useMutation({
    mutationFn: async (payload: any) => (await api.post("/transactions", payload)).data as Transaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 생성 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) =>
      (await api.patch(`/transactions/${id}`, payload)).data as Transaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/transactions/${id}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 삭제 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // Inline create/edit state
  const [editing, setEditing] = useState<Partial<Transaction> | null>(null);

  function startCreate() {
    setEditing({
      asset_id: assetFilter || assetsQuery.data?.items?.[0]?.id || "",
      type: (typeFilter || "deposit") as TransactionType,
      quantity: 0,
      price: 1,
      fee: 0,
      tax: 0,
      transaction_date: new Date().toISOString().slice(0, 16),
      description: "",
      memo: "",
      is_confirmed: true,
    });
  }

  function startEdit(row: Transaction) {
    setEditing({
      id: row.id,
      description: row.description || "",
      memo: row.memo || "",
      is_confirmed: row.is_confirmed,
      category_id: row.category_id || "",
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

    if (editing.id) {
      // Update: only description, memo, is_confirmed, category_id
      const payload: any = {
        description: fd.get("description")?.toString().trim() || null,
        memo: fd.get("memo")?.toString().trim() || null,
        is_confirmed: fd.get("is_confirmed") === "on",
        category_id: fd.get("category_id")?.toString() || null,
      };
      await updateMut.mutateAsync({ id: editing.id as string, payload });
    } else {
      // Create
      const asset_id = fd.get("asset_id")?.toString();
      const type = fd.get("type")?.toString() as TransactionType;
      if (!asset_id) return alert("자산을 선택하세요.");

      const payload: any = {
        asset_id,
        type,
        quantity: parseFloat(fd.get("quantity")?.toString() || "0"),
        price: parseFloat(fd.get("price")?.toString() || "1"),
        fee: parseFloat(fd.get("fee")?.toString() || "0"),
        tax: parseFloat(fd.get("tax")?.toString() || "0"),
        transaction_date: fd.get("transaction_date")?.toString() || new Date().toISOString(),
        description: fd.get("description")?.toString().trim() || null,
        memo: fd.get("memo")?.toString().trim() || null,
        is_confirmed: fd.get("is_confirmed") === "on",
        category_id: fd.get("category_id")?.toString() || null,
      };
      await createMut.mutateAsync(payload);
    }
  }

  const columns: ColumnDef<Transaction>[] = [
    {
      accessorKey: "transaction_date",
      header: "일시",
      cell: ({ getValue }) => new Date(getValue() as string).toLocaleString("ko-KR", { year: "2-digit", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }),
    },
    {
      accessorKey: "asset.name",
      header: "자산",
      cell: ({ row }) => <span className="text-slate-700">{row.original.asset?.name || "-"}</span>,
    },
    {
      accessorKey: "type",
      header: "유형",
      cell: ({ getValue }) => txTypeOptions.find((t) => t.value === getValue())?.label ?? String(getValue()),
    },
    { accessorKey: "quantity", header: "수량", cell: ({ getValue }) => <span className="font-mono">{(getValue() as number).toLocaleString()}</span> },
    { accessorKey: "price", header: "가격", cell: ({ getValue }) => <span className="font-mono">{(getValue() as number).toLocaleString()}</span> },
    { accessorKey: "fee", header: "수수료", cell: ({ getValue }) => <span className="font-mono text-xs text-slate-600">{(getValue() as number).toLocaleString()}</span> },
    { accessorKey: "tax", header: "세금", cell: ({ getValue }) => <span className="font-mono text-xs text-slate-600">{(getValue() as number).toLocaleString()}</span> },
    {
      accessorKey: "category.name",
      header: "카테고리",
      cell: ({ row }) => <span className="text-xs text-slate-600">{row.original.category?.name || "-"}</span>,
    },
    {
      accessorKey: "description",
      header: "설명",
      cell: ({ getValue }) => <span className="text-sm text-slate-700 max-w-xs truncate">{(getValue() as string) || "-"}</span>,
    },
    {
      accessorKey: "is_confirmed",
      header: "확정",
      cell: ({ row }) => (
        <button
          onClick={() => updateMut.mutate({ id: row.original.id, payload: { is_confirmed: !row.original.is_confirmed } })}
          className={`px-2 py-1 rounded text-xs ${row.original.is_confirmed ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}
        >
          {row.original.is_confirmed ? "확정" : "임시"}
        </button>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="space-x-2">
          <button className="px-2 py-1 text-xs rounded bg-slate-100" onClick={() => startEdit(row.original)}>편집</button>
          <button
            className="px-2 py-1 text-xs rounded bg-rose-100 text-rose-700"
            onClick={() => {
              if (confirm("정말 삭제하시겠습니까? 연관 거래와 잔고에 영향을 줄 수 있습니다.")) deleteMut.mutate(row.original.id);
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
          <label className="block text-xs text-slate-600 mb-1">자산</label>
          <select value={assetFilter} onChange={(e) => { setAssetFilter(e.target.value); setPage(1); }} className="border rounded px-2 py-1 min-w-40">
            <option value="">전체</option>
            {(assetsQuery.data?.items || []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
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
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value as TransactionType | ""); setPage(1); }} className="border rounded px-2 py-1">
            <option value="">전체</option>
            {txTypeOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">카테고리</label>
          <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }} className="border rounded px-2 py-1 min-w-32">
            <option value="">전체</option>
            {(categoriesQuery.data || []).map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="block text-xs text-slate-600 mb-1">확정만</label>
          <input type="checkbox" checked={confirmedOnly === true} onChange={(e) => { setConfirmedOnly(e.target.checked ? true : ""); setPage(1); }} />
        </div>
        <div className="flex-1" />
        <button onClick={startCreate} className="px-3 py-2 rounded bg-emerald-600 text-white">새 거래</button>
      </div>

      {/* Inline Form */}
      {editing && (
        <form onSubmit={submitForm} className="border rounded p-3 space-y-2 bg-slate-50">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {editing.id ? null : (
              <>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">자산</label>
                  <select name="asset_id" defaultValue={editing.asset_id || ""} className="w-full border rounded px-2 py-1">
                    <option value="">선택하세요</option>
                    {(assetsQuery.data?.items || []).map((a) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">유형</label>
                  <select name="type" defaultValue={(editing.type || "deposit") as string} className="w-full border rounded px-2 py-1">
                    {txTypeOptions.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">수량</label>
                  <input type="number" step="any" name="quantity" defaultValue={editing.quantity ?? 0} className="w-full border rounded px-2 py-1" required />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">가격</label>
                  <input type="number" step="any" name="price" defaultValue={editing.price ?? 1} className="w-full border rounded px-2 py-1" required />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">수수료</label>
                  <input type="number" step="any" name="fee" defaultValue={editing.fee ?? 0} className="w-full border rounded px-2 py-1" />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">세금</label>
                  <input type="number" step="any" name="tax" defaultValue={editing.tax ?? 0} className="w-full border rounded px-2 py-1" />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 mb-1">거래일시</label>
                  <input type="datetime-local" name="transaction_date" defaultValue={editing.transaction_date?.slice(0, 16) || ""} className="w-full border rounded px-2 py-1" required />
                </div>
              </>
            )}
            <div>
              <label className="block text-xs text-slate-600 mb-1">카테고리</label>
              <select name="category_id" defaultValue={editing.category_id || ""} className="w-full border rounded px-2 py-1">
                <option value="">없음</option>
                {(categoriesQuery.data || []).map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">설명</label>
              <input name="description" defaultValue={editing.description || ""} className="w-full border rounded px-2 py-1" />
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">메모</label>
              <input name="memo" defaultValue={editing.memo || ""} className="w-full border rounded px-2 py-1" />
            </div>
            <div className="flex items-center gap-2 pt-5">
              <input type="checkbox" name="is_confirmed" defaultChecked={editing.is_confirmed ?? true} />
              <span>확정</span>
            </div>
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
        <DataTable columns={columns} data={transactions} />
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
