export type TransactionType =
  | "buy" | "sell" | "deposit" | "withdraw" | "cash_dividend" | "stock_dividend" | "interest"
  | "fee" | "transfer_in" | "transfer_out" | "adjustment" | "invest"
  | "redeem" | "internal_transfer" | "card_payment" | "promotion_deposit"
  | "auto_transfer" | "remittance" | "exchange" | "out_asset" | "in_asset";

export const transactionTypeLabels: Record<TransactionType, string> = {
  buy: "매수",
  sell: "매도",
  deposit: "입금",
  withdraw: "출금",
  cash_dividend: "현금배당",
  stock_dividend: "주식배당",
  interest: "이자",
  fee: "수수료",
  transfer_in: "이체입금",
  transfer_out: "이체출금",
  internal_transfer: "내부이체",
  adjustment: "수량조정",
  invest: "투자",
  redeem: "해지",
  card_payment: "카드결제",
  promotion_deposit: "프로모션입금",
  auto_transfer: "자동이체",
  remittance: "송금",
  exchange: "환전",
  out_asset: "자산매수출금",
  in_asset: "자산매도입금",
};

// transactionTypeLabels로부터 자동 생성
export const transactionTypeOptions: { value: TransactionType; label: string }[] = 
  Object.entries(transactionTypeLabels).map(([value, label]) => ({
    value: value as TransactionType,
    label,
  }));
