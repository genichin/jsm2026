"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import RecentTransactions from "@/components/RecentTransactions";
import { Modal } from "@/components/Modal";
import { DynamicTransactionForm } from "@/components/TransactionForm/DynamicTransactionForm";
import { AssetFormModal, type AssetFormData } from "@/components/AssetFormModal";
import { useMemo, useState } from "react";
import { formatNumber, formatCurrency, formatPercent } from "@/lib/number-formatter";

type TransactionType = 
  | "buy" | "sell" | "deposit" | "withdraw" | "transfer_in" | "transfer_out"
  | "cash_dividend" | "stock_dividend" | "interest" | "fee" | "adjustment"
  | "invest" | "redeem" | "internal_transfer" | "card_payment" 
  | "promotion_deposit" | "auto_transfer" | "remittance" | "exchange"
  | "out_asset" | "in_asset" | "payment_cancel";

// Types
interface Asset {
  id: string;
  name: string;
  asset_type: string;
  symbol: string | null;
  currency: string;
  account_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  asset_metadata?: any | null;  // JSON 메타데이터
  balance?: number;  // Redis에서 조회한 현재 잔고
  price?: number;    // Redis에서 조회한 현재 가격
  change?: number;   // Redis에서 조회한 가격 변화량 (퍼센트)
  last_reviewed_at?: string | null;  // 마지막 검토 일시
  next_review_date?: string | null;  // 다음 검토 예정일
  review_interval_days?: number;     // 검토 주기 (일)
}

interface AssetSummary {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  symbol: string | null;
  current_quantity: number;
  total_cost: number;
  realized_profit: number;
  unrealized_profit: number | null;
  current_value: number | null;
  foreign_value?: number | null;
  foreign_currency?: string | null;
  krw_value?: number | null;
  // 필요 거래 정보(있을 경우 표시)
  need_trade?: {
    price?: number;
    quantity?: number;
  } | null;
}

interface Transaction {
  id: string;
  asset_id: string;
  type: string;
  transaction_date: string;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  description: string | null;
  memo: string | null;
  flow_type: string;
  category_id: string | null;
  related_transaction_id: string | null;
  realized_profit: number | null;
  asset?: {
    name: string;
    symbol: string | null;
  };
}

interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface Tag {
  id: string;
  name: string;
  color: string | null;
  description: string | null;
}

interface EntityTagsResponse {
  entity_type: string;
  entity_id: string;
  tags: Tag[];
  total: number;
}

interface Activity {
  id: string;
  user_id: string;
  target_type: string;
  target_id: string;
  activity_type: "comment" | "log";
  content: string | null;
  payload: Record<string, any> | null;
  parent_id: string | null;
  thread_root_id: string | null;
  visibility: "private" | "shared" | "public";
  is_immutable: boolean;
  is_deleted: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  user?: {
    username: string;
    full_name: string | null;
  };
}

interface ActivitiesResponse {
  items: Activity[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export default function AssetDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "transactions" | "tags" | "activities">("overview");
  const [txPage, setTxPage] = useState(1);
  const [txSize] = useState(20);
  const [activityPage, setActivityPage] = useState(1);
  const [activitySize] = useState(20);
  const [newComment, setNewComment] = useState("");

  // 거래 추가 모달 상태
  const [isTransactionModalOpen, setIsTransactionModalOpen] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<TransactionType | null>(null);
  const [editing, setEditing] = useState<any>(null);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestedCategoryId, setSuggestedCategoryId] = useState<string | null>(null);

  // 자산 편집 모달 상태
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetFormData | null>(null);

  // 파일 업로드 모달 상태
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // 가격 변경 모달 상태
  const [isPriceModalOpen, setIsPriceModalOpen] = useState(false);
  const [newPrice, setNewPrice] = useState<string>("");
  const [newChange, setNewChange] = useState<string>("");
  const [useSymbol, setUseSymbol] = useState(false);

  // 액션 메뉴 (모바일) 상태
  const [isActionMenuOpen, setIsActionMenuOpen] = useState(false);

  // 자산 기본 정보
  const assetQuery = useQuery<Asset>({
    queryKey: ["asset", params.id],
    queryFn: async () => (await api.get(`/assets/${params.id}`)).data,
  });

  // 자산 요약 정보
  const summaryQuery = useQuery<AssetSummary>({
    queryKey: ["asset-summary", params.id],
    queryFn: async () => (await api.get(`/assets/${params.id}/summary`)).data,
  });

  // 모든 활성 자산 목록 (거래 폼에서 현금 자산 선택용)
  const allAssetsQuery = useQuery({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await api.get(`/assets`);
      return data.items || [];
    },
  });

  // 거래 내역 (개요 탭에서도 사용하므로 항상 로드)
  const transactionsQuery = useQuery<TransactionListResponse>({
    queryKey: ["asset-transactions", params.id, txPage, txSize],
    queryFn: async () => {
      const { data } = await api.get(`/transactions/assets/${params.id}/transactions`, {
        params: { page: txPage, size: txSize },
      });
      return data;
    },
  });

  // 태그 (개요 탭에서도 사용하므로 항상 로드)
  const tagsQuery = useQuery<EntityTagsResponse>({
    queryKey: ["asset-tags", params.id],
    queryFn: async () => (await api.get(`/assets/${params.id}/tags`)).data,
  });

  // 활동 내역 (개요 탭에서도 사용하므로 항상 로드)
  const activitiesQuery = useQuery<ActivitiesResponse>({
    queryKey: ["asset-activities", params.id, activityPage, activitySize],
    queryFn: async () => {
      const { data } = await api.get(`/activities`, {
        params: {
          target_type: "asset",
          target_id: params.id,
          page: activityPage,
          size: activitySize,
        },
      });
      return data;
    },
  });

  // 모든 태그 조회 (태그 추가 시 사용)
  const allTagsQuery = useQuery({
    queryKey: ["all-tags"],
    queryFn: async () => {
      const res = await api.get("/tags");
      return res.data;
    },
  });

  // 카테고리 조회
  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: async () => {
      const res = await api.get("/categories");
      return res.data;
    },
  });

  // 카테고리 평탄화
  const categoriesFlat = useMemo(() => {
    if (!categoriesQuery.data?.categories) return [];
    const flatten = (cats: any[], level = 0): any[] => {
      return cats.flatMap((c) => [
        { ...c, level },
        ...(c.children ? flatten(c.children, level + 1) : [])
      ]);
    };
    return flatten(categoriesQuery.data.categories);
  }, [categoriesQuery.data]);

  // 거래 생성 mutation
  const createTransactionMut = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/transactions", payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
      setIsTransactionModalOpen(false);
      setEditing(null);
      setSelectedAssetId(null);
      setSelectedType(null);
      setSuggestedCategoryId(null);
    },
    onError: (error: any) => {
      console.error("Transaction creation failed:", error);
      const errorDetail = error.response?.data?.detail || 
                          JSON.stringify(error.response?.data) || 
                          error.message;
      console.error("Error details:", errorDetail);
      alert(`거래 생성 실패: ${errorDetail}`);
    },
  });

  // 파일 업로드 mutation
  const uploadMut = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post("/transactions/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["asset-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
      
      if (data.dry_run) {
        alert(`미리보기 결과:\n생성될 거래: ${data.created || 0}개\n중복 스킵: ${data.skipped || 0}개\n실패: ${data.failed || 0}개`);
      } else {
        setIsUploadModalOpen(false);
      }
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "파일 업로드 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // 가격 변경 mutation
  const updatePriceMut = useMutation({
    mutationFn: async (data: { price: number; change?: number; use_symbol: boolean }) => {
      const queryParams = new URLSearchParams({
        price: data.price.toString(),
        use_symbol: data.use_symbol.toString(),
      });
      if (data.change !== undefined) {
        queryParams.append("change", data.change.toString());
      }
      const response = await api.put(`/assets/${params.id}/price?${queryParams.toString()}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", params.id] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary", params.id] });
      setIsPriceModalOpen(false);
      setNewPrice("");
      setNewChange("");
      alert("가격이 업데이트되었습니다.");
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "가격 업데이트 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // 자산 수정 mutation
  const updateAssetMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) => {
      const res = await api.put(`/assets/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", params.id] });
      queryClient.invalidateQueries({ queryKey: ["asset-summary", params.id] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setIsAssetModalOpen(false);
      setEditingAsset(null);
      alert("자산이 수정되었습니다.");
    },
    onError: (error: any) => {
      console.error("Asset update failed:", error);
      alert(`자산 수정 실패: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 태그 추가 mutation
  const addTagMut = useMutation({
    mutationFn: async (tagId: string) =>
      (await api.post("/tags/attach", {
        tag_id: tagId,
        taggable_type: "asset",
        taggable_id: params.id,
      })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset-tags", params.id] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "태그 추가 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // 태그 제거 mutation
  const removeTagMut = useMutation({
    mutationFn: async (taggableId: string) =>
      (await api.delete(`/tags/detach/${taggableId}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset-tags", params.id] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "태그 제거 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // 검토 완료 mutation
  const markReviewedMut = useMutation({
    mutationFn: async () =>
      (await api.post(`/assets/${params.id}/mark-reviewed`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", params.id] });
      queryClient.invalidateQueries({ queryKey: ["assets", "review-pending"] });
      alert("검토 완료로 표시되었습니다.");
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "검토 완료 처리 중 오류가 발생했습니다.";
      alert(msg);
    },
  });

  // 거래 추가 시작
  function startCreateTransaction() {
    setSelectedAssetId(params.id);
    setSelectedType(null);
    setEditing(null);
    setIsTransactionModalOpen(true);
  }

  // 가격 변경 모달 열기
  function openPriceModal() {
    setNewPrice(asset?.price?.toString() || "");
    setNewChange(asset?.change?.toString() || "");
    setUseSymbol(false);
    setIsPriceModalOpen(true);
  }

  // 가격 변경 제출
  function handlePriceUpdate(e: React.FormEvent) {
    e.preventDefault();
    const price = parseFloat(newPrice);
    if (isNaN(price) || price <= 0) {
      alert("유효한 가격을 입력해주세요.");
      return;
    }
    
    const change = newChange ? parseFloat(newChange) : undefined;
    updatePriceMut.mutate({ price, change, use_symbol: useSymbol });
  }

  // 자산 편집 시작
  function startEditAsset() {
    if (!asset) return;
    
    // asset_metadata 파싱 (JSON 문자열인 경우 파싱)
    let metadataObj = asset.asset_metadata || {};
    if (typeof asset.asset_metadata === 'string') {
      try {
        metadataObj = JSON.parse(asset.asset_metadata);
      } catch {
        metadataObj = {};
      }
    }

    setEditingAsset({
      id: asset.id,
      name: asset.name,
      account_id: asset.account_id,
      asset_type: asset.asset_type as any,
      symbol: asset.symbol || "",
      market: metadataObj.market || "KRX",
      currency: asset.currency,
      is_active: asset.is_active,
      asset_metadata: metadataObj,
    });
    setIsAssetModalOpen(true);
  }

  // 자산 편집 취소
  function cancelAssetEdit() {
    setIsAssetModalOpen(false);
    setEditingAsset(null);
  }

  // 자산 폼 제출
  async function submitAssetForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editingAsset) return;
    
    const form = e.currentTarget as HTMLFormElement;
    const formData = new FormData(form);

    const name = formData.get("name")?.toString() || "";
    const asset_type = formData.get("asset_type")?.toString() || "";
    const symbol = formData.get("symbol")?.toString() || "";
    const market = formData.get("market")?.toString() || "KRX";
    const currency = formData.get("currency")?.toString() || "KRW";
    const is_active = formData.get("is_active") === "on";

    if (!name.trim()) {
      alert("자산명을 입력해주세요.");
      return;
    }

    let asset_metadata: any = {};
    if (symbol && symbol.trim()) {
      asset_metadata.market = market;
    }

    const payload = {
      name: name.trim(),
      asset_type,
      symbol: symbol.trim() || null,
      currency,
      is_active,
      asset_metadata: Object.keys(asset_metadata).length > 0 ? asset_metadata : {},
    };

    if (editingAsset.id) {
      await updateAssetMut.mutateAsync({
        id: editingAsset.id,
        payload,
      });
    }
  }

  // 거래 폼 제출
  async function submitTransactionForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    
    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);

    if (!selectedAssetId) {
      alert("자산을 선택해주세요.");
      return;
    }
    if (!selectedType) {
      alert("거래 유형을 선택해주세요.");
      return;
    }

    const payload: any = {
      asset_id: selectedAssetId,
      type: selectedType,
      quantity: parseFloat(fd.get("quantity")?.toString() || "0"),
      transaction_date: fd.get("transaction_date")?.toString(),
      description: fd.get("description")?.toString().trim() || null,
      memo: fd.get("memo")?.toString().trim() || null,
      extras: {},
    };

    const categoryId = fd.get("category_id")?.toString();
    if (categoryId) {
      payload.category_id = categoryId;
    }

    const price = fd.get("price");
    const fee = fd.get("fee");
    const tax = fd.get("tax");
    
    if (price) payload.extras.price = parseFloat(price.toString());
    if (fee) payload.extras.fee = parseFloat(fee.toString());
    if (tax) payload.extras.tax = parseFloat(tax.toString());

    if (selectedType === "exchange") {
      payload.target_asset_id = fd.get("target_asset_id")?.toString();
      payload.target_amount = parseFloat(fd.get("target_amount")?.toString() || "0");
    }

    if (selectedType === "cash_dividend") {
      const dividendAssetId = fd.get("dividend_asset_id")?.toString();
      if (dividendAssetId) {
        payload.extras.asset = dividendAssetId;
      }
    }

    if (selectedType === "buy" || selectedType === "sell") {
      const cashAssetId = fd.get("cash_asset_id")?.toString();
      if (cashAssetId) {
        payload.cash_asset_id = cashAssetId;
      }
    }

    await createTransactionMut.mutateAsync(payload);
  }

  // 카테고리 추천
  async function suggestCategory() {
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
  }

  // 모달 닫기
  function cancelTransactionEdit() {
    setIsTransactionModalOpen(false);
    setEditing(null);
    setSelectedAssetId(null);
    setSelectedType(null);
    setSuggestedCategoryId(null);
  }

  // 댓글 작성
  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    try {
      await api.post("/activities", {
        target_type: "asset",
        target_id: params.id,
        activity_type: "comment",
        content: newComment.trim(),
        visibility: "private",
      });
      setNewComment("");
      activitiesQuery.refetch();
    } catch (error) {
      console.error("댓글 작성 실패:", error);
      alert("댓글 작성에 실패했습니다.");
    }
  };

  // 댓글 삭제 (소프트 삭제)
  const handleDeleteComment = async (activityId: string) => {
    if (!confirm("이 댓글을 삭제하시겠습니까?")) return;

    try {
      await api.delete(`/activities/${activityId}`);
      activitiesQuery.refetch();
    } catch (error) {
      console.error("댓글 삭제 실패:", error);
      alert("댓글 삭제에 실패했습니다.");
    }
  };

  // 거래 내역 컬럼
  const transactionColumns: ColumnDef<Transaction>[] = useMemo(
    () => [
      {
        accessorKey: "transaction_date",
        header: "날짜",
        cell: ({ row }) => new Date(row.original.transaction_date).toLocaleDateString(),
      },
      {
        accessorKey: "type",
        header: "타입",
        cell: ({ row }) => {
          const typeLabels: Record<string, string> = {
            buy: "매수",
            sell: "매도",
            deposit: "입금",
            withdraw: "출금",
            dividend: "배당",
            interest: "이자",
            fee: "수수료",
            transfer_in: "이체(입)",
            transfer_out: "이체(출)",
            adjustment: "조정",
            invest: "투자",
            redeem: "환매",
            internal_transfer: "내부이체",
            card_payment: "카드결제",
            promotion_deposit: "프로모션입금",
            auto_transfer: "자동이체",
            remittance: "송금",
            exchange: "교환",
          };
          return typeLabels[row.original.type] || row.original.type;
        },
      },
      {
        accessorKey: "quantity",
        header: "수량",
        cell: ({ row }) => row.original.quantity.toFixed(4),
      },
      {
        accessorKey: "price",
        header: "가격",
        cell: ({ row }) => row.original.price?.toLocaleString() || "-",
      },
      {
        accessorKey: "fee",
        header: "수수료",
        cell: ({ row }) => row.original.fee?.toLocaleString() || "-",
      },
      {
        id: "total",
        header: "합계",
        cell: ({ row }) => {
          const { quantity, price, fee, tax } = row.original;
          if (price == null || quantity == null) return "-";
          const total = quantity * price + (fee || 0) + (tax || 0);
          return total.toLocaleString();
        },
      },
      {
        accessorKey: "flow_type",
        header: "흐름",
        cell: ({ row }) => row.original.flow_type || "-",
      },
    ],
    []
  );

  if (assetQuery.isLoading) return <div className="p-6">로딩 중...</div>;
  if (assetQuery.isError) return <div className="p-6 text-red-600">자산 정보를 불러오는데 실패했습니다.</div>;

  const asset = assetQuery.data;
  const summary = summaryQuery.data;

  const showReviewInfo = !!(
    asset?.review_interval_days &&
    (
      !asset.next_review_date ||
      new Date(asset.next_review_date) <= new Date()
    )
  );

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-gray-100 rounded"
            aria-label="뒤로가기"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              {asset?.name}
              {asset?.symbol && <span className="text-gray-500 text-lg">({asset.symbol})</span>}
            </h1>
            <div className="text-sm text-gray-600 flex gap-2 mt-1">
              <span className="px-2 py-0.5 bg-gray-100 rounded">{asset?.asset_type}</span>
              <span>{asset?.currency}</span>
              {!asset?.is_active && <span className="text-red-600">비활성</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* 모바일: 드롭다운 액션 메뉴 */}
          <div className="relative md:hidden">
            <button
              onClick={() => setIsActionMenuOpen((v) => !v)}
              className="px-3 py-2 rounded border bg-white hover:bg-gray-50 text-sm font-medium"
              aria-haspopup="menu"
              aria-expanded={isActionMenuOpen}
            >
              ⋯
            </button>
            {isActionMenuOpen && (
              <div className="absolute right-0 mt-2 w-44 bg-white border rounded-lg shadow-lg z-10 py-1">
                <button
                  onClick={() => { setIsUploadModalOpen(true); setIsActionMenuOpen(false); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 12V4m0 0l-4 4m4-4l4 4" />
                    </svg>
                    <span>파일 업로드</span>
                  </span>
                </button>
                <button
                  onClick={() => { startCreateTransaction(); setIsActionMenuOpen(false); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
                    </svg>
                    <span>거래 추가</span>
                  </span>
                </button>
                {asset?.review_interval_days && (
                  <button
                    onClick={() => { markReviewedMut.mutate(); setIsActionMenuOpen(false); }}
                    disabled={markReviewedMut.isPending}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                  >
                    <span className="inline-flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      <span>검토 완료</span>
                    </span>
                  </button>
                )}
                <button
                  onClick={() => { startEditAsset(); setIsActionMenuOpen(false); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4l8 8-6 6H6v-8l6-6z" />
                    </svg>
                    <span>편집</span>
                  </span>
                </button>
              </div>
            )}
          </div>

          {/* 데스크톱: GitHub 스타일 버튼 그룹 */}
          <div className="hidden md:inline-flex items-center border border-gray-200 rounded-md overflow-hidden bg-white divide-x divide-gray-200">
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <span className="inline-flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 12V4m0 0l-4 4m4-4l4 4" />
                </svg>
                <span>파일 업로드</span>
              </span>
            </button>
            <button
              onClick={() => startCreateTransaction()}
              className="px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <span className="inline-flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
                </svg>
                <span>거래 추가</span>
              </span>
            </button>
            {asset?.review_interval_days && (
              <button
                onClick={() => markReviewedMut.mutate()}
                disabled={markReviewedMut.isPending}
                className="px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
                title="이 자산을 검토 완료로 표시합니다"
              >
                <span className="inline-flex items-center gap-2">
                  <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span>검토 완료</span>
                </span>
              </button>
            )}
            <button
              onClick={() => startEditAsset()}
              className="px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <span className="inline-flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4l8 8-6 6H6v-8l6-6z" />
                </svg>
                <span>편집</span>
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* 검토 정보 (주기가 설정되고, 다음 검토일이 지났을 때만 노출) */}
      {showReviewInfo && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">검토 정보</h3>
              <div className="space-y-1 text-sm text-amber-800">
                {asset.last_reviewed_at ? (
                  <>
                    <p>
                      마지막 검토:{" "}
                      <span className="font-medium">
                        {new Date(asset.last_reviewed_at).toLocaleDateString("ko-KR")}
                      </span>
                    </p>
                    {asset.next_review_date && (
                      <p>
                        다음 검토 예정:{" "}
                        <span className="font-medium">
                          {new Date(asset.next_review_date).toLocaleDateString("ko-KR")}
                        </span>
                        {new Date(asset.next_review_date) < new Date() && (
                          <span className="ml-2 text-red-600 font-bold">검토 필요!</span>
                        )}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-orange-700 font-medium">
                    이 자산은 아직 검토되지 않았습니다.
                  </p>
                )}
                <p className="text-xs text-amber-700 mt-2">
                  검토 주기: {asset.review_interval_days}일마다
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 필요 거래 (검토 정보와 별도 표시) */}
      {summary?.need_trade && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">필요 거래</h3>
              <div className="space-y-1 text-sm text-amber-800">
                <p>
                  가격:{" "}
                  <span className="font-medium">
                    {summary.need_trade.price != null
                      ? summary.need_trade.price.toLocaleString()
                      : "-"}
                  </span>
                </p>
                <p>
                  수량:{" "}
                  <span className="font-medium">
                    {summary.need_trade.quantity != null
                      ? Number(summary.need_trade.quantity).toLocaleString(undefined, { maximumFractionDigits: 8 })
                      : "-"}
                  </span>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 요약 카드 */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 p-4 border rounded-lg bg-gray-50">
          <div>
            <div className="flex items-center mb-1">
              <div className="text-xs text-gray-600">현재가</div>
              {asset?.asset_type !== "cash" && (
                <button
                  onClick={openPriceModal}
                  className="text-xs text-blue-600 hover:text-blue-800 hover:underline ms-2"
                  title="가격 변경"
                >
                  (수동변경)
                </button>
              )}
            </div>
            <div className="text-lg font-semibold text-indigo-600">
              {asset?.price != null 
                ? formatNumber(asset.price)
                : "-"}
            </div>
            {asset?.change != null && (
              <div className={`text-xs font-medium mt-0.5 ${
                asset.change > 0 ? "text-red-600" : asset.change < 0 ? "text-blue-600" : "text-gray-500"
              }`}>
                {asset.change > 0 ? "▲" : asset.change < 0 ? "▼" : ""}
                {formatPercent(Math.abs(asset.change))}
              </div>
            )}
          </div>
          <div>
            <div className="text-xs text-gray-600">현재 잔고</div>
            <div className="text-lg font-semibold">
              {summary.current_quantity != null
                ? Number(summary.current_quantity) % 1 === 0
                  ? Math.floor(Number(summary.current_quantity)).toLocaleString()
                  : Number(summary.current_quantity).toLocaleString(undefined, { maximumFractionDigits: 8, minimumFractionDigits: 0 })
                : "0"}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600">총취득원가</div>
            <div className="text-lg font-semibold">{formatNumber(summary.total_cost)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-600">평단가</div>
            <div className="text-lg font-semibold">
              {summary.current_quantity > 0
                ? formatNumber(summary.total_cost / summary.current_quantity)
                : "-"}
            </div>
          </div>
          
          <div>
            <div className="text-xs text-gray-600">실현손익</div>
            <div className={`text-lg font-semibold ${(summary.realized_profit || 0) >= 0 ? "text-blue-600" : "text-red-600"}`}>
              {(summary.realized_profit || 0) >= 0 ? "+" : ""}
              {formatNumber(summary.realized_profit || 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-600">평가액</div>
            <div className="text-lg font-semibold">
              {summary.krw_value != null
                ? `${formatNumber(summary.krw_value)} 원`
                : "-"}
            </div>
            {asset?.currency && asset.currency !== "KRW" && (
              <div className="mt-1 text-xs text-gray-600 space-y-0.5">
                <div>
                  <span className="font-medium">
                    {summary.foreign_value != null
                      ? `${formatNumber(summary.foreign_value)} ${summary.foreign_currency || asset.currency}`
                      : "-"}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 탭 */}
      <div className="border-b mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === "overview"
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            개요
          </button>
          <button
            onClick={() => setActiveTab("transactions")}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === "transactions"
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            전체 거래
          </button>
          <button
            onClick={() => setActiveTab("tags")}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === "tags"
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            태그
          </button>
          <button
            onClick={() => setActiveTab("activities")}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === "activities"
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            검토 & 이력
          </button>
        </div>
      </div>

      {/* 탭 내용 */}
      <div>
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 왼쪽: 최근 거래 */}
            <div className="border rounded-lg p-4">
              {transactionsQuery.isError ? (
                <p className="text-red-600">거래 내역을 불러오는데 실패했습니다.</p>
              ) : (
                <RecentTransactions
                  transactions={transactionsQuery.data?.items || []}
                  isLoading={transactionsQuery.isLoading}
                  viewAllLink={`/transactions?asset_id=${params.id}`}
                  maxItems={10}
                  showAssetName={false}
                />
              )}
            </div>

            {/* 오른쪽: 태그 + 검토 */}
            <div className="space-y-6">
              {/* 태그 섹션 */}
              <div className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold">태그</h2>
                  <button
                    onClick={() => setActiveTab("tags")}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    관리 →
                  </button>
                </div>
                {tagsQuery.isLoading && <p className="text-gray-500">태그 로딩 중...</p>}
                {tagsQuery.isError && <p className="text-red-600">태그를 불러오는데 실패했습니다.</p>}
                {tagsQuery.isSuccess && (
                  <>
                    {tagsQuery.data.tags.length === 0 ? (
                      <p className="text-gray-500 text-center py-8">연결된 태그가 없습니다.</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {tagsQuery.data.tags.slice(0, 10).map((tag) => (
                          <div
                            key={tag.id}
                            className="flex items-center gap-2 px-3 py-1.5 border rounded-full"
                            style={{ borderColor: tag.color || undefined }}
                          >
                            {tag.color && (
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: tag.color }}
                              />
                            )}
                            <span className="text-sm font-medium">{tag.name}</span>
                          </div>
                        ))}
                        {tagsQuery.data.tags.length > 10 && (
                          <span className="text-sm text-gray-500 px-3 py-1.5">
                            +{tagsQuery.data.tags.length - 10}개 더
                          </span>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* 최근 검토 */}
              <div className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold">최근 검토</h2>
                  <button
                    onClick={() => setActiveTab("activities")}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    전체 보기 →
                  </button>
                </div>
                {activitiesQuery.isLoading && <p className="text-gray-500">활동 내역 로딩 중...</p>}
                {activitiesQuery.isError && <p className="text-red-600">활동 내역을 불러오는데 실패했습니다.</p>}
                {activitiesQuery.isSuccess && activitiesQuery.data && (
                  <>
                    {activitiesQuery.data.items?.length === 0 ? (
                      <p className="text-gray-500 text-center py-8">검토 내역이 없습니다.</p>
                    ) : (
                      <div className="space-y-3">
                        {activitiesQuery.data.items?.slice(0, 3).map((activity) => (
                          <div key={activity.id} className="border-b pb-3 last:border-b-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium text-gray-700">
                                {activity.user?.username || "사용자"}
                              </span>
                              <span className="text-xs text-gray-500">
                                {new Date(activity.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <p className="text-sm text-gray-800 line-clamp-2">
                              {activity.activity_type === "comment" 
                                ? activity.content 
                                : `[로그] ${JSON.stringify(activity.payload)}`}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "transactions" && (
          <div className="space-y-4">
            {transactionsQuery.isLoading && <p>거래 내역 로딩 중...</p>}
            {transactionsQuery.isError && <p className="text-red-600">거래 내역을 불러오는데 실패했습니다.</p>}
            {transactionsQuery.isSuccess && (
              <>
                <div className="flex justify-between items-center">
                  <p className="text-sm text-gray-600">총 {transactionsQuery.data.total}건</p>
                  <button
                    onClick={() => router.push(`/transactions?asset_id=${params.id}`)}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    전체 보기 →
                  </button>
                </div>
                <DataTable columns={transactionColumns} data={transactionsQuery.data.items} />
                {transactionsQuery.data.pages > 1 && (
                  <div className="flex justify-center gap-2">
                    <button
                      onClick={() => setTxPage((p) => Math.max(1, p - 1))}
                      disabled={txPage === 1}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      이전
                    </button>
                    <span className="px-3 py-1">
                      {txPage} / {transactionsQuery.data.pages}
                    </span>
                    <button
                      onClick={() => setTxPage((p) => Math.min(transactionsQuery.data.pages, p + 1))}
                      disabled={txPage === transactionsQuery.data.pages}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      다음
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === "tags" && (
          <div className="space-y-6">
            {tagsQuery.isLoading && <p>태그 로딩 중...</p>}
            {tagsQuery.isError && <p className="text-red-600">태그를 불러오는데 실패했습니다.</p>}
            {tagsQuery.isSuccess && (
              <>
                {/* 현재 태그 목록 */}
                <div className="border rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">현재 태그</h3>
                  {tagsQuery.data.tags.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">연결된 태그가 없습니다.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {tagsQuery.data.tags.map((tag) => (
                        <div
                          key={tag.id}
                          className="flex items-center gap-2 px-3 py-1.5 border rounded-full group hover:bg-red-50"
                          style={{ borderColor: tag.color || undefined }}
                        >
                          {tag.color && (
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: tag.color }}
                            />
                          )}
                          <span className="text-sm font-medium">{tag.name}</span>
                          <button
                            onClick={() => {
                              const taggableId = (tag as any).taggable_id;
                              if (taggableId) {
                                removeTagMut.mutate(taggableId);
                              }
                            }}
                            disabled={removeTagMut.isPending}
                            className="ml-1 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 disabled:opacity-50"
                            title="태그 제거"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 태그 추가 */}
                <div className="border rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-4">태그 추가</h3>
                  {allTagsQuery.isLoading && <p>태그 목록 로딩 중...</p>}
                  {allTagsQuery.isError && <p className="text-red-600">태그 목록을 불러오는데 실패했습니다.</p>}
                  {allTagsQuery.isSuccess && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {allTagsQuery.data?.tags?.map((tag: any) => {
                        const alreadyAdded = tagsQuery.data.tags.some(
                          (t: any) => t.id === tag.id
                        );
                        return (
                          <button
                            key={tag.id}
                            onClick={() => {
                              if (!alreadyAdded) {
                                addTagMut.mutate(tag.id);
                              }
                            }}
                            disabled={alreadyAdded || addTagMut.isPending}
                            className={`px-4 py-2 border rounded text-sm font-medium transition-colors ${
                              alreadyAdded
                                ? "border-gray-200 bg-gray-100 text-gray-500 cursor-not-allowed"
                                : "border-blue-500 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
                            }`}
                            style={
                              tag.color && !alreadyAdded
                                ? {
                                    borderColor: tag.color,
                                    color: tag.color,
                                  }
                                : undefined
                            }
                          >
                            {tag.color && !alreadyAdded && (
                              <span
                                className="inline-block w-2 h-2 rounded-full mr-2"
                                style={{ backgroundColor: tag.color }}
                              />
                            )}
                            {tag.name}
                            {alreadyAdded && " ✓"}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === "activities" && (
          <div className="space-y-6">
            {/* 댓글 작성 폼 */}
            <div className="border rounded-lg p-4 bg-gray-50">
              <h3 className="text-sm font-semibold mb-3">검토 글 작성</h3>
              <form onSubmit={handleSubmitComment} className="space-y-3">
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="자산에 대한 검토 내용을 작성하세요..."
                  className="w-full border rounded px-3 py-2 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={!newComment.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    작성
                  </button>
                </div>
              </form>
            </div>

            {/* 활동 내역 목록 */}
            {activitiesQuery.isLoading && <p>활동 내역 로딩 중...</p>}
            {activitiesQuery.isError && <p className="text-red-600">활동 내역을 불러오는데 실패했습니다.</p>}
            {activitiesQuery.isSuccess && activitiesQuery.data && (
              <>
                <div className="flex justify-between items-center">
                  <p className="text-sm text-gray-600">총 {activitiesQuery.data.total}건</p>
                </div>
                
                {activitiesQuery.data.items?.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">활동 내역이 없습니다.</p>
                ) : (
                  <div className="space-y-4">
                    {activitiesQuery.data.items?.map((activity) => (
                      <div key={activity.id} className="border rounded-lg p-4 bg-white">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                              {activity.activity_type === "comment" ? "💬" : "📋"}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-sm">
                                  {activity.user?.username || "사용자"}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {new Date(activity.created_at).toLocaleString("ko-KR")}
                                </span>
                                {activity.activity_type === "log" && (
                                  <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                    시스템 로그
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          {activity.activity_type === "comment" && !activity.is_immutable && !activity.is_deleted && (
                            <button
                              onClick={() => handleDeleteComment(activity.id)}
                              className="text-xs text-red-600 hover:text-red-800"
                            >
                              삭제
                            </button>
                          )}
                        </div>

                        <div className="mt-3 ml-11">
                          {activity.activity_type === "comment" && activity.content && (
                            <p className="text-sm text-gray-800 whitespace-pre-wrap">{activity.content}</p>
                          )}
                          
                          {activity.activity_type === "log" && activity.payload && (
                            <div className="text-sm">
                              <div className="font-medium text-gray-700 mb-2">
                                {activity.payload.event || "변경 이력"}
                              </div>
                              <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto">
                                {JSON.stringify(activity.payload, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activitiesQuery.data?.pages && activitiesQuery.data.pages > 1 && (
                  <div className="flex justify-center gap-2 mt-6">
                    <button
                      onClick={() => setActivityPage((p) => Math.max(1, p - 1))}
                      disabled={activityPage === 1}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      이전
                    </button>
                    <span className="px-3 py-1">
                      {activityPage} / {activitiesQuery.data.pages}
                    </span>
                    <button
                      onClick={() => setActivityPage((p) => Math.min(activitiesQuery.data?.pages || 1, p + 1))}
                      disabled={activityPage === activitiesQuery.data.pages}
                      className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                      다음
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* 거래 추가 모달 */}
      <Modal
        isOpen={isTransactionModalOpen}
        onClose={cancelTransactionEdit}
        title={`새 거래 - ${asset?.name || ""}`}
        size="xl"
      >
        <DynamicTransactionForm
          transactionType={(selectedType || 'deposit') as TransactionType}
          editing={editing}
          isEditMode={false}
          assets={allAssetsQuery.data || [{
            id: params.id,
            name: asset?.name || '',
            symbol: asset?.symbol || '',
            asset_type: asset?.asset_type || '',
            account_id: asset?.account_id || ''
          }]}
          categories={categoriesFlat}
          selectedAssetId={params.id}
          onAssetChange={() => {}}
          onTypeChange={(type) => setSelectedType(type)}
          onSubmit={submitTransactionForm}
          onCancel={cancelTransactionEdit}
          onSuggestCategory={suggestCategory}
          isSuggesting={isSuggesting}
          suggestedCategoryId={suggestedCategoryId}
        />
      </Modal>

      {/* 자산 편집 모달 */}
      <AssetFormModal
        isOpen={isAssetModalOpen}
        onClose={cancelAssetEdit}
        onSubmit={submitAssetForm}
        editingAsset={editingAsset}
        accounts={asset ? [{ id: asset.account_id, name: asset.account_id }] : []}
        isLoading={updateAssetMut.isPending}
      />

      {/* 파일 업로드 모달 */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="거래 내역 파일 업로드"
        size="lg"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            // 자산 ID를 폼 데이터에 추가
            formData.set('asset_id', params.id);
            uploadMut.mutate(formData);
          }}
          className="space-y-4"
        >
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">지원 형식</h3>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• <strong>토스뱅크</strong>: 암호화된 Excel 파일 (.xlsx) - 비밀번호 입력 필요</li>
              <li>• <strong>KB은행</strong>: HTML 형식 Excel 파일 (.xls)</li>
              <li>• <strong>KB증권</strong>: 거래내역 CSV/Excel</li>
              <li>• <strong>미래에셋증권</strong>: 거래내역 CSV/Excel</li>
              <li>• <strong>CSV 파일</strong>: UTF-8 또는 CP949 인코딩</li>
            </ul>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-sm text-amber-900">
              <strong>선택된 자산:</strong> {asset?.name || params.id}
            </p>
            <p className="text-xs text-amber-700 mt-1">
              파일의 거래 내역이 이 자산에 연결됩니다
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              파일 선택 *
            </label>
            <input
              type="file"
              name="file"
              accept=".csv,.xlsx,.xls"
              required
              className="w-full border rounded px-3 py-2 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <p className="text-xs text-slate-500 mt-1">
              CSV, XLSX, XLS 파일 지원
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              파일 비밀번호 (선택사항)
            </label>
            <input
              type="password"
              name="password"
              placeholder="암호화된 Excel 파일인 경우 입력"
              className="w-full border rounded px-3 py-2"
            />
            <p className="text-xs text-slate-500 mt-1">
              토스뱅크 등 암호화된 파일의 경우 비밀번호를 입력하세요
            </p>
          </div>

          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded p-3">
            <input
              type="checkbox"
              name="dry_run"
              id="dry_run"
              value="true"
              className="w-4 h-4"
            />
            <label htmlFor="dry_run" className="text-sm text-amber-900">
              <strong>미리보기 모드</strong> (실제로 저장하지 않고 확인만)
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(false)}
              className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={uploadMut.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploadMut.isPending ? "업로드 중..." : "업로드"}
            </button>
          </div>
        </form>

        {uploadMut.isSuccess && uploadMut.data && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
            <h4 className="font-semibold text-green-900 mb-2">업로드 완료</h4>
            <div className="text-sm text-green-800 space-y-1">
              <p>• 생성된 거래: {uploadMut.data.created || 0}개</p>
              {uploadMut.data.skipped > 0 && (
                <p>• 중복 스킵: {uploadMut.data.skipped}개</p>
              )}
              {uploadMut.data.failed > 0 && (
                <p className="text-red-700">• 실패: {uploadMut.data.failed}개</p>
              )}
              {uploadMut.data.errors && uploadMut.data.errors.length > 0 && (
                <div className="mt-2">
                  <p className="text-red-700 font-medium">오류 발생: {uploadMut.data.errors.length}개</p>
                  <ul className="mt-1 text-xs text-red-600 max-h-40 overflow-y-auto">
                    {uploadMut.data.errors.map((err: any, idx: number) => (
                      <li key={idx}>행 {err.row}: {err.error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* 가격 변경 모달 */}
      <Modal
        isOpen={isPriceModalOpen}
        onClose={() => setIsPriceModalOpen(false)}
        title="자산 가격 변경"
        size="md"
      >
        <form onSubmit={handlePriceUpdate} className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">가격 업데이트</h3>
            <p className="text-xs text-blue-800">
              Redis에 저장된 실시간 가격 정보를 업데이트합니다.
            </p>
            {asset?.symbol && (
              <p className="text-xs text-blue-700 mt-1">
                심볼: <strong>{asset.symbol}</strong>
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              현재가 *
            </label>
            <input
              type="number"
              step="0.01"
              value={newPrice}
              onChange={(e) => setNewPrice(e.target.value)}
              required
              className="w-full border rounded px-3 py-2"
              placeholder="예: 68000"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              변화량 (%) <span className="text-xs text-gray-500">(선택사항)</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={newChange}
              onChange={(e) => setNewChange(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="예: 2.35 또는 -1.52"
            />
            <p className="text-xs text-slate-500 mt-1">
              양수는 상승(▲), 음수는 하락(▼)
            </p>
          </div>

          {asset?.symbol && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded p-3">
              <input
                type="checkbox"
                id="use_symbol"
                checked={useSymbol}
                onChange={(e) => setUseSymbol(e.target.checked)}
                className="w-4 h-4"
              />
              <label htmlFor="use_symbol" className="text-sm text-amber-900">
                <strong>심볼 기반 업데이트</strong> (동일 심볼 &quot;{asset.symbol}&quot;을 가진 모든 자산에 적용)
              </label>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => setIsPriceModalOpen(false)}
              className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={updatePriceMut.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {updatePriceMut.isPending ? "업데이트 중..." : "변경"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
