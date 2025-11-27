import React, { useState, useMemo, useEffect } from "react";
import { TransactionType, transactionTypeLabels } from "@/lib/transactionTypes";
import { AssetBrief, CategoryBrief, TransactionFormData } from "./types";
import { shouldShowField, hasSpecialBehavior, FIELD_LABELS } from "./config";
import * as Fields from "./FormFields";

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
  // 환전 관련 상태
  const [exchangeSourceAmount, setExchangeSourceAmount] = useState(0);
  const [exchangeTargetAmount, setExchangeTargetAmount] = useState(0);
  const [exchangeRate, setExchangeRate] = useState<number | null>(null);

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

  // 동일 계좌 내 현금 자산 (exchange용)
  const cashAssetsInSameAccount = useMemo(() => {
    if (!selectedAsset) return [];
    return assets.filter(
      (a) =>
        a.account_id === selectedAsset.account_id &&
        a.asset_type === "cash" &&
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

  // 필드 표시 여부 체크
  const showQuantity = shouldShowField("quantity", transactionType);
  const showPrice = shouldShowField("price", transactionType);
  const showFee = shouldShowField("fee", transactionType);
  const showTax = shouldShowField("tax", transactionType);
  const showCategory = shouldShowField("category", transactionType);
  const showDescription = shouldShowField("description", transactionType);
  const showCashAsset = shouldShowField("cash_asset", transactionType);
  const showExchange = transactionType === "exchange";

  // 특수 동작 체크
  const isNegativeQuantity = hasSpecialBehavior("negativeQuantity", transactionType);
  const isDividend = transactionType === "dividend";

  // 자산 선택 시 자동 확정
  const handleAssetSelect = (assetId: string) => {
    onAssetChange(assetId);
    if (assetId) {
      setIsAssetLocked(true);
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
                <Fields.QuantityField
                  label={FIELD_LABELS[transactionType]?.quantity || "수량"}
                  defaultValue={
                    editing?.quantity ? Math.abs(editing.quantity) : 0
                  }
                  required
                  showNegativeHint={isNegativeQuantity}
                />
              </div>
            )}

            {/* 거래일시 */}
            <div className="col-span-1">
              <Fields.DateField
                defaultValue={editing?.transaction_date}
                required
              />
            </div>

            {/* 가격/수수료/세금 (config 기반 표시) */}
            {showPrice && (
              <div className="col-span-1">
                <Fields.PriceField required defaultValue={0} />
              </div>
            )}
            {showFee && (
              <div className="col-span-1">
                <Fields.FeeField defaultValue={0} />
              </div>
            )}
            {showTax && (
              <div className="col-span-1">
                <Fields.TaxField defaultValue={0} />
              </div>
            )}

            {/* 현금 자산 선택 (buy/sell/dividend) */}
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
