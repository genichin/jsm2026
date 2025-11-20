"use client";

import { useMemo, useState, useEffect } from "react";
import TransactionCards from "@/components/TransactionCards";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { Modal } from "@/components/Modal";
import { ColumnDef } from "@tanstack/react-table";
import { TransactionType, transactionTypeOptions, transactionTypeLabels } from "@/lib/transactionTypes";

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

type AssetsListResponse = { items: { id: string; name: string; asset_type: string; currency?: string; account_id?: string }[] };
type AccountsListResponse = { total: number; accounts: { id: string; name: string }[] };
type CategoriesTreeResponse = { id: string; name: string; flow_type: string }[];

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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [suggestedCategoryId, setSuggestedCategoryId] = useState<string | null>(null);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [viewMode, setViewMode] = useState<"table" | "card">(() => {
    if (typeof window === "undefined") return "card";
    const saved = window.localStorage.getItem("txViewMode");
    if (saved === "card" || saved === "table") return saved as any;
    return "card";
  });

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

  // Flatten categories tree for select options
  const categoriesFlat = useMemo(() => {
    const flat: Array<{ id: string; name: string; depth: number }> = [];
    const traverse = (nodes: any[], depth = 0) => {
      for (const node of nodes) {
        flat.push({ id: node.id, name: node.name, depth });
        if (node.children?.length) {
          traverse(node.children, depth + 1);
        }
      }
    };
    if (categoriesQuery.data) {
      traverse(categoriesQuery.data);
    }
    return flat;
  }, [categoriesQuery.data]);

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

  // Inline create/edit state
  const [editing, setEditing] = useState<Partial<Transaction> | null>(null);
  const [selectedType, setSelectedType] = useState<TransactionType | "">("");
  const [selectedAssetId, setSelectedAssetId] = useState<string>("");
  
  // 환전 관련 상태
  const [exchangeSourceAmount, setExchangeSourceAmount] = useState<number>(0);
  const [exchangeTargetAmount, setExchangeTargetAmount] = useState<number>(0);
  const [exchangeRate, setExchangeRate] = useState<number | null>(null);

  // 선택한 자산의 계좌에 속한 현금 자산 필터링
  const cashAssetsInSameAccount = useMemo(() => {
    if (!selectedAssetId || !assetsQuery.data?.items) return [];
    
    const selectedAsset = assetsQuery.data.items.find(a => a.id === selectedAssetId);
    if (!selectedAsset) return [];
    
    // 선택한 자산과 같은 계좌의 현금 자산만 필터링
    return assetsQuery.data.items.filter(a => 
      a.asset_type === 'cash' &&
      a.account_id === selectedAsset.account_id
    );
  }, [selectedAssetId, assetsQuery.data?.items]);

  // 매수/매도 시 동일 통화의 현금 자산 필터링
  const cashAssetsForBuySell = useMemo(() => {
    if (!selectedAssetId || !assetsQuery.data?.items) return [];
    
    const selectedAsset = assetsQuery.data.items.find(a => a.id === selectedAssetId);
    if (!selectedAsset) return [];
    
    // 선택한 자산과 같은 통화의 현금 자산만 필터링
    return assetsQuery.data.items.filter(a => 
      a.asset_type === 'cash' &&
      a.currency === selectedAsset.currency &&
      a.account_id === selectedAsset.account_id
    );
  }, [selectedAssetId, assetsQuery.data?.items]);

  // Mutations
  const createMut = useMutation({
    mutationFn: async (payload: any) => (await api.post("/transactions", payload)).data as Transaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
      setIsModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 생성 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) =>
      (await api.put(`/transactions/${id}`, payload)).data as Transaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
      setIsModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 수정 중 오류가 발생했습니다.";
      alert(msg);
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

  const uploadMut = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post("/transactions/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data;
    },
    onSuccess: (data: any) => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      
      const successCount = data.created || 0;
      const skippedCount = data.skipped || 0;
      const errorCount = data.failed || 0;
      
      if (errorCount > 0) {
        const errorMsg = data.errors.slice(0, 3).map((e: any) => 
          `행 ${e.row}: ${e.error}`
        ).join('\n');
        alert(`${successCount}개 생성, ${skippedCount}개 중복 스킵, ${errorCount}개 오류:\n${errorMsg}${errorCount > 3 ? '\n...' : ''}`);
      } else if (skippedCount > 0) {
        alert(`${successCount}개 생성, ${skippedCount}개 중복으로 스킵되었습니다.`);
      } else {
        alert(`${successCount}개의 거래가 성공적으로 생성되었습니다.`);
      }
      
      setIsUploadModalOpen(false);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "파일 업로드 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  function startCreate() {
    const initialType = (typeFilter || "deposit") as TransactionType;
    const initialAssetId = assetFilter || assetsQuery.data?.items?.[0]?.id || "";
    setSelectedType(initialType);
    setSelectedAssetId(initialAssetId);
    setExchangeSourceAmount(0);
    setExchangeTargetAmount(0);
    setExchangeRate(null);
    setEditing({
      asset_id: initialAssetId,
      type: initialType,
      quantity: 0,
      price: 1,
      fee: 0,
      tax: 0,
      transaction_date: new Date().toISOString().slice(0, 19),
      description: "",
      memo: "",
      is_confirmed: true,
    });
    setIsModalOpen(true);
  }

  function startEdit(row: Transaction) {
    setSelectedType(row.type);
    setSelectedAssetId(row.asset_id);
    setEditing(row);
    setIsModalOpen(true);
  }

  function cancelEdit() {
    setEditing(null);
    setSelectedType("");
    setSelectedAssetId("");
    setExchangeSourceAmount(0);
    setExchangeTargetAmount(0);
    setExchangeRate(null);
    setIsModalOpen(false);
    setSuggestedCategoryId(null);
  }

  async function suggestCategory() {
    const form = document.querySelector("form") as HTMLFormElement;
    if (!form) return;
    const description = (form.querySelector("[name='description']") as HTMLInputElement)?.value?.trim();
    if (!description) {
      alert("설명을 입력하세요.");
      return;
    }
    setIsSuggesting(true);
    try {
      const res = await api.post("/auto-rules/simulate", { description });
      const data = res.data;
      if (data.matched && data.category_id) {
        setSuggestedCategoryId(data.category_id);
        // 카테고리 select에 자동 선택
        const categorySelect = form.querySelector("[name='category_id']") as HTMLSelectElement;
        if (categorySelect) {
          categorySelect.value = data.category_id;
        }
      } else {
        setSuggestedCategoryId(null);
        alert("매칭되는 자동 규칙이 없습니다.");
      }
    } catch (e) {
      console.error(e);
      alert("자동 추천 실패");
    } finally {
      setIsSuggesting(false);
    }
  }

  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editing) return;
    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);

    if (editing.id) {
      // Update: type, description, memo, is_confirmed, category_id
      const payload: any = {
        description: fd.get("description")?.toString().trim() || null,
        memo: fd.get("memo")?.toString().trim() || null,
        is_confirmed: fd.get("is_confirmed") === "on",
      };
      
      // type 처리
      const typeValue = fd.get("type")?.toString();
      if (typeValue) {
        payload.type = typeValue;
      }
      
      // category_id 처리: 빈 문자열은 null로, 값이 있으면 그대로
      const categoryIdValue = fd.get("category_id")?.toString();
      if (categoryIdValue) {
        payload.category_id = categoryIdValue;
      } else {
        payload.category_id = null;
      }
      
      await updateMut.mutateAsync({ id: editing.id as string, payload });
    } else {
      // Create
      const asset_id = fd.get("asset_id")?.toString();
      const type = fd.get("type")?.toString() as TransactionType;
      if (!asset_id) return alert("자산을 선택하세요.");

      let quantity = parseFloat(fd.get("quantity")?.toString() || "0");
      
      // 매도/출금은 음수로 변환
      if (type === "sell" || type === "withdraw" || type === "transfer_out") {
        quantity = -Math.abs(quantity);
      } else {
        // 매수/입금은 양수로 보장
        if (type === "buy" || type === "deposit" || type === "transfer_in") {
          quantity = Math.abs(quantity);
        }
      }
      
      const payload: any = {
        asset_id,
        type,
        quantity,
        price: parseFloat(fd.get("price")?.toString() || "1"),
        fee: parseFloat(fd.get("fee")?.toString() || "0"),
        tax: parseFloat(fd.get("tax")?.toString() || "0"),
        transaction_date: fd.get("transaction_date")?.toString() || new Date().toISOString(),
        description: fd.get("description")?.toString().trim() || null,
        memo: fd.get("memo")?.toString().trim() || null,
        is_confirmed: fd.get("is_confirmed") === "on",
        category_id: fd.get("category_id")?.toString() || null,
      };

      // 환전인 경우 대상 자산과 금액 추가
      if (type === "exchange") {
        const target_asset_id = fd.get("target_asset_id")?.toString();
        const target_amount = fd.get("target_amount")?.toString();
        if (!target_asset_id) return alert("환전 대상 자산을 선택하세요.");
        if (!target_amount || parseFloat(target_amount) <= 0) return alert("환전 대상 금액을 입력하세요.");
        payload.target_asset_id = target_asset_id;
        payload.target_amount = parseFloat(target_amount);
        
        // 환율 정보를 transaction_metadata에 추가
        if (exchangeRate !== null) {
          payload.transaction_metadata = {
            exchange_rate: exchangeRate
          };
        }
      }

      // 매수/매도인 경우 현금 자산 추가
      if (type === "buy" || type === "sell") {
        const cash_asset_id = fd.get("cash_asset_id")?.toString();
        if (cash_asset_id) {
          payload.cash_asset_id = cash_asset_id;
        }
      }

      // 배당인 경우 현금 자산 추가 (선택사항)
      if (type === "dividend") {
        const cash_asset_id = fd.get("cash_asset_id")?.toString();
        if (cash_asset_id) {
          payload.cash_asset_id = cash_asset_id;
        }
      }

      await createMut.mutateAsync(payload);
    }
  }

  // Column visibility state (persisted)
  const [hiddenCols, setHiddenCols] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      const raw = window.localStorage.getItem("txHiddenCols");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("txHiddenCols", JSON.stringify(hiddenCols));
    }
  }, [hiddenCols]);

  const baseColumns: ColumnDef<Transaction>[] = useMemo(() => [
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
      cell: ({ getValue }) => transactionTypeOptions.find((t) => t.value === getValue())?.label ?? String(getValue()),
    },
    { accessorKey: "quantity", header: "수량", cell: ({ getValue }) => <span className="font-mono">{(getValue() as number).toLocaleString()}</span> },
    { accessorKey: "price", header: "가격", cell: ({ getValue }) => <span className="font-mono">{(getValue() as number).toLocaleString()}</span> },
    {
      id: "amount",
      header: "금액",
      cell: ({ row }) => {
        const amt = Math.abs(row.original.quantity) * row.original.price;
        return <span className="font-mono text-slate-800">{amt.toLocaleString()}</span>;
      },
    },
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
      id: "realized_profit",
      header: "실현손익",
      cell: ({ row }) => {
        const v = row.original.realized_profit;
        if (v === null || v === undefined) return <span className="text-xs text-slate-400">-</span>;
        return <span className={`font-mono text-xs ${v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "text-slate-400"}`}>{v.toLocaleString()}</span>;
      },
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
  ], [updateMut, deleteMut]);
  const columns: ColumnDef<Transaction>[] = useMemo(() => {
    return baseColumns.filter(c => {
      const key = (c as any).accessorKey || c.id;
      if (!key) return true;
      return !hiddenCols[key];
    });
  }, [baseColumns, hiddenCols]);

  return (
    <div className="space-y-4">
      {/* Filters & Column Settings */}
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
            {transactionTypeOptions.map((o) => (
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
        <button onClick={() => setIsUploadModalOpen(true)} className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
          파일 업로드
        </button>
        <button onClick={startCreate} className="px-3 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700">새 거래</button>
      </div>

      {/* Modal Form */}
      <Modal
        isOpen={isModalOpen}
        onClose={cancelEdit}
        title={editing?.id ? "거래 수정" : "새 거래"}
        size="xl"
      >
        <form onSubmit={submitForm} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {editing?.id ? (
              <>
                {/* 편집 모드: 유형 변경 가능 */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">유형 *</label>
                  <select 
                    name="type" 
                    value={selectedType} 
                    onChange={(e) => setSelectedType(e.target.value as TransactionType)}
                    className="w-full border rounded px-3 py-2"
                  >
                    {transactionTypeOptions.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">자산</label>
                  <input 
                    type="text" 
                    value={assetsQuery.data?.items.find(a => a.id === editing.asset_id)?.name || ''} 
                    disabled 
                    className="w-full border rounded px-3 py-2 bg-gray-50 text-gray-600" 
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">자산 *</label>
                  <select 
                    name="asset_id" 
                    value={selectedAssetId} 
                    onChange={(e) => setSelectedAssetId(e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">선택하세요</option>
                    {(assetsQuery.data?.items || []).map((a) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">유형 *</label>
                  <select 
                    name="type" 
                    value={selectedType} 
                    onChange={(e) => setSelectedType(e.target.value as TransactionType)}
                    className="w-full border rounded px-3 py-2"
                  >
                    {transactionTypeOptions.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                {selectedType !== "exchange" && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      수량 * 
                      {(selectedType === "sell" || selectedType === "withdraw" || selectedType === "transfer_out") && 
                        <span className="text-xs text-amber-600 ml-1">(양수 입력, 자동으로 차감 처리됩니다)</span>
                      }
                    </label>
                    <input 
                      type="number" 
                      step="any" 
                      name="quantity" 
                      defaultValue={editing?.quantity ? Math.abs(editing.quantity) : 0} 
                      className="w-full border rounded px-3 py-2" 
                      required 
                      min="0"
                      placeholder={(selectedType === "sell" || selectedType === "withdraw" || selectedType === "transfer_out") ? "양수 입력 (예: 1.036021)" : ""}
                    />
                  </div>
                )}
                {selectedType !== "exchange" && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">가격 *</label>
                    <input 
                      type="number" 
                      step="any" 
                      name="price" 
                      defaultValue={selectedType === "dividend" ? 0 : (editing?.price ?? 1)} 
                      className="w-full border rounded px-3 py-2" 
                      required 
                    />
                  </div>
                )}
                {selectedType !== "exchange" && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">수수료</label>
                      <input type="number" step="any" name="fee" defaultValue={editing?.fee ?? 0} className="w-full border rounded px-3 py-2" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">세금</label>
                      <input type="number" step="any" name="tax" defaultValue={editing?.tax ?? 0} className="w-full border rounded px-3 py-2" />
                    </div>
                  </>
                )}
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">거래일시 *</label>
                  <input type="datetime-local" name="transaction_date" defaultValue={editing?.transaction_date?.slice(0, 19) || ""} className="w-full border rounded px-3 py-2" step="1" required />
                </div>
                {(selectedType === "buy" || selectedType === "sell") && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      현금 자산 {cashAssetsForBuySell.length === 0 ? "" : "(선택사항)"}
                    </label>
                    <select name="cash_asset_id" defaultValue="" className="w-full border rounded px-3 py-2">
                      <option value="">자동 선택</option>
                      {cashAssetsForBuySell.map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    {cashAssetsForBuySell.length === 0 && (
                      <p className="text-xs text-amber-600 mt-1">동일 계좌·통화의 현금 자산이 없습니다. 자동으로 생성됩니다.</p>
                    )}
                  </div>
                )}
                {selectedType === "exchange" && (
                  <>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">환전 대상 자산 (현금) *</label>
                      <select name="target_asset_id" defaultValue="" className="w-full border rounded px-3 py-2" required>
                        <option value="">선택하세요</option>
                        {cashAssetsInSameAccount.map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">환전 출발 금액 *</label>
                      <input 
                        type="number" 
                        step="any" 
                        name="quantity" 
                        value={exchangeSourceAmount || ""} 
                        onChange={(e) => {
                          const val = parseFloat(e.target.value) || 0;
                          setExchangeSourceAmount(val);
                          if (val > 0 && exchangeTargetAmount > 0) {
                            const selectedAsset = assetsQuery.data?.items.find(a => a.id === selectedAssetId);
                            const sourceCurrency = selectedAsset?.currency || "";
                            // KRW 항상 분자: KRW가 출발이면 KRW/외화, KRW가 대상이면 KRW/외화
                            const rate = sourceCurrency === "KRW" 
                              ? val / exchangeTargetAmount 
                              : exchangeTargetAmount / val;
                            setExchangeRate(rate);
                          }
                        }}
                        className="w-full border rounded px-3 py-2" 
                        required 
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">환전 대상 금액 *</label>
                      <input 
                        type="number" 
                        step="any" 
                        name="target_amount" 
                        value={exchangeTargetAmount || ""} 
                        onChange={(e) => {
                          const val = parseFloat(e.target.value) || 0;
                          setExchangeTargetAmount(val);
                          if (exchangeSourceAmount > 0 && val > 0) {
                            const selectedAsset = assetsQuery.data?.items.find(a => a.id === selectedAssetId);
                            const sourceCurrency = selectedAsset?.currency || "";
                            // KRW 항상 분자: KRW가 출발이면 KRW/외화, KRW가 대상이면 KRW/외화
                            const rate = sourceCurrency === "KRW" 
                              ? exchangeSourceAmount / val 
                              : val / exchangeSourceAmount;
                            setExchangeRate(rate);
                          }
                        }}
                        className="w-full border rounded px-3 py-2" 
                        required 
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">환전 수수료</label>
                      <input type="number" step="any" name="fee" defaultValue={editing?.fee ?? 0} className="w-full border rounded px-3 py-2" />
                    </div>
                    {exchangeRate !== null && exchangeRate > 0 && (
                      <div className="col-span-2">
                        <div className="bg-blue-50 border border-blue-200 rounded px-4 py-3">
                          <p className="text-sm font-medium text-blue-900">
                            환율: {exchangeRate.toFixed(2)} KRW
                          </p>
                          <p className="text-xs text-blue-700 mt-1">
                            {(() => {
                              const selectedAsset = assetsQuery.data?.items.find(a => a.id === selectedAssetId);
                              const sourceCurrency = selectedAsset?.currency || "";
                              return sourceCurrency === "KRW"
                                ? `${exchangeSourceAmount.toLocaleString()} KRW → ${exchangeTargetAmount.toLocaleString()}`
                                : `${exchangeSourceAmount.toLocaleString()} → ${exchangeTargetAmount.toLocaleString()} KRW`;
                            })()}
                          </p>
                        </div>
                      </div>
                    )}
                  </>
                )}
                {selectedType === "dividend" && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      배당금 입금 계좌 (현금)
                    </label>
                    <select name="cash_asset_id" defaultValue="" className="w-full border rounded px-3 py-2">
                      <option value="">없음 (가격이 0인 경우)</option>
                      {cashAssetsForBuySell.map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    {cashAssetsForBuySell.length === 0 && (
                      <p className="text-xs text-amber-600 mt-1">동일 계좌·통화의 현금 자산이 없습니다. 가격 &gt; 0이면 자동으로 생성됩니다.</p>
                    )}
                  </div>
                )}
              </>
            )}
            {/* 카테고리: dividend와 exchange를 제외하고 표시 (편집 모드 포함) */}
            {selectedType !== "dividend" && selectedType !== "exchange" && (
              <div className={editing?.id ? "col-span-2" : ""}>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  카테고리
                  {suggestedCategoryId && (
                    <span className="ml-2 text-xs text-emerald-600">✓ 자동 추천됨</span>
                  )}
                </label>
                <select name="category_id" defaultValue={editing?.category_id || ""} className="w-full border rounded px-3 py-2">
                  <option value="">없음</option>
                  {categoriesFlat.map((c) => (
                    <option key={c.id} value={c.id}>
                      {"\u00A0".repeat(c.depth * 2)}{c.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className={editing?.id ? "col-span-2" : ""}>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-slate-700 mb-1">설명</label>
                  <input name="description" defaultValue={editing?.description || ""} className="w-full border rounded px-3 py-2" />
                </div>
                {selectedType !== "dividend" && selectedType !== "exchange" && (
                  <button
                    type="button"
                    onClick={suggestCategory}
                    disabled={isSuggesting}
                    className="px-3 py-2 rounded bg-blue-100 text-blue-700 text-sm whitespace-nowrap hover:bg-blue-200 disabled:opacity-50"
                  >
                    {isSuggesting ? "추천 중..." : "자동 추천"}
                  </button>
                )}
              </div>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">메모</label>
              <input name="memo" defaultValue={editing?.memo || ""} className="w-full border rounded px-3 py-2" />
            </div>
            <div className="col-span-2 flex items-center gap-2">
              <input type="checkbox" name="is_confirmed" id="is_confirmed" defaultChecked={editing?.is_confirmed ?? true} className="w-4 h-4" />
              <label htmlFor="is_confirmed" className="text-sm font-medium text-slate-700">거래 확정</label>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={cancelEdit} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300">취소</button>
            <button type="submit" className="px-4 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700">{editing?.id ? "수정" : "생성"}</button>
          </div>
        </form>
      </Modal>

      {/* File Upload Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="거래 내역 파일 업로드"
        size="lg"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            uploadMut.mutate(formData);
          }}
          className="space-y-4"
        >
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">지원 형식</h3>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• <strong>토스뱅크</strong>: 암호화된 Excel 파일 (.xlsx) - 비밀번호 입력 필요</li>
              <li>• <strong>KB은행</strong>: HTML 형식 Excel 파일 (.xls)</li>
              <li>• <strong>KB증권</strong>: 거래내역 CSV/Excel</li>
              <li>• <strong>미래에셋증권</strong>: 거래내역 CSV/Excel</li>
              <li>• <strong>CSV 파일</strong>: UTF-8 또는 CP949 인코딩</li>
            </ul>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              자산 선택 *
            </label>
            <select name="asset_id" required className="w-full border rounded px-3 py-2">
              <option value="">자산을 선택하세요</option>
              {(assetsQuery.data?.items || []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.asset_type})
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 mt-1">
              파일의 거래 내역이 이 자산에 연결됩니다
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              파일 선택 *
            </label>
            <input
              type="file"
              name="file"
              accept=".csv,.xlsx,.xls"
              required
              className="w-full border rounded px-3 py-2 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <p className="text-xs text-slate-500 mt-1">
              CSV, XLSX, XLS 파일 지원
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              파일 비밀번호 (선택사항)
            </label>
            <input
              type="password"
              name="password"
              placeholder="암호화된 Excel 파일인 경우 입력"
              className="w-full border rounded px-3 py-2"
            />
            <p className="text-xs text-slate-500 mt-1">
              토스뱅크 등 암호화된 파일의 경우 비밀번호를 입력하세요
            </p>
          </div>

          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded p-3">
            <input
              type="checkbox"
              name="dry_run"
              id="dry_run"
              value="true"
              className="w-4 h-4"
            />
            <label htmlFor="dry_run" className="text-sm text-amber-900">
              <strong>미리보기 모드</strong> (실제로 저장하지 않고 확인만)
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(false)}
              className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={uploadMut.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploadMut.isPending ? "업로드 중..." : "업로드"}
            </button>
          </div>
        </form>

        {uploadMut.isSuccess && uploadMut.data && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
            <h4 className="font-semibold text-green-900 mb-2">업로드 완료</h4>
            <div className="text-sm text-green-800 space-y-1">
              <p>• 생성된 거래: {uploadMut.data.created || 0}개</p>
              {uploadMut.data.skipped > 0 && (
                <p>• 중복 스킵: {uploadMut.data.skipped}개</p>
              )}
              {uploadMut.data.failed > 0 && (
                <p className="text-red-700">• 실패: {uploadMut.data.failed}개</p>
              )}
              {uploadMut.data.errors && uploadMut.data.errors.length > 0 && (
                <div className="mt-2">
                  <p className="text-red-700 font-medium">오류 발생: {uploadMut.data.errors.length}개</p>
                  <ul className="mt-1 text-xs text-red-600 max-h-40 overflow-y-auto">
                    {uploadMut.data.errors.map((err: any, idx: number) => (
                      <li key={idx}>행 {err.row}: {err.error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* View Mode Toggle */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <span>보기:</span>
          <button
            onClick={() => { setViewMode("card"); if (typeof window !== "undefined") window.localStorage.setItem("txViewMode", "card"); }}
            className={`px-2 py-1 rounded ${viewMode === "card" ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-700"}`}
          >카드</button>
          <button
            onClick={() => { setViewMode("table"); if (typeof window !== "undefined") window.localStorage.setItem("txViewMode", "table"); }}
            className={`px-2 py-1 rounded ${viewMode === "table" ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-700"}`}
          >테이블</button>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <details className="relative">
            <summary className="cursor-pointer px-3 py-2 rounded bg-slate-100 text-xs">컬럼 설정</summary>
            <div className="absolute z-10 mt-2 w-52 p-3 rounded border bg-white shadow space-y-2">
              {[
                { key: "fee", label: "수수료" },
                { key: "tax", label: "세금" },
                { key: "description", label: "설명" },
                { key: "realized_profit", label: "실현손익" },
                { key: "amount", label: "금액" },
              ].map(opt => (
                <label key={opt.key} className="flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={!hiddenCols[opt.key]}
                    onChange={(e) => setHiddenCols(h => ({ ...h, [opt.key]: !e.target.checked }))}
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
              <button
                type="button"
                onClick={() => setHiddenCols({})}
                className="w-full mt-1 text-xs px-2 py-1 rounded bg-slate-200"
              >초기화</button>
            </div>
          </details>
        </div>
      </div>

      {/* Data View */}
      {listQuery.isLoading ? (
        <div>로딩 중...</div>
      ) : viewMode === "table" ? (
        <DataTable columns={columns} data={transactions} />
      ) : (
        <TransactionCards
          items={transactions.map(t => ({
            id: t.id,
            asset_id: t.asset_id,
            asset_name: t.asset?.name,
            type: t.type,
            quantity: t.quantity,
            price: t.price,
            fee: t.fee,
            tax: t.tax,
            realized_profit: t.realized_profit,
            transaction_date: t.transaction_date,
            category_name: t.category?.name,
            description: t.description,
            memo: t.memo,
            is_confirmed: t.is_confirmed,
            external_id: t.external_id,
            related_transaction_id: t.related_transaction_id,
          }))}
          onEdit={(id) => {
            const tx = transactions.find(x => x.id === id);
            if (tx) startEdit(tx);
          }}
        />
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
