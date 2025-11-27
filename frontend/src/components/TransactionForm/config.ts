import { TransactionType } from "@/lib/transactionTypes";
import { TransactionTypeConfig } from "./types";

// 거래 유형별 필드 라벨 정의
export const FIELD_LABELS: Record<TransactionType, Partial<Record<string, string>>> = {
  deposit: { quantity: "입금 금액" },
  withdraw: { quantity: "출금 금액" },
  buy: { quantity: "매수 수량" },
  sell: { quantity: "매도 수량" },
  dividend: { quantity: "배당 주식 수" },
  interest: { quantity: "이자 금액" },
  fee: { quantity: "수수료 금액" },
  transfer_in: { quantity: "이체 입금 금액" },
  transfer_out: { quantity: "이체 출금 금액" },
  internal_transfer: { quantity: "이체 금액" },
  adjustment: { quantity: "조정 수량" },
  invest: { quantity: "투자 금액" },
  redeem: { quantity: "해지 금액" },
  card_payment: { quantity: "결제 금액" },
  promotion_deposit: { quantity: "입금 금액" },
  auto_transfer: { quantity: "이체 금액" },
  remittance: { quantity: "송금 금액" },
  exchange: { quantity: "환전 금액" },
};

export const TRANSACTION_TYPE_CONFIGS: Record<TransactionType, TransactionTypeConfig> = {
  deposit: {
    type: 'deposit',
    label: '입금',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: [],
  },
  withdraw: {
    type: 'withdraw',
    label: '출금',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  buy: {
    type: 'buy',
    label: '매수',
    fields: ['asset', 'quantity', 'price', 'fee', 'tax', 'date', 'cash_asset', 'memo'],
    requiredFields: ['asset', 'quantity', 'price','date'],
    specialBehavior: ['cashAssetSelector'],
  },
  sell: {
    type: 'sell',
    label: '매도',
    fields: ['asset', 'quantity', 'price', 'fee', 'tax', 'date', 'cash_asset', 'memo'],
    requiredFields: ['asset', 'quantity', 'price', 'date'],
    specialBehavior: ['negativeQuantity', 'cashAssetSelector'],
  },
  dividend: {
    type: 'dividend',
    label: '배당',
    fields: ['asset', 'quantity', 'date', 'cash_asset', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    hiddenFields: ['category'],
    specialBehavior: ['dividendCashAsset'],
  },
  interest: {
    type: 'interest',
    label: '이자',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: [],
  },
  fee: {
    type: 'fee',
    label: '수수료',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  transfer_in: {
    type: 'transfer_in',
    label: '이체 입금',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: [],
  },
  transfer_out: {
    type: 'transfer_out',
    label: '이체 출금',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  internal_transfer: {
    type: 'internal_transfer',
    label: '내부이체',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: [],
  },
  adjustment: {
    type: 'adjustment',
    label: '수량조정',
    fields: ['asset', 'quantity', 'date', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    hiddenFields: ['category'],
    specialBehavior: [],
  },
  invest: {
    type: 'invest',
    label: '투자',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: [],
  },
  redeem: {
    type: 'redeem',
    label: '해지',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  card_payment: {
    type: 'card_payment',
    label: '카드결제',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  promotion_deposit: {
    type: 'promotion_deposit',
    label: '프로모션입금',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: [],
  },
  auto_transfer: {
    type: 'auto_transfer',
    label: '자동이체',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  remittance: {
    type: 'remittance',
    label: '송금',
    fields: ['asset', 'quantity', 'date', 'category', 'description', 'memo'],
    requiredFields: ['asset', 'quantity', 'date'],
    specialBehavior: ['negativeQuantity'],
  },
  exchange: {
    type: 'exchange',
    label: '환전',
    fields: ['asset', 'target_asset', 'source_amount', 'target_amount', 'date', 'description', 'memo'],
    requiredFields: ['asset', 'target_asset', 'source_amount', 'target_amount', 'date'],
    hiddenFields: ['quantity', 'category'],
    specialBehavior: ['exchangeRate'],
  },
};

// 필드가 특정 유형에서 표시되는지 확인
export function shouldShowField(
  fieldName: string,
  transactionType: TransactionType
): boolean {
  const config = TRANSACTION_TYPE_CONFIGS[transactionType];
  if (!config) return false;
  
  // 숨김 필드 체크
  if (config.hiddenFields?.includes(fieldName)) {
    return false;
  }
  
  // 카테고리는 dividend와 exchange에서 숨김
  if (fieldName === 'category' && (transactionType === 'dividend' || transactionType === 'exchange')) {
    return false;
  }
  
  return config.fields.includes(fieldName);
}

// 특수 동작이 활성화되어 있는지 확인
export function hasSpecialBehavior(
  behavior: string,
  transactionType: TransactionType
): boolean {
  const config = TRANSACTION_TYPE_CONFIGS[transactionType];
  return config?.specialBehavior?.includes(behavior as any) ?? false;
}
