/**
 * 숫자를 포맷팅합니다.
 * - 정수는 쉼표만 추가 (예: 369,345)
 * - 소수는 전체 숫자 크기에 비례해서 소수점 자리 결정
 *   - 1 이상: 최대 2자리 (예: 1,234.57)
 *   - 0.1~1: 2자리 (예: 0.57)
 *   - 0.01~0.1: 3자리 (예: 0.057)
 *   - 0.001~0.01: 4자리 (예: 0.0057)
 *   - 0.0001 이하: 8자리 (예: 0.00000123)
 */
export function formatNumber(num: number | string | null | undefined): string {
  if (num === null || num === undefined || num === "") {
    return "0";
  }

  const value = typeof num === "string" ? parseFloat(num) : num;

  if (isNaN(value)) {
    return "0";
  }

  // 절대값으로 자리 결정
  const absValue = Math.abs(value);

  let decimals = 0;
  if (absValue >= 1) {
    // 1 이상: 최대 2자리, 하지만 끝의 0은 제거
    decimals = 2;
  } else if (absValue >= 0.1) {
    decimals = 2;
  } else if (absValue >= 0.01) {
    decimals = 3;
  } else if (absValue >= 0.001) {
    decimals = 4;
  } else if (absValue >= 0.0001) {
    decimals = 5;
  } else if (absValue > 0) {
    decimals = 8;
  }

  // toFixed로 반올림 후, 끝의 0 제거
  const formatted = value.toFixed(decimals);
  const withoutTrailingZeros = formatted.replace(/\.?0+$/, "");
  
  // 정수 부분에 쉼표 추가
  const parts = withoutTrailingZeros.split(".");
  const integerPart = Number(parts[0]);
  if (isNaN(integerPart)) {
    return "0";
  }
  parts[0] = integerPart.toLocaleString();
  
  return parts.join(".");
}

/**
 * 통화 포맷팅 (KRW 기본값)
 */
export function formatCurrency(
  num: number | string | null | undefined,
  currency: string = "KRW"
): string {
  const formatted = formatNumber(num);
  
  // 통화별 심볼 매핑
  const currencySymbols: Record<string, string> = {
    KRW: '원',
    USD: '$',
    EUR: '€',
    JPY: '¥',
    CNY: '¥',
  };
  
  const symbol = currencySymbols[currency] || currency;
  
  // USD, EUR 등은 앞에 표시, KRW, JPY 등은 뒤에 표시
  const prefixCurrencies = ['USD', 'EUR'];
  if (prefixCurrencies.includes(currency)) {
    return `${symbol}${formatted}`;
  }
  
  return `${formatted}${symbol}`;
}

/**
 * 백분율 포맷팅
 */
export function formatPercent(
  num: number | string | null | undefined,
  decimals: number = 2
): string {
  if (num === null || num === undefined || num === "") {
    return "0%";
  }

  const value = typeof num === "string" ? parseFloat(num) : num;

  if (isNaN(value)) {
    return "0%";
  }

  return `${value.toFixed(decimals)}%`;
}
