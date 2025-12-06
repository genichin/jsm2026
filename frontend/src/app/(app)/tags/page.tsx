"use client";

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/Button";

// ==================== Types ====================

type TaggableType = "asset" | "account" | "transaction";

interface Tag {
  id: string;
  user_id: string;
  name: string;
  color: string | null;
  description: string | null;
  allowed_types: TaggableType[];
  created_at: string;
  updated_at: string;
}

interface TagWithStats extends Tag {
  asset_count: number;
  account_count: number;
  transaction_count: number;
  total_count: number;
}

interface TagListResponse {
  total: number;
  tags: Tag[] | TagWithStats[];
}

interface TagCreatePayload {
  name: string;
  color?: string | null;
  description?: string | null;
  allowed_types?: TaggableType[];
}

interface TagUpdatePayload {
  name?: string;
  color?: string | null;
  description?: string | null;
  allowed_types?: TaggableType[];
}

// ==================== Page Component ====================

export default function TagsPage() {
  const queryClient = useQueryClient();

  // State
  const [includeStats, setIncludeStats] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [deleteTagId, setDeleteTagId] = useState<string | null>(null);

  // Create/Edit form state
  const [formData, setFormData] = useState<TagCreatePayload>({
    name: "",
    color: null,
    description: null,
    allowed_types: ["asset", "account", "transaction"],
  });

  // ==================== Queries ====================

  const tagsQuery = useQuery({
    queryKey: ["tags", includeStats],
    queryFn: async (): Promise<TagListResponse> => {
      const { data } = await api.get(`/tags`, {
        params: { include_stats: includeStats },
      });
      return data;
    },
  });

  // ==================== Mutations ====================

  const createMut = useMutation({
    mutationFn: async (payload: TagCreatePayload) => {
      const { data } = await api.post(`/tags`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      setIsCreating(false);
      resetForm();
      alert("태그가 생성되었습니다.");
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || "태그 생성에 실패했습니다.");
    },
  });

  const updateMut = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: TagUpdatePayload;
    }) => {
      const { data } = await api.patch(`/tags/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      setEditingTagId(null);
      resetForm();
      alert("태그가 수정되었습니다.");
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || "태그 수정에 실패했습니다.");
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/tags/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      setDeleteTagId(null);
      alert("태그가 삭제되었습니다.");
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || "태그 삭제에 실패했습니다.");
    },
  });

  // ==================== Handlers ====================

  const resetForm = () => {
    setFormData({
      name: "",
      color: null,
      description: null,
      allowed_types: ["asset", "account", "transaction"],
    });
  };

  const handleCreate = () => {
    if (!formData.name.trim()) {
      alert("태그명을 입력하세요.");
      return;
    }
    createMut.mutate(formData);
  };

  const handleUpdate = () => {
    if (!editingTagId) return;
    if (!formData.name?.trim()) {
      alert("태그명을 입력하세요.");
      return;
    }
    updateMut.mutate({ id: editingTagId, payload: formData });
  };

  const startEdit = (tag: Tag) => {
    setEditingTagId(tag.id);
    setFormData({
      name: tag.name,
      color: tag.color,
      description: tag.description,
      allowed_types: tag.allowed_types,
    });
    setIsCreating(false);
  };

  const cancelEdit = () => {
    setEditingTagId(null);
    setIsCreating(false);
    resetForm();
  };

  const toggleAllowedType = (type: TaggableType) => {
    setFormData((prev) => {
      const current = prev.allowed_types || [];
      if (current.includes(type)) {
        return { ...prev, allowed_types: current.filter((t) => t !== type) };
      } else {
        return { ...prev, allowed_types: [...current, type] };
      }
    });
  };

  // ==================== Table Columns ====================

  const columns: ColumnDef<Tag | TagWithStats>[] = useMemo(
    () => [
      {
        accessorKey: "name",
        header: "태그명",
        cell: ({ row }) => {
          const tag = row.original;
          return (
            <div className="flex items-center gap-2">
              {tag.color && (
                <div
                  className="w-4 h-4 rounded border"
                  style={{ backgroundColor: tag.color }}
                />
              )}
              <span className="font-medium">{tag.name}</span>
            </div>
          );
        },
      },
      {
        accessorKey: "description",
        header: "설명",
        cell: ({ row }) => row.original.description || "-",
      },
      {
        accessorKey: "allowed_types",
        header: "사용 가능 타입",
        cell: ({ row }) => {
          const types = row.original.allowed_types;
          return (
            <div className="flex gap-1">
              {types.map((t) => (
                <span
                  key={t}
                  className="px-2 py-0.5 bg-gray-100 rounded text-xs"
                >
                  {t}
                </span>
              ))}
            </div>
          );
        },
      },
      ...(includeStats
        ? [
            {
              id: "stats",
              header: "사용 통계",
              cell: ({ row }: { row: any }) => {
                const tag = row.original as TagWithStats;
                return (
                  <div className="text-sm text-gh-fg-muted">
                    자산 {tag.asset_count || 0} / 계좌 {tag.account_count || 0}{" "}
                    / 거래 {tag.transaction_count || 0}
                  </div>
                );
              },
            },
          ]
        : []),
      {
        accessorKey: "created_at",
        header: "생성일",
        cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
      },
      {
        id: "actions",
        header: "액션",
        cell: ({ row }) => {
          const tag = row.original;
          return (
            <div className="flex gap-2">
              <Button
                variant="default"
                size="sm"
                onClick={() => startEdit(tag)}
              >
                수정
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setDeleteTagId(tag.id)}
              >
                삭제
              </Button>
            </div>
          );
        },
      },
    ],
    [includeStats]
  );

  // ==================== Render ====================

  const tags = tagsQuery.data?.tags || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeStats}
              onChange={(e) => setIncludeStats(e.target.checked)}
              className="rounded"
            />
            <span>사용 통계 표시</span>
          </label>
          <Button
            onClick={() => {
              setIsCreating(true);
              setEditingTagId(null);
              resetForm();
            }}
          >
            새 태그 추가
          </Button>
        </div>
      </div>

      {/* Create/Edit Form */}
      {(isCreating || editingTagId) && (
        <div className="mb-6 p-4 border border-gh-border-default rounded-lg bg-gh-canvas-inset">
          <h2 className="text-lg font-semibold mb-4">
            {isCreating ? "새 태그 추가" : "태그 수정"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-1">
                태그명 *
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="예: 중요, 월급, 투자..."
                className="w-full px-3 py-1.5 border-gh-border-default bg-gh-canvas-inset rounded-md focus:ring-2 focus:ring-gh-accent-emphasis"
              />
            </div>
            <div>
              <label htmlFor="color" className="block text-sm font-medium mb-1">
                색상 (선택)
              </label>
              <div className="flex gap-2">
                <input
                  id="color"
                  type="text"
                  value={formData.color || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      color: e.target.value || null,
                    })
                  }
                  placeholder="#FF5733"
                  pattern="^#[0-9A-Fa-f]{6}$"
                  className="flex-1 px-3 py-1.5 border-gh-border-default bg-gh-canvas-inset rounded-md focus:ring-2 focus:ring-gh-accent-emphasis"
                />
                <input
                  type="color"
                  value={formData.color || "#000000"}
                  onChange={(e) =>
                    setFormData({ ...formData, color: e.target.value })
                  }
                  className="w-20 h-10 border-gh-border-default rounded cursor-pointer"
                />
              </div>
            </div>
            <div className="md:col-span-2">
              <label htmlFor="description" className="block text-sm font-medium mb-1">
                설명 (선택)
              </label>
              <textarea
                id="description"
                value={formData.description || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    description: e.target.value || null,
                  })
                }
                placeholder="태그에 대한 설명을 입력하세요."
                rows={2}
                className="w-full px-3 py-1.5 border-gh-border-default bg-gh-canvas-inset rounded-md focus:ring-2 focus:ring-gh-accent-emphasis"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">
                사용 가능한 엔티티 타입
              </label>
              <div className="flex gap-4">
                {(["asset", "account", "transaction"] as TaggableType[]).map(
                  (type) => (
                    <label key={type} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.allowed_types?.includes(type)}
                        onChange={() => toggleAllowedType(type)}
                        className="rounded"
                      />
                      <span className="capitalize">{type}</span>
                    </label>
                  )
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <Button
              onClick={isCreating ? handleCreate : handleUpdate}
              disabled={createMut.isPending || updateMut.isPending}
            >
              {isCreating ? "추가" : "수정"}
            </Button>
            <Button
              variant="default"
              onClick={cancelEdit}
            >
              취소
            </Button>
          </div>
        </div>
      )}

      {/* Tags Table */}
      {tagsQuery.isLoading && <p>로딩 중...</p>}
      {tagsQuery.isError && (
        <p className="text-red-600">
          태그 목록을 불러오는데 실패했습니다.
        </p>
      )}
      {tagsQuery.isSuccess && (
        <div>
          <p className="text-sm text-gh-fg-muted mb-2">
            총 {tagsQuery.data.total}개의 태그
          </p>
          <DataTable columns={columns} data={tags} />
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteTagId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">태그 삭제</h3>
            <p className="text-gh-fg-muted mb-4">
              정말로 이 태그를 삭제하시겠습니까? 해당 태그가 연결된 모든
              엔티티에서 태그가 제거됩니다.
            </p>
            <div className="flex gap-2 justify-end">
              <Button
                variant="default"
                onClick={() => setDeleteTagId(null)}
              >
                취소
              </Button>
              <Button
                variant="danger"
                onClick={() => deleteTagId && deleteMut.mutate(deleteTagId)}
              >
                삭제
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
