"""
File Parser Service Integration Tests
file_parser.py의 전체 파이프라인 통합 테스트
"""

import pytest
from pathlib import Path
from app.services.file_parser import parse_transaction_file


TEST_DIR = Path(__file__).parent
TOSS_FILE = TEST_DIR / "testdata/toss_sample.xlsx"
KB_FILE = TEST_DIR / "testdata/KB_sample.xls"


def test_parse_toss_bank_file_integration():
    """토스뱅크 파일 전체 파이프라인 테스트"""
    assert TOSS_FILE.exists(), f"테스트 파일이 없습니다: {TOSS_FILE}"
    
    with open(TOSS_FILE, 'rb') as f:
        content = f.read()
    
    # 파싱 실행
    df = parse_transaction_file(content, '.xlsx', password='770819')
    
    # 결과 검증
    assert not df.empty, "파싱된 데이터가 비어있습니다"
    assert len(df) > 0, "거래 내역이 없습니다"
    
    # 표준 컬럼 확인
    expected_columns = ['transaction_date', 'description', 'quantity', 'price', 
                       'fee', 'tax', 'type', 'balance_after', 'memo']
    assert all(col in df.columns for col in expected_columns), \
        f"필수 컬럼이 없습니다. 현재 컬럼: {df.columns.tolist()}"
    
    # 데이터 타입 확인
    assert df['quantity'].dtype in ['float64', 'int64'], "quantity가 숫자 타입이 아닙니다"
    assert df['balance_after'].dtype in ['float64', 'int64'], "balance_after가 숫자 타입이 아닙니다"
    
    # 거래 타입 확인
    valid_types = ['card_payment', 'internal_transfer', 'promotion_deposit', 
                   'interest', 'auto_transfer', 'deposit', 'withdraw', 
                   'remittance', 'transfer_in', 'exchange']
    assert all(t in valid_types for t in df['type'].unique()), \
        f"잘못된 거래 타입이 있습니다: {df['type'].unique()}"
    
    print(f"\n✅ 토스뱅크 파일 파싱 성공: {len(df)}개 거래")
    print(f"거래 타입: {df['type'].value_counts().to_dict()}")


def test_parse_kb_bank_file_integration():
    """KB은행 파일 전체 파이프라인 테스트"""
    assert KB_FILE.exists(), f"테스트 파일이 없습니다: {KB_FILE}"
    
    with open(KB_FILE, 'rb') as f:
        content = f.read()
    
    # 파싱 실행
    df = parse_transaction_file(content, '.xls')
    
    # 결과 검증
    assert not df.empty, "파싱된 데이터가 비어있습니다"
    assert len(df) > 0, "거래 내역이 없습니다"
    
    # 표준 컬럼 확인
    expected_columns = ['transaction_date', 'description', 'quantity', 'price', 
                       'fee', 'tax', 'type', 'balance_after', 'memo']
    assert all(col in df.columns for col in expected_columns), \
        f"필수 컬럼이 없습니다. 현재 컬럼: {df.columns.tolist()}"
    
    # 데이터 타입 확인
    assert df['quantity'].dtype in ['float64', 'int64'], "quantity가 숫자 타입이 아닙니다"
    assert df['balance_after'].dtype in ['float64', 'int64'], "balance_after가 숫자 타입이 아닙니다"
    
    # 거래 타입 확인
    valid_types = ['card_payment', 'transfer_in', 'transfer_out', 'deposit', 
                   'withdraw', 'auto_transfer', 'other']
    assert all(t in valid_types for t in df['type'].unique()), \
        f"잘못된 거래 타입이 있습니다: {df['type'].unique()}"
    
    # 'transfer' 타입이 없는지 확인 (transfer_in/transfer_out으로 분리되어야 함)
    assert 'transfer' not in df['type'].values, \
        "transfer 타입이 발견되었습니다. transfer_in 또는 transfer_out으로 변환되어야 합니다."
    
    # KB 특정 검증
    assert len(df) >= 50, f"KB 파일은 50개 이상의 거래가 있어야 합니다: {len(df)}"
    
    # 입출금 검증 (quantity가 양수/음수로 올바르게 변환되었는지)
    has_positive = (df['quantity'] > 0).any()
    has_negative = (df['quantity'] < 0).any()
    assert has_positive or has_negative, "입금 또는 출금 데이터가 없습니다"
    
    print(f"\n✅ KB은행 파일 파싱 성공: {len(df)}개 거래")
    print(f"거래 타입: {df['type'].value_counts().to_dict()}")
    print(f"입금 건수: {(df['quantity'] > 0).sum()}")
    print(f"출금 건수: {(df['quantity'] < 0).sum()}")


def test_file_format_detection():
    """파일 형식 자동 감지 테스트"""
    from app.services.file_parser import detect_file_format
    import pandas as pd
    
    # 토스뱅크 형식
    toss_df = pd.DataFrame({
        '토스뱅크 거래내역': ['데이터'],
    })
    assert detect_file_format(toss_df) == 'toss_bank'
    
    # KB은행 형식
    kb_df = pd.DataFrame({
        '거래일시': ['2025.01.01'],
        '적요': ['체크카드'],
        '출금액': [1000],
        '입금액': [0],
        '잔액': [10000],
    })
    assert detect_file_format(kb_df) == 'kb_bank'
    
    # KB증권 형식
    kb_sec_df = pd.DataFrame({
        '거래일자': ['20250101'],
        '종목명': ['삼성전자'],
        '거래구분': ['매수'],
        '거래수량': [10],
    })
    assert detect_file_format(kb_sec_df) == 'kb_securities'
    
    # 미래에셋 형식
    mirae_df = pd.DataFrame({
        '체결일': ['2025-01-01'],
        '체결시간': ['10:00'],
        '매수매도구분': ['매수'],
    })
    assert detect_file_format(mirae_df) == 'mirae'
    
    print("\n✅ 파일 형식 감지 테스트 통과")


def test_error_handling():
    """에러 처리 테스트"""
    from app.services.file_parser import parse_transaction_file
    
    # 잘못된 확장자
    with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
        parse_transaction_file(b"test", '.pdf')
    
    # 빈 파일
    with pytest.raises(Exception):
        parse_transaction_file(b"", '.xlsx')
    
    print("\n✅ 에러 처리 테스트 통과")
