"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

// Types
interface Asset {
  id: string;
  name: string;
  asset_type: string;
  symbol: string | null;
  currency: string;
  account_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface AssetSummary {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  symbol: string | null;
  current_quantity: number;
  total_cost: number;
  realized_profit: number;
  unrealized_profit: number | null;
  current_value: number | null;
}

interface Transaction {
  id: string;
  asset_id: string;
  type: string;
  transaction_date: string;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  description: string | null;
  memo: string | null;
  is_confirmed: boolean;
  category_id: string | null;
  related_transaction_id: string | null;
  realized_profit: number | null;
  asset?: {
    name: string;
    symbol: string | null;
  };
}

interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface Tag {
  id: string;
  name: string;
  color: string | null;
  description: string | null;
}

interface EntityTagsResponse {
  entity_type: string;
  entity_id: string;
  tags: Tag[];
  total: number;
}

export default function AssetDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"transactions" | "tags">("transactions");
  const [txPage, setTxPage] = useState(1);
  const [txSize] = useState(20);

  // 자산 기본 정보
  const assetQuery = useQuery<Asset>({
    queryKey: ["asset", params.id],
    queryFn: async () => (await api.get(`/assets/${params.id}`)).data,
  });

  // 자산 요약 정보
  const summaryQuery = useQuery<AssetSummary>({
    queryKey: ["asset-summary", params.id],
    queryFn: async () => (await api.get(`/assets/${params.id}/summary`)).data,
  });

  // 거래 내역
  const transactionsQuery = useQuery<TransactionListResponse>({
    queryKey: ["asset-transactions", params.id, txPage, txSize],
    queryFn: async () => {
      const { data } = await api.get(`/transactions/assets/${params.id}/transactions`, {
        params: { page: txPage, size: txSize },
      });
      return data;
    },
    enabled: activeTab === "transactions",
  });

  // 태그
  const tagsQuery = useQuery<EntityTagsResponse>({
    queryKey: ["asset-tags", params.id],
    queryFn: async () => (await api.get(`/assets/${params.id}/tags`)).data,
    enabled: activeTab === "tags",
  });

  // 거래 내역 컬럼
  const transactionColumns: ColumnDef<Transaction>[] = useMemo(
    () => [
      {
        accessorKey: "transaction_date",
        header: "날짜",
        cell: ({ row }) => new Date(row.original.transaction_date).toLocaleDateString(),
      },
      {
        accessorKey: "type",
        header: "타입",
        cell: ({ row }) => {
          const typeLabels: Record<string, string> = {
            buy: "매수",
            sell: "매도",
            deposit: "입금",
            withdraw: "출금",
            dividend: "배당",
            interest: "이자",
            fee: "수수료",
            transfer_in: "이체(입)",
            transfer_out: "이체(출)",
            adjustment: "조정",
            invest: "투자",
            redeem: "환매",
            internal_transfer: "내부이체",
            card_payment: "카드결제",
            promotion_deposit: "프로모션입금",
            auto_transfer: "자동이체",
            remittance: "송금",
            exchange: "교환",
          };
          return typeLabels[row.original.type] || row.original.type;
        },
      },
      {
        accessorKey: "quantity",
        header: "수량",
        cell: ({ row }) => row.original.quantity.toFixed(4),
      },
      {
        accessorKey: "price",
        header: "가격",
        cell: ({ row }) => row.original.price?.toLocaleString() || "-",
      },
      {
        accessorKey: "fee",
        header: "수수료",
        cell: ({ row }) => row.original.fee?.toLocaleString() || "-",
      },
      {
        id: "total",
        header: "합계",
        cell: ({ row }) => {
          const { quantity, price, fee, tax } = row.original;
          if (price == null || quantity == null) return "-";
          const total = quantity * price + (fee || 0) + (tax || 0);
          return total.toLocaleString();
        },
      },
      {
        accessorKey: "is_confirmed",
        header: "확정",
        cell: ({ row }) => (row.original.is_confirmed ? "✓" : "-"),
      },
    ],
    []
  );

  if (assetQuery.isLoading) return <div className="p-6">로딩 중...</div>;
  if (assetQuery.isError) return <div className="p-6 text-red-600">자산 정보를 불러오는데 실패했습니다.</div>;

  const asset = assetQuery.data;
  const summary = summaryQuery.data;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 rounded"
            aria-label="뒤로가기"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              {asset?.name}
              {asset?.symbol && <span className="text-gray-500 text-lg">({asset.symbol})</span>}
            </h1>
            <div className="text-sm text-gray-600 flex gap-2 mt-1">
              <span className="px-2 py-0.5 bg-gray-100 rounded">{asset?.asset_type}</span>
              <span>{asset?.currency}</span>
              {!asset?.is_active && <span className="text-red-600">비활성</span>}
            </div>
          </div>
        </div>
        <button
          onClick={() => router.push(`/assets?edit=${params.id}`)}
          className="px-4 py-2 border rounded hover:bg-gray-50"
        >
          편집
        </button>
      </div>

      {/* 요약 카드 */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-4 border rounded-lg bg-gray-50">
          <div>
            <div className="text-xs text-gray-600">현재 잔고</div>
            <div className="text-lg font-semibold">{summary.current_quantity?.toLocaleString() || "0"}</div>
          </div>
          <div>
            <div className="text-xs text-gray-600">총 취득원가</div>
            <div className="text-lg font-semibold">{summary.total_cost?.toLocaleString() || "0"}</div>
          </div>
          <div>
            <div className="text-xs text-gray-600">평단가</div>
            <div className="text-lg font-semibold">
              {summary.current_quantity > 0
                ? (summary.total_cost / summary.current_quantity).toFixed(2)
                : "-"}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600">실현손익</div>
            <div className={`text-lg font-semibold ${(summary.realized_profit || 0) >= 0 ? "text-blue-600" : "text-red-600"}`}>
              {(summary.realized_profit || 0) >= 0 ? "+" : ""}
              {summary.realized_profit?.toLocaleString() || "0"}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600">평가액</div>
            <div className="text-lg font-semibold">
              {summary.current_value != null ? summary.current_value.toLocaleString() : "-"}
            </div>
          </div>
        </div>
      )}

      {/* 탭 */}
      <div className="border-b">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("transactions")}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === "transactions"
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            거래 내역
          </button>
          <button
            onClick={() => setActiveTab("tags")}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === "tags"
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            태그
          </button>
        </div>
      </div>

      {/* 탭 내용 */}
      <div>
        {activeTab === "transactions" && (
          <div className="space-y-4">
            {transactionsQuery.isLoading && <p>거래 내역 로딩 중...</p>}
            {transactionsQuery.isError && <p className="text-red-600">거래 내역을 불러오는데 실패했습니다.</p>}
            {transactionsQuery.isSuccess && (
              <>
                <div className="flex justify-between items-center">
                  <p className="text-sm text-gray-600">총 {transactionsQuery.data.total}건</p>
                  <button
                    onClick={() => router.push(`/transactions?asset_id=${params.id}`)}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    전체 보기 →
                  </button>
                </div>
                <DataTable columns={transactionColumns} data={transactionsQuery.data.items} />
                {transactionsQuery.data.pages > 1 && (
                  <div className="flex justify-center gap-2">
                    <button
                      onClick={() => setTxPage((p) => Math.max(1, p - 1))}
                      disabled={txPage === 1}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      이전
                    </button>
                    <span className="px-3 py-1">
                      {txPage} / {transactionsQuery.data.pages}
                    </span>
                    <button
                      onClick={() => setTxPage((p) => Math.min(transactionsQuery.data.pages, p + 1))}
                      disabled={txPage === transactionsQuery.data.pages}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      다음
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === "tags" && (
          <div className="space-y-4">
            {tagsQuery.isLoading && <p>태그 로딩 중...</p>}
            {tagsQuery.isError && <p className="text-red-600">태그를 불러오는데 실패했습니다.</p>}
            {tagsQuery.isSuccess && (
              <>
                <p className="text-sm text-gray-600">총 {tagsQuery.data.total}개의 태그</p>
                {tagsQuery.data.tags.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">연결된 태그가 없습니다.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {tagsQuery.data.tags.map((tag) => (
                      <div
                        key={tag.id}
                        className="flex items-center gap-2 px-3 py-1.5 border rounded-full"
                        style={{ borderColor: tag.color || undefined }}
                      >
                        {tag.color && (
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: tag.color }}
                          />
                        )}
                        <span className="text-sm font-medium">{tag.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
