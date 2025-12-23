"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { useRouter } from "next/navigation";
import { AssetFormModal, type AssetFormData } from "@/components/AssetFormModal";
import { formatCurrency, formatNumber } from "@/lib/number-formatter";

// Backend enums
export type AssetType = "stock" | "crypto" | "bond" | "fund" | "etf" | "cash" | "savings" | "deposit";

// Backend responses
type AccountBrief = { id: string; name: string; account_type: string };

type Asset = {
  id: string;
  user_id: string;
  account_id: string;
  name: string;
  asset_type: AssetType;
  symbol?: string | null;
  market?: string | null;
  currency: string;
  asset_metadata?: any | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  balance?: number | null;
  price?: number | null;
  change?: number | null;
  need_trade?: { price?: number | null; quantity?: number | null; ttl?: number | null } | null;
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
  { value: "savings", label: "예금" },
  { value: "deposit", label: "적금" },
];

const assetTypeAccent: Record<AssetType, string> = {
  stock: "ring-emerald-400/25 border-emerald-100/70",
  crypto: "ring-indigo-400/25 border-indigo-100/70",
  bond: "ring-amber-400/25 border-amber-100/70",
  fund: "ring-sky-400/25 border-sky-100/70",
  etf: "ring-purple-400/25 border-purple-100/70",
  cash: "ring-slate-400/25 border-slate-200/70",
  savings: "ring-teal-400/25 border-teal-100/70",
  deposit: "ring-rose-400/25 border-rose-100/70",
};

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

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetFormData | null>(null);

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
      setIsModalOpen(false);
      setEditingAsset(null);
    },
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<Asset> }) =>
      (await api.put(`/assets/${id}`, payload)).data as Asset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setIsModalOpen(false);
      setEditingAsset(null);
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

  function startCreate() {
    setEditingAsset({
      name: "",
      account_id: accountFilter || accountsQuery.data?.accounts?.[0]?.id || "",
      asset_type: (typeFilter || "stock") as AssetType,
      symbol: "",
      market: "",
      currency: "KRW",
      is_active: true,
      asset_metadata: null,
    });
    setIsModalOpen(true);
  }

  function startEdit(row: Asset) {
    setEditingAsset({
      id: row.id,
      name: row.name,
      account_id: row.account_id,
      symbol: row.symbol || "",
      market: row.market || "",
      currency: row.currency,
      is_active: row.is_active,
      asset_metadata: row.asset_metadata ?? null,
    });
    setIsModalOpen(true);
  }

  function cancelEdit() {
    setIsModalOpen(false);
    setEditingAsset(null);
  }

  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editingAsset) return;
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

    if (editingAsset.id) {
      const payload: any = {
        name: fd.get("name")?.toString().trim(),
        symbol: fd.get("symbol")?.toString().trim() || null,
        market: fd.get("market")?.toString().trim() || null,
        currency: fd.get("currency")?.toString().trim() || "KRW",
        is_active: fd.get("is_active") === "on",
        asset_metadata,
      };
      await updateMut.mutateAsync({ id: editingAsset.id as string, payload });
    } else {
      const account_id = fd.get("account_id")?.toString();
      const asset_type = fd.get("asset_type")?.toString() as AssetType;
      if (!account_id) return alert("계좌를 선택하세요.");
      const payload: any = {
        account_id,
        name: fd.get("name")?.toString().trim(),
        asset_type,
        symbol: fd.get("symbol")?.toString().trim() || null,
        market: fd.get("market")?.toString().trim() || null,
        currency: fd.get("currency")?.toString().trim() || "KRW",
        is_active: fd.get("is_active") === "on",
        asset_metadata,
      };
      await createMut.mutateAsync(payload);
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-end">
        <div>
          <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">검색</label>
          <input
            value={qText}
            onChange={(e) => setQText(e.target.value)}
            className="border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
            placeholder="이름/심볼/계좌"
          />
        </div>
        <div>
          <label className="block text-xs text-gh-fg-muted mb-1">계좌</label>
          <select value={accountFilter} onChange={(e) => { setAccountFilter(e.target.value); setPage(1); }} className="border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 focus:ring-2 focus:ring-gh-accent-emphasis">
            <option value="">전체</option>
            {(accountsQuery.data?.accounts || []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gh-fg-muted mb-1">유형</label>
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value as AssetType | ""); setPage(1); }} className="border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 focus:ring-2 focus:ring-gh-accent-emphasis">
            <option value="">전체</option>
            {assetTypeOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="block text-xs text-gh-fg-muted mb-1">활성만</label>
          <input type="checkbox" checked={activeOnly === true} onChange={(e) => { setActiveOnly(e.target.checked ? true : ""); setPage(1); }} />
        </div>
        <div className="flex-1" />
        <Button onClick={startCreate}>새 자산</Button>
      </div>
      {/* Asset Form Modal */}
      <AssetFormModal
        isOpen={isModalOpen}
        onClose={cancelEdit}
        editingAsset={editingAsset}
        accounts={accountsQuery.data?.accounts || []}
        onSubmit={submitForm}
        isLoading={createMut.isPending || updateMut.isPending}
      />

      {/* Card list */}
      {listQuery.isLoading ? (
        <div className="rounded-xl border border-gh-border-default bg-gh-canvas-default divide-y divide-gh-border-default">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="h-24 animate-pulse" />
          ))}
        </div>
      ) : assets.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gh-border-default bg-gh-canvas-subtle px-6 py-10 text-center text-gh-fg-muted">
          조건에 맞는 자산이 없습니다.
        </div>
      ) : (
        <div className="rounded-xl border border-gh-border-default bg-gh-canvas-default divide-y divide-gh-border-default">
          {assets.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onOpen={() => router.push(`/assets/${asset.id}`)}
              onEdit={() => startEdit(asset)}
              onRecalc={() => recalcMut.mutate(asset.id)}
              onDelete={() => {
                if (confirm("정말 삭제하시겠습니까? 거래 내역이 있는 자산은 삭제할 수 없습니다.")) deleteMut.mutate(asset.id);
              }}
              onToggleActive={() => updateMut.mutate({ id: asset.id, payload: { is_active: !asset.is_active } })}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm text-gh-fg-muted">
          총 {listQuery.data?.total ?? 0}개, 페이지 {listQuery.data?.page ?? page}/{listQuery.data?.pages ?? 1}
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

type AssetCardProps = {
  asset: Asset;
  onOpen: () => void;
  onEdit: () => void;
  onRecalc: () => void;
  onDelete: () => void;
  onToggleActive: () => void;
};

function Field({ label, value, align = "left" }: { label: string; value: ReactNode; align?: "left" | "right" }) {
  return (
    <div className="rounded-md border border-gh-border-default bg-gh-canvas-default px-3 py-2">
      <div className="text-[12px] text-gh-fg-muted">{label}</div>
      <div className={`text-sm font-medium text-gh-fg ${align === "right" ? "text-right" : ""}`}>{value ?? "-"}</div>
    </div>
  );
}

function renderByType(asset: Asset) {
  switch (asset.asset_type) {
    case "stock":
    case "etf":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Field label="티커" value={asset.symbol || "-"} />
          <Field label="시장" value={asset.market || "-"} />
        </div>
      );
    case "crypto":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Field label="심볼" value={asset.symbol || "-"} />
          <Field label="네트워크" value={asset.asset_metadata?.network || "-"} />
        </div>
      );
    case "bond":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Field label="표면금리" value={asset.asset_metadata?.coupon_rate ?? "-"} />
          <Field label="만기" value={asset.asset_metadata?.maturity_date ?? "-"} />
        </div>
      );
    case "fund":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Field label="펀드 코드" value={asset.symbol || "-"} />
          <Field label="운용사" value={asset.asset_metadata?.manager || "-"} />
        </div>
      );
    case "savings":
    case "deposit":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Field label="금리" value={asset.asset_metadata?.rate ?? "-"} />
          <Field label="만기" value={asset.asset_metadata?.maturity_date ?? "-"} />
        </div>
      );
    case "cash":
      return (
        <div className="grid grid-cols-2 gap-3">
          <Field label="통화" value={asset.currency} />
          <Field label="메모" value={asset.asset_metadata?.memo || "-"} />
        </div>
      );
    default:
      return null;
  }
}

function AssetCard({ asset, onOpen, onEdit, onRecalc, onDelete, onToggleActive }: AssetCardProps) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = assetTypeOptions.find((t) => t.value === asset.asset_type)?.label ?? asset.asset_type;
  const accent = assetTypeAccent[asset.asset_type] ?? "ring-gh-border-muted/30 border-gh-border-default";

  function renderSummaryByType() {
    switch (asset.asset_type) {
      case "stock":
      case "etf":
        const priceChange = asset.change;
        const changeColor = priceChange && priceChange > 0 ? "text-red-600" : priceChange && priceChange < 0 ? "text-blue-600" : "text-gh-fg-muted";
        const changePrefix = priceChange && priceChange > 0 ? "+" : "";
        
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="티커" value={asset.symbol || "-"} />
            <Field label="잔고" value={formatNumber(asset.balance)} align="right" />
            <Field 
              label="현재가" 
              value={asset.price ? formatCurrency(asset.price, asset.currency) : "-"} 
              align="right" 
            />
            <Field 
              label="등락률" 
              value={
                priceChange != null ? (
                  <span className={changeColor}>
                    {changePrefix}{priceChange.toFixed(2)}%
                  </span>
                ) : "-"
              } 
              align="right" 
            />
          </div>
        );
      case "crypto":
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="심볼" value={asset.symbol || "-"} />
            <Field label="네트워크" value={asset.asset_metadata?.network || "-"} />
          </div>
        );
      case "bond":
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="표면금리" value={asset.asset_metadata?.coupon_rate ?? "-"} />
            <Field label="만기" value={asset.asset_metadata?.maturity_date ?? "-"} />
          </div>
        );
      case "fund":
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="코드" value={asset.symbol || "-"} />
            <Field label="운용사" value={asset.asset_metadata?.manager || "-"} />
          </div>
        );
      case "savings":
      case "deposit":
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="금리" value={asset.asset_metadata?.rate ?? "-"} />
            <Field label="만기" value={asset.asset_metadata?.maturity_date ?? "-"} />
          </div>
        );
      case "cash":
        console.log('Cash asset:', {
          balance: asset.balance,
          balanceType: typeof asset.balance,
          currency: asset.currency,
          fullAsset: asset
        });
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="잔고" value={formatCurrency(asset.balance, asset.currency)} align="right" />
          </div>
        );
      default:
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="수량" value={(asset.balance ?? 0).toLocaleString()} />
            <Field label="가격" value={(asset.price ?? 0).toLocaleString()} />
          </div>
        );
    }
  }

  return (
    <article className="group relative px-4 py-3 hover:bg-gh-canvas-subtle transition">
      <div className="flex flex-col gap-3 md:grid md:grid-cols-12 md:items-center md:gap-4">
        <div className="md:col-span-5 flex items-start gap-3">
          <div className={`mt-1 h-8 w-1 rounded-full ${accent}`} aria-hidden />
          <div className="space-y-1">
            <button onClick={onOpen} className="text-left text-base font-semibold text-gh-accent-fg hover:underline">
              <span className="inline-flex items-center gap-2">
                {asset.name}
                {asset.need_trade?.price != null || asset.need_trade?.quantity != null ? (
                  <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-[11px] font-medium text-yellow-800 border border-yellow-200">
                    거래요청
                  </span>
                ) : null}
              </span>
            </button>
            <div className="flex flex-wrap items-center gap-2 text-[12px] text-gh-fg-muted">
              <span className="inline-flex items-center gap-1 rounded-full bg-gh-canvas-inset px-2 py-0.5 font-medium text-gh-fg">{typeLabel}</span>
              <span className="inline-flex items-center gap-1 font-medium text-gh-fg-muted">{asset.account?.name || "미지정"}</span>
              <span className="inline-flex items-center gap-1 font-medium text-gh-fg-muted">{asset.currency}</span>
            </div>
          </div>
        </div>

        <div className="md:col-span-5">
          {renderSummaryByType()}
        </div>

        <div className="md:col-span-2 flex items-center justify-end gap-3">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[12px] font-semibold ${asset.is_active ? "bg-emerald-50 text-emerald-700 border border-emerald-100" : "bg-slate-100 text-slate-700 border border-slate-200"}`}>
            {asset.is_active ? "활성" : "비활성"}
          </span>
          <Button
            size="sm"
            variant="default"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? "접기" : "확장"}
          </Button>
        </div>
      </div>

      {expanded ? (
        <div className="mt-3 rounded-lg border border-gh-border-default bg-gh-canvas-inset p-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1 text-sm text-gh-fg-muted">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gh-fg">{asset.symbol || "-"}</span>
                <span>{asset.market || "시장 미지정"}</span>
              </div>
              <div className="text-[12px]">최근 갱신: {new Date(asset.updated_at).toLocaleString()}</div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="default" onClick={onToggleActive}>
                {asset.is_active ? "비활성 전환" : "활성 전환"}
              </Button>
              <Button size="sm" variant="primary" onClick={onOpen}>열기</Button>
              <Button size="sm" variant="default" onClick={onEdit}>편집</Button>
              <Button size="sm" variant="default" onClick={onRecalc}>잔고재계산</Button>
              <Button size="sm" variant="danger" onClick={onDelete}>삭제</Button>
            </div>
          </div>
          {renderByType(asset) ? (
            <div className="mt-3">{renderByType(asset)}</div>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
