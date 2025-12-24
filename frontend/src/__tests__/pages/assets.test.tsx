import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AssetDetailPage from "@/app/(app)/assets/[id]/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useParams: () => ({ id: "asset-123" }),
}));

// Mock API
jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
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

describe("AssetDetailPage - useTransactionForm Hook Integration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.clear();

    // Mock API responses
    const { api } = require("@/lib/api");
    api.get.mockResolvedValue({
      data: {
        id: "asset-123",
        name: "BTC",
        asset_type: "crypto",
        currency: "BTC",
        is_active: true,
        quantity: 0.5,
        current_price: 50000,
        items: [],
        assets: [],
        categories: [],
      },
    });
  });

  it("자산 기본 정보를 불러와 렌더링해야 함", async () => {
    const { api } = require("@/lib/api");

    render(<AssetDetailPage params={{ id: "asset-123" }} />, { wrapper });

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/assets/asset-123");
    });
  });

  it("요약/거래/자산 목록 요청을 순차 호출해야 함", async () => {
    const { api } = require("@/lib/api");

    render(<AssetDetailPage params={{ id: "asset-123" }} />, { wrapper });

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/assets/asset-123/summary");
      expect(api.get).toHaveBeenCalledWith(`/transactions/assets/asset-123/transactions`, { params: { page: 1, size: 20 } });
      expect(api.get).toHaveBeenCalledWith("/assets");
    });
  });
});
