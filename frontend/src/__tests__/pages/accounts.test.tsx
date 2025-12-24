import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AccountDetailPage from "@/app/(app)/accounts/[id]/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useParams: () => ({ id: "account-123" }),
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

describe("AccountDetailPage - useTransactionForm Hook Integration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.clear();

    // Mock API responses
    const { api } = require("@/lib/api");
    api.get.mockResolvedValue({
      data: {
        id: "account-123",
        name: "My Account",
        account_type: "bank_account",
        currency: "KRW",
        is_active: true,
        items: [],
        accounts: [],
        categories: [],
      },
    });
  });

  it("계좌 상세 페이지가 로드되고 빈 상태 문구를 표시해야 함", async () => {
    render(<AccountDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/거래 내역이 없습니다./i)).toBeInTheDocument();
    });

    const { api } = require("@/lib/api");
    expect(api.get).toHaveBeenCalled();
  });

  it("보유 자산 섹션도 빈 상태 문구를 표시해야 함", async () => {
    render(<AccountDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/자산이 없습니다./i)).toBeInTheDocument();
    });
  });
});
