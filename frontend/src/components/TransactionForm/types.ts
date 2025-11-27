import { TransactionType } from "@/lib/transactionTypes";

export type AssetBrief = {
  id: string;
  name: string;
  asset_type: string;
  symbol?: string;
  currency?: string;
  is_active?: boolean;
  account_id?: string;
};

export type CategoryBrief = {
  id: string;
  name: string;
  flow_type: string;
  depth?: number;
};

export type TransactionFormData = {
  id?: string;
  asset_id: string;
  type: TransactionType;
  quantity: number;
  transaction_date: string;
  description?: string;
  memo?: string;
  category_id?: string;
};

export type FieldConfig = {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'datetime-local' | 'checkbox' | 'textarea';
  required?: boolean;
  placeholder?: string;
  hint?: string;
  min?: number | string;
  step?: string;
  options?: { value: string; label: string }[];
  className?: string;
  hidden?: boolean;
  disabled?: boolean;
  colSpan?: 1 | 2;
};

export type TransactionTypeConfig = {
  type: TransactionType;
  label: string;
  fields: string[];
  requiredFields: string[];
  hiddenFields?: string[];
  specialBehavior?: Array<
    | 'negativeQuantity'
    | 'cashAssetSelector'
    | 'dividendCashAsset'
    | 'exchangeRate'
    | 'zeroPrice'
  >;
};
