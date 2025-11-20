"use client";
import { useMemo, useRef, useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { ColumnDef } from "@tanstack/react-table";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

type Category = { id: string; name: string; flow_type: FlowType; is_active: boolean; parent_id?: string | null };
type ListResponse = { items: Category[]; total: number; page: number; size: number; pages: number };
type FlowType = "expense" | "income" | "transfer" | "investment" | "neutral";

type AutoRule = {
  id: string;
  category_id: string;
  pattern_type: "exact" | "contains" | "regex";
  pattern_text: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

const flowOptions: { value: FlowType; label: string }[] = [
  { value: "expense", label: "지출" },
  { value: "income", label: "수입" },
  { value: "transfer", label: "이동" },
  { value: "investment", label: "투자" },
  { value: "neutral", label: "중립" },
];

const patternTypeOptions = [
  { value: "exact", label: "정확히 일치" },
  { value: "contains", label: "포함" },
  { value: "regex", label: "정규표현식" },
];

const formSchema = z.object({
  id: z.string().optional(),
  name: z.string().min(1, "이름을 입력하세요").max(50),
  flow_type: z.enum(["expense", "income", "transfer", "investment", "neutral"]).default("expense"),
  parent_id: z.string().optional().or(z.literal("")),
  is_active: z.boolean().default(true),
});
type FormValues = z.infer<typeof formSchema>;

const ruleFormSchema = z.object({
  id: z.string().optional(),
  category_id: z.string().min(1, "카테고리를 선택하세요"),
  pattern_type: z.enum(["exact", "contains", "regex"]).default("contains"),
  pattern_text: z.string().min(1, "패턴을 입력하세요"),
  priority: z.number().min(0).max(100000).default(100),
  is_active: z.boolean().default(true),
});
type RuleFormValues = z.infer<typeof ruleFormSchema>;

export default function CategoriesPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<"categories" | "rules">("categories");
  
  // Filters and pagination
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [qText, setQText] = useState("");
  const [flow, setFlow] = useState<FlowType | "">("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [order, setOrder] = useState<"asc" | "desc">("asc");

  // Auto Rules state
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [testDescription, setTestDescription] = useState("");

  const listQuery = useQuery<ListResponse>({
    queryKey: ["categories", { page, size, qText, flow, activeOnly, order }],
    queryFn: async () => {
      const params: any = { page, size, order };
      if (qText) params.q = qText;
      if (flow) params.flow_type = flow;
      if (activeOnly !== null) params.is_active = activeOnly;
      const res = await api.get("/categories", { params });
      return res.data as ListResponse;
    },
  });

  // Parent options (tree) based on selected flow filter
  const treeQuery = useQuery<{ id: string; name: string; parent_id?: string | null; children?: any[] }[]>({
    queryKey: ["categories-tree", { flow }],
    queryFn: async () => (await api.get("/categories/tree", { params: flow ? { flow_type: flow } : {} })).data,
  });

  const parentOptionsFlat = useMemo(() => {
    const out: { id: string; name: string }[] = [];
    const visit = (n: any, depth = 0) => {
      out.push({ id: n.id, name: `${"\u00A0".repeat(depth * 2)}${n.name}` });
      (n.children || []).forEach((c: any) => visit(c, depth + 1));
    };
    (treeQuery.data || []).forEach((r) => visit(r, 0));
    return out;
  }, [treeQuery.data]);

  // Build maps for quick hierarchy rendering
  const depthById = useMemo(() => {
    const map: Record<string, number> = {};
    const visit = (n: any, depth = 0) => {
      map[n.id] = depth;
      (n.children || []).forEach((c: any) => visit(c, depth + 1));
    };
    (treeQuery.data || []).forEach((r) => visit(r, 0));
    return map;
  }, [treeQuery.data]);

  const nameById = useMemo(() => {
    const map: Record<string, string> = {};
    const visit = (n: any) => {
      map[n.id] = n.name;
      (n.children || []).forEach((c: any) => visit(c));
    };
    (treeQuery.data || []).forEach((r) => visit(r));
    return map;
  }, [treeQuery.data]);

  // Create/Update form state
  const [editing, setEditing] = useState<FormValues | null>(null);
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "", flow_type: "expense", parent_id: "", is_active: true },
    values: editing ?? undefined,
  });

  const createMut = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = { name: values.name, flow_type: values.flow_type, is_active: values.is_active, parent_id: values.parent_id || null };
      return (await api.post("/categories", payload)).data as Category;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["categories"] }); qc.invalidateQueries({ queryKey: ["categories-tree"] }); reset(); setEditing(null); },
  });

  const updateMut = useMutation({
    mutationFn: async (values: FormValues) => {
      if (!values.id) throw new Error("id 없음");
      const payload: any = {};
      if (values.name !== undefined) payload.name = values.name;
      if (values.flow_type !== undefined) payload.flow_type = values.flow_type;
      if (values.is_active !== undefined) payload.is_active = values.is_active;
      if (values.parent_id !== undefined) payload.parent_id = values.parent_id === "" ? "" : values.parent_id;
      return (await api.put(`/categories/${values.id}`, payload)).data as Category;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["categories"] }); qc.invalidateQueries({ queryKey: ["categories-tree"] }); setEditing(null); },
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/categories/${id}`)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["categories"] }); qc.invalidateQueries({ queryKey: ["categories-tree"] }); },
  });

  const toggleActive = (row: Category) => {
    updateMut.mutate({ id: row.id, name: row.name, flow_type: row.flow_type, parent_id: row.parent_id || "", is_active: !row.is_active });
  };

  const startCreate = () => { setEditing({ name: "", flow_type: (flow || "expense") as FlowType, parent_id: "", is_active: true }); };
  const startEdit = (row: Category) => { setEditing({ id: row.id, name: row.name, flow_type: row.flow_type, parent_id: row.parent_id || "", is_active: row.is_active }); };
  const cancelEdit = () => { setEditing(null); reset(); };

  const onSubmit = (vals: FormValues) => {
    if (vals.id) updateMut.mutate(vals); else createMut.mutate(vals);
  };

  // Auto Rules State
  const [editingRule, setEditingRule] = useState<RuleFormValues | null>(null);

  // Rule form hook
  const ruleForm = useForm<RuleFormValues>({
    resolver: zodResolver(ruleFormSchema),
    defaultValues: { pattern_type: "contains", pattern_text: "", priority: 100, is_active: true },
  });
  const { register: registerRule, handleSubmit: handleRuleSubmit, reset: resetRuleForm, formState: { errors: ruleFormErrors } } = ruleForm;

  // Sync editingRule to form
  useEffect(() => {
    if (editingRule) {
      resetRuleForm(editingRule);
    } else {
      resetRuleForm({ pattern_type: "contains", pattern_text: "", priority: 100, is_active: true });
    }
  }, [editingRule, resetRuleForm]);

  const rulesQuery = useQuery<AutoRule[]>({
    queryKey: ["auto-rules"],
    queryFn: async () => (await api.get("/auto-rules")).data,
    enabled: activeTab === "rules",
  });

  const createRuleMut = useMutation({
    mutationFn: async (values: RuleFormValues) => (await api.post("/auto-rules", values)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["auto-rules"] });
      ruleForm.reset();
      setEditingRule(null);
    },
  });

  const updateRuleMut = useMutation({
    mutationFn: async (values: RuleFormValues) => {
      if (!values.id) throw new Error("id 없음");
      const { id, ...payload } = values;
      return (await api.put(`/auto-rules/${id}`, payload)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["auto-rules"] });
      setEditingRule(null);
    },
  });

  const deleteRuleMut = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/auto-rules/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["auto-rules"] }),
  });

  const testRuleMut = useMutation({
    mutationFn: async (payload: { description: string }) => (await api.post("/auto-rules/simulate", payload)).data,
  });

  const startEditRule = (rule: AutoRule) => {
    setEditingRule({
      id: rule.id,
      category_id: rule.category_id,
      pattern_type: rule.pattern_type,
      pattern_text: rule.pattern_text,
      priority: rule.priority,
      is_active: rule.is_active,
    });
  };

  const cancelRuleEdit = () => {
    setEditingRule(null);
    resetRuleForm();
    setShowRuleForm(false);
  };

  const onRuleSubmit = (vals: RuleFormValues) => {
    if (vals.id) updateRuleMut.mutate(vals);
    else createRuleMut.mutate(vals);
  };

  // Export / Import
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importing, setImporting] = useState(false);

  async function fetchAllCategories(): Promise<Category[]> {
    const out: Category[] = [];
    let p = 1;
    const size = 200;
    // fetch without filters to export 전체
    // loop until no more pages
    // protect from runaway: max 200 pages
    for (let i = 0; i < 200; i++) {
      const res = await api.get("/categories", { params: { page: p, size, order: "asc" } });
      const data = res.data as ListResponse;
      out.push(...(data.items || []));
      if (p >= (data.pages || 1)) break;
      p += 1;
    }
    return out;
  }

  async function onExportJSON() {
    try {
      const all = await fetchAllCategories();
      const allRules = (await api.get("/auto-rules")).data as AutoRule[];
      const payload = {
        type: "jsmoney.categories",
        version: 2,
        exported_at: new Date().toISOString(),
        count: all.length,
        categories: all,
        auto_rules: allRules,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      a.href = url;
      a.download = `categories-${ts}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Export 실패: " + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function onImportJSON(file: File) {
    try {
      setImporting(true);
      const text = await file.text();
      const data = JSON.parse(text);
      const list: Category[] = Array.isArray(data)
        ? data
        : Array.isArray(data?.categories)
        ? data.categories
        : [];
      const rules: AutoRule[] = Array.isArray(data?.auto_rules) ? data.auto_rules : [];
      if (!list.length) {
        alert("유효한 카테고리 목록이 아닙니다.");
        return;
      }
      const msg = rules.length > 0
        ? `총 ${list.length}개 카테고리와 ${rules.length}개 자동 규칙을 생성합니다. 중복이 발생할 수 있습니다. 진행할까요?`
        : `총 ${list.length}개 카테고리를 생성합니다. 중복이 발생할 수 있습니다. 진행할까요?`;
      if (!confirm(msg)) return;

      // Build quick children map by parent_id
      const byId = new Map<string, Category>();
      const childrenMap = new Map<string | null, Category[]>();
      for (const c of list) {
        if (c.id) byId.set(c.id, c);
        const pid = (c.parent_id as string | null) ?? null;
        const arr = childrenMap.get(pid) || [];
        arr.push(c);
        childrenMap.set(pid, arr);
      }

      // Topologically create: roots first, then children
      const idMap = new Map<string, string>(); // oldId -> newId
      const created = new Set<string>(); // key by reference index to avoid re-creating

      // We need a deterministic iteration: perform BFS from null parent
      const queue: (Category & { __old_parent?: string | null })[] = [];
      (childrenMap.get(null) || []).forEach((c) => queue.push({ ...c, __old_parent: null }));
      // Add orphans whose parent not present as additional roots
      for (const c of list) {
        const pid = (c.parent_id as string | null) ?? null;
        if (pid && !byId.has(pid)) queue.push({ ...c, __old_parent: pid });
      }

      // Helper to enqueue children when parent created
      function enqueueChildren(oldId: string) {
        const arr = childrenMap.get(oldId as any) || [];
        for (const ch of arr) queue.push({ ...ch, __old_parent: oldId });
      }

      // To avoid infinite loops, also fall back to N passes
      let safety = list.length * 3 + 50;
      while (queue.length && safety-- > 0) {
        const c = queue.shift()!;
        // If not root and parent not created yet, requeue
        const oldPid = (c.parent_id as string | null) ?? null;
        if (oldPid && !idMap.has(oldPid)) {
          queue.push(c);
          continue;
        }
        // Create category with mapped parent
        const payload = {
          name: c.name,
          flow_type: c.flow_type,
          is_active: c.is_active ?? true,
          parent_id: oldPid ? idMap.get(oldPid)! : null,
        };
        const createdCat = (await api.post("/categories", payload)).data as Category;
        if (c.id) idMap.set(c.id, createdCat.id);
        enqueueChildren(c.id as any);
      }

      // Import auto rules
      let rulesCreated = 0;
      if (rules.length > 0) {
        for (const r of rules) {
          const oldCatId = r.category_id;
          const newCatId = idMap.get(oldCatId);
          if (!newCatId) continue; // 카테고리가 import되지 않았으면 스킵
          try {
            await api.post("/auto-rules", {
              category_id: newCatId,
              pattern_type: r.pattern_type,
              pattern_text: r.pattern_text,
              priority: r.priority,
              is_active: r.is_active ?? true,
            });
            rulesCreated++;
          } catch (e) {
            console.error("규칙 생성 실패:", e);
          }
        }
      }

      qc.invalidateQueries({ queryKey: ["categories"] });
      qc.invalidateQueries({ queryKey: ["categories-tree"] });
      qc.invalidateQueries({ queryKey: ["auto-rules"] });
      const resultMsg = rulesCreated > 0
        ? `Import 완료 (카테고리: ${idMap.size}개, 자동 규칙: ${rulesCreated}개)`
        : `Import 완료 (카테고리: ${idMap.size}개)`;
      alert(resultMsg);
    } catch (e) {
      alert("Import 실패: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const items: Category[] = listQuery.data?.items ?? [];
  const columns: ColumnDef<Category>[] = [
    {
      accessorKey: "name",
      header: "이름",
      cell: ({ row }) => {
        const d = depthById[row.original.id] ?? 0;
        return (
          <div className="flex items-center" style={{ paddingLeft: d * 16 }}>
            {d > 0 && <span className="mr-1 text-slate-400">└─</span>}
            <span>{row.original.name}</span>
          </div>
        );
      },
    },
    { accessorKey: "flow_type", header: "흐름", cell: ({ getValue }) => flowOptions.find((o) => o.value === getValue())?.label ?? String(getValue()) },
    {
      id: "parent",
      header: "상위",
      cell: ({ row }) => <span className="text-slate-500 text-sm">{row.original.parent_id ? (nameById[row.original.parent_id] || "-") : "(루트)"}</span>,
    },
    { accessorKey: "is_active", header: "활성", cell: ({ row }) => (
      <button onClick={() => toggleActive(row.original)} className={`px-2 py-1 rounded text-xs ${row.original.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
        {row.original.is_active ? "활성" : "비활성"}
      </button>
    ) },
    { id: "actions", header: "", cell: ({ row }) => (
      <div className="space-x-2">
        <button className="px-2 py-1 text-xs rounded bg-slate-100" onClick={() => startEdit(row.original)}>편집</button>
        <button className="px-2 py-1 text-xs rounded bg-rose-100 text-rose-700" onClick={() => { if (confirm("삭제하시겠습니까?")) deleteMut.mutate(row.original.id); }}>삭제</button>
      </div>
    ) },
  ];

  // Auto Rules Columns
  const ruleColumns: ColumnDef<AutoRule>[] = [
    { accessorKey: "priority", header: "우선순위", cell: ({ getValue }) => <span className="font-mono text-sm">{getValue() as number}</span> },
    {
      accessorKey: "pattern_type",
      header: "타입",
      cell: ({ getValue }) => patternTypeOptions.find((o) => o.value === getValue())?.label ?? String(getValue()),
    },
    { accessorKey: "pattern_text", header: "패턴", cell: ({ getValue }) => <span className="font-mono text-sm">{getValue() as string}</span> },
    {
      accessorKey: "category_id",
      header: "카테고리",
      cell: ({ row }) => <span className="text-slate-700">{nameById[row.original.category_id] || "-"}</span>,
    },
    {
      accessorKey: "is_active",
      header: "활성",
      cell: ({ row }) => (
        <span className={`px-2 py-1 rounded text-xs ${row.original.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
          {row.original.is_active ? "활성" : "비활성"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="space-x-2">
          <button className="px-2 py-1 text-xs rounded bg-slate-100" onClick={() => startEditRule(row.original)}>
            편집
          </button>
          <button
            className="px-2 py-1 text-xs rounded bg-rose-100 text-rose-700"
            onClick={() => {
              if (confirm("이 규칙을 삭제하시겠습니까?")) deleteRuleMut.mutate(row.original.id);
            }}
          >
            삭제
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header with Export/Import */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">카테고리 관리</h1>
        <div className="flex gap-2">
          <button onClick={onExportJSON} className="px-3 py-2 rounded bg-slate-200 text-sm">
            Export JSON
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onImportJSON(f);
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="px-3 py-2 rounded bg-slate-200 text-sm disabled:opacity-50"
          >
            {importing ? "Import 중..." : "Import JSON"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab("categories")}
          className={`px-4 py-2 font-medium ${
            activeTab === "categories"
              ? "border-b-2 border-emerald-600 text-emerald-600"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          카테고리
        </button>
        <button
          onClick={() => setActiveTab("rules")}
          className={`px-4 py-2 font-medium ${
            activeTab === "rules"
              ? "border-b-2 border-emerald-600 text-emerald-600"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          자동 규칙
        </button>
      </div>

      {/* Categories Tab */}
      {activeTab === "categories" && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-end">
        <div>
          <label className="block text-xs text-slate-600 mb-1">검색</label>
          <input value={qText} onChange={(e) => setQText(e.target.value)} className="border rounded px-2 py-1" placeholder="이름 검색" />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">흐름</label>
          <select value={flow} onChange={(e) => { setFlow(e.target.value as any); setPage(1); }} className="border rounded px-2 py-1">
            <option value="">전체</option>
            {flowOptions.map((o) => (<option key={o.value} value={o.value}>{o.label}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">활성만</label>
          <input type="checkbox" checked={activeOnly} onChange={(e) => { setActiveOnly(e.target.checked); setPage(1); }} />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">정렬</label>
          <select value={order} onChange={(e) => setOrder(e.target.value as any)} className="border rounded px-2 py-1">
            <option value="asc">이름 오름차순</option>
            <option value="desc">이름 내림차순</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">페이지 크기</label>
          <select value={size} onChange={(e) => { setSize(Number(e.target.value)); setPage(1); }} className="border rounded px-2 py-1">
            {[10,20,50,100].map((n) => (<option key={n} value={n}>{n}</option>))}
          </select>
        </div>
        <button onClick={() => listQuery.refetch()} className="px-3 py-2 rounded bg-slate-800 text-white">검색</button>
        <div className="flex-1" />
        <button onClick={startCreate} className="px-3 py-2 rounded bg-emerald-600 text-white">새 카테고리</button>
      </div>

      {/* Inline Form */}
      {editing && (
        <form onSubmit={handleSubmit(onSubmit)} className="border rounded p-3 space-y-2 bg-slate-50">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-slate-600 mb-1">이름</label>
              <input {...register("name")} className="w-full border rounded px-2 py-1" />
              {errors.name && <p className="text-xs text-rose-600 mt-1">{errors.name.message}</p>}
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">흐름</label>
              <select {...register("flow_type")} className="w-full border rounded px-2 py-1">
                {flowOptions.map((o) => (<option key={o.value} value={o.value}>{o.label}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">상위 카테고리</label>
              <select {...register("parent_id")} className="w-full border rounded px-2 py-1">
                <option value="">(루트)</option>
                {parentOptionsFlat.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
              </select>
            </div>
            <div className="flex items-center gap-2 pt-5">
              <input type="checkbox" {...register("is_active")} />
              <span>활성</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={isSubmitting || createMut.isPending || updateMut.isPending} className="px-3 py-2 rounded bg-slate-800 text-white">{editing.id ? "수정" : "생성"}</button>
            <button type="button" onClick={cancelEdit} className="px-3 py-2 rounded bg-slate-200">취소</button>
          </div>
        </form>
      )}

      {/* Table */}
      {listQuery.isLoading ? (
        <div>로딩 중...</div>
      ) : (
        <DataTable columns={columns} data={items} />
      )}

      {/* Pagination */}
      <div className="flex items-center gap-3">
        <button disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="px-3 py-1 rounded bg-slate-100">이전</button>
        <span className="text-sm text-slate-600">{listQuery.data?.page ?? page} / {listQuery.data?.pages ?? 1} (총 {listQuery.data?.total ?? 0})</span>
        <button disabled={(listQuery.data?.page ?? 1) >= (listQuery.data?.pages ?? 1)} onClick={() => setPage((p) => p + 1)} className="px-3 py-1 rounded bg-slate-100">다음</button>
      </div>
        </>
      )}

      {/* Auto Rules Tab */}
      {activeTab === "rules" && (
        <>
          {/* Rule Form */}
          {(editingRule || showRuleForm) && (
            <form onSubmit={handleRuleSubmit(onRuleSubmit)} className="p-4 border rounded space-y-3 bg-slate-50">
              <h3 className="font-semibold">{editingRule ? "규칙 수정" : "규칙 추가"}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">카테고리</label>
                  <select {...registerRule("category_id")} className="w-full px-3 py-2 border rounded">
                    <option value="">선택</option>
                    {parentOptionsFlat.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  {ruleFormErrors.category_id && <span className="text-xs text-rose-600">{ruleFormErrors.category_id.message}</span>}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">패턴 타입</label>
                  <select {...registerRule("pattern_type")} className="w-full px-3 py-2 border rounded">
                    {patternTypeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  {ruleFormErrors.pattern_type && <span className="text-xs text-rose-600">{ruleFormErrors.pattern_type.message}</span>}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">패턴 텍스트</label>
                  <input {...registerRule("pattern_text")} className="w-full px-3 py-2 border rounded" placeholder="예: 스타벅스" />
                  {ruleFormErrors.pattern_text && <span className="text-xs text-rose-600">{ruleFormErrors.pattern_text.message}</span>}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">우선순위 (0-100000)</label>
                  <input type="number" {...registerRule("priority", { valueAsNumber: true })} className="w-full px-3 py-2 border rounded" />
                  {ruleFormErrors.priority && <span className="text-xs text-rose-600">{ruleFormErrors.priority.message}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" {...registerRule("is_active")} />
                  <span className="text-sm">활성</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button type="submit" disabled={createRuleMut.isPending || updateRuleMut.isPending} className="px-3 py-2 rounded bg-slate-800 text-white">
                  {editingRule ? "수정" : "생성"}
                </button>
                <button type="button" onClick={cancelRuleEdit} className="px-3 py-2 rounded bg-slate-200">취소</button>
              </div>
            </form>
          )}

          {/* Add Rule Button */}
          {!editingRule && !showRuleForm && (
            <button onClick={() => setShowRuleForm(true)} className="px-4 py-2 rounded bg-emerald-600 text-white">
              + 규칙 추가
            </button>
          )}

          {/* Rules Table */}
          {rulesQuery.isLoading ? (
            <div>로딩 중...</div>
          ) : (
            <DataTable columns={ruleColumns} data={rulesQuery.data ?? []} />
          )}

          {/* Test Simulation */}
          <div className="p-4 border rounded space-y-3 bg-blue-50">
            <h3 className="font-semibold">테스트 시뮬레이션</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={testDescription}
                onChange={(e) => setTestDescription(e.target.value)}
                placeholder="거래 설명을 입력하세요 (예: 스타벅스 강남점)"
                className="flex-1 px-3 py-2 border rounded"
              />
              <button
                onClick={() => testRuleMut.mutate({ description: testDescription })}
                disabled={testRuleMut.isPending || !testDescription.trim()}
                className="px-4 py-2 rounded bg-blue-600 text-white"
              >
                테스트
              </button>
            </div>
            {testRuleMut.data && (
              <div className="p-3 bg-white rounded">
                {testRuleMut.data.matched ? (
                  <div className="text-sm">
                    <span className="font-medium text-emerald-600">✓ 매칭됨</span>
                    <div className="mt-1">카테고리: <span className="font-mono">{nameById[testRuleMut.data.category_id!] || testRuleMut.data.category_id}</span></div>
                    <div className="text-xs text-slate-600 mt-1">규칙 ID: {testRuleMut.data.rule_id}</div>
                  </div>
                ) : (
                  <span className="text-sm text-slate-600">매칭되는 규칙이 없습니다.</span>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
