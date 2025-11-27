import React, { useState, useMemo, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { TransactionType, transactionTypeOptions } from "@/lib/transactionTypes";
import { AssetBrief, CategoryBrief } from "./types";

export type FormFieldProps = {
  value?: any;
  defaultValue?: any;
  onChange?: (e: React.ChangeEvent<any>) => void;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  name?: string;
};

// 자산 선택 필드 (검색 가능)
export function AssetField({
  value,
  onChange,
  required,
  disabled,
  assets,
}: FormFieldProps & { assets: AssetBrief[] }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  const inputRef = useRef<HTMLDivElement>(null);

  const filteredAssets = useMemo(() => {
    if (!searchTerm) return assets;
    const term = searchTerm.toLowerCase();
    return assets.filter((a) =>
      a.name.toLowerCase().includes(term) ||
      a.symbol?.toLowerCase().includes(term) ||
      a.asset_type.toLowerCase().includes(term)
    );
  }, [assets, searchTerm]);

  const selectedAsset = assets.find((a) => a.id === value);

  // 드롭다운 위치 계산
  useEffect(() => {
    if (isOpen && inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + window.scrollY,
        left: rect.left + window.scrollX,
        width: rect.width,
      });
    }
  }, [isOpen]);

  const handleSelect = (assetId: string) => {
    if (onChange) {
      onChange({ target: { name: "asset_id", value: assetId } } as any);
    }
    setIsOpen(false);
    setSearchTerm("");
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        자산 {required && '*'}
      </label>
      
      {/* 선택된 자산 표시 또는 검색 입력 */}
      <div className="relative" ref={inputRef}>
        <input
          type="text"
          value={isOpen ? searchTerm : (selectedAsset?.name || "")}
          onChange={(e) => setSearchTerm(e.target.value)}
          onFocus={() => setIsOpen(true)}
          placeholder="자산을 검색하세요"
          disabled={disabled}
          required={required && !value}
          className="w-full border rounded px-3 py-2 pr-8"
        />
        <input type="hidden" name="asset_id" value={value || ""} required={required} />
        
        {/* 드롭다운 토글 아이콘 */}
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Portal로 드롭다운 렌더링 */}
      {typeof window !== 'undefined' && isOpen && !disabled && createPortal(
        <>
          {/* 백드롭 */}
          <div 
            className="fixed inset-0 z-[100]" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* 옵션 목록 */}
          <div 
            className="fixed bg-white border rounded-lg shadow-xl max-h-96 overflow-y-auto z-[101]"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`,
              width: `${dropdownPosition.width}px`,
            }}
          >
            {filteredAssets.length === 0 ? (
              <div className="px-3 py-2 text-sm text-slate-500">
                검색 결과가 없습니다
              </div>
            ) : (
              filteredAssets.map((asset) => (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => handleSelect(asset.id)}
                  className={`w-full text-left px-3 py-2 hover:bg-slate-50 border-b last:border-b-0 ${
                    asset.id === value ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="font-medium text-sm">{asset.name}</div>
                  <div className="text-xs text-slate-500">
                    {asset.symbol && `${asset.symbol} · `}
                    {asset.asset_type} · {asset.currency}
                  </div>
                </button>
              ))
            )}
          </div>
        </>,
        document.body
      )}
    </div>
  );
}

// 거래 유형 선택 필드
export function TypeField({
  value,
  onChange,
  required,
  disabled,
}: FormFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        유형 {required && '*'}
      </label>
      <select
        name="type"
        value={value}
        onChange={onChange}
        disabled={disabled}
        required={required}
        className="w-full border rounded px-3 py-2"
      >
        {transactionTypeOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// 수량 입력 필드
export function QuantityField({
  value,
  defaultValue,
  onChange,
  required,
  showNegativeHint,
  label = "수량",
}: FormFieldProps & { showNegativeHint?: boolean; label?: string }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {label} {required && '*'}
        {showNegativeHint && (
          <span className="text-xs text-amber-600 ml-1">
            (양수 입력, 자동으로 차감 처리됩니다)
          </span>
        )}
      </label>
      <input
        type="number"
        step="any"
        name="quantity"
        value={value}
        defaultValue={defaultValue}
        onChange={onChange}
        required={required}
        min="0"
        className="w-full border rounded px-3 py-2"
        placeholder={showNegativeHint ? "양수 입력 (예: 1.036021)" : ""}
      />
    </div>
  );
}

// 가격 입력 필드 (extras.price)
export function PriceField({
  value,
  defaultValue,
  onChange,
  required,
}: FormFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        가격 {required && '*'}
      </label>
      <input
        type="number"
        step="any"
        name="price"
        value={value}
        defaultValue={defaultValue ?? 0}
        onChange={onChange}
        required={required}
        className="w-full border rounded px-3 py-2"
      />
    </div>
  );
}

// 수수료 입력 필드 (extras.fee)
export function FeeField({
  defaultValue,
  onChange,
}: FormFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        수수료
      </label>
      <input
        type="number"
        step="any"
        name="fee"
        defaultValue={defaultValue ?? 0}
        onChange={onChange}
        className="w-full border rounded px-3 py-2"
      />
    </div>
  );
}

// 세금 입력 필드 (extras.tax)
export function TaxField({
  defaultValue,
  onChange,
}: FormFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        세금
      </label>
      <input
        type="number"
        step="any"
        name="tax"
        defaultValue={defaultValue ?? 0}
        onChange={onChange}
        className="w-full border rounded px-3 py-2"
      />
    </div>
  );
}

// 거래일시 입력 필드
export function DateField({
  defaultValue,
  required,
}: FormFieldProps) {
  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        거래일시 {required && '*'}
      </label>
      <input
        type="datetime-local"
        name="transaction_date"
        defaultValue={defaultValue || new Date().toISOString().slice(0, 19)}
        className="w-full border rounded px-3 py-2"
        step="1"
        required={required}
      />
    </div>
  );
}

// 카테고리 선택 필드
export function CategoryField({
  defaultValue,
  categories,
  suggestedCategoryId,
  onSuggestClick,
  isSuggesting,
}: FormFieldProps & {
  categories: CategoryBrief[];
  suggestedCategoryId?: string | null;
  onSuggestClick?: () => void;
  isSuggesting?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        카테고리
        {suggestedCategoryId && (
          <span className="ml-2 text-xs text-emerald-600">✓ 자동 추천됨</span>
        )}
      </label>
      <select
        name="category_id"
        defaultValue={defaultValue || ""}
        className="w-full border rounded px-3 py-2"
      >
        <option value="">없음</option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {"\u00A0".repeat((c.depth || 0) * 2)}
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}

// 설명 입력 필드
export function DescriptionField({
  defaultValue,
  onChange,
  onSuggestClick,
  isSuggesting,
  showSuggestButton,
}: FormFieldProps & {
  onSuggestClick?: () => void;
  isSuggesting?: boolean;
  showSuggestButton?: boolean;
}) {
  return (
    <div className="flex items-end gap-2 flex-1">
      <div className="flex-1">
        <label className="block text-sm font-medium text-slate-700 mb-1">
          설명
        </label>
        <input
          name="description"
          defaultValue={defaultValue || ""}
          onChange={onChange}
          className="w-full border rounded px-3 py-2"
        />
      </div>
      {showSuggestButton && onSuggestClick && (
        <button
          type="button"
          onClick={onSuggestClick}
          disabled={isSuggesting}
          className="px-3 py-2 rounded bg-blue-100 text-blue-700 text-sm whitespace-nowrap hover:bg-blue-200 disabled:opacity-50"
        >
          {isSuggesting ? "추천 중..." : "자동 추천"}
        </button>
      )}
    </div>
  );
}

// 메모 입력 필드
export function MemoField({
  defaultValue,
  onChange,
}: FormFieldProps) {
  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        메모
      </label>
      <input
        name="memo"
        defaultValue={defaultValue || ""}
        onChange={onChange}
        className="w-full border rounded px-3 py-2"
      />
    </div>
  );
}

// 현금 자산 선택 필드 (매수/매도/배당용)
export function CashAssetField({
  assets,
  transactionType,
  defaultValue,
}: FormFieldProps & {
  assets: AssetBrief[];
  transactionType: TransactionType;
}) {
  const isDividend = transactionType === 'dividend';
  
  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {isDividend ? '배당금 입금 계좌 (현금)' : '현금 자산'}
        {!isDividend && assets.length === 0 && ' (선택사항)'}
      </label>
      <select
        name="cash_asset_id"
        defaultValue={defaultValue || ""}
        className="w-full border rounded px-3 py-2"
      >
        <option value="">
          {isDividend ? '없음 (가격이 0인 경우)' : '자동 선택'}
        </option>
        {assets.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      {assets.length === 0 && (
        <p className="text-xs text-amber-600 mt-1">
          {isDividend
            ? '동일 계좌·통화의 현금 자산이 없습니다. 가격 > 0이면 자동으로 생성됩니다.'
            : '동일 계좌·통화의 현금 자산이 없습니다. 자동으로 생성됩니다.'}
        </p>
      )}
    </div>
  );
}

// 환전 대상 자산 선택 필드
export function TargetAssetField({
  assets,
  required,
}: FormFieldProps & {
  assets: AssetBrief[];
}) {
  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        환전 대상 자산 (현금) {required && '*'}
      </label>
      <select
        name="target_asset_id"
        defaultValue=""
        className="w-full border rounded px-3 py-2"
        required={required}
      >
        <option value="">선택하세요</option>
        {assets.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
    </div>
  );
}

// 환전 금액 입력 필드들
export function ExchangeAmountFields({
  sourceAmount,
  targetAmount,
  onSourceChange,
  onTargetChange,
  exchangeRate,
  sourceCurrency,
}: {
  sourceAmount: number;
  targetAmount: number;
  onSourceChange: (val: number) => void;
  onTargetChange: (val: number) => void;
  exchangeRate: number | null;
  sourceCurrency: string;
}) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          환전 출발 금액 *
        </label>
        <input
          type="number"
          step="any"
          name="quantity"
          value={sourceAmount || ""}
          onChange={(e) => onSourceChange(parseFloat(e.target.value) || 0)}
          className="w-full border rounded px-3 py-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          환전 대상 금액 *
        </label>
        <input
          type="number"
          step="any"
          name="target_amount"
          value={targetAmount || ""}
          onChange={(e) => onTargetChange(parseFloat(e.target.value) || 0)}
          className="w-full border rounded px-3 py-2"
          required
        />
      </div>
      {exchangeRate !== null && exchangeRate > 0 && (
        <>
          <input type="hidden" name="exchange_rate" value={exchangeRate} />
          <div className="col-span-2">
            <div className="bg-blue-50 border border-blue-200 rounded px-4 py-3">
              <p className="text-sm font-medium text-blue-900">
                환율: {exchangeRate.toFixed(2)} KRW
              </p>
              <p className="text-xs text-blue-700 mt-1">
                {sourceCurrency === "KRW"
                  ? `${sourceAmount.toLocaleString()} KRW → ${targetAmount.toLocaleString()}`
                  : `${sourceAmount.toLocaleString()} → ${targetAmount.toLocaleString()} KRW`}
              </p>
            </div>
          </div>
        </>
      )}
    </>
  );
}
