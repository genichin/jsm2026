"use client";

import { useRouter } from "next/navigation";
import { transactionTypeLabels, TransactionType } from "@/lib/transactionTypes";

interface Transaction {
  id: string;
  asset_id: string;
  type: string;
  quantity: number;
  transaction_date: string;
  description?: string | null;
  asset?: {
    name: string;
  };
}

interface RecentTransactionsProps {
  transactions: Transaction[];
  isLoading?: boolean;
  viewAllLink?: string;
  maxItems?: number;
  showAssetName?: boolean;
}

export default function RecentTransactions({ 
  transactions, 
  isLoading, 
  viewAllLink,
  maxItems = 10,
  showAssetName = true
}: RecentTransactionsProps) {
  const router = useRouter();

  if (isLoading) {
    return <div className="text-sm text-gray-600">로딩 중...</div>;
  }

  if (transactions.length === 0) {
    return <div className="text-sm text-gray-600">거래 내역이 없습니다.</div>;
  }

  return (
    <div>
      {viewAllLink && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">최근 거래</h3>
          <button
            onClick={() => {
              router.push(viewAllLink as any);
            }}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            전체 보기 →
          </button>
        </div>
      )}
      
      <div className="space-y-2">
        {transactions.slice(0, maxItems).map((tx) => (
          <div 
            key={tx.id} 
            className="flex items-center justify-between p-3 border rounded hover:bg-gray-50 cursor-pointer"
            onClick={() => {
              const url = `/transactions?asset_id=${tx.asset_id}`;
              router.push(url as any);
            }}
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                {showAssetName && (
                  <span className="text-sm font-medium">{tx.asset?.name || tx.asset_id}</span>
                )}
                <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600">
                  {transactionTypeLabels[tx.type as TransactionType] || tx.type}
                </span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {new Date(tx.transaction_date).toLocaleDateString()}
              </div>
            </div>
            <div className="text-right">
              <div className={`font-mono text-sm ${tx.quantity >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {tx.quantity >= 0 ? '+' : ''}{tx.quantity.toLocaleString()}
              </div>
              {tx.description && (
                <div className="text-xs text-gray-500 mt-1 truncate max-w-[150px]">{tx.description}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
