/**
 * 자산 유형(AssetType) 테스트
 */

describe('AssetType', () => {
  // 백엔드와 동기화된 자산 유형 목록
  const validAssetTypes = [
    'stock',
    'crypto',
    'bond',
    'fund',
    'etf',
    'cash',
    'savings',
    'deposit',
  ];

  const assetTypeLabels: Record<string, string> = {
    stock: '주식',
    crypto: '가상화폐',
    bond: '채권',
    fund: '펀드',
    etf: 'ETF',
    cash: '현금',
    savings: '예금',
    deposit: '적금',
  };

  it('모든 자산 유형이 정의되어야 함', () => {
    expect(validAssetTypes).toHaveLength(8);
    expect(validAssetTypes).toContain('stock');
    expect(validAssetTypes).toContain('crypto');
    expect(validAssetTypes).toContain('bond');
    expect(validAssetTypes).toContain('fund');
    expect(validAssetTypes).toContain('etf');
    expect(validAssetTypes).toContain('cash');
    expect(validAssetTypes).toContain('savings');
    expect(validAssetTypes).toContain('deposit');
  });

  it('각 자산 유형에 한글 레이블이 있어야 함', () => {
    validAssetTypes.forEach((type) => {
      expect(assetTypeLabels[type]).toBeDefined();
      expect(assetTypeLabels[type]).toBeTruthy();
    });
  });

  it('예적금 자산 유형이 포함되어야 함', () => {
    expect(validAssetTypes).toContain('savings');
    expect(validAssetTypes).toContain('deposit');
    expect(assetTypeLabels['savings']).toBe('예금');
    expect(assetTypeLabels['deposit']).toBe('적금');
  });

  it('거래 가능/불가능 자산 유형 구분', () => {
    const tradableTypes = ['stock', 'crypto', 'bond', 'fund', 'etf'];
    const nonTradableTypes = ['cash', 'savings', 'deposit'];

    tradableTypes.forEach((type) => {
      expect(validAssetTypes).toContain(type);
    });

    nonTradableTypes.forEach((type) => {
      expect(validAssetTypes).toContain(type);
    });
  });

  it('자산 유형 레이블이 중복되지 않아야 함', () => {
    const labels = Object.values(assetTypeLabels);
    const uniqueLabels = new Set(labels);
    expect(labels.length).toBe(uniqueLabels.size);
  });
});
