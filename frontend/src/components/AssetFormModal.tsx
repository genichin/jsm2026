"use client";

import { Modal } from "@/components/Modal";
import { Button } from "@/components/Button";
import { useState } from "react";

export type AssetType = "stock" | "crypto" | "bond" | "fund" | "etf" | "cash" | "savings" | "deposit";

export type AssetFormData = {
  id?: string;
  name: string;
  account_id: string;
  asset_type?: AssetType;
  symbol?: string;
  market?: string;
  currency: string;
  is_active: boolean;
  asset_metadata?: any;
};

type AccountOption = { id: string; name: string };

interface AssetFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
  editingAsset: AssetFormData | null;
  accounts: AccountOption[];
  isLoading?: boolean;
}

const assetTypeOptions: { value: AssetType; label: string }[] = [
  { value: "stock", label: "주식" },
  { value: "crypto", label: "암호화폐" },
  { value: "bond", label: "채권" },
  { value: "fund", label: "펀드" },
  { value: "etf", label: "ETF" },
  { value: "cash", label: "현금" },
  { value: "savings", label: "예금" },
  { value: "deposit", label: "적금" },
];

const marketOptions = [
  { value: "KOSPI", label: "KOSPI" },
  { value: "KOSDAQ", label: "KOSDAQ" },
  { value: "KRW", label: "KRW" },
];

export function AssetFormModal({
  isOpen,
  onClose,
  onSubmit,
  editingAsset,
  accounts,
  isLoading = false,
}: AssetFormModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(e);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!editingAsset) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editingAsset.id ? "자산 수정" : "새 자산"}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gh-fg-default mb-1.5">이름</label>
            <input
              name="name"
              defaultValue={editingAsset.name || ""}
              className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
              required
            />
          </div>
          {!editingAsset.id && (
            <div>
              <label className="block text-sm font-medium text-gh-fg-default mb-1.5">계좌</label>
              <select
                name="account_id"
                defaultValue={editingAsset.account_id || ""}
                className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
              >
                <option value="">선택하세요</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          {!editingAsset.id && (
            <div>
              <label className="block text-sm font-medium text-gh-fg-default mb-1.5">유형</label>
              <select
                name="asset_type"
                defaultValue={(editingAsset.asset_type || "stock") as string}
                className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
              >
                {assetTypeOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gh-fg-default mb-1.5">심볼</label>
            <input
              name="symbol"
              defaultValue={editingAsset.symbol || ""}
              className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gh-fg-default mb-1.5">거래소</label>
            <select
              name="market"
              defaultValue={editingAsset.market || ""}
              className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
            >
              <option value="">선택하세요</option>
              {marketOptions.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gh-fg-default mb-1.5">통화</label>
            <input
              name="currency"
              defaultValue={editingAsset.currency || "KRW"}
              className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
            />
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input
              type="checkbox"
              name="is_active"
              defaultChecked={editingAsset.is_active ?? true}
              className="rounded"
            />
            <label className="text-sm text-gh-fg-default">활성</label>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gh-fg-default mb-1.5">
            asset_metadata (JSON)
          </label>
          <textarea
            name="asset_metadata"
            defaultValue={
              editingAsset.asset_metadata
                ? JSON.stringify(editingAsset.asset_metadata, null, 2)
                : ""
            }
            className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 h-32 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
          />
        </div>
        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="default" onClick={onClose} disabled={isSubmitting}>
            취소
          </Button>
          <Button type="submit" disabled={isSubmitting || isLoading}>
            {isSubmitting ? "처리 중..." : editingAsset.id ? "수정" : "생성"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
