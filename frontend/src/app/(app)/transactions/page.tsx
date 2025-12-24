"use client";

import { useMemo, useState, useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import TransactionCards from "@/components/TransactionCards";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { Modal } from "@/components/Modal";
import { ColumnDef } from "@tanstack/react-table";
import { TransactionType, transactionTypeOptions, transactionTypeLabels } from "@/lib/transactionTypes";
import { useTransactionForm } from "@/hooks/useTransactionForm";
import { DynamicTransactionForm, CategoryBrief as CategoryBriefType } from "@/components/TransactionForm";
import { Button } from "@/components/Button";

// Backend responses
type AssetBrief = {
  id: string;
  name: string;
  asset_type: string;
  symbol?: string;
  currency: string;
  is_active: boolean;
};

type CategoryBrief = CategoryBriefType;

type Transaction = {
  id: string;
  asset_id: string;
  related_transaction_id?: string | null;
  related_asset_name?: string | null;
  category_id?: string | null;
  category?: CategoryBrief | null;
  type: TransactionType;
  quantity: number;
  transaction_date: string;
  description?: string | null;
  memo?: string | null;
  flow_type: string;
  confirmed?: boolean;
  price?: number | null;
  fee?: number | null;
  tax?: number | null;
  realized_profit?: number | null;
  extras?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  asset?: AssetBrief | null;
};

type FlowType = "expense" | "income" | "transfer" | "investment" | "neutral" | "undefined";

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
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Filters & paging
  const [assetFilter, setAssetFilter] = useState<string | "">("");
  const [accountFilter, setAccountFilter] = useState<string | "">("")
  const [typeFilter, setTypeFilter] = useState<TransactionType | "">("")
  const [categoryFilter, setCategoryFilter] = useState<string | "">("")
  const [flowTypeFilter, setFlowTypeFilter] = useState<string>("")
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"table" | "card">(() => {
    if (typeof window === "undefined") return "card";
    const saved = window.localStorage.getItem("txViewMode");
    if (saved === "card" || saved === "table") return saved as any;
    return "card";
  });

  // Transaction form hook
  const transactionForm = useTransactionForm({
    typeFilter,
    assetFilter,
    onSuccess: () => {
      // Hook에서 자동으로 쿼리 무효화됨
    },
  });

  const {
    editing,
    selectedType,
    selectedAssetId,
    isModalOpen,
    suggestedCategoryId,
    isSuggesting,
    setSelectedType,
    setSelectedAssetId,
    startCreate,
    startEdit,
    submitForm,
    cancelEdit,
    suggestCategory,
    deleteMut,
    uploadMut,
  } = transactionForm;

  // URL 파라미터에서 초기 필터 설정
  useEffect(() => {
    const assetId = searchParams.get('asset_id');
    if (assetId && assetId !== assetFilter) {
      setAssetFilter(assetId);
      setPage(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);



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
    const flat: Array<CategoryBrief & { depth: number }> = [];
    const traverse = (nodes: any[], depth = 0) => {
      for (const node of nodes) {
        flat.push({ id: node.id, name: node.name, flow_type: node.flow_type, depth });
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
    queryKey: ["transactions", { assetFilter, accountFilter, typeFilter, categoryFilter, flowTypeFilter, page, size }],
    queryFn: async () => {
      const params: any = { page, size };
      if (assetFilter) params.asset_id = assetFilter;
      if (accountFilter) params.account_id = accountFilter;
      if (typeFilter) params.type = typeFilter;
      if (categoryFilter) params.category_id = categoryFilter;
      if (flowTypeFilter) params.flow_type = flowTypeFilter;
    
      const res = await api.get("/transactions/recent", { params });
      return res.data as TransactionListResponse;
    },
    placeholderData: (previousData) => previousData,
  });

  const transactions = listQuery.data?.items ?? [];


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
    {
      accessorKey: "category.name",
      header: "카테고리",
      cell: ({ row }) => <span className="text-xs text-slate-600">{row.original.category?.name || "-"}</span>,
    },
    {
      accessorKey: "flow_type",
      header: "흐름",
      cell: ({ getValue }) => {
        const labelMap: Record<string, string> = {
          expense: "지출",
          income: "수입",
          transfer: "이체",
          investment: "투자",
          neutral: "중립",
          undefined: "미분류",
        };
        const v = getValue() as string;
        return <span className="text-xs text-slate-600">{labelMap[v] || v || "-"}</span>;
      },
    },
    {
      accessorKey: "confirmed",
      header: "확정",
      cell: ({ row }) => {
        const confirmed = row.original.confirmed ?? false;
        return (
          <span className={`text-xs px-2 py-0.5 rounded ${confirmed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
            {confirmed ? '확정' : '미확정'}
          </span>
        );
      },
    },
    {
      accessorKey: "description",
      header: "설명",
      cell: ({ getValue }) => <span className="text-sm text-gh-fg-muted max-w-xs truncate">{(getValue() as string) || "-"}</span>,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="space-x-2">
          <Button size="sm" variant="default" onClick={() => startEdit(row.original)}>편집</Button>
          <Button
            size="sm"
            variant="danger"
            onClick={() => {
              if (confirm("정말 삭제하시겠습니까? 연관 거래와 잔고에 영향을 줄 수 있습니다.")) deleteMut.mutate(row.original.id);
            }}
          >
            삭제
          </Button>
        </div>
      ),
    },
  ], [deleteMut]);
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
          <label className="block text-xs text-gh-fg-muted mb-1">계좌</label>
          <select 
            value={accountFilter} 
            onChange={(e) => { setAccountFilter(e.target.value); setPage(1); }} 
            className={`border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 min-w-40 focus:ring-2 focus:ring-gh-accent-emphasis ${searchParams.get('asset_id') ? 'opacity-50 cursor-not-allowed' : ''}`}
            disabled={!!searchParams.get('asset_id')}
          >
            <option value="">전체</option>
            {(accountsQuery.data?.accounts || []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gh-fg-muted mb-1">자산</label>
          <select 
            value={assetFilter} 
            onChange={(e) => { 
              const newValue = e.target.value;
              setAssetFilter(newValue); 
              setPage(1);
            }} 
            className={`border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 min-w-40 focus:ring-2 focus:ring-gh-accent-emphasis ${searchParams.get('asset_id') ? 'opacity-50 cursor-not-allowed' : ''}`}
            disabled={!!searchParams.get('asset_id')}
            title={searchParams.get('asset_id') ? '자산 상세 페이지에서 필터링됨' : ''}
          >
            <option value="">전체</option>
            {(assetsQuery.data?.items || []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gh-fg-muted mb-1">유형</label>
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value as TransactionType | ""); setPage(1); }} className="border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 focus:ring-2 focus:ring-gh-accent-emphasis">
            <option value="">전체</option>
            {transactionTypeOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gh-fg-muted mb-1">카테고리</label>
          <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }} className="border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 min-w-32 focus:ring-2 focus:ring-gh-accent-emphasis">
            <option value="">전체</option>
            {(categoriesQuery.data || []).map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gh-fg-muted mb-1">흐름 타입</label>
          <select value={flowTypeFilter} onChange={(e) => { setFlowTypeFilter(e.target.value); setPage(1); }} className="border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 focus:ring-2 focus:ring-gh-accent-emphasis">
            <option value="">전체</option>
            <option value="expense">지출</option>
            <option value="income">수입</option>
            <option value="transfer">이체</option>
            <option value="investment">투자</option>
            <option value="neutral">중립</option>
            <option value="undefined">미분류</option>
          </select>
        </div>
        <div className="flex-1" />
        {searchParams.get('asset_id') && (
          <Button 
            variant="default"
            onClick={() => {
              setAssetFilter("");
              router.push('/transactions');
            }}
          >
            필터 초기화
          </Button>
        )}
        <Button onClick={() => setIsUploadModalOpen(true)}>
          파일 업로드
        </Button>
        <Button onClick={startCreate}>새 거래</Button>
      </div>

      {/* Modal Form */}
      <Modal
        isOpen={isModalOpen}
        onClose={cancelEdit}
        title={
          editing?.id 
            ? `거래 수정 - ${assetsQuery.data?.items.find(a => a.id === selectedAssetId)?.name || ""}` 
            : selectedAssetId && assetsQuery.data?.items
            ? `새 거래 - ${assetsQuery.data.items.find(a => a.id === selectedAssetId)?.name || ""}`
            : "새 거래"
        }
        size="xl"
      >
        <DynamicTransactionForm
          transactionType={selectedType as TransactionType}
          editing={editing as any}
          isEditMode={!!editing?.id}
          assets={assetsQuery.data?.items || []}
          categories={categoriesFlat}
          selectedAssetId={selectedAssetId}
          onAssetChange={setSelectedAssetId}
          onTypeChange={setSelectedType}
          onSubmit={submitForm}
          onCancel={cancelEdit}
          onSuggestCategory={suggestCategory}
          isSuggesting={isSuggesting}
          suggestedCategoryId={suggestedCategoryId}
        />
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
          <div className="bg-gh-accent-subtle border border-gh-accent-muted rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-gh-accent-fg mb-2">지원 형식</h3>
            <ul className="text-xs text-gh-accent-fg space-y-1">
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
            <select 
              name="asset_id" 
              required 
              className="w-full border rounded px-3 py-2"
              defaultValue={assetFilter}
            >
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

          <div className="flex justify-end gap-3 pt-4 border-t border-gh-border-default">
            <Button
              type="button"
              variant="default"
              onClick={() => setIsUploadModalOpen(false)}
            >
              취소
            </Button>
            <Button
              type="submit"
              disabled={uploadMut.isPending}
            >
              {uploadMut.isPending ? "업로드 중..." : "업로드"}
            </Button>
          </div>
        </form>

        {uploadMut.isSuccess && uploadMut.data && (
          <div className="mt-4 p-4 bg-gh-success-subtle border border-gh-success-muted rounded-md">
            <h4 className="font-semibold text-gh-success-fg mb-2">업로드 완료</h4>
            <div className="text-sm text-gh-success-fg space-y-1">
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
        <div className="flex items-center gap-2 text-xs text-gh-fg-muted">
          <span>보기:</span>
          <Button
            size="sm"
            variant={viewMode === "card" ? "primary" : "default"}
            onClick={() => { setViewMode("card"); if (typeof window !== "undefined") window.localStorage.setItem("txViewMode", "card"); }}
          >카드</Button>
          <Button
            size="sm"
            variant={viewMode === "table" ? "primary" : "default"}
            onClick={() => { setViewMode("table"); if (typeof window !== "undefined") window.localStorage.setItem("txViewMode", "table"); }}
          >테이블</Button>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <details className="relative">
            <summary className="cursor-pointer px-3 py-2 rounded-md bg-gh-canvas-subtle border border-gh-border-default text-xs text-gh-fg-default">컬럼 설정</summary>
            <div className="absolute z-10 mt-2 w-52 p-3 rounded-md border border-gh-border-default bg-gh-canvas-overlay shadow-lg space-y-2">
              {[
                { key: "fee", label: "수수료" },
                { key: "tax", label: "세금" },
                { key: "description", label: "설명" },
                { key: "realized_profit", label: "실현손익" },
                { key: "amount", label: "금액" },
              ].map(opt => (
                <label key={opt.key} className="flex items-center gap-2 text-xs text-gh-fg-default">
                  <input
                    type="checkbox"
                    checked={!hiddenCols[opt.key]}
                    onChange={(e) => setHiddenCols(h => ({ ...h, [opt.key]: !e.target.checked }))}
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
              <Button
                type="button"
                size="sm"
                variant="default"
                onClick={() => setHiddenCols({})}
                className="w-full mt-1"
              >초기화</Button>
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
          items={transactions.map(t => {
            // 현금배당의 경우 extras.asset에서 배당 자산 이름 찾기
            let dividendAssetName = null;
            if (t.type === 'cash_dividend' && t.extras?.source_asset_id && assetsQuery.data?.items) {
              const dividendAsset = assetsQuery.data.items.find(a => a.id === t.extras!.source_asset_id);
              dividendAssetName = dividendAsset?.name || null;
            }
            
            return {
              id: t.id,
              asset_id: t.asset_id,
              asset_name: t.asset?.name,
              type: t.type,
              quantity: t.quantity,
              transaction_date: t.transaction_date,
              category_name: t.category?.name,
              description: t.description,
              memo: t.memo,
              related_transaction_id: t.related_transaction_id,
              related_asset_name: t.related_asset_name,  // 연결된 자산 이름 추가
              extras: t.extras,
              dividend_asset_name: dividendAssetName,  // 배당 자산 이름 추가
              currency: t.asset?.currency,  // 통화 정보 추가
              flow_type: t.flow_type,
            };
          })}
          onEdit={(id) => {
            const tx = transactions.find(x => x.id === id);
            if (tx) startEdit(tx);
          }}
          onDelete={(id) => {
            if (confirm("정말 삭제하시겠습니까? 연관 거래와 잔고에 영향을 줄 수 있습니다.")) {
              deleteMut.mutate(id);
            }
          }}
        />
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm text-gh-fg-muted">
          총 {transactions.length}개, 페이지 {listQuery.data?.page ?? page}/{listQuery.data?.pages ?? 1}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            이전
          </Button>
          <Button
            variant="default"
            size="sm"
            disabled={!!listQuery.data && page >= (listQuery.data.pages || 1)}
            onClick={() => setPage((p) => p + 1)}
          >
            다음
          </Button>
          <select
            className="border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 focus:ring-2 focus:ring-gh-accent-emphasis"
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
