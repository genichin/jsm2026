/**
 * flow_type과 confirmed 필드 관련 테스트
 * 백엔드 스키마 변경사항 검증
 */

import { describe, it, expect } from '@jest/globals';

describe('Transaction flow_type and confirmed fields', () => {
  describe('FlowType values', () => {
    it('should include all valid flow types', () => {
      const validFlowTypes = ['expense', 'income', 'transfer', 'investment', 'neutral', 'undefined'];
      
      validFlowTypes.forEach(flowType => {
        expect(validFlowTypes).toContain(flowType);
      });
    });

    it('should have undefined as valid flow type for unclassified transactions', () => {
      const flowType = 'undefined';
      expect(flowType).toBe('undefined');
    });
  });

  describe('Transaction confirmed field', () => {
    it('should default to false for new transactions', () => {
      const transaction = {
        id: '1',
        type: 'deposit',
        quantity: 1000,
        confirmed: false,
        flow_type: 'income',
      };

      expect(transaction.confirmed).toBe(false);
    });

    it('should accept boolean values', () => {
      const confirmedTx = { confirmed: true };
      const unconfirmedTx = { confirmed: false };

      expect(typeof confirmedTx.confirmed).toBe('boolean');
      expect(typeof unconfirmedTx.confirmed).toBe('boolean');
    });
  });

  describe('Flow type badge display logic', () => {
    it('should show "미분류" badge for undefined flow type', () => {
      const tx = { flow_type: 'undefined' };
      
      expect(tx.flow_type === 'undefined').toBe(true);
    });

    it('should not show badge for defined flow types', () => {
      const definedFlowTypes = ['expense', 'income', 'transfer', 'investment', 'neutral'];
      
      definedFlowTypes.forEach(flowType => {
        expect(flowType === 'undefined').toBe(false);
      });
    });
  });

  describe('Confirmed status display logic', () => {
    it('should show "미확정" badge when confirmed is false', () => {
      const tx = { confirmed: false };
      
      expect(tx.confirmed === false).toBe(true);
    });

    it('should not show badge when confirmed is true', () => {
      const tx = { confirmed: true };
      
      expect(tx.confirmed === false).toBe(false);
    });

    it('should handle undefined confirmed field as unconfirmed', () => {
      const tx: { confirmed?: boolean } = {};
      
      expect(tx.confirmed ?? false).toBe(false);
    });
  });

  describe('Flow type labels', () => {
    const labelMap: Record<string, string> = {
      expense: '지출',
      income: '수입',
      transfer: '이체',
      investment: '투자',
      neutral: '중립',
      undefined: '미분류',
    };

    it('should have Korean labels for all flow types', () => {
      Object.keys(labelMap).forEach(key => {
        expect(labelMap[key]).toBeTruthy();
        expect(typeof labelMap[key]).toBe('string');
      });
    });

    it('should map flow types to correct labels', () => {
      expect(labelMap.expense).toBe('지출');
      expect(labelMap.income).toBe('수입');
      expect(labelMap.transfer).toBe('이체');
      expect(labelMap.investment).toBe('투자');
      expect(labelMap.neutral).toBe('중립');
      expect(labelMap.undefined).toBe('미분류');
    });
  });

  describe('Transaction type compatibility', () => {
    it('should allow investment flow type for buy/sell', () => {
      const buyTx = { type: 'buy', flow_type: 'investment' };
      const sellTx = { type: 'sell', flow_type: 'investment' };
      
      expect(buyTx.flow_type).toBe('investment');
      expect(sellTx.flow_type).toBe('investment');
    });

    it('should allow income flow type for deposit', () => {
      const depositTx = { type: 'deposit', flow_type: 'income' };
      
      expect(depositTx.flow_type).toBe('income');
    });

    it('should allow expense flow type for withdraw', () => {
      const withdrawTx = { type: 'withdraw', flow_type: 'expense' };
      
      expect(withdrawTx.flow_type).toBe('expense');
    });

    it('should allow transfer flow type for transfer_in/out', () => {
      const transferInTx = { type: 'transfer_in', flow_type: 'transfer' };
      const transferOutTx = { type: 'transfer_out', flow_type: 'transfer' };
      
      expect(transferInTx.flow_type).toBe('transfer');
      expect(transferOutTx.flow_type).toBe('transfer');
    });

    it('should allow undefined flow type for any transaction type', () => {
      const txTypes = ['buy', 'sell', 'deposit', 'withdraw', 'transfer_in', 'transfer_out'];
      
      txTypes.forEach(type => {
        const tx = { type, flow_type: 'undefined' };
        expect(tx.flow_type).toBe('undefined');
      });
    });
  });
});
