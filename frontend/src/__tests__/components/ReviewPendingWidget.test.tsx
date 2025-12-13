/**
 * ReviewPendingWidget 컴포넌트 테스트
 */
import { render, screen, waitFor } from '../test-utils';
import { ReviewPendingWidget } from '@/components/ReviewPendingWidget';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { api } from '@/lib/api';

// date-fns 모킹
jest.mock('date-fns', () => ({
  formatDistanceToNow: (date: Date) => '2개월 전',
}));

jest.mock('date-fns/locale', () => ({
  ko: {},
}));

// API 모킹
jest.mock('@/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// useRouter 모킹
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    refresh: jest.fn(),
  }),
}));

describe('ReviewPendingWidget', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    jest.clearAllMocks();
  });

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('로딩 중 상태를 표시해야 함', () => {
    mockedApi.get.mockImplementation(() => new Promise(() => {})); // 무한 pending

    renderWithQueryClient(<ReviewPendingWidget />);

    expect(screen.getByText('검토가 필요한 자산')).toBeInTheDocument();
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
  });

  it('검토 필요한 자산이 없을 때 메시지를 표시해야 함', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: [] });

    renderWithQueryClient(<ReviewPendingWidget />);

    await waitFor(() => {
      expect(screen.getByText(/검토가 필요한 자산이 없습니다/)).toBeInTheDocument();
    });
  });

  it('검토 필요한 자산 목록을 렌더링해야 함', async () => {
    const mockAssets = [
      {
        id: '1',
        name: '삼성전자',
        asset_type: 'stock',
        last_reviewed_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(), // 60일 전
        next_review_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30일 전 (기한 초과)
        review_interval_days: 30,
        balance: 10,
        price: 70000,
      },
      {
        id: '2',
        name: '비트코인',
        asset_type: 'crypto',
        last_reviewed_at: null,
        next_review_date: null,
        review_interval_days: 30,
        balance: 0.5,
        price: 50000000,
      },
    ];

    mockedApi.get.mockResolvedValueOnce({ data: mockAssets });

    renderWithQueryClient(<ReviewPendingWidget />);

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument();
      expect(screen.getByText('비트코인')).toBeInTheDocument();
    });
  });

  it('검토 완료 버튼 클릭 시 API를 호출해야 함', async () => {
    const mockAssets = [
      {
        id: '1',
        name: '삼성전자',
        asset_type: 'stock',
        last_reviewed_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
        next_review_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        review_interval_days: 30,
        balance: 10,
        price: 70000,
      },
    ];

    mockedApi.get.mockResolvedValueOnce({ data: mockAssets });
    mockedApi.post.mockResolvedValueOnce({ data: { ...mockAssets[0], last_reviewed_at: new Date().toISOString() } });

    renderWithQueryClient(<ReviewPendingWidget />);

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument();
    });

    const completeButton = screen.getByText('완료');
    completeButton.click();

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith('/assets/1/mark-reviewed');
    });
  });

  it('에러 발생 시 에러 메시지를 표시해야 함', async () => {
    mockedApi.get.mockRejectedValueOnce(new Error('Network error'));

    renderWithQueryClient(<ReviewPendingWidget />);

    await waitFor(() => {
      expect(screen.getByText('데이터를 불러오는데 실패했습니다.')).toBeInTheDocument();
    });
  });

  it('한 번도 검토하지 않은 자산은 "미검토 자산" 텍스트를 표시해야 함', async () => {
    const mockAssets = [
      {
        id: '1',
        name: '비트코인',
        asset_type: 'crypto',
        last_reviewed_at: null,
        next_review_date: null,
        review_interval_days: 30,
        balance: 0.5,
        price: 50000000,
      },
    ];

    mockedApi.get.mockResolvedValueOnce({ data: mockAssets });

    renderWithQueryClient(<ReviewPendingWidget />);

    await waitFor(() => {
      expect(screen.getByText('미검토 자산')).toBeInTheDocument();
    });
  });
});
