import React, { useState, useMemo, useEffect } from "react";
import { TransactionType, transactionTypeLabels } from "@/lib/transactionTypes";
import { AssetBrief, CategoryBrief, TransactionFormData } from "./types";
import { shouldShowField, hasSpecialBehavior, FIELD_LABELS } from "./config";
import * as Fields from "./FormFields";
import { Modal } from "@/components/Modal";
import { api } from "@/lib/api";

type DynamicTransactionFormProps = {
  transactionType: TransactionType;
  editing: TransactionFormData | null;
  isEditMode: boolean;
  assets: AssetBrief[];
  categories: CategoryBrief[];
  selectedAssetId: string;
  onAssetChange: (assetId: string) => void;
  onTypeChange: (type: TransactionType) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onSuggestCategory?: () => void;
  isSuggesting?: boolean;
  suggestedCategoryId?: string | null;
};

export function DynamicTransactionForm({
  transactionType,
  editing,
  isEditMode,
  assets,
  categories,
  selectedAssetId,
  onAssetChange,
  onTypeChange,
  onSubmit,
  onCancel,
  onSuggestCategory,
  isSuggesting,
  suggestedCategoryId,
}: DynamicTransactionFormProps) {
  // 연결 거래 생성 모달 상태
  const [isCreatingRelated, setIsCreatingRelated] = useState(false);
  const [relatedTransactionType, setRelatedTransactionType] = useState<TransactionType | null>(null);
  
  // 연결 거래 선택 상태
  const [relatedTransactionId, setRelatedTransactionId] = useState<string>(editing?.related_transaction_id || "");
  const [relatedMode, setRelatedMode] = useState<'select' | 'create'>('create'); // 기본: 생성
  const [relatedAssetId, setRelatedAssetId] = useState<string>("");
  const [relatedPrice, setRelatedPrice] = useState<number>(0);
  
  // 환전 관련 상태
  const [exchangeSourceAmount, setExchangeSourceAmount] = useState(0);
  const [exchangeTargetAmount, setExchangeTargetAmount] = useState(0);
  const [exchangeRate, setExchangeRate] = useState<number | null>(null);
  
  // 흐름 타입 상태 (카테고리 변경 시 자동 업데이트)
  const [flowType, setFlowType] = useState<string>((editing as any)?.flow_type || 'undefined');

  // datetime-local용 로컬 시간 포맷터
  const toLocalDateTimeInput = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, "0");
    const year = d.getFullYear();
    const month = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const hour = pad(d.getHours());
    const minute = pad(d.getMinutes());
    return `${year}-${month}-${day}T${hour}:${minute}`;
  };

  // 거래 날짜 상태 (로컬 타임존로 표시)
  const [transactionDate, setTransactionDate] = useState<string>(() => {
    if (editing?.transaction_date) {
      const d = new Date(editing.transaction_date);
      return toLocalDateTimeInput(d);
    }
    return toLocalDateTimeInput(new Date());
  });

  // 현금배당 계산 상태
  const [grossDividend, setGrossDividend] = useState(
    (editing as any)?.price || 0   // 세전배당금
  );
  const [dividendFee, setDividendFee] = useState(
    (editing as any)?.fee || 0
  );
  const [dividendTax, setDividendTax] = useState(
    (editing as any)?.tax || 0
  );

  // 배당금액 계산 (세전배당금 - 수수료 - 세금) = quantity로 사용
  const calculatedDividendAmount = useMemo(() => {
    if (transactionType !== 'cash_dividend') return 0;
    const netAmount = grossDividend - dividendFee - dividendTax;
    return Math.max(0, netAmount); // 음수 방지
  }, [transactionType, grossDividend, dividendFee, dividendTax]);

  // 단계적 입력 상태
  const [isAssetLocked, setIsAssetLocked] = useState(isEditMode || !!selectedAssetId);

  // selectedAssetId 변경 감지 (부모에서 리셋된 경우)
  useEffect(() => {
    if (!selectedAssetId && !isEditMode) {
      setIsAssetLocked(false);
    }
  }, [selectedAssetId, isEditMode]);

  // 선택된 자산 정보
  const selectedAsset = useMemo(() => {
    return assets.find((a) => a.id === selectedAssetId);
  }, [assets, selectedAssetId]);

  // 현금 자산 필터링 (buy/sell/dividend용)
  const cashAssetsForBuySell = useMemo(() => {
    if (!selectedAsset) return [];
    return assets.filter(
      (a) =>
        a.account_id === selectedAsset.account_id &&
        a.currency === selectedAsset.currency &&
        a.asset_type === "cash"
    );
  }, [assets, selectedAsset]);

  // 동일 계좌 내 다른 통화의 현금 자산 (exchange용)
  const cashAssetsInSameAccount = useMemo(() => {
    if (!selectedAsset) return [];
    return assets.filter(
      (a) =>
        a.account_id === selectedAsset.account_id &&
        a.asset_type === "cash" &&
        a.currency !== selectedAsset.currency && // 다른 통화만
        a.id !== selectedAssetId
    );
  }, [assets, selectedAsset, selectedAssetId]);

  // 환전 금액 변경 핸들러
  const handleExchangeSourceChange = (val: number) => {
    setExchangeSourceAmount(val);
    if (val > 0 && exchangeTargetAmount > 0) {
      const sourceCurrency = selectedAsset?.currency || "";
      const rate =
        sourceCurrency === "KRW"
          ? val / exchangeTargetAmount
          : exchangeTargetAmount / val;
      setExchangeRate(rate);
    }
  };

  const handleExchangeTargetChange = (val: number) => {
    setExchangeTargetAmount(val);
    if (exchangeSourceAmount > 0 && val > 0) {
      const sourceCurrency = selectedAsset?.currency || "";
      const rate =
        sourceCurrency === "KRW"
          ? exchangeSourceAmount / val
          : val / exchangeSourceAmount;
      setExchangeRate(rate);
    }
  };

  // 연결 거래 생성 핸들러
  const handleCreateRelatedTransaction = () => {
    // out_asset -> buy (자산매수) / in_asset -> sell (자산매도)
    const suggestedType: TransactionType = transactionType === "out_asset" ? "buy" : "sell";
    setRelatedTransactionType(suggestedType);
    setIsCreatingRelated(true);
  };

  const handleRelatedTransactionSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // TODO: API 호출로 연결 거래 생성
    // 생성 후 자동으로 RelatedTransactionField에 반영되도록 처리
    setIsCreatingRelated(false);
  };

  // 필드 표시 여부 체크
  const showQuantity = shouldShowField("quantity", transactionType);
  const showPrice = shouldShowField("price", transactionType);
  const showFee = shouldShowField("fee", transactionType);
  const showTax = shouldShowField("tax", transactionType);
  const showCategory = shouldShowField("category", transactionType);
  const showDescription = shouldShowField("description", transactionType);
  const showCashAsset = shouldShowField("cash_asset", transactionType);
  const showDividendAsset = shouldShowField("dividend_asset", transactionType);
  const showRelatedTransaction = shouldShowField("related_transaction", transactionType);
  const showExchange = transactionType === "exchange";

  // 특수 동작 체크
  const isNegativeQuantity = hasSpecialBehavior("negativeQuantity", transactionType);
  const isDividend = transactionType === "cash_dividend";

  // out_asset / in_asset 현금 금액 추적 (연결 거래 수량 계산용)
  const [cashAmount, setCashAmount] = useState<number>(() => {
    if (isEditMode && editing?.quantity != null) return Math.abs(editing.quantity);
    return 0;
  });

  // 자산 선택 시 자동 확정
  const handleAssetSelect = (assetId: string) => {
    onAssetChange(assetId);
    if (assetId) {
      setIsAssetLocked(true);
    }
  };

  // 연결 거래 생성 확정 (인라인)
  const handleCreateRelatedConfirm = async () => {
    // transactionType 기반으로 자동 설정
    const targetType: TransactionType = transactionType === "out_asset" ? "buy" : "sell";
    
    console.log('handleCreateRelatedConfirm called', {
      transactionType,
      targetType,
      relatedAssetId,
      relatedPrice,
      selectedAssetId,
      cashAmount,
    });
    
    if (!relatedAssetId || !relatedPrice || !selectedAssetId) {
      console.log('Early return: missing required fields');
      return;
    }
    if (!cashAmount || relatedPrice <= 0) {
      console.log('Early return: invalid cashAmount or price', { cashAmount, relatedPrice });
      return;
    }
    let quantity = Number((cashAmount / relatedPrice).toFixed(8));
    
    // 매도(sell) 거래는 수량이 음수여야 함
    if (targetType === 'sell') {
      quantity = -Math.abs(quantity);
    }
    
    try {
      // Convert local time to UTC for backend
      const localDate = new Date(transactionDate);
      const utcDate = new Date(localDate.getTime() - localDate.getTimezoneOffset() * 60000).toISOString();
      const payload: any = {
        type: targetType,
        asset_id: relatedAssetId,
        quantity,
        transaction_date: utcDate,
        cash_asset_id: selectedAssetId,
        memo: '[자동] 연결 거래 생성',
        skip_auto_cash_transaction: true, // 현금 거래 자동 생성 건너뛰기
        extras: {
          price: relatedPrice,
        }
      };
      
      // 편집 모드에서 기존 out_asset/in_asset 거래와 연결
      if (isEditMode && editing?.id) {
        payload.related_transaction_id = editing.id;
      }
      
      console.log('Sending payload:', payload);
      const res = await api.post('/transactions', payload);
      const data = res.data;
      const newId = data?.id || data?.transaction?.id || '';
      console.log('Created transaction:', data, 'ID:', newId);
      if (newId) {
        setRelatedTransactionId(newId);
        setIsCreatingRelated(false);
        alert('연결 거래가 생성되었습니다!');
      }
    } catch (e) {
      console.error(e);
      alert('연결 거래 생성 실패: ' + (e as Error).message);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 자산 선택 영역 */}
        {isEditMode ? (
          <>
            
          </>
        ) : (
          <>
            {/* 생성 모드: 자산 선택 */}
            {!isAssetLocked && (
              <div className="col-span-1 md:col-span-2">
                <Fields.AssetField
                  value={selectedAssetId}
                  onChange={(e) => handleAssetSelect(e.target.value)}
                  required
                  assets={assets}
                />
              </div>
            )}
          </>
        )}

        {/* 공통 필드 영역 (편집 모드이거나 자산이 선택된 경우 표시) */}
        {(isEditMode || isAssetLocked) && (
          <>
           {/* 유형 필드 표시 */}
            
            <div className="col-span-1">
              <Fields.TypeField
                value={transactionType}
                onChange={(e) => onTypeChange(e.target.value as TransactionType)}
                required
              />
            </div>
            
            {/* 수량 (exchange 제외) */}
            {showQuantity && (
              <div className="col-span-1">
                {transactionType === 'cash_dividend' ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      배당금액 (자동계산)
                    </label>
                    <input
                      type="number"
                      value={calculatedDividendAmount}
                      readOnly
                      className="w-full border rounded px-3 py-2 bg-slate-50 text-slate-600"
                      title={`${grossDividend} - ${dividendFee} - ${dividendTax} = ${calculatedDividendAmount}`}
                    />
                    {/* 실제 quantity는 계산된 배당금액 */}
                    <input type="hidden" name="quantity" value={calculatedDividendAmount} />
                  </div>
                ) : (
                  <Fields.QuantityField
                    label={FIELD_LABELS[transactionType]?.quantity || "수량"}
                    defaultValue={
                      editing?.quantity ? Math.abs(editing.quantity) : 0
                    }
                    onChange={(e) => setCashAmount(parseFloat(e.target.value) || 0)}
                    required
                    showNegativeHint={isNegativeQuantity}
                  />
                )}
              </div>
            )}

            {/* 거래일시 */}
            <div className="col-span-1">
              <Fields.DateField
                value={transactionDate}
                onChange={(e) => setTransactionDate(e.target.value)}
                defaultValue={editing?.transaction_date}
                required
              />
            </div>

            {/* 가격/수수료/세금 (config 기반 표시) */}
            {showPrice && (
              <div className="col-span-1">
                {transactionType === 'cash_dividend' ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      세전배당금 *
                    </label>
                    <input
                      type="number"
                      step="any"
                      name="price"
                      value={grossDividend}
                      onChange={(e) => setGrossDividend(Number(e.target.value) || 0)}
                      required
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                ) : (
                  <Fields.PriceField 
                    required 
                    defaultValue={(editing as any)?.price || 0} 
                  />
                )}
              </div>
            )}
            {showFee && (
              <div className="col-span-1">
                {transactionType === 'cash_dividend' ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      수수료
                    </label>
                    <input
                      type="number"
                      step="any"
                      name="fee"
                      value={dividendFee}
                      onChange={(e) => setDividendFee(Number(e.target.value) || 0)}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                ) : (
                  <Fields.FeeField 
                    defaultValue={(editing as any)?.fee || 0} 
                  />
                )}
              </div>
            )}
            {showTax && (
              <div className="col-span-1">
                {transactionType === 'cash_dividend' ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      세금
                    </label>
                    <input
                      type="number"
                      step="any"
                      name="tax"
                      value={dividendTax}
                      onChange={(e) => setDividendTax(Number(e.target.value) || 0)}
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                ) : (
                  <Fields.TaxField 
                    defaultValue={(editing as any)?.tax || 0} 
                  />
                )}
              </div>
            )}



            {/* 배당 자산 선택 (cash_dividend 전용) */}
            {showDividendAsset && (
              <div className="col-span-1">
                <Fields.DividendAssetField
                  assets={assets.filter(a => a.asset_type !== 'cash')}
                  defaultValue={(editing as any)?.dividend_asset_id || ""}
                />
              </div>
            )}

            {/* 현금 자산 선택 (buy/sell) */}
            {showCashAsset && (
              <div className="col-span-1">
                <Fields.CashAssetField
                  assets={cashAssetsForBuySell}
                  transactionType={transactionType}
                  defaultValue=""
                />
              </div>
            )}

            {/* 환전 전용 필드들 */}
            {showExchange && (
              <>
                <div className="col-span-1">
                  <Fields.TargetAssetField
                    assets={cashAssetsInSameAccount}
                    required
                  />
                </div>
                <div className="col-span-1 md:col-span-2">
                  <Fields.ExchangeAmountFields
                    sourceAmount={exchangeSourceAmount}
                    targetAmount={exchangeTargetAmount}
                    onSourceChange={handleExchangeSourceChange}
                    onTargetChange={handleExchangeTargetChange}
                    exchangeRate={exchangeRate}
                    sourceCurrency={selectedAsset?.currency || ""}
                  />
                </div>
              </>
            )}

            {/* 카테고리/설명 (dividend, exchange 제외) */}
            {showCategory && (
              <div className="col-span-1">
                <Fields.CategoryField
                  defaultValue={editing?.category_id}
                  categories={categories}
                  suggestedCategoryId={suggestedCategoryId}
                  onSuggestClick={onSuggestCategory}
                  isSuggesting={isSuggesting}
                  onChange={(e) => {
                    // 카테고리 변경 시 해당 카테고리의 flow_type으로 자동 업데이트
                    const selectedCategory = categories.find(c => c.id === e.target.value);
                    if (selectedCategory?.flow_type) {
                      setFlowType(selectedCategory.flow_type);
                    }
                  }}
                />
              </div>
            )}
            
            {/* 흐름 타입 */}
            {shouldShowField('flow_type', transactionType) && (
              <div className="col-span-1">
                <Fields.FlowTypeField
                  value={flowType}
                  onChange={(e) => setFlowType(e.target.value)}
                />
              </div>
            )}
            
            {showDescription && (
              <div className="col-span-1">
                <Fields.DescriptionField
                  defaultValue={editing?.description}
                  onSuggestClick={onSuggestCategory}
                  isSuggesting={isSuggesting}
                  showSuggestButton={showCategory}
                />
              </div>
            )}

            {/* 연결 거래 (out_asset, in_asset, payment_cancel) */}
            {showRelatedTransaction && (
              <div className="col-span-1 md:col-span-2">
                {transactionType === 'payment_cancel' ? (
                  <>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      연결 거래 (선택사항)
                    </label>
                    <Fields.RelatedTransactionField
                      value={relatedTransactionId}
                      onChange={(e) => setRelatedTransactionId(e.target.value)}
                      transactionDate={transactionDate}
                      selectedAsset={selectedAsset}
                      assets={assets}
                      currentQuantity={cashAmount}
                      transactionType={transactionType}
                    />
                    <input type="hidden" name="related_transaction_id" value={relatedTransactionId} />
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-slate-700">
                        연결 거래
                      </label>
                      <div className="flex gap-1 border rounded">
                        <button
                          type="button"
                          onClick={() => setRelatedMode('create')}
                          className={`px-3 py-1 text-xs rounded transition-colors ${
                            relatedMode === 'create'
                              ? 'bg-blue-600 text-white'
                              : 'bg-white text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          새로 생성
                        </button>
                        <button
                          type="button"
                          onClick={() => setRelatedMode('select')}
                          className={`px-3 py-1 text-xs rounded transition-colors ${
                            relatedMode === 'select'
                              ? 'bg-blue-600 text-white'
                              : 'bg-white text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          기존 선택
                        </button>
                      </div>
                    </div>

                    {relatedMode === 'select' ? (
                      <>
                        <Fields.RelatedTransactionField
                          value={relatedTransactionId}
                          onChange={(e) => setRelatedTransactionId(e.target.value)}
                          transactionDate={transactionDate}
                          selectedAsset={selectedAsset}
                          assets={assets}
                          onCreateNew={handleCreateRelatedTransaction}
                          transactionType={transactionType}
                        />
                        <input type="hidden" name="related_transaction_id" value={relatedTransactionId} />
                      </>
                    ) : (
                      <>
                        <input type="hidden" name="related_transaction_id" value={relatedTransactionId} />
                      <div className="border rounded p-3 bg-slate-50">
                        <div className="text-sm font-medium text-slate-700 mb-2">
                          연결 거래 생성: { (transactionType === 'out_asset' ? '매수' : '매도') }
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">자산 *</label>
                            <select
                              value={relatedAssetId}
                              onChange={(e) => setRelatedAssetId(e.target.value)}
                              className="w-full border rounded px-3 py-2"
                            >
                              <option value="">선택하세요</option>
                              {assets
                                .filter(a => a.account_id === selectedAsset?.account_id)
                                .map(a => (
                                  <option key={a.id} value={a.id}>{a.name}</option>
                                ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">가격 *</label>
                            <input
                              type="number"
                              step="any"
                              value={relatedPrice || ''}
                              onChange={(e) => setRelatedPrice(parseFloat(e.target.value) || 0)}
                              className="w-full border rounded px-3 py-2"
                              placeholder="예: 10350"
                            />
                          </div>
                          <div className="md:col-span-2">
                            <div className="text-xs text-slate-600">
                              현금 금액: {cashAmount?.toLocaleString() || 0} → 수량: {relatedPrice > 0 ? (cashAmount / relatedPrice).toFixed(6) : '-'}
                            </div>
                          </div>
                        </div>
                        <div className="flex justify-end gap-2 mt-3">
                          <button
                            type="button"
                            className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm disabled:opacity-50"
                            disabled={!relatedAssetId || !relatedPrice}
                            onClick={handleCreateRelatedConfirm}
                          >
                            생성 및 연결
                          </button>
                        </div>
                      </div>
                      </>
                    )}
                  </>
                )}
              </div>
            )}

            {/* 메모 */}
            <div className="col-span-1 md:col-span-2">
              <Fields.MemoField defaultValue={editing?.memo} />
            </div>
          </>
        )}
      </div>

      {/* 버튼 */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300"
        >
          취소
        </button>
        <button
          type="submit"
          className="px-4 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700"
        >
          {isEditMode ? "수정" : "생성"}
        </button>
      </div>
    </form>
  );
}
