"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { formatDistanceToNow } from "date-fns";
import { ko } from "date-fns/locale";

type Asset = {
  id: string;
  name: string;
  asset_type: string;
  last_reviewed_at: string | null;
  next_review_date: string | null;
  review_interval_days: number;
  balance?: number;
  price?: number;
};

export function ReviewPendingWidget() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: pendingAssets, isLoading, isError } = useQuery<Asset[]>({
    queryKey: ["assets", "review-pending"],
    queryFn: async () => {
      const response = await api.get("/assets/review-pending?limit=5");
      return response.data;
    },
  });

  const markReviewedMutation = useMutation({
    mutationFn: async (assetId: string) => {
      return await api.post(`/assets/${assetId}/mark-reviewed`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", "review-pending"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });

  if (isLoading) {
    return (
      <div className="border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">검토가 필요한 자산</h2>
        <p className="text-gray-500">로딩 중...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">검토가 필요한 자산</h2>
        <p className="text-red-600">데이터를 불러오는데 실패했습니다.</p>
      </div>
    );
  }

  if (!pendingAssets || pendingAssets.length === 0) {
    return (
      <div className="border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">검토가 필요한 자산</h2>
        <p className="text-gray-500 text-center py-8">
          검토가 필요한 자산이 없습니다. 훌륭합니다! 🎉
        </p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">검토가 필요한 자산</h2>
        <span className="text-sm text-gray-600">
          {pendingAssets.length}개 자산
        </span>
      </div>

      <div className="space-y-3">
        {pendingAssets.map((asset) => (
          <div
            key={asset.id}
            className="flex items-center justify-between p-3 border rounded hover:bg-gray-50 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{asset.name}</p>
              <p className="text-sm text-gray-600">
                {asset.last_reviewed_at ? (
                  <>
                    마지막 검토:{" "}
                    {formatDistanceToNow(new Date(asset.last_reviewed_at), {
                      addSuffix: true,
                      locale: ko,
                    })}
                  </>
                ) : (
                  <span className="text-orange-600 font-medium">
                    미검토 자산
                  </span>
                )}
              </p>
              {asset.balance !== undefined && asset.balance > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  보유: {asset.balance.toLocaleString()}
                  {asset.price
                    ? ` × ${asset.price.toLocaleString()}원 = ${(
                        asset.balance * asset.price
                      ).toLocaleString()}원`
                    : ""}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2 ml-4">
              <Button
                size="sm"
                variant="default"
                onClick={() => router.push(`/assets/${asset.id}`)}
              >
                상세
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  markReviewedMutation.mutate(asset.id);
                }}
                disabled={markReviewedMutation.isPending}
              >
                완료
              </Button>
            </div>
          </div>
        ))}
      </div>

      {pendingAssets.length >= 5 && (
        <div className="mt-4 text-center">
          <Button
            variant="default"
            size="sm"
            onClick={() => router.push("/assets?review=pending")}
          >
            모든 검토 대기 자산 보기 →
          </Button>
        </div>
      )}
    </div>
  );
}
