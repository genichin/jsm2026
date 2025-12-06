/**
 * 문자열 유틸리티 테스트
 */

// 간단한 유틸 함수 예제
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
  }).format(value)
}

describe('formatCurrency', () => {
  it('숫자를 원화 형식으로 포맷해야 함', () => {
    expect(formatCurrency(1000)).toBe('₩1,000')
  })

  it('소수점을 처리해야 함', () => {
    expect(formatCurrency(1000.5)).toContain('₩')
  })

  it('음수를 처리해야 함', () => {
    const result = formatCurrency(-1000)
    expect(result).toContain('₩')
    expect(result).toContain('-')
  })

  it('0을 처리해야 함', () => {
    expect(formatCurrency(0)).toContain('₩')
  })
})
