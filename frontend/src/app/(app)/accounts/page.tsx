"use client";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { Button } from "@/components/Button";
import { ColumnDef } from "@tanstack/react-table";

// Types aligned with backend schemas
export type AccountType =
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
  api_config?: any | null;
  daemon_config?: any | null;
  created_at: string;
  updated_at: string;
};

type AccountListResponse = { total: number; accounts: Account[] };

type ShareRole = "owner" | "editor" | "viewer";

type AccountShare = {
  id: string;
  account_id: string;
  user_id: string;
  role: ShareRole;
  can_read: boolean;
  can_write: boolean;
  can_delete: boolean;
  can_share: boolean;
  shared_at: string;
  shared_by?: string | null;
  created_at: string;
  updated_at: string;
};

type AccountShareListResponse = { total: number; shares: AccountShare[] };

const typeOptions: { value: AccountType; label: string }[] = [
  { value: "bank_account", label: "은행계좌" },
  { value: "securities", label: "증권" },
  { value: "cash", label: "현금" },
  { value: "debit_card", label: "체크카드" },
  { value: "credit_card", label: "신용카드" },
  { value: "savings", label: "저축" },
  { value: "deposit", label: "적금" },
  { value: "crypto_wallet", label: "암호화폐" },
];

export default function AccountsPage() {
  const qc = useQueryClient();

  // Filters
  const [typeFilter, setTypeFilter] = useState<AccountType | "">("");
  const [activeOnly, setActiveOnly] = useState<boolean | "">(true);
  const [qText, setQText] = useState("");

  const listQuery = useQuery<AccountListResponse>({
    queryKey: ["accounts", { typeFilter, activeOnly }],
    queryFn: async () => {
      const params: any = {};
      if (typeFilter) params.account_type = typeFilter;
      if (activeOnly !== "") params.is_active = activeOnly;
      const res = await api.get("/accounts", { params });
      return res.data as AccountListResponse;
    },
  });

  const accounts = useMemo(() => {
    const items = listQuery.data?.accounts ?? [];
    if (!qText) return items;
    const q = qText.toLowerCase();
    return items.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        (a.provider || "").toLowerCase().includes(q) ||
        (a.account_number || "").toLowerCase().includes(q)
    );
  }, [listQuery.data?.accounts, qText]);

  // Create / Update / Delete / Toggle
  const createMut = useMutation({
    mutationFn: async (payload: Partial<Account>) => (await api.post("/accounts", payload)).data as Account,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const updateMut = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<Account> }) =>
      (await api.patch(`/accounts/${id}`, payload)).data as Account,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/accounts/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });

  const toggleActiveMut = useMutation({
    mutationFn: async (id: string) => (await api.post(`/accounts/${id}/toggle-active`)).data as Account,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });

  // Create/edit modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Partial<Account> | null>(null);

  function startCreate() {
    setEditing({
      name: "",
      account_type: (typeFilter || "bank_account") as AccountType,
      provider: "",
      account_number: "",
      currency: "KRW",
      is_active: true,
      api_config: null,
      daemon_config: null,
    });
    setShowModal(true);
  }

  function startEdit(row: Account) {
    setEditing({ ...row });
    setShowModal(true);
  }

  function cancelEdit() {
    setEditing(null);
    setShowModal(false);
  }

  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editing) return;
    const form = e.currentTarget as HTMLFormElement;
    const fd = new FormData(form);
    const payload: any = {
      name: fd.get("name")?.toString().trim(),
      account_type: fd.get("account_type")?.toString() as AccountType,
      provider: fd.get("provider")?.toString().trim() || null,
      account_number: fd.get("account_number")?.toString().trim() || null,
      currency: fd.get("currency")?.toString().trim() || "KRW",
      is_active: fd.get("is_active") === "on",
    };
    const apiCfgText = fd.get("api_config")?.toString().trim();
    const daemonCfgText = fd.get("daemon_config")?.toString().trim();
    try {
      payload.api_config = apiCfgText ? JSON.parse(apiCfgText) : null;
    } catch {
      alert("api_config JSON 형식이 올바르지 않습니다.");
      return;
    }
    try {
      payload.daemon_config = daemonCfgText ? JSON.parse(daemonCfgText) : null;
    } catch {
      alert("daemon_config JSON 형식이 올바르지 않습니다.");
      return;
    }

    if (editing.id) {
      await updateMut.mutateAsync({ id: editing.id, payload });
    } else {
      await createMut.mutateAsync(payload);
    }
    setEditing(null);
    setShowModal(false);
  }

  // Shares modal state
  const [shareAccount, setShareAccount] = useState<Account | null>(null);
  const sharesQuery = useQuery<AccountShareListResponse>({
    queryKey: ["account-shares", shareAccount?.id],
    queryFn: async () => (await api.get(`/accounts/${shareAccount?.id}/shares`)).data,
    enabled: !!shareAccount?.id,
  });
  const addShareMut = useMutation({
    mutationFn: async ({ user_email, role }: { user_email: string; role: ShareRole }) =>
      (await api.post(`/accounts/${shareAccount?.id}/shares`, { user_email, role })).data as AccountShare,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["account-shares", shareAccount?.id] }),
  });
  const updateShareMut = useMutation({
    mutationFn: async ({ share_id, role }: { share_id: string; role: ShareRole }) =>
      (await api.patch(`/accounts/${shareAccount?.id}/shares/${share_id}`, { role })).data as AccountShare,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["account-shares", shareAccount?.id] }),
  });
  const deleteShareMut = useMutation({
    mutationFn: async (share_id: string) => (await api.delete(`/accounts/${shareAccount?.id}/shares/${share_id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["account-shares", shareAccount?.id] }),
  });

  const columns: ColumnDef<Account>[] = [
    { accessorKey: "name", header: "이름" },
    { accessorKey: "account_type", header: "유형", cell: ({ getValue }) => typeOptions.find((t) => t.value === getValue())?.label ?? String(getValue()) },
    { accessorKey: "provider", header: "기관", cell: ({ getValue }) => <span className="text-gh-fg-muted">{(getValue() as string) || "-"}</span> },
    { accessorKey: "account_number", header: "계좌번호", cell: ({ getValue }) => <span className="text-gh-fg-muted">{(getValue() as string) || "-"}</span> },
    { accessorKey: "currency", header: "통화" },
    {
      accessorKey: "is_active",
      header: "활성",
      cell: ({ row }) => (
        <Button
          size="sm"
          variant={row.original.is_active ? "primary" : "default"}
          onClick={() => toggleActiveMut.mutate(row.original.id)}
        >
          {row.original.is_active ? "활성" : "비활성"}
        </Button>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="space-x-2">
          <Button size="sm" variant="default" onClick={() => startEdit(row.original)}>편집</Button>
          <Button size="sm" variant="default" onClick={() => setShareAccount(row.original)}>공유</Button>
          <Button
            size="sm"
            variant="danger"
            onClick={() => {
              if (confirm("정말 삭제하시겠습니까? 관련 거래도 삭제됩니다.")) deleteMut.mutate(row.original.id);
            }}
          >
            삭제
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end pb-4">
        <div>
          <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">검색</label>
          <input value={qText} onChange={(e) => setQText(e.target.value)} className="border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" placeholder="이름/기관/번호" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">유형</label>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as any)} className="border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis">
            <option value="">전체</option>
            {typeOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2 pt-6">
          <input type="checkbox" checked={activeOnly === true} onChange={(e) => setActiveOnly(e.target.checked ? true : "")} className="rounded"/>
          <label className="text-sm text-gh-fg-default">활성만</label>
        </div>
        <div className="flex-1" />
        <Button variant="primary" onClick={startCreate}>새 계좌</Button>
      </div>

      {/* Table */}
      {listQuery.isLoading ? (
        <div>로딩 중...</div>
      ) : (
        <DataTable columns={columns} data={accounts} />
      )}

      {/* Create/Edit Modal */}
      {showModal && editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={cancelEdit} />
          <div className="relative z-10 w-full max-w-3xl rounded-md bg-gh-canvas-overlay border border-gh-border-default shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gh-border-default p-4 sticky top-0 bg-gh-canvas-overlay">
              <h2 className="text-lg font-semibold">{editing.id ? "계좌 수정" : "새 계좌"}</h2>
              <Button size="sm" variant="invisible" onClick={cancelEdit}>닫기</Button>
            </div>
            <form onSubmit={submitForm} className="p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">이름 *</label>
                  <input name="name" defaultValue={editing.name || ""} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" required />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">유형 *</label>
                  <select name="account_type" defaultValue={(editing.account_type || "bank_account") as string} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis">
                    {typeOptions.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">기관</label>
                  <input name="provider" defaultValue={editing.provider || ""} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">계좌번호</label>
                  <input name="account_number" defaultValue={editing.account_number || ""} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">통화</label>
                  <input name="currency" defaultValue={editing.currency || "KRW"} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" />
                </div>
                <div className="flex items-center gap-2 pt-7">
                  <input type="checkbox" name="is_active" defaultChecked={editing.is_active ?? true} className="rounded" />
                  <span className="text-sm text-gh-fg-default">활성</span>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">api_config (JSON)</label>
                  <textarea name="api_config" defaultValue={editing.api_config ? JSON.stringify(editing.api_config, null, 2) : ""} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 h-32 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">daemon_config (JSON)</label>
                  <textarea name="daemon_config" defaultValue={editing.daemon_config ? JSON.stringify(editing.daemon_config, null, 2) : ""} className="w-full border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-2 h-32 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" />
                </div>
              </div>
              <div className="flex gap-2 justify-end pt-2 border-t border-gh-border-default">
                <Button type="button" variant="default" onClick={cancelEdit}>취소</Button>
                <Button type="submit" variant="primary">{editing.id ? "수정" : "생성"}</Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Shares Modal */}
      {shareAccount && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShareAccount(null)} />
          <div className="relative z-10 w-full max-w-2xl rounded-md bg-gh-canvas-overlay border border-gh-border-default shadow-xl">
            <div className="flex items-center justify-between border-b border-gh-border-default p-4">
              <h2 className="text-lg font-semibold">공유 설정 — {shareAccount.name}</h2>
              <Button size="sm" variant="invisible" onClick={() => setShareAccount(null)}>닫기</Button>
            </div>
            <div className="p-4 space-y-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">이메일</label>
                  <input id="share_email" className="border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis" placeholder="user@example.com" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gh-fg-muted mb-1.5">역할</label>
                  <select id="share_role" className="border border-gh-border-default bg-gh-canvas-inset rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis">
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                  </select>
                </div>
                <Button
                  variant="primary"
                  onClick={() => {
                    const email = (document.getElementById("share_email") as HTMLInputElement)?.value.trim();
                    const role = (document.getElementById("share_role") as HTMLSelectElement)?.value as ShareRole;
                    if (!email) return alert("이메일을 입력하세요");
                    addShareMut.mutate({ user_email: email, role });
                  }}
                >
                  추가
                </Button>
              </div>

              {sharesQuery.isLoading ? (
                <div className="text-gh-fg-muted">공유 정보 로딩...</div>
              ) : (
                <div className="overflow-x-auto border border-gh-border-default rounded-md">
                  <table className="min-w-full">
                    <thead className="bg-gh-canvas-subtle">
                      <tr className="border-b border-gh-border-default">
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gh-fg-muted">공유 ID</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gh-fg-muted">역할</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gh-fg-muted"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {(sharesQuery.data?.shares || []).map((s) => (
                        <tr key={s.id} className="border-b border-gh-border-default">
                          <td className="px-3 py-3 text-sm">{s.id}</td>
                          <td className="px-3 py-3 text-sm">
                            {s.role === "owner" ? (
                              <span className="text-gh-fg-default font-medium">Owner</span>
                            ) : (
                              <select
                                defaultValue={s.role}
                                className="border border-gh-border-default bg-gh-canvas-inset rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-gh-accent-emphasis"
                                onChange={(e) => updateShareMut.mutate({ share_id: s.id, role: e.target.value as ShareRole })}
                              >
                                <option value="viewer">Viewer</option>
                                <option value="editor">Editor</option>
                              </select>
                            )}
                          </td>
                          <td className="px-3 py-3 text-sm">
                            {s.role === "owner" ? null : (
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => deleteShareMut.mutate(s.id)}
                              >
                                삭제
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
