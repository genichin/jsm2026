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

export default function DashboardPage() {
  const accountsQ = useQuery({ queryKey: ["accounts"], queryFn: async () => (await api.get("/accounts")).data });
  const assetsQ = useQuery({ queryKey: ["assets"], queryFn: async () => (await api.get("/assets")).data });
  const txQ = useQuery({ queryKey: ["transactions", { page: 1 }], queryFn: async () => (await api.get("/transactions", { params: { page: 1, size: 50 } })).data });

  const loading = accountsQ.isLoading || assetsQ.isLoading || txQ.isLoading;

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
            <div className="text-3xl font-bold">{accountsQ.data?.total ?? accountsQ.data?.items?.length ?? 0}</div>
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
