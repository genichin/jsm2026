import { buildCashDividendFields } from "@/lib/transactionPayload";

describe("buildCashDividendFields", () => {
  it("배당 자산 ID가 없으면 에러를 발생시켜야 함", () => {
    const formData = new FormData();
    // dividend_asset_id를 설정하지 않음

    expect(() => buildCashDividendFields(formData)).toThrow();
  });

  it("배당 자산 ID가 있으면 source_asset_id를 포함한 extras를 반환해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    formData.append("price", "5000");
    formData.append("fee", "100");
    formData.append("tax", "500");
    formData.append("quantity", "10");

    const result = buildCashDividendFields(formData);

    expect(result.extras).toBeDefined();
    expect(result.extras.source_asset_id).toBe("asset-123");
  });

  it("가격, 수수료, 세금을 올바르게 파싱해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    formData.append("price", "5000");
    formData.append("fee", "100");
    formData.append("tax", "500");
    formData.append("quantity", "10");

    const result = buildCashDividendFields(formData);

    expect(result.price).toBe(5000);
    expect(result.fee).toBe(100);
    expect(result.tax).toBe(500);
    expect(result.quantity).toBe(10);
  });

  it("선택적 필드가 없으면 undefined를 반환해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    // price, fee, tax, quantity를 설정하지 않음

    const result = buildCashDividendFields(formData);

    expect(result.extras).toBeDefined();
    expect(result.extras.source_asset_id).toBe("asset-123");
    expect(result.price).toBeUndefined();
    expect(result.fee).toBeUndefined();
    expect(result.tax).toBeUndefined();
    expect(result.quantity).toBe(0);
  });

  it("빈 문자열은 undefined로 처리해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    formData.append("price", "");
    formData.append("fee", "");
    formData.append("tax", "");
    formData.append("quantity", "");

    const result = buildCashDividendFields(formData);

    expect(result.extras.source_asset_id).toBe("asset-123");
    expect(result.price).toBeUndefined();
    expect(result.fee).toBeUndefined();
    expect(result.tax).toBeUndefined();
    expect(result.quantity).toBe(0);
  });

  it("0 값도 올바르게 처리해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    formData.append("price", "0");
    formData.append("fee", "0");
    formData.append("tax", "0");
    formData.append("quantity", "0");

    const result = buildCashDividendFields(formData);

    expect(result.price).toBeUndefined();
    expect(result.fee).toBeUndefined();
    expect(result.tax).toBeUndefined();
    expect(result.quantity).toBe(0);
  });

  it("음수 값도 올바르게 처리해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    formData.append("price", "-100");
    formData.append("quantity", "-5");

    const result = buildCashDividendFields(formData);

    expect(result.price).toBeUndefined();
    expect(result.quantity).toBe(-5);
  });

  it("소수점 값도 올바르게 처리해야 함", () => {
    const formData = new FormData();
    formData.append("dividend_asset_id", "asset-123");
    formData.append("price", "5000.5");
    formData.append("fee", "99.99");
    formData.append("quantity", "10.5");

    const result = buildCashDividendFields(formData);

    expect(result.price).toBe(5000.5);
    expect(result.fee).toBe(99.99);
    expect(result.quantity).toBe(10.5);
  });
});
