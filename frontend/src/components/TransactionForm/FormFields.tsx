"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { TransactionType, transactionTypeOptions } from "@/lib/transactionTypes";
import { AssetBrief, CategoryBrief } from "./types";
import { api } from "@/lib/api";

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
  value,
  defaultValue,
  onChange,
  required,
}: FormFieldProps) {
  // 로컬 시간으로 기본값 생성
  const getLocalDateTimeString = () => {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const year = now.getFullYear();
    const month = pad(now.getMonth() + 1);
    const day = pad(now.getDate());
    const hour = pad(now.getHours());
    const minute = pad(now.getMinutes());
    const second = pad(now.getSeconds());
    return `${year}-${month}-${day}T${hour}:${minute}:${second}`;
  };

  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        거래일시 {required && '*'}
      </label>
      <input
        type="datetime-local"
        name="transaction_date"
        className="w-full border rounded px-3 py-2"
        step="1"
        required={required}
        {...(value !== undefined
          ? { value, onChange }
          : { defaultValue: defaultValue || getLocalDateTimeString(), onChange })}
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

// 현금 자산 선택 필드 (매수/매도용)
export function CashAssetField({
  assets,
  transactionType,
  defaultValue,
}: FormFieldProps & {
  assets: AssetBrief[];
  transactionType: TransactionType;
}) {
  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        현금 자산
        {assets.length === 0 && ' (선택사항)'}
      </label>
      <select
        name="cash_asset_id"
        defaultValue={defaultValue || ""}
        className="w-full border rounded px-3 py-2"
      >
        <option value="">자동 선택</option>
        {assets.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      {assets.length === 0 && (
        <p className="text-xs text-amber-600 mt-1">
          동일 계좌·통화의 현금 자산이 없습니다. 자동으로 생성됩니다.
        </p>
      )}
    </div>
  );
}

// 배당 자산 선택 필드 (cash_dividend 전용)
export function DividendAssetField({
  assets,
  defaultValue,
}: FormFieldProps & { assets: AssetBrief[] }) {
  return (
    <div className="col-span-2">
      <label className="block text-sm font-medium text-slate-700 mb-1">
        배당 자산
      </label>
      <select
        name="dividend_asset_id"
        defaultValue={defaultValue || ""}
        className="w-full border rounded px-3 py-2"
        required
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

// 연결 거래 선택 필드 (검색 가능)
export function RelatedTransactionField({
  value,
  onChange,
  required,
  disabled,
  transactionDate,
  selectedAsset,
  assets,
  onCreateNew,
  currentQuantity,
  transactionType,
}: FormFieldProps & {
  transactionDate?: string;
  selectedAsset?: AssetBrief;
  assets: AssetBrief[];
  onCreateNew?: () => void;
  currentQuantity?: number;
  transactionType?: TransactionType;
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  const [transactions, setTransactions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLDivElement>(null);

  // 거래 조회 (결제취소는 동일 자산만, 다른 타입은 계좌 전체)
  useEffect(() => {
    if (!selectedAsset || !transactionDate) {
      return;
    }

    const fetchTransactions = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ size: '100' });
        
        // 결제취소는 동일 자산의 거래만 조회
        if (transactionType === 'payment_cancel') {
          params.append('asset_id', selectedAsset.id);
        } else {
          // 다른 타입은 계좌 전체 조회
          params.append('account_id', selectedAsset.account_id || '');
        }
        
        const response = await api.get(`/transactions?${params.toString()}`);
        const items = response.data.items || [];
        
        // 결제취소 거래는 필터링 (결제취소끼리는 연결 불가)
        const filtered = items.filter((t: any) => t.type !== 'payment_cancel');
        setTransactions(filtered);
      } catch (error) {
        console.error('Failed to fetch transactions:', error);
        setTransactions([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTransactions();
  }, [selectedAsset, transactionDate, transactionType]);

  const filteredTransactions = useMemo(() => {
    let filtered = transactions;
    
    // 결제취소는 금액이 일치하는 거래만 (절댓값 같고 부호 반대)
    if (transactionType === 'payment_cancel' && currentQuantity !== undefined) {
      filtered = filtered.filter((t) => 
        Math.abs(t.quantity) === Math.abs(currentQuantity) &&
        Math.sign(t.quantity) !== Math.sign(currentQuantity)
      );
    }
    
    // 검색어 필터링
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((t) =>
        t.description?.toLowerCase().includes(term) ||
        t.memo?.toLowerCase().includes(term) ||
        t.type?.toLowerCase().includes(term)
      );
    }
    
    return filtered;
  }, [transactions, searchTerm, transactionType, currentQuantity]);

  const selectedTransaction = transactions.find((t) => t.id === value);

  // 드롭다운 열기 및 위치 계산
  const handleToggleOpen = () => {
    if (disabled) return;
    
    if (!isOpen && inputRef.current) {
      // fixed 포지션은 viewport 기준이므로 scroll을 더하지 않음
      const rect = inputRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom,
        left: rect.left,
        width: rect.width,
      });
    }
    setIsOpen(!isOpen);
  };

  const handleSelect = (transactionId: string) => {
    if (onChange) {
      onChange({ target: { value: transactionId } } as any);
    }
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleClear = () => {
    if (onChange) {
      onChange({ target: { value: "" } } as any);
    }
    setSearchTerm("");
  };

  const getTransactionAsset = (transaction: any) => {
    return assets.find(a => a.id === transaction.asset_id);
  };

  return (
    <div className="relative">
      {/* Hidden input for form submission */}
      <input type="hidden" name="related_transaction_id" value={value || ""} />
      
      <label className="block text-sm font-medium text-slate-700 mb-1">
        연결 거래 (선택사항)
        {!isLoading && transactions.length > 0 && (
          <span className="ml-2 text-xs text-gray-500">({transactions.length}개)</span>
        )}
      </label>
      
      {/* 선택 버튼 */}
      <div className="relative" ref={inputRef}>
        <button
          type="button"
          onClick={handleToggleOpen}
          disabled={disabled}
          className={`w-full text-left px-3 py-2 border rounded-md shadow-sm ${
            disabled ? "bg-gray-100 cursor-not-allowed" : "bg-white hover:border-blue-500"
          }`}
        >
          {selectedTransaction ? (
            <div className="flex justify-between items-center">
              <div>
                <span className="font-medium text-sm">{selectedTransaction.description || '설명 없음'}</span>
                <span className="text-xs text-gray-500 ml-2">
                  ({selectedTransaction.type}) {selectedTransaction.quantity?.toLocaleString()}
                </span>
              </div>
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="text-gray-400 hover:text-gray-600 ml-2 cursor-pointer"
              >
                ✕
              </span>
            </div>
          ) : (
            <span className="text-gray-400 text-sm">
              {isLoading ? "로딩 중..." : "연결할 거래 선택"}
            </span>
          )}
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
          
          {/* 드롭다운 */}
          <div 
            className="fixed bg-white border rounded-lg shadow-xl max-h-96 overflow-y-auto z-[101]"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`,
              width: `${dropdownPosition.width}px`,
              minWidth: '300px',
            }}
          >
            <div className="sticky top-0 bg-white border-b p-2">
              <input
                type="text"
                className="w-full px-3 py-1.5 border rounded-md text-sm"
                placeholder="거래 검색..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                autoFocus
              />
            </div>
            <div className="py-1">
              {filteredTransactions.length === 0 ? (
                <div className="px-3 py-2 text-sm text-gray-500">
                  {isLoading ? "로딩 중..." : 
                   transactionType === 'payment_cancel' 
                     ? "해당 자산에 연결 가능한 거래가 없습니다"
                     : "거래가 없습니다"}
                </div>
              ) : (
                filteredTransactions.map((transaction) => {
                  const txAsset = getTransactionAsset(transaction);
                  // 결제취소는 원래 거래의 반대 방향이므로 부호가 반대여야 함
                  const isMatchingAmount = currentQuantity && transactionType === 'payment_cancel' &&
                    Math.abs(transaction.quantity) === Math.abs(currentQuantity) &&
                    Math.sign(transaction.quantity) !== Math.sign(currentQuantity);
                  
                  return (
                    <button
                      key={transaction.id}
                      type="button"
                      onClick={() => handleSelect(transaction.id)}
                      className={`w-full text-left px-3 py-2 hover:bg-slate-50 border-b last:border-b-0 ${
                        isMatchingAmount ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="text-sm font-medium">
                            {transaction.description || '설명 없음'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {txAsset?.name} · {transaction.type}
                            {isMatchingAmount && (
                              <span className="ml-2 text-blue-600 font-semibold">
                                ✓ 금액 일치
                              </span>
                            )}
                          </p>
                        </div>
                        <span
                          className={`text-sm font-medium ${
                            transaction.quantity >= 0 ? "text-green-600" : "text-red-600"
                          }`}
                        >
                          {transaction.quantity?.toLocaleString()}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </>,
        document.body
      )}
      {!selectedAsset && (
        <p className="text-xs text-gray-500 mt-1">
          먼저 자산을 선택하세요
        </p>
      )}
      {!transactionDate && selectedAsset && (
        <p className="text-xs text-gray-500 mt-1">
          먼저 거래 날짜를 선택하세요
        </p>
      )}
    </div>
  );
}
