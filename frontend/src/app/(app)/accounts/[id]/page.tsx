"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardTitle } from "@/components/Card";
import { Modal } from "@/components/Modal";
import { DynamicTransactionForm } from "@/components/TransactionForm/DynamicTransactionForm";
import { AssetFormModal, type AssetFormData } from "@/components/AssetFormModal";
import RecentTransactions from "@/components/RecentTransactions";
import { useMemo, useState } from "react";

type TransactionType = 
  | "buy" | "sell" | "deposit" | "withdraw" | "transfer_in" | "transfer_out"
  | "cash_dividend" | "stock_dividend" | "interest" | "fee" | "adjustment"
  | "invest" | "redeem" | "internal_transfer" | "card_payment" 
  | "promotion_deposit" | "auto_transfer" | "remittance" | "exchange"
  | "out_asset" | "in_asset" | "payment_cancel";

type AccountType =
  | "bank_account"
  | "securities"
  | "cash"
  | "debit_card"
  | "credit_card"
  | "savings"
  | "deposit"
  | "crypto_wallet";

type Account = {
  id: string;
  name: string;
  account_type: AccountType;
  provider?: string | null;
  account_number?: string | null;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type Asset = {
  id: string;
  account_id: string;
  name: string;
  asset_type: string;
  symbol?: string | null;
  currency: string;
  balance?: number;
  price?: number;
  is_active: boolean;
};

const typeLabels: Record<AccountType, string> = {
  bank_account: "은행계좌",
  securities: "증권",
  cash: "현금",
  debit_card: "체크카드",
  credit_card: "신용카드",
  savings: "저축",
  deposit: "적금",
  crypto_wallet: "암호화폐",
};

export default function AccountDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const accountId = params.id as string;

  // 거래 추가 모달 상태
  const [isTransactionModalOpen, setIsTransactionModalOpen] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<TransactionType | null>(null);
  const [editing, setEditing] = useState<any>(null);

  // 자산 추가 모달 상태
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<AssetFormData | null>(null);

  // 자산 선택 핸들러 - 자산 선택 시 기본 거래 유형 설정
  const handleAssetChange = (assetId: string) => {
    setSelectedAssetId(assetId);
    if (assetId && !selectedType) {
      // 자산 선택 시 기본 거래 유형을 deposit으로 설정
      setSelectedType('deposit');
    }
  };
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestedCategoryId, setSuggestedCategoryId] = useState<string | null>(null);

  // 계좌 정보 조회
  const accountQuery = useQuery<Account>({
    queryKey: ["account", accountId],
    queryFn: async () => {
      const res = await api.get(`/accounts/${accountId}`);
      return res.data as Account;
    },
  });

  // 계좌의 자산들 조회
  const assetsQuery = useQuery<{ items: Asset[] }>({
    queryKey: ["assets", { account_id: accountId }],
    queryFn: async () => {
      const res = await api.get("/assets", { params: { account_id: accountId } });
      return res.data;
    },
  });

  // 거래 내역 조회 (최근 20건)
  const transactionsQuery = useQuery({
    queryKey: ["transactions", { account_id: accountId }],
    queryFn: async () => {
      const res = await api.get("/transactions", { params: { account_id: accountId, size: 20 } });
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
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setIsTransactionModalOpen(false);
      setEditing(null);
      setSelectedAssetId(null);
      setSelectedType(null);
      setSuggestedCategoryId(null);
    },
    onError: (error: any) => {
      console.error("Transaction creation failed:", error);
      console.error("Error response:", error.response?.data);
      alert(`거래 생성 실패: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 자산 생성 mutation
  const createAssetMut = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/assets", payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setIsAssetModalOpen(false);
      setEditingAsset(null);
    },
    onError: (error: any) => {
      console.error("Asset creation failed:", error);
      alert(`자산 생성 실패: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 자산 수정 mutation
  const updateAssetMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) => {
      const res = await api.put(`/assets/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setIsAssetModalOpen(false);
      setEditingAsset(null);
    },
    onError: (error: any) => {
      console.error("Asset update failed:", error);
      alert(`자산 수정 실패: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 거래 추가 시작
  function startCreateTransaction(assetId?: string) {
    // 자산 선택은 사용자가 직접 하도록 함 (assetId가 명시적으로 전달된 경우에만 설정)
    setSelectedAssetId(assetId || null);
    setSelectedType(null);
    setEditing(null);
    setIsTransactionModalOpen(true);
  }

  // 거래 폼 제출
  async function submitTransactionForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    
    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);

    // 필수 필드 검증
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

    console.log("Submitting transaction payload:", payload);

    // 카테고리 처리
    const categoryId = fd.get("category_id")?.toString();
    if (categoryId) {
      payload.category_id = categoryId;
    }

    // 거래 유형별 extras 처리
    const price = fd.get("price");
    const fee = fd.get("fee");
    const tax = fd.get("tax");
    
    if (price) payload.extras.price = parseFloat(price.toString());
    if (fee) payload.extras.fee = parseFloat(fee.toString());
    if (tax) payload.extras.tax = parseFloat(tax.toString());

    // 환전 거래
    if (selectedType === "exchange") {
      payload.target_asset_id = fd.get("target_asset_id")?.toString();
      payload.target_amount = parseFloat(fd.get("target_amount")?.toString() || "0");
    }

    // 현금배당
    if (selectedType === "cash_dividend") {
      const dividendAssetId = fd.get("dividend_asset_id")?.toString();
      if (dividendAssetId) {
        payload.extras.asset = dividendAssetId;
      }
    }

    // 매수/매도
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

  // 자산 추가 시작
  function startCreateAsset() {
    setEditingAsset({
      name: "",
      account_id: accountId,
      asset_type: "stock" as const,
      symbol: "",
      market: "",
      currency: "KRW",
      is_active: true,
      asset_metadata: null,
    });
    setIsAssetModalOpen(true);
  }

  // 자산 추가/수정 폼 제출
  async function submitAssetForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editingAsset) return;

    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);

    const metaText = fd.get("asset_metadata")?.toString().trim();
    let asset_metadata: any = null;
    if (metaText) {
      try {
        asset_metadata = JSON.parse(metaText);
      } catch {
        alert("asset_metadata JSON 형식이 올바르지 않습니다.");
        return;
      }
    }

    if (editingAsset.id) {
      // 수정
      const payload: any = {
        name: fd.get("name")?.toString().trim(),
        symbol: fd.get("symbol")?.toString().trim() || null,
        market: fd.get("market")?.toString().trim() || null,
        currency: fd.get("currency")?.toString().trim() || "KRW",
        is_active: fd.get("is_active") === "on",
        asset_metadata,
      };
      await updateAssetMut.mutateAsync({ id: editingAsset.id as string, payload });
    } else {
      // 생성
      const account_id = fd.get("account_id")?.toString();
      const asset_type = fd.get("asset_type")?.toString();
      if (!account_id) {
        alert("계좌를 선택하세요.");
        return;
      }
      const payload: any = {
        account_id,
        name: fd.get("name")?.toString().trim(),
        asset_type,
        symbol: fd.get("symbol")?.toString().trim() || null,
        market: fd.get("market")?.toString().trim() || null,
        currency: fd.get("currency")?.toString().trim() || "KRW",
        is_active: fd.get("is_active") === "on",
        asset_metadata,
      };
      await createAssetMut.mutateAsync(payload);
    }
  }

  // 자산 모달 닫기
  function cancelAssetEdit() {
    setIsAssetModalOpen(false);
    setEditingAsset(null);
  }

  // 계좌 요약 계산
  const summary = useMemo(() => {
    if (!assetsQuery.data?.items) return null;

    const assets = assetsQuery.data.items;
    
    // 총 평가금액
    const totalValue = assets.reduce((sum, asset) => {
      const balance = asset.balance || 0;
      const price = asset.price || 0;
      return sum + (balance * price);
    }, 0);

    // 현금 자산
    const cashAssets = assets.filter(a => a.asset_type === 'cash');
    const totalCash = cashAssets.reduce((sum, asset) => {
      const balance = asset.balance || 0;
      const price = asset.price || 1;
      return sum + (balance * price);
    }, 0);

    // 투자 자산
    const investmentAssets = assets.filter(a => a.asset_type !== 'cash');
    const totalInvestment = investmentAssets.reduce((sum, asset) => {
      const balance = asset.balance || 0;
      const price = asset.price || 0;
      return sum + (balance * price);
    }, 0);

    return {
      totalValue,
      totalCash,
      totalInvestment,
      assetCount: assets.length,
      cashAssetCount: cashAssets.length,
      investmentAssetCount: investmentAssets.length,
    };
  }, [assetsQuery.data]);

  if (accountQuery.isLoading) {
    return <div className="p-4">로딩 중...</div>;
  }

  if (accountQuery.isError || !accountQuery.data) {
    return <div className="p-4 text-red-600">계좌를 찾을 수 없습니다.</div>;
  }

  const account = accountQuery.data;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <button 
            onClick={() => router.back()} 
            className="text-sm text-blue-600 hover:text-blue-800 mb-2"
          >
            ← 뒤로가기
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{account.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-gray-600">{typeLabels[account.account_type]}</span>
            {account.provider && (
              <>
                <span className="text-gray-400">•</span>
                <span className="text-sm text-gray-600">{account.provider}</span>
              </>
            )}
            {account.account_number && (
              <>
                <span className="text-gray-400">•</span>
                <span className="text-sm text-gray-600">{account.account_number}</span>
              </>
            )}
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-2">
          {/* 제어 메뉴 */}
          <div className="flex items-center gap-2">
            <button
              onClick={startCreateAsset}
              className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium transition-colors"
            >
              + 자산 추가
            </button>
            <button
              onClick={() => startCreateTransaction()}
              className="px-3 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700 text-sm font-medium transition-colors"
            >
              + 거래 추가
            </button>
          </div>
          
          {/* 활성 상태 배지 */}
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            account.is_active 
              ? 'bg-green-100 text-green-800' 
              : 'bg-gray-100 text-gray-600'
          }`}>
            {account.is_active ? '활성' : '비활성'}
          </div>
        </div>
      </div>

      {/* 2열 레이아웃 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 왼쪽 컬럼: 요약 + 최근 거래 */}
        <div className="space-y-6">
          {/* 요약 카드 */}
          {summary && (
            <div className="bg-white rounded-lg border p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 mb-1">총 평가금액</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {summary.totalValue.toLocaleString()}
                    <span className="text-base font-normal text-gray-600 ml-1">{account.currency}</span>
                  </div>
                </div>
                <div className="text-right text-sm text-gray-600">
                  <div>현금 {summary.totalCash.toLocaleString()}원</div>
                  <div>투자 {summary.totalInvestment.toLocaleString()}원</div>
                  <div className="mt-1">총 {summary.assetCount}개 자산</div>
                </div>
              </div>
            </div>
          )}

          {/* 최근 거래 */}
          <Card>
            <RecentTransactions
              transactions={transactionsQuery.data?.items || []}
              isLoading={transactionsQuery.isLoading}
              viewAllLink={`/transactions?account_id=${accountId}`}
              maxItems={10}
            />
          </Card>
        </div>

        {/* 오른쪽 컬럼: 보유 자산 */}
        <div>
          <Card>
            <div className="flex items-center justify-between mb-4">
              <CardTitle>보유 자산</CardTitle>
              <button
                onClick={() => router.push(`/assets?account_id=${accountId}`)}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                전체 보기 →
              </button>
            </div>
            
            {assetsQuery.isLoading ? (
              <div className="text-sm text-gray-600">로딩 중...</div>
            ) : assetsQuery.data?.items.length === 0 ? (
              <div className="text-sm text-gray-600">자산이 없습니다.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">이름</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">유형</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">잔고</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">가격</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">평가금액</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {assetsQuery.data?.items.map((asset) => {
                      const balance = asset.balance || 0;
                      const price = asset.price || 0;
                      const value = balance * price;
                      
                      return (
                        <tr 
                          key={asset.id}
                          className="hover:bg-gray-50 cursor-pointer"
                          onClick={() => router.push(`/assets/${asset.id}`)}
                        >
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">
                            {asset.name}
                            {asset.symbol && (
                              <span className="ml-2 text-xs text-gray-500">({asset.symbol})</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600">{asset.asset_type}</td>
                          <td className="px-4 py-3 text-sm text-right font-mono">{balance.toLocaleString()}</td>
                          <td className="px-4 py-3 text-sm text-right font-mono">{price.toLocaleString()}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold">{value.toLocaleString()}원</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* 자산 추가 모달 */}
      <AssetFormModal
        isOpen={isAssetModalOpen}
        onClose={cancelAssetEdit}
        editingAsset={editingAsset}
        accounts={[{ id: accountId, name: account?.name || "" }]}
        onSubmit={submitAssetForm}
        isLoading={createAssetMut.isPending || updateAssetMut.isPending}
      />

      {/* 거래 추가 모달 */}
      <Modal
        isOpen={isTransactionModalOpen}
        onClose={cancelTransactionEdit}
        title={
          selectedAssetId && assetsQuery.data?.items
            ? `새 거래 - ${assetsQuery.data.items.find(a => a.id === selectedAssetId)?.name || ""}`
            : "새 거래"
        }
        size="xl"
      >
        <DynamicTransactionForm
          transactionType={(selectedType || 'deposit') as TransactionType}
          editing={editing}
          isEditMode={false}
          assets={assetsQuery.data?.items?.filter(a => a.account_id === accountId).map(a => ({
            id: a.id,
            name: a.name,
            symbol: a.symbol || '',
            asset_type: a.asset_type
          })) || []}
          categories={categoriesFlat}
          selectedAssetId={selectedAssetId || ''}
          onAssetChange={handleAssetChange}
          onTypeChange={(type) => setSelectedType(type)}
          onSubmit={submitTransactionForm}
          onCancel={cancelTransactionEdit}
          onSuggestCategory={suggestCategory}
          isSuggesting={isSuggesting}
          suggestedCategoryId={suggestedCategoryId}
        />
      </Modal>
    </div>
  );
}
