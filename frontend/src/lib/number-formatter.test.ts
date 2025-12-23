import { formatNumber } from "@/lib/number-formatter";

// 테스트 케이스
const testCases = [
  { input: 369345.00000000000000, expected: "369,345" },
  { input: 1234.567, expected: "1,234.57" },
  { input: 0.001234, expected: "0.0012" },
  { input: 123.4567890123, expected: "123.46" },
  { input: 1000, expected: "1,000" },
  { input: 1000.5, expected: "1,000.5" },
  { input: 0.5, expected: "0.5" },
  { input: 0.05, expected: "0.05" },
  { input: 0.005, expected: "0.005" },
  { input: 0.0005, expected: "0.0005" },
  { input: 0.00005, expected: "0.00005" },
  { input: 0, expected: "0" },
  { input: null, expected: "0" },
  { input: undefined, expected: "0" },
];

console.log("=== Number Formatter Tests ===");
testCases.forEach(({ input, expected }) => {
  const result = formatNumber(input);
  const passed = result === expected;
  console.log(`${passed ? "✓" : "✗"} formatNumber(${input}) => "${result}" (expected: "${expected}")`);
});
