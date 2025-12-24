import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TransactionType } from "@/lib/transactionTypes";
import { buildCashDividendFields } from "@/lib/transactionPayload";

export type Transaction = {
  id: string;
  asset_id: string;
  related_transaction_id?: string | null;
  related_asset_name?: string | null;
  category_id?: string | null;
  category?: any;
  type: TransactionType;
  quantity: number;
  transaction_date: string;
  description?: string | null;
  memo?: string | null;
  flow_type: string;
  confirmed?: boolean;
  price?: number | null;
  fee?: number | null;
  tax?: number | null;
  realized_profit?: number | null;
  extras?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  asset?: any;
};

interface UseTransactionFormOptions {
  typeFilter?: TransactionType | "";
  assetFilter?: string;
  onSuccess?: () => void;
}

export function useTransactionForm(options: UseTransactionFormOptions = {}) {
  const { typeFilter = "", assetFilter = "", onSuccess } = options;
  const qc = useQueryClient();

  // State
  const [editing, setEditing] = useState<Partial<Transaction> | null>(null);
  const [selectedType, setSelectedType] = useState<TransactionType | "">("");
  const [selectedAssetId, setSelectedAssetId] = useState<string>("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [suggestedCategoryId, setSuggestedCategoryId] = useState<string | null>(null);
  const [isSuggesting, setIsSuggesting] = useState(false);

  // Mutations
  const createMut = useMutation({
    mutationFn: async (payload: any) => (await api.post("/transactions", payload)).data as Transaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
      setIsModalOpen(false);
      onSuccess?.();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 생성 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) =>
      (await api.put(`/transactions/${id}`, payload)).data as Transaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      setEditing(null);
      setIsModalOpen(false);
      onSuccess?.();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 수정 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/transactions/${id}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      onSuccess?.();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "거래 삭제 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  const uploadMut = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post("/transactions/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data;
    },
    onSuccess: (data: any) => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["assets"] });

      const successCount = data.created || 0;
      const skippedCount = data.skipped || 0;
      const errorCount = data.failed || 0;

      if (errorCount > 0) {
        const errorMsg = data.errors.slice(0, 3).map((e: any) => `행 ${e.row}: ${e.error}`).join("\n");
        alert(`${successCount}개 생성, ${skippedCount}개 중복 스킵, ${errorCount}개 오류:\n${errorMsg}${errorCount > 3 ? "\n..." : ""}`);
      } else if (skippedCount > 0) {
        alert(`${successCount}개 생성, ${skippedCount}개 중복으로 스킵되었습니다.`);
      } else {
        alert(`${successCount}개의 거래가 성공적으로 생성되었습니다.`);
      }

      onSuccess?.();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "파일 업로드 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // Functions
  const startCreate = useCallback(() => {
    const initialType = (typeFilter || "deposit") as TransactionType;
    const initialAssetId = assetFilter || "";

    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    const localDateTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

    setSelectedType(initialType);
    setSelectedAssetId(initialAssetId);
    setEditing({
      asset_id: initialAssetId,
      type: initialType,
      quantity: 0,
      transaction_date: localDateTime,
      description: "",
      memo: "",
    });
    setIsModalOpen(true);
  }, [typeFilter, assetFilter]);

  const startEdit = useCallback((row: Transaction) => {
    setSelectedType(row.type);
    setSelectedAssetId(row.asset_id);

    const editingData = {
      ...row,
      transaction_date: new Date(row.transaction_date).toISOString().slice(0, 19),
    };

    if (row.type === "cash_dividend" && row.extras) {
      const editData = editingData as any;
      editData.price = row.price || 0;
      editData.fee = row.fee || 0;
      editData.tax = row.tax || 0;
      editData.dividend_asset_id = row.extras.source_asset_id || "";
    }

    setEditing(editingData);
    setIsModalOpen(true);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditing(null);
    setSelectedType("");
    setSelectedAssetId("");
    setIsModalOpen(false);
    setSuggestedCategoryId(null);
  }, []);

  const suggestCategory = useCallback(async () => {
    const form = document.querySelector("form") as HTMLFormElement;
    if (!form) return;
    const description = (form.querySelector("[name='description']") as HTMLInputElement)?.value?.trim();
    if (!description) {
      alert("설명을 입력하세요.");
      return;
    }
    setIsSuggesting(true);
    try {
      const res = await api.post("/auto-rules/simulate", { description });
      const data = res.data;
      if (data.matched && data.category_id) {
        setSuggestedCategoryId(data.category_id);
        const categorySelect = form.querySelector("[name='category_id']") as HTMLSelectElement;
        if (categorySelect) {
          categorySelect.value = data.category_id;
        }
      } else {
        setSuggestedCategoryId(null);
        alert("매칭되는 자동 규칙이 없습니다.");
      }
    } catch (e) {
      console.error(e);
      alert("자동 추천 실패");
    } finally {
      setIsSuggesting(false);
    }
  }, []);

  const submitForm = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editing) return;
    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);

    if (editing.id) {
      // Update
      let transactionDate = fd.get("transaction_date")?.toString();
      if (transactionDate) {
        const localDate = new Date(transactionDate);
        transactionDate = new Date(localDate.getTime() - localDate.getTimezoneOffset() * 60000).toISOString();
      }

      const payload: any = {
        description: fd.get("description")?.toString().trim() || null,
        memo: fd.get("memo")?.toString().trim() || null,
        transaction_date: transactionDate,
      };

      const typeValue = fd.get("type")?.toString();
      if (typeValue) {
        payload.type = typeValue;
      }

      const categoryIdValue = fd.get("category_id")?.toString();
      payload.category_id = categoryIdValue || null;

      const relatedTransactionIdValue = fd.get("related_transaction_id")?.toString();
      payload.related_transaction_id = relatedTransactionIdValue || null;

      const flowTypeValue = fd.get("flow_type")?.toString();
      if (flowTypeValue) {
        payload.flow_type = flowTypeValue;
      }

      if (editing.type === "cash_dividend") {
        try {
          const cashDividendFields = buildCashDividendFields(fd);
          payload.extras = cashDividendFields.extras;
          if (cashDividendFields.price !== undefined) payload.price = cashDividendFields.price;
          if (cashDividendFields.fee !== undefined) payload.fee = cashDividendFields.fee;
          if (cashDividendFields.tax !== undefined) payload.tax = cashDividendFields.tax;
          if (cashDividendFields.quantity !== undefined) payload.quantity = cashDividendFields.quantity;
        } catch (err: any) {
          return alert(err?.message || "배당 자산을 선택하세요.");
        }
      }

      await updateMut.mutateAsync({ id: editing.id as string, payload });
    } else {
      // Create
      const asset_id = selectedAssetId;
      const type = fd.get("type")?.toString() as TransactionType;
      if (!asset_id) return alert("자산을 선택하세요.");

      let quantity = parseFloat(fd.get("quantity")?.toString() || "0");

      if (type === "sell" || type === "withdraw" || type === "transfer_out") {
        quantity = -Math.abs(quantity);
      } else {
        if (type === "buy" || type === "deposit" || type === "transfer_in") {
          quantity = Math.abs(quantity);
        }
      }

      let transactionDate = fd.get("transaction_date")?.toString() || new Date().toISOString();
      if (transactionDate && !transactionDate.endsWith("Z") && transactionDate.length === 19) {
        transactionDate = transactionDate + ".000Z";
      }

      const payload: any = {
        asset_id,
        type,
        quantity,
        transaction_date: transactionDate,
        description: fd.get("description")?.toString().trim() || null,
        memo: fd.get("memo")?.toString().trim() || null,
        category_id: fd.get("category_id")?.toString() || null,
      };

      if (type === "out_asset" || type === "in_asset") {
        payload.skip_auto_cash_transaction = true;
      }

      if (type === "exchange") {
        const target_asset_id = fd.get("target_asset_id")?.toString();
        const target_amount = fd.get("target_amount")?.toString();
        const exchange_rate = fd.get("exchange_rate")?.toString();

        if (!target_asset_id) return alert("환전 대상 자산을 선택하세요.");
        if (!target_amount || parseFloat(target_amount) <= 0) return alert("환전 대상 금액을 입력하세요.");

        payload.target_asset_id = target_asset_id;
        payload.target_amount = parseFloat(target_amount);

        if (exchange_rate && parseFloat(exchange_rate) > 0) {
          payload.extras = { exchange_rate: parseFloat(exchange_rate) };
        }
      }

      if (type === "buy" || type === "sell") {
        const cash_asset_id = fd.get("cash_asset_id")?.toString();
        if (cash_asset_id) {
          payload.cash_asset_id = cash_asset_id;
        }
      }

      if (type === "buy" || type === "sell") {
        const price = parseFloat(fd.get("price")?.toString() || "0");
        const fee = parseFloat(fd.get("fee")?.toString() || "0");
        const tax = parseFloat(fd.get("tax")?.toString() || "0");
        if (!isNaN(price) && price > 0) payload.price = price;
        if (!isNaN(fee) && fee > 0) payload.fee = fee;
        if (!isNaN(tax) && tax > 0) payload.tax = tax;
      }

      if (type === "cash_dividend") {
        try {
          const cashDividendFields = buildCashDividendFields(fd);
          payload.extras = { ...(payload.extras || {}), ...cashDividendFields.extras };
          if (cashDividendFields.price !== undefined) payload.price = cashDividendFields.price;
          if (cashDividendFields.fee !== undefined) payload.fee = cashDividendFields.fee;
          if (cashDividendFields.tax !== undefined) payload.tax = cashDividendFields.tax;
        } catch (err: any) {
          return alert(err?.message || "배당 자산을 선택하세요.");
        }
      }

      await createMut.mutateAsync(payload);
    }
  }, [editing, selectedAssetId, createMut, updateMut]);

  return {
    // State
    editing,
    selectedType,
    selectedAssetId,
    isModalOpen,
    suggestedCategoryId,
    isSuggesting,

    // State setters
    setEditing,
    setSelectedType,
    setSelectedAssetId,
    setIsModalOpen,
    setSuggestedCategoryId,

    // Functions
    startCreate,
    startEdit,
    submitForm,
    cancelEdit,
    suggestCategory,

    // Mutations
    createMut,
    updateMut,
    deleteMut,
    uploadMut,
  };
}
