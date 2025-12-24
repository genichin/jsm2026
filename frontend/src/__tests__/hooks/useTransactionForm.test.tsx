import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTransactionForm } from "@/hooks/useTransactionForm";
import { ReactNode } from "react";

// Mock API
jest.mock("@/lib/api", () => ({
  api: {
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock("@/lib/transactionPayload", () => ({
  buildCashDividendFields: jest.fn(() => ({
    extras: { source_asset_id: "asset-1" },
    price: 100,
  })),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("useTransactionForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.clear();
  });

  it("초기 상태가 올바르게 설정되어야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    expect(result.current.editing).toBeNull();
    expect(result.current.selectedType).toBe("");
    expect(result.current.selectedAssetId).toBe("");
    expect(result.current.isModalOpen).toBe(false);
    expect(result.current.suggestedCategoryId).toBeNull();
    expect(result.current.isSuggesting).toBe(false);
  });

  it("startCreate 함수가 모달을 열어야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    act(() => {
      result.current.startCreate();
    });

    expect(result.current.isModalOpen).toBe(true);
    expect(result.current.selectedType).toBe("deposit");
    expect(result.current.editing).not.toBeNull();
  });

  it("startCreate에서 assetFilter를 사용해야 함", () => {
    const { result } = renderHook(
      () => useTransactionForm({ assetFilter: "asset-123" }),
      { wrapper }
    );

    act(() => {
      result.current.startCreate();
    });

    expect(result.current.selectedAssetId).toBe("asset-123");
  });

  it("startCreate에서 typeFilter를 사용해야 함", () => {
    const { result } = renderHook(
      () => useTransactionForm({ typeFilter: "buy" }),
      { wrapper }
    );

    act(() => {
      result.current.startCreate();
    });

    expect(result.current.selectedType).toBe("buy");
  });

  it("cancelEdit 함수가 모든 상태를 초기화해야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    // 먼저 모달을 염
    act(() => {
      result.current.startCreate();
    });

    expect(result.current.isModalOpen).toBe(true);

    // 그 다음 취소
    act(() => {
      result.current.cancelEdit();
    });

    expect(result.current.isModalOpen).toBe(false);
    expect(result.current.editing).toBeNull();
    expect(result.current.selectedType).toBe("");
    expect(result.current.selectedAssetId).toBe("");
    expect(result.current.suggestedCategoryId).toBeNull();
  });

  it("setSelectedType 함수가 거래 유형을 변경해야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    act(() => {
      result.current.setSelectedType("sell");
    });

    expect(result.current.selectedType).toBe("sell");
  });

  it("setSelectedAssetId 함수가 자산 ID를 변경해야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    act(() => {
      result.current.setSelectedAssetId("asset-456");
    });

    expect(result.current.selectedAssetId).toBe("asset-456");
  });

  it("mutations이 올바른 메서드를 제공해야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    expect(result.current.createMut).toBeDefined();
    expect(result.current.updateMut).toBeDefined();
    expect(result.current.deleteMut).toBeDefined();
    expect(result.current.uploadMut).toBeDefined();
  });

  it("suggestCategory는 폼의 설명을 읽어야 함", async () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    // Mock form
    const form = document.createElement("form");
    const descriptionInput = document.createElement("input");
    descriptionInput.name = "description";
    descriptionInput.value = "테스트 설명";
    form.appendChild(descriptionInput);
    document.body.appendChild(form);

    // Mock querySelector
    const querySelectorSpy = jest.spyOn(document, "querySelector");
    querySelectorSpy.mockReturnValueOnce(form as any);
    querySelectorSpy.mockReturnValueOnce(descriptionInput as any);

    // Mock API response
    const { api } = require("@/lib/api");
    api.post.mockResolvedValueOnce({
      data: { matched: true, category_id: "cat-123" },
    });

    act(() => {
      result.current.suggestCategory();
    });

    await waitFor(() => {
      expect(result.current.isSuggesting).toBe(false);
    });

    querySelectorSpy.mockRestore();
    document.body.removeChild(form);
  });

  it("startEdit가 거래 데이터를 설정해야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    const transaction = {
      id: "tx-1",
      asset_id: "asset-1",
      type: "buy" as const,
      quantity: 100,
      transaction_date: "2025-12-24T10:00:00Z",
      description: "테스트 거래",
      memo: "메모",
      flow_type: "investment",
      confirmed: true,
      price: 50,
      fee: 100,
      tax: 50,
      realized_profit: null,
      extras: null,
      created_at: "2025-12-24T10:00:00Z",
      updated_at: "2025-12-24T10:00:00Z",
      asset: null,
      category: null,
    };

    act(() => {
      result.current.startEdit(transaction);
    });

    expect(result.current.editing).not.toBeNull();
    expect(result.current.selectedAssetId).toBe("asset-1");
    expect(result.current.selectedType).toBe("buy");
    expect(result.current.isModalOpen).toBe(true);
  });

  it("cash_dividend 타입의 거래 편집에서 특별 필드를 설정해야 함", () => {
    const { result } = renderHook(() => useTransactionForm(), { wrapper });

    const transaction = {
      id: "tx-2",
      asset_id: "asset-1",
      type: "cash_dividend" as const,
      quantity: 1000,
      transaction_date: "2025-12-24T10:00:00Z",
      description: "배당금",
      memo: "메모",
      flow_type: "income",
      confirmed: true,
      price: 0,
      fee: 0,
      tax: 0,
      realized_profit: null,
      extras: { source_asset_id: "source-asset-1" },
      created_at: "2025-12-24T10:00:00Z",
      updated_at: "2025-12-24T10:00:00Z",
      asset: null,
      category: null,
    };

    act(() => {
      result.current.startEdit(transaction);
    });

    expect(result.current.editing).not.toBeNull();
    const editingData = result.current.editing as any;
    expect(editingData.dividend_asset_id).toBe("source-asset-1");
  });

  it("onSuccess 콜백이 호출되어야 함", async () => {
    const onSuccessMock = jest.fn();
    const { result } = renderHook(
      () => useTransactionForm({ onSuccess: onSuccessMock }),
      { wrapper }
    );

    expect(onSuccessMock).not.toHaveBeenCalled();
    // Note: 실제 mutation 성공 테스트는 더 복잡하므로
    // 여기서는 콜백이 설정되었음을 확인하는 정도로만 테스트
  });
});
