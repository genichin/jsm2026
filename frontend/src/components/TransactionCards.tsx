import React, { useState, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { VirtualItem } from "@tanstack/react-virtual";
import { TransactionType, transactionTypeLabels } from "@/lib/transactionTypes";

export interface TransactionCardItem {
  id: string;
  asset_id: string;
  asset_name?: string;
  type: TransactionType;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  realized_profit?: number | null;
  transaction_date: string; // ISO
  category_name?: string | null;
  description?: string | null;
  memo?: string | null;
  is_confirmed: boolean;
  external_id?: string | null;
  related_transaction_id?: string | null;
}

interface Props {
  items: TransactionCardItem[];
  onEdit: (txId: string) => void;
  virtualizeThreshold?: number; // item 수가 임계값을 넘으면 가상 스크롤 적용
}

const typeColor: Record<string, string> = {
  buy: "bg-emerald-100 text-emerald-700",
  sell: "bg-rose-100 text-rose-700",
  deposit: "bg-blue-100 text-blue-700",
  withdraw: "bg-orange-100 text-orange-700",
  dividend: "bg-yellow-100 text-yellow-800",
  interest: "bg-purple-100 text-purple-700",
  fee: "bg-slate-100 text-slate-600",
  transfer_in: "bg-indigo-100 text-indigo-700",
  transfer_out: "bg-indigo-50 text-indigo-600",
  adjustment: "bg-slate-100 text-slate-600",
  invest: "bg-teal-100 text-teal-700",
  redeem: "bg-teal-50 text-teal-600",
  internal_transfer: "bg-cyan-100 text-cyan-700",
  card_payment: "bg-pink-100 text-pink-700",
  promotion_deposit: "bg-lime-100 text-lime-700",
  auto_transfer: "bg-fuchsia-100 text-fuchsia-700",
  remittance: "bg-amber-100 text-amber-700",
  exchange: "bg-sky-100 text-sky-700",
};

function formatNumber(v: number | null | undefined, opts: Intl.NumberFormatOptions = {}): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 6, ...opts }).format(v);
}

function money(qty: number, price: number): number {
  return qty * price;
}

export const TransactionCards: React.FC<Props> = ({ items, onEdit, virtualizeThreshold = 300 }) => {
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setExpandedMap(m => ({ ...m, [id]: !m[id] }));

  const shouldVirtualize = items.length >= virtualizeThreshold;
  const parentRef = useRef<HTMLDivElement | null>(null);

  const virtualizer = useVirtualizer({
    count: shouldVirtualize ? items.length : 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 150, // 기본 추정 높이(확장 전)
    overscan: 8,
    enabled: shouldVirtualize,
  });

  const virtualItems = virtualizer.getVirtualItems();

  if (!items.length) return <div className="text-sm text-slate-500">표시할 거래가 없습니다.</div>;

  if (shouldVirtualize) {
    return (
      <div ref={parentRef} className="relative w-full h-[70vh] overflow-auto rounded border p-2 bg-slate-50">
        <div
          className="relative w-full"
          style={{ height: virtualizer.getTotalSize() }}
        >
          {virtualItems.map((vItem: VirtualItem) => {
            const tx = items[vItem.index];
            const amount = money(Math.abs(tx.quantity), tx.price);
            const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));
            const profit = tx.realized_profit;
            const expanded = !!expandedMap[tx.id];
            const panelId = `tx-panel-${tx.id}`;
            const btnId = `tx-toggle-${tx.id}`;
            return (
              <div
                key={tx.id}
                data-index={vItem.index}
                ref={virtualizer.measureElement}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${vItem.start}px)`
                }}
              >
                <div className="border rounded p-3 bg-white shadow-sm flex flex-col gap-2" role="article" aria-labelledby={btnId}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs font-mono text-slate-500">{tx.transaction_date.slice(0,10)}</span>
                      <span className={`text-[10px] px-2 py-1 rounded font-medium shrink-0 ${typeColor[tx.type] || "bg-slate-100 text-slate-600"}`}>{transactionTypeLabels[tx.type] || tx.type}</span>
                      <span className="text-[10px] px-2 py-1 rounded bg-slate-100 text-slate-600 truncate max-w-[120px]" title={tx.category_name ?? undefined}>{tx.category_name || "미분류"}</span>
                      {!tx.is_confirmed && <span className="text-[10px] px-2 py-1 rounded bg-slate-200 text-slate-700">임시</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        id={btnId}
                        onClick={() => toggle(tx.id)}
                        className="text-xs px-2 py-1 rounded bg-slate-50 hover:bg-slate-100 focus:outline-none focus:ring focus:ring-slate-300"
                        aria-expanded={expanded}
                        aria-controls={panelId}
                      >{expanded ? "접기" : "상세"}</button>
                      <button
                        onClick={() => onEdit(tx.id)}
                        className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 focus:outline-none focus:ring focus:ring-slate-300"
                      >편집</button>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1 text-sm">
                    <div className="flex items-center justify-between">
                      <div className="font-medium truncate" title={tx.asset_name || tx.asset_id}>{tx.asset_name || tx.asset_id}</div>
                      <div className="font-mono text-right">
                        {(tx.type === "auto_transfer" || tx.type === "card_payment" || tx.type === "transfer_in" || tx.type === "deposit" || tx.type === "transfer_out") ? (
                          <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}</span>
                        ) : (
                          <>
                            <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}</span>
                            <span className="text-slate-400 ml-1">@ {formatNumber(tx.price)}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      {tx.type !== "auto_transfer" && tx.type !== "card_payment" && tx.type !== "transfer_in" && tx.type !== "deposit" && tx.type !== "transfer_out" && (
                        <div className="font-mono text-slate-700">{formatNumber(amount)}</div>
                      )}
                    </div>
                    {profit !== null && profit !== undefined && profit !== 0 && (
                      <div className={`text-xs font-mono ${profit > 0 ? "text-emerald-600" : "text-rose-600"}`}>실현손익 {formatNumber(profit)}</div>
                    )}
                    {(tx.fee !== 0 || tx.tax !== 0) && (
                      <div className="text-xs text-slate-500">
                        {tx.fee !== 0 && <span>수수료 {formatNumber(tx.fee)}</span>}
                        {tx.fee !== 0 && tx.tax !== 0 && <span> / </span>}
                        {tx.tax !== 0 && <span>세금 {formatNumber(tx.tax)}</span>}
                      </div>
                    )}
                    {tx.description && <div className="text-xs text-slate-600 truncate" title={tx.description ?? undefined}>{tx.description}</div>}
                    {tx.memo && <div className="text-[11px] text-slate-400 truncate" title={tx.memo ?? undefined}>{tx.memo}</div>}
                  </div>
                  <div
                    id={panelId}
                    role="region"
                    aria-label="거래 상세"
                    className={`transition-all duration-200 ease-in-out overflow-hidden ${expanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"}`}
                  >
                    {expanded && (
                      <div className="border-t pt-2 text-[11px] space-y-1 text-slate-600">
                        <div className="flex justify-between"><span className="text-slate-500">원시 수량(부호):</span><span className="font-mono">{tx.quantity}</span></div>
                        {tx.external_id && <div className="flex justify-between"><span className="text-slate-500">외부 ID:</span><span className="font-mono truncate" title={tx.external_id}>{tx.external_id}</span></div>}
                        {tx.related_transaction_id && <div className="flex justify-between"><span className="text-slate-500">연관 거래:</span><span className="font-mono truncate" title={tx.related_transaction_id}>{tx.related_transaction_id}</span></div>}
                        {tx.description && <div><span className="text-slate-500 block">설명 전체:</span><div className="mt-0.5 break-words text-slate-700">{tx.description}</div></div>}
                        {tx.memo && <div><span className="text-slate-500 block">메모 전체:</span><div className="mt-0.5 break-words text-slate-500">{tx.memo}</div></div>}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // 기존 그리드(소량 데이터) 경로
  return (
    <div className="flex flex-col gap-3">
      {items.map(tx => {
        const amount = money(Math.abs(tx.quantity), tx.price);
        const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));
        const profit = tx.realized_profit;
        const expanded = !!expandedMap[tx.id];
        const panelId = `tx-panel-${tx.id}`;
        const btnId = `tx-toggle-${tx.id}`;
        return (
          <div key={tx.id} className="border rounded p-3 bg-white shadow-sm flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-mono text-slate-500">{tx.transaction_date.slice(0,10)}</span>
                <span className={`text-[10px] px-2 py-1 rounded font-medium shrink-0 ${typeColor[tx.type] || "bg-slate-100 text-slate-600"}`}>{transactionTypeLabels[tx.type] || tx.type}</span>
                <span className="text-[10px] px-2 py-1 rounded bg-slate-100 text-slate-600 truncate max-w-[120px]" title={tx.category_name ?? undefined}>{tx.category_name || "미분류"}</span>
                {!tx.is_confirmed && <span className="text-[10px] px-2 py-1 rounded bg-slate-200 text-slate-700">임시</span>}
              </div>
              <div className="flex items-center gap-2">
                <button
                  id={btnId}
                  onClick={() => toggle(tx.id)}
                  className="text-xs px-2 py-1 rounded bg-slate-50 hover:bg-slate-100 focus:outline-none focus:ring focus:ring-slate-300"
                  aria-expanded={expanded}
                  aria-controls={panelId}
                >{expanded ? "접기" : "상세"}</button>
                <button
                  onClick={() => onEdit(tx.id)}
                  className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 focus:outline-none focus:ring focus:ring-slate-300"
                >편집</button>
              </div>
            </div>
            <div className="flex flex-col gap-1 text-sm">
              <div className="flex items-center justify-between">
                <div className="font-medium truncate" title={tx.asset_name || tx.asset_id}>{tx.asset_name || tx.asset_id}</div>
                <div className="font-mono text-right">
                  {(tx.type === "auto_transfer" || tx.type === "card_payment" || tx.type === "transfer_in" || tx.type === "deposit" || tx.type === "transfer_out") ? (
                    <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}</span>
                  ) : (
                    <>
                      <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}</span>
                      <span className="text-slate-400 ml-1">@ {formatNumber(tx.price)}</span>
                    </>
                  )}
                </div>
              </div>
              {tx.type !== "auto_transfer" && tx.type !== "card_payment" && tx.type !== "transfer_in" && tx.type !== "deposit" && tx.type !== "transfer_out" && (
                <div className="flex items-center justify-between text-xs">               
                  <div className="font-mono text-slate-700">{formatNumber(amount)}</div>
                </div>
              )}
              {profit !== null && profit !== undefined && profit !== 0 && (
                <div className={`text-xs font-mono ${profit > 0 ? "text-emerald-600" : "text-rose-600"}`}>실현손익 {formatNumber(profit)}</div>
              )}
              {(tx.fee !== 0 || tx.tax !== 0) && (
                <div className="text-xs text-slate-500">
                  {tx.fee !== 0 && <span>수수료 {formatNumber(tx.fee)}</span>}
                  {tx.fee !== 0 && tx.tax !== 0 && <span> / </span>}
                  {tx.tax !== 0 && <span>세금 {formatNumber(tx.tax)}</span>}
                </div>
              )}
              {tx.description && <div className="text-xs text-slate-600 truncate" title={tx.description ?? undefined}>{tx.description}</div>}
              {tx.memo && <div className="text-[11px] text-slate-400 truncate" title={tx.memo ?? undefined}>{tx.memo}</div>}
            </div>
            <div
              id={panelId}
              role="region"
              aria-label="거래 상세"
              className={`transition-all duration-200 ease-in-out overflow-hidden ${expanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"}`}
            >
              {expanded && (
                <div className="border-t pt-2 text-[11px] space-y-1 text-slate-600">
                  <div className="flex justify-between"><span className="text-slate-500">원시 수량(부호):</span><span className="font-mono">{tx.quantity}</span></div>
                  {tx.external_id && <div className="flex justify-between"><span className="text-slate-500">외부 ID:</span><span className="font-mono truncate" title={tx.external_id}>{tx.external_id}</span></div>}
                  {tx.related_transaction_id && <div className="flex justify-between"><span className="text-slate-500">연관 거래:</span><span className="font-mono truncate" title={tx.related_transaction_id}>{tx.related_transaction_id}</span></div>}
                  {tx.description && <div><span className="text-slate-500 block">설명 전체:</span><div className="mt-0.5 break-words text-slate-700">{tx.description}</div></div>}
                  {tx.memo && <div><span className="text-slate-500 block">메모 전체:</span><div className="mt-0.5 break-words text-slate-500">{tx.memo}</div></div>}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TransactionCards;
