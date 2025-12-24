import { TransactionType } from "@/lib/transactionTypes";

/**
 * 공통: 현금배당 거래에서 extras/source_asset_id와 금액 필드 추출
 */
export function buildCashDividendFields(fd: FormData) {
  const dividendAssetId = fd.get("dividend_asset_id")?.toString();
  if (!dividendAssetId) {
    throw new Error("배당 자산을 선택하세요.");
  }

  const price = parseFloat(fd.get("price")?.toString() || "0");
  const fee = parseFloat(fd.get("fee")?.toString() || "0");
  const tax = parseFloat(fd.get("tax")?.toString() || "0");
  const quantity = parseFloat(fd.get("quantity")?.toString() || "0");

  const extras = { source_asset_id: dividendAssetId } as Record<string, any>;
  const fields: Record<string, any> = { extras };

  if (!Number.isNaN(price) && price > 0) fields.price = price;
  if (!Number.isNaN(fee) && fee > 0) fields.fee = fee;
  if (!Number.isNaN(tax) && tax > 0) fields.tax = tax;
  if (!Number.isNaN(quantity)) fields.quantity = quantity;

  return fields;
}

/**
 * 거래 타입이 현금배당인지 여부 확인용 헬퍼 (가독성용)
 */
export function isCashDividend(type?: TransactionType | string | null): boolean {
  return type === "cash_dividend";
}
