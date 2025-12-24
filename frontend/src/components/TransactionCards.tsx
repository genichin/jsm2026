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
  price?: number | null;
  fee?: number | null;
  tax?: number | null;
  transaction_date: string; // ISO
  category_name?: string | null;
  description?: string | null;
  memo?: string | null;
  related_transaction_id?: string | null;
  related_asset_name?: string | null; // 연결된 거래의 자산명 (out_asset/in_asset용)
  extras?: Record<string, any> | null;
  realized_profit?: number | null;
  flow_type?: string;
  confirmed?: boolean;
  external_id?: string | null;
  // 현금배당용 추가 필드
  dividend_asset_name?: string | null;
  currency?: string;
}

interface Props {
  items: TransactionCardItem[];
  onEdit: (txId: string) => void;
  onDelete?: (txId: string) => void;
  virtualizeThreshold?: number; // item 수가 임계값을 넘으면 가상 스크롤 적용
}

// 거래 유형별 색상 매핑 (타입 안전성 보장)
const typeColor: Partial<Record<TransactionType, string>> = {
  buy: "bg-emerald-100 text-emerald-700",
  sell: "bg-rose-100 text-rose-700",
  deposit: "bg-blue-100 text-blue-700",
  withdraw: "bg-orange-100 text-orange-700",
  cash_dividend: "bg-yellow-100 text-yellow-800",
  stock_dividend: "bg-amber-100 text-amber-700",
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
  payment_cancel: "bg-green-100 text-green-700",
};

const DEFAULT_TYPE_COLOR = "bg-slate-100 text-slate-600";

function formatNumber(v: number | null | undefined, opts: Intl.NumberFormatOptions = {}): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "-";
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 6, ...opts }).format(v);
}

function formatDate(isoDate: string): string {
  // ISO 형식에서 날짜 부분만 추출 (YYYY-MM-DD)
  return isoDate.slice(0, 10);
}

function getCurrencySymbol(currency?: string): string {
  if (!currency) return "원";
  
  const currencyMap: Record<string, string> = {
    "KRW": "원",
    "USD": "$",
    "EUR": "€",
    "JPY": "¥",
    "CNY": "¥",
    "GBP": "£"
  };
  
  return currencyMap[currency.toUpperCase()] || currency;
}

function money(qty: number, price: number): number {
  return qty * price;
}

// 현금성 거래 타입 (가격/금액 개념이 없고 수량만 표시)
const CASH_TRANSACTION_TYPES: readonly TransactionType[] = [
  "auto_transfer",
  "card_payment", 
  "transfer_in",
  "transfer_out",
  "deposit",
  "exchange"
] as const;

function isCashTransaction(type: TransactionType): boolean {
  return CASH_TRANSACTION_TYPES.includes(type);
}

// 카테고리를 표시하지 않는 거래 타입
const NO_CATEGORY_TYPES: readonly TransactionType[] = ["exchange","cash_dividend","out_asset","in_asset","buy"] as const;

function shouldShowCategory(type: TransactionType): boolean {
  return !NO_CATEGORY_TYPES.includes(type);
}

// UI 상수
const CARD_ESTIMATED_HEIGHT = 150; // 가상 스크롤 카드 높이 추정값 (px)
const CATEGORY_BADGE_MAX_WIDTH = "max-w-[120px]"; // 카테고리 배지 최대 너비

interface TransactionCardProps {
  tx: TransactionCardItem;
  expanded: boolean;
  onToggle: () => void;
  onEdit: (txId: string) => void;
  onDelete?: (txId: string) => void;
}

// 거래 유형별 렌더러
interface TransactionRenderer {
  renderDescription?: (tx: TransactionCardItem) => React.ReactNode;
  renderQuantityPrice: (tx: TransactionCardItem) => React.ReactNode;
  renderAmount?: (tx: TransactionCardItem) => React.ReactNode;
  renderFeesTaxes: (tx: TransactionCardItem) => React.ReactNode;
  renderExtraInfo?: (tx: TransactionCardItem) => React.ReactNode;
  renderExpandedExtraInfo?: (tx: TransactionCardItem) => React.ReactNode;
}

// 기본 렌더러 (매수/매도 등)
const defaultRenderer: TransactionRenderer = {
  renderQuantityPrice: (tx) => {
    const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));
    const price = tx.price;
    return (
      <>
        <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}</span>
        <span className="text-slate-400 ml-1">@ {formatNumber(price)}</span>
      </>
    );
  },
  renderAmount: (tx) => {
    const price = tx.price;
    const amount = typeof price === 'number' ? Math.abs(tx.quantity) * price : 0;
    return <div className="font-mono text-slate-700">{formatNumber(amount)}</div>;
  },
  renderFeesTaxes: (tx) => {
    const hasFees = (tx.fee != null && tx.fee !== 0) || (tx.tax != null && tx.tax !== 0);
    if (!hasFees) return null;
    
    return (
      <div className="text-xs text-slate-500">
        {(tx.fee != null && tx.fee !== 0) && <span>수수료 {formatNumber(tx.fee)}</span>}
        {(tx.fee != null && tx.fee !== 0) && (tx.tax != null && tx.tax !== 0) && <span> / </span>}
        {(tx.tax != null && tx.tax !== 0) && <span>세금 {formatNumber(tx.tax)}</span>}
      </div>
    );
  }
};

// 현금성 거래 렌더러
const cashRenderer: TransactionRenderer = {
  renderDescription: (tx) => {
    return (
      <>
      {tx.description}
      </>
    );
  },  
  renderQuantityPrice: (tx) => {
    const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));
    const currencySymbol = getCurrencySymbol(tx.currency);
    return <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}{currencySymbol}</span>;
  },
  renderFeesTaxes: () => null, // 현금성 거래는 수수료/세금 표시 안함
};

// 현금배당 렌더러
const cashDividendRenderer: TransactionRenderer = {
  renderDescription: (tx) => {
    return (
      <>
      {tx.dividend_asset_name}
      </>
    );
  },  
  renderQuantityPrice: (tx) => {
    const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));    
    const currencySymbol = getCurrencySymbol(tx.currency);
    return (
      <>
        <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}{currencySymbol}</span>        
      </>
    );
  },
  renderFeesTaxes: (tx) => {
    return (
      <>
      </>
    );
  },
  renderExtraInfo: (tx) => {
    return (
      <>
      </>
    );
  },
  renderExpandedExtraInfo: (tx) => {
    const hasValidExtras = tx.extras && typeof tx.extras === 'object';
    const extrasPrice = hasValidExtras ? tx.price : undefined;
    const extrasFee = hasValidExtras ? tx.fee : undefined;
    const extrasTax = hasValidExtras ? tx.tax : undefined;
    if (!tx.dividend_asset_name) return null;
    return (
      <>
        <div className="text-xs text-slate-500">
          {extrasPrice && <span>배당금 {formatNumber(extrasPrice)}</span>}
          {extrasPrice && <span> / </span>}
          {Number(extrasFee) > 0 && <span>수수료 {formatNumber(Number(extrasFee))}</span>}
          {Number(extrasFee) > 0 && Number(extrasTax) > 0 && <span> / </span>}
          {Number(extrasTax) > 0 && <span>세금 {formatNumber(Number(extrasTax))}</span>}
        </div>
        <div className="text-xs text-blue-600">
          배당자산: {tx.dividend_asset_name}
        </div>
      </>
    );
  }
};

// 자산매수출금(out_asset) / 자산매도입금(in_asset) 렌더러
const assetTransferRenderer: TransactionRenderer = {
  renderDescription: (tx) => {
    // 설명에 연결된 거래의 자산명 표시
    return (
      <>
        {tx.related_asset_name ? (
          <span className="text-blue-600 font-medium">→ {tx.related_asset_name}</span>
        ) : (
          <span className="text-slate-400 text-xs">(연결 자산 없음)</span>
        )}
        {tx.description && (
          <span className="ml-2 text-slate-600">{tx.description}</span>
        )}
      </>
    );
  },  
  renderQuantityPrice: (tx) => {
    const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));    
    const currencySymbol = getCurrencySymbol(tx.currency);
    return (
      <>
        <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}{currencySymbol}</span>        
      </>
    );
  },
  renderFeesTaxes: () => null, // 현금성 거래는 수수료/세금 표시 안함
};

// 매수(buy) / 매도(sell) 렌더러
const assetTransactionRenderer: TransactionRenderer = {
  renderQuantityPrice: (tx) => {
    const qtyDisplay = (tx.quantity < 0 ? "-" : "") + formatNumber(Math.abs(tx.quantity));
    const price = tx.price;
    return (
      <>
        <span className={tx.quantity < 0 ? "text-rose-600" : "text-emerald-600"}>{qtyDisplay}</span>
        <span className="text-slate-400 ml-1">@ {formatNumber(price)}</span>
      </>
    );
  },
  renderFeesTaxes: (tx) => {
    const hasFees = (tx.fee != null && tx.fee !== 0) || (tx.tax != null && tx.tax !== 0);
    if (!hasFees) return null;
    
    return (
      <div className="text-xs text-slate-500">
        {(tx.fee != null && tx.fee !== 0) && <span>수수료 {formatNumber(tx.fee)}</span>}
        {(tx.fee != null && tx.fee !== 0) && (tx.tax != null && tx.tax !== 0) && <span> / </span>}
        {(tx.tax != null && tx.tax !== 0) && <span>세금 {formatNumber(tx.tax)}</span>}
      </div>
    );
  }
};

// 거래 유형별 렌더러 매핑
const TRANSACTION_RENDERERS: Record<string, TransactionRenderer> = {
  // 현금성 거래
  auto_transfer: cashRenderer,
  card_payment: cashRenderer,
  transfer_in: cashRenderer,
  transfer_out: cashRenderer,
  deposit: cashRenderer,
  exchange: cashRenderer,
  
  // 현금배당
  cash_dividend: cashDividendRenderer,

  // 자산매수출금/매도입금
  out_asset: assetTransferRenderer,
  in_asset: assetTransferRenderer,

  // 매수/매도
  buy: assetTransactionRenderer,
  sell: assetTransactionRenderer,
  
  // 기본 (매수/매도 등)
  default: defaultRenderer,
};

function getTransactionRenderer(type: TransactionType): TransactionRenderer {
  return TRANSACTION_RENDERERS[type] || TRANSACTION_RENDERERS.default;
}

const TransactionCard: React.FC<TransactionCardProps> = ({ tx, expanded, onToggle, onEdit, onDelete }) => {
  const profit = tx.realized_profit;
  const panelId = `tx-panel-${tx.id}`;
  
  // 거래 유형별 렌더러 선택
  const renderer = getTransactionRenderer(tx.type);

  return (
    <div 
      className="border rounded p-3 bg-white shadow-sm flex flex-col gap-2 cursor-pointer hover:bg-slate-50 transition-colors" 
      role="button"
      tabIndex={0}
      onClick={onToggle}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onToggle();
        }
      }}
      aria-expanded={expanded}
      aria-controls={panelId}
      aria-label={`${tx.asset_name || tx.asset_id} 거래 ${expanded ? '접기' : '확장'}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-mono text-slate-500">{formatDate(tx.transaction_date)}</span>
          <span className={`text-xs px-2 py-1 rounded font-medium shrink-0 ${typeColor[tx.type] || DEFAULT_TYPE_COLOR}`}>{transactionTypeLabels[tx.type] || tx.type}</span>
          {shouldShowCategory(tx.type) && (
            <span className={`text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 truncate ${CATEGORY_BADGE_MAX_WIDTH}`} title={tx.category_name ?? undefined}>{tx.category_name || "미분류"}</span>
          )}
          {tx.flow_type === 'undefined' && (
            <span className="text-xs px-2 py-1 rounded bg-amber-100 text-amber-700 font-medium shrink-0">미분류</span>
          )}
          {tx.confirmed === false && (
            <span className="text-xs px-2 py-1 rounded bg-orange-100 text-orange-700 font-medium shrink-0">미확정</span>
          )}
          <span className="text-xs text-slate-500" title={tx.asset_name || tx.asset_id}>{tx.asset_name || tx.asset_id}</span>
        </div>
      </div>
      <div className="flex flex-col gap-1 text-sm">
        <div className="flex items-center justify-between">
          <div className="font-medium truncate">
            {renderer.renderDescription && renderer.renderDescription(tx)}
          </div>
          <div className="font-mono text-right">
            {renderer.renderQuantityPrice(tx)}
          </div>
        </div>
        {renderer.renderAmount && (
          <div className="flex items-center justify-between text-xs">               
            {renderer.renderAmount(tx)}
          </div>
        )}
        {profit !== null && profit !== undefined && profit !== 0 && (
          <div className={`text-xs font-mono ${profit > 0 ? "text-emerald-600" : "text-rose-600"}`}>실현손익 {formatNumber(profit)}</div>
        )}
        {renderer.renderFeesTaxes(tx)}
        {renderer.renderExtraInfo && renderer.renderExtraInfo(tx)}
        {/* {tx.description && <div className="text-xs text-slate-600 truncate" title={tx.description ?? undefined}>{tx.description}</div>} */}
        {/*tx.memo && <div className="text-xs text-slate-400 truncate" title={tx.memo ?? undefined}>{tx.memo}</div>*/}
      </div>
      <div
        id={panelId}
        role="region"
        aria-label="거래 상세"
        className={`transition-all duration-200 ease-in-out overflow-hidden ${expanded ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        {expanded && (
          <div className="border-t pt-2 text-xs space-y-1 text-slate-600 overflow-y-auto max-h-[580px]">
            <div className="flex justify-between"><span className="text-slate-500">원시 수량(부호):</span><span className="font-mono">{tx.quantity}</span></div>
            {tx.external_id && <div className="flex justify-between"><span className="text-slate-500">외부 ID:</span><span className="font-mono truncate" title={tx.external_id}>{tx.external_id}</span></div>}
            {tx.related_transaction_id && <div className="flex justify-between"><span className="text-slate-500">연관 거래:</span><span className="font-mono truncate" title={tx.related_transaction_id}>{tx.related_transaction_id}</span></div>}
            {tx.description && <div><span className="text-slate-500 block">설명 전체:</span><div className="mt-0.5 break-words text-slate-700">{tx.description}</div></div>}
            {tx.memo && <div><span className="text-slate-500 block">메모 전체:</span><div className="mt-0.5 break-words text-slate-500">{tx.memo}</div></div>}
            {renderer.renderExpandedExtraInfo && renderer.renderExpandedExtraInfo(tx)}
            {/* 편집/삭제 버튼 */}
            <div className="flex gap-2 pt-2 border-t">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(tx.id);
                }}
                className="text-xs px-3 py-1 rounded bg-blue-100 text-blue-700 hover:bg-blue-200 focus:outline-none focus:ring focus:ring-blue-300"
              >편집</button>
              {onDelete && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(tx.id);
                  }}
                  className="text-xs px-3 py-1 rounded bg-rose-100 text-rose-700 hover:bg-rose-200 focus:outline-none focus:ring focus:ring-rose-300"
                >삭제</button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const TransactionCards: React.FC<Props> = ({ items, onEdit, onDelete, virtualizeThreshold = 300 }) => {
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setExpandedMap(m => ({ ...m, [id]: !m[id] }));

  const shouldVirtualize = items.length >= virtualizeThreshold;
  const parentRef = useRef<HTMLDivElement | null>(null);

  const virtualizer = useVirtualizer({
    count: shouldVirtualize ? items.length : 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => CARD_ESTIMATED_HEIGHT,
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
            const expanded = !!expandedMap[tx.id];
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
                <TransactionCard
                  tx={tx}
                  expanded={expanded}
                  onToggle={() => toggle(tx.id)}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
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
        const expanded = !!expandedMap[tx.id];
        return (
          <TransactionCard
            key={tx.id}
            tx={tx}
            expanded={expanded}
            onToggle={() => toggle(tx.id)}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        );
      })}
    </div>
  );
};export default TransactionCards;
