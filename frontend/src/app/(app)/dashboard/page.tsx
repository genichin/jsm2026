"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardTitle } from "@/components/Card";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useMemo } from "react";

export default function DashboardPage() {
  const accountsQ = useQuery({ queryKey: ["accounts"], queryFn: async () => (await api.get("/accounts")).data });
  const assetsQ = useQuery({ queryKey: ["assets"], queryFn: async () => (await api.get("/assets")).data });
  const txQ = useQuery({ queryKey: ["transactions", { page: 1 }], queryFn: async () => (await api.get("/transactions", { params: { page: 1, size: 50 } })).data });

  const loading = accountsQ.isLoading || assetsQ.isLoading || txQ.isLoading;

  // 계좌별 요약 정보 계산
  const accountSummaries = useMemo(() => {
    if (!accountsQ.data?.accounts || !assetsQ.data?.items) {
      return [];
    }

    const summaries = accountsQ.data.accounts.map((account: any) => {
      // 해당 계좌의 자산들 찾기
      const accountAssets = assetsQ.data.items.filter((asset: any) => asset.account_id === account.id);
      
      // 잔고(평가금액) 계산: balance * price의 합계
      const totalValue = accountAssets.reduce((sum: number, asset: any) => {
        const balance = asset.balance || 0;
        const price = asset.price || 0;
        return sum + (balance * price);
      }, 0);
      
      // 수익률 계산 (TODO: 취득원가 정보가 필요, 임시로 랜덤 값)
      const returnRate = Math.random() * 20 - 10; // -10% ~ +10%
      
      return {
        id: account.id,
        name: account.name,
        account_type: account.account_type,
        provider: account.provider,
        totalValue,
        returnRate,
        assetCount: accountAssets.length
      };
    });
    
    return summaries;
  }, [accountsQ.data, assetsQ.data]);

  // Simple derived chart from transactions count per day (using transaction_date)
  const chartData = (txQ.data?.items || []).reduce((acc: any[], t: any) => {
    const d = new Date(t.transaction_date).toISOString().slice(0, 10);
    const found = acc.find((x) => x.date === d);
    if (found) found.count += 1; else acc.push({ date: d, count: 1 });
    return acc;
  }, [] as { date: string; count: number }[]).sort((a: any, b: any) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-4">
      {loading ? (
        <div>로딩 중...</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card>
            <CardTitle>계좌 수</CardTitle>
            <div className="text-3xl font-bold">{accountsQ.data?.total ?? accountsQ.data?.accounts?.length ?? 0}</div>
          </Card>
          <Card>
            <CardTitle>자산 수</CardTitle>
            <div className="text-3xl font-bold">{assetsQ.data?.total ?? assetsQ.data?.items?.length ?? 0}</div>
          </Card>
          <Card>
            <CardTitle>최근 거래 (50건)</CardTitle>
            <div className="text-3xl font-bold">{txQ.data?.items?.length ?? 0}</div>
          </Card>
        </div>
      )}

      {/* 계좌별 요약 카드 */}
      {!loading && accountSummaries.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">계좌 현황</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {accountSummaries.map((account: any) => (
              <div key={account.id} className="bg-white rounded-lg border p-4 shadow hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-lg text-gray-900">{account.name}</h3>
                    <p className="text-sm text-gray-600">{account.provider || account.account_type}</p>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    account.returnRate >= 0 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {account.returnRate >= 0 ? '+' : ''}{account.returnRate.toFixed(2)}%
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">잔고(평가금액)</span>
                    <span className="font-semibold text-lg">
                      {account.totalValue.toLocaleString()}원
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">보유 자산</span>
                    <span className="font-medium">
                      {account.assetCount}개
                    </span>
                  </div>
                </div>
                
                <div className="mt-4 pt-3 border-t border-gray-200">
                  <button 
                    className="w-full text-sm text-blue-600 hover:text-blue-800 font-medium"
                    onClick={() => window.location.href = `/accounts/${account.id}`}
                  >
                    자세히 보기 →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Card>
        <CardTitle>일자별 거래 건수</CardTitle>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ left: 12, right: 12, top: 12, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#0ea5e9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
