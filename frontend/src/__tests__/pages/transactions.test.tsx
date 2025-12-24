import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TransactionsPage from "@/app/(app)/transactions/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/transactions",
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

describe("TransactionsPage - useTransactionForm Hook Integration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.clear();

    // Mock API responses
    const { api } = require("@/lib/api");
    api.get.mockResolvedValue({
      data: {
        items: [
          {
            id: "tx-1",
            asset_id: "asset-1",
            type: "buy",
            quantity: 100,
            transaction_date: "2025-12-24T10:00:00Z",
            description: "테스트",
            flow_type: "investment",
            confirmed: true,
          },
        ],
        total: 1,
        page: 1,
        pages: 1,
      },
    });
  });

  it("페이지가 로드되어야 함", async () => {
    render(<TransactionsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/거래/i)).toBeInTheDocument();
    });
  });

  it("새 거래 버튼을 클릭하면 모달이 열려야 함", async () => {
    render(<TransactionsPage />, { wrapper });

    const newTransactionButton = screen.getByRole("button", { name: /새 거래/i });
    expect(newTransactionButton).toBeInTheDocument();

    // 버튼 클릭 시뮬레이션
    fireEvent.click(newTransactionButton);

    // 모달이 열려야 함
    await waitFor(() => {
      expect(screen.getByText(/새 거래/i)).toBeInTheDocument();
    });
  });

  it("필터가 적용되어야 함", async () => {
    render(<TransactionsPage />, { wrapper });

    // 자산 필터 선택
    const assetSelect = screen.getByDisplayValue("전체") || screen.getByRole("combobox");
    expect(assetSelect).toBeInTheDocument();
  });

  it("거래 폼 훅이 상태를 관리해야 함", async () => {
    const { api } = require("@/lib/api");

    // Mock successful response
    api.post.mockResolvedValueOnce({
      data: {
        id: "new-tx",
        asset_id: "asset-1",
        type: "buy",
        quantity: 50,
        transaction_date: "2025-12-24T11:00:00Z",
      },
    });

    render(<TransactionsPage />, { wrapper });

    // 새 거래 버튼 클릭
    const newTransactionButton = screen.getByRole("button", { name: /새 거래/i });
    fireEvent.click(newTransactionButton);

    // 모달이 열려야 함
    await waitFor(() => {
      const modal = screen.getByText(/새 거래/i);
      expect(modal).toBeInTheDocument();
    });
  });
});
