/**
 * 컴포넌트 렌더링 테스트 예제
 */
import { render, screen } from '../test-utils'

// 간단한 컴포넌트 예제
const Button = ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
  <button onClick={onClick}>{children}</button>
)

describe('Button 컴포넌트', () => {
  it('텍스트를 렌더링해야 함', () => {
    render(<Button>클릭하세요</Button>)
    expect(screen.getByText('클릭하세요')).toBeInTheDocument()
  })

  it('클릭 이벤트를 처리해야 함', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>클릭</Button>)
    
    const button = screen.getByText('클릭')
    button.click()
    
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('버튼 엘리먼트여야 함', () => {
    render(<Button>테스트</Button>)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })
})
