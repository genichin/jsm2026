"""
File Parser Service Tests
파일 파서 서비스 테스트
"""

import pytest
import pandas as pd
import io
from pathlib import Path
from app.services.file_parser import (
    read_encrypted_excel,
    detect_file_format,
    detect_toss_bank_format,
    transform_toss_bank_to_standard,
    transform_mirae_to_standard,
    transform_kb_securities_to_standard,
    transform_kb_bank_to_standard,
    transform_to_standard,
    parse_transaction_file,
)


# 테스트 파일 경로
TEST_DIR = Path(__file__).parent
TOSS_BANK_FILE = TEST_DIR / "토스뱅크_거래내역.xlsx"
FILE_PASSWORD = '770819'


class TestReadEncryptedExcel:
    """read_encrypted_excel 함수 테스트"""
    
    def test_read_encrypted_excel_with_password(self):
        """암호화된 Excel 파일 읽기 테스트"""
        if not TOSS_BANK_FILE.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(TOSS_BANK_FILE, 'rb') as f:
            file_content = f.read()
        
        df = read_encrypted_excel(file_content, FILE_PASSWORD, header=0)
        
        assert not df.empty
        assert len(df.columns) > 0
    
    def test_read_encrypted_excel_with_header_7(self):
        """header=7로 Excel 파일 읽기 테스트"""
        if not TOSS_BANK_FILE.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(TOSS_BANK_FILE, 'rb') as f:
            file_content = f.read()
        
        df = read_encrypted_excel(file_content, FILE_PASSWORD, header=7)
        
        assert not df.empty
        assert len(df) > 0


class TestDetectFileFormat:
    """detect_file_format 함수 테스트"""
    
    def test_detect_toss_bank_format(self):
        """토스뱅크 형식 감지 테스트"""
        if not TOSS_BANK_FILE.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(TOSS_BANK_FILE, 'rb') as f:
            file_content = f.read()
        
        df = read_encrypted_excel(file_content, FILE_PASSWORD, header=0)
        file_format = detect_file_format(df)
        
        assert file_format == 'toss_bank'
    
    def test_detect_mirae_format(self):
        """미래에셋 형식 감지 테스트"""
        csv_data = """체결일,체결시간,종목명,매수매도구분,체결수량,체결단가,수수료
2025-11-07,10:30:00,삼성전자,매수,100,50000,500"""
        
        df = pd.read_csv(io.StringIO(csv_data))
        file_format = detect_file_format(df)
        
        assert file_format == 'mirae'
    
    def test_detect_kb_format(self):
        """KB증권 형식 감지 테스트"""
        csv_data = """거래일자,종목명,거래구분,거래수량,거래단가,수수료
20251107,삼성전자,매수,100,50000,500"""
        
        df = pd.read_csv(io.StringIO(csv_data))
        file_format = detect_file_format(df)
        
        assert file_format == 'kb_securities'
    
    def test_detect_standard_format(self):
        """표준 형식 감지 테스트"""
        csv_data = """transaction_date,type,quantity,description
2025-11-07T10:30:00,buy,100,삼성전자"""
        
        df = pd.read_csv(io.StringIO(csv_data))
        file_format = detect_file_format(df)
        
        assert file_format == 'standard'
    
    def test_detect_unknown_format(self):
        """알 수 없는 형식 감지 테스트"""
        csv_data = """col1,col2,col3
value1,value2,value3"""
        
        df = pd.read_csv(io.StringIO(csv_data))
        file_format = detect_file_format(df)
        
        assert file_format == 'unknown'
    
    def test_detect_empty_dataframe(self):
        """빈 DataFrame 감지 테스트"""
        df = pd.DataFrame()
        file_format = detect_file_format(df)
        
        assert file_format == 'unknown'


class TestDetectTossBankFormat:
    """detect_toss_bank_format 함수 테스트"""
    
    def test_detect_by_column_name(self):
        """컬럼명으로 토스뱅크 형식 감지"""
        df = pd.DataFrame(columns=['토스뱅크 거래내역', 'Unnamed: 1'])
        
        assert detect_toss_bank_format(df) == True
    
    def test_detect_by_first_row(self):
        """첫 행 데이터로 토스뱅크 형식 감지"""
        df = pd.DataFrame({
            'col1': ['성명', 'data1'],
            'col2': ['고진환', 'data2']
        })
        
        assert detect_toss_bank_format(df) == True
    
    def test_not_toss_bank_format(self):
        """토스뱅크가 아닌 형식"""
        df = pd.DataFrame({
            'transaction_date': ['2025-11-07'],
            'type': ['buy']
        })
        
        assert detect_toss_bank_format(df) == False


class TestTransformTossBankToStandard:
    """transform_toss_bank_to_standard 함수 테스트"""
    
    def test_transform_with_real_file(self):
        """실제 토스뱅크 파일 변환 테스트"""
        if not TOSS_BANK_FILE.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(TOSS_BANK_FILE, 'rb') as f:
            file_content = f.read()
        
        df = read_encrypted_excel(file_content, FILE_PASSWORD, header=7)
        standard_df = transform_toss_bank_to_standard(df)
        
        # 필수 컬럼 확인
        assert 'transaction_date' in standard_df.columns
        assert 'description' in standard_df.columns
        assert 'quantity' in standard_df.columns
        assert 'type' in standard_df.columns
        assert 'balance_after' in standard_df.columns
        assert 'memo' in standard_df.columns
        
        # 데이터 확인
        assert len(standard_df) > 0
        assert not standard_df['transaction_date'].isna().all()
        assert not standard_df['description'].isna().all()
    
    def test_transaction_type_mapping(self):
        """거래 유형 매핑 테스트"""
        # 시뮬레이션 데이터 생성 (이미 헤더 처리된 상태)
        test_data = {
            '거래 일시': ['2025.11.07 10:30:00', '2025.11.07 11:00:00', '2025.11.07 12:00:00'],
            '적요': ['테스트1', '테스트2', '테스트3'],
            '거래 금액': [-10000, 5000, -3000],
            '거래 유형': ['체크카드결제', '프로모션입금', '이자입금'],
            '거래 후 잔액': [90000, 95000, 92000],
            '거래 기관': ['토스뱅크', '토스뱅크', '토스뱅크'],
            '계좌번호': ['1234', '1234', '1234'],
            '메모': ['', '', '']
        }
        
        df = pd.DataFrame(test_data)
        standard_df = transform_toss_bank_to_standard(df)
        
        # 타입 매핑 확인
        assert standard_df.iloc[0]['type'] == 'card_payment'
        assert standard_df.iloc[1]['type'] == 'promotion_deposit'
        assert standard_df.iloc[2]['type'] == 'interest'
    
    def test_missing_required_columns(self):
        """필수 컬럼 누락 테스트"""
        df = pd.DataFrame({
            '거래 일시': ['2025.11.07 10:30:00'],
            '적요': ['테스트']
        })
        
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            transform_toss_bank_to_standard(df)


class TestTransformMiraeToStandard:
    """transform_mirae_to_standard 함수 테스트"""
    
    def test_transform_mirae(self):
        """미래에셋 형식 변환 테스트"""
        mirae_data = {
            '체결일': ['2025-11-07', '2025-11-07'],
            '체결시간': ['10:30:00', '11:45:00'],
            '종목명': ['삼성전자', '삼성전자'],
            '매수매도구분': ['매수', '매도'],
            '체결수량': [100, 50],
            '체결단가': [50000, 51000],
            '수수료': [500, 500],
            '세금': [0, 100]
        }
        
        df = pd.DataFrame(mirae_data)
        standard_df = transform_mirae_to_standard(df)
        
        # 필수 컬럼 확인
        assert 'transaction_date' in standard_df.columns
        assert 'description' in standard_df.columns
        assert 'type' in standard_df.columns
        
        # 데이터 확인
        assert len(standard_df) == 2
        assert standard_df.iloc[0]['type'] == 'buy'
        assert standard_df.iloc[1]['type'] == 'sell'
        assert standard_df.iloc[0]['quantity'] == 100
        assert standard_df.iloc[1]['quantity'] == 50


class TestTransformKbSecuritiesToStandard:
    """transform_kb_securities_to_standard 함수 테스트"""
    
    def test_transform_kb_securities(self):
        """KB증권 형식 변환 테스트"""
        kb_data = {
            '거래일자': [20251107, 20251107],
            '종목명': ['삼성전자', '삼성전자'],
            '거래구분': ['매수', '매도'],
            '거래수량': [100, 50],
            '거래단가': [50000, 51000],
            '수수료': [500, 500]
        }
        
        df = pd.DataFrame(kb_data)
        standard_df = transform_kb_securities_to_standard(df)
        
        # 필수 컬럼 확인
        assert 'transaction_date' in standard_df.columns
        assert 'description' in standard_df.columns
        assert 'type' in standard_df.columns
        
        # 데이터 확인
        assert len(standard_df) == 2
        assert standard_df.iloc[0]['type'] == 'buy'
        assert standard_df.iloc[1]['type'] == 'sell'


class TestTransformToStandard:
    """transform_to_standard 함수 테스트"""
    
    def test_transform_toss_bank(self):
        """토스뱅크 형식 변환 라우팅 테스트"""
        if not TOSS_BANK_FILE.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(TOSS_BANK_FILE, 'rb') as f:
            file_content = f.read()
        
        df = read_encrypted_excel(file_content, FILE_PASSWORD, header=7)
        standard_df = transform_to_standard(df, 'toss_bank')
        
        assert 'transaction_date' in standard_df.columns
        assert len(standard_df) > 0
    
    def test_transform_standard_format(self):
        """이미 표준 형식인 경우"""
        df = pd.DataFrame({
            'transaction_date': ['2025-11-07'],
            'type': ['buy'],
            'quantity': [100]
        })
        
        standard_df = transform_to_standard(df, 'standard')
        
        assert standard_df.equals(df)
    
    def test_transform_unknown_format(self):
        """알 수 없는 형식 변환 시도"""
        df = pd.DataFrame({'col1': [1]})
        
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
            transform_to_standard(df, 'unknown')


class TestParseTransactionFile:
    """parse_transaction_file 함수 테스트 (통합 테스트)"""
    
    def test_parse_toss_bank_excel(self):
        """토스뱅크 Excel 파일 전체 파이프라인 테스트"""
        if not TOSS_BANK_FILE.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(TOSS_BANK_FILE, 'rb') as f:
            file_content = f.read()
        
        standard_df = parse_transaction_file(
            file_content=file_content,
            file_extension='.xlsx',
            password=FILE_PASSWORD
        )
        
        # 필수 컬럼 확인
        assert 'transaction_date' in standard_df.columns
        assert 'description' in standard_df.columns
        assert 'quantity' in standard_df.columns
        assert 'type' in standard_df.columns
        
        # 데이터 확인
        assert len(standard_df) > 0
        assert not standard_df.empty
    
    def test_parse_csv_mirae(self):
        """미래에셋 CSV 파일 파싱 테스트"""
        csv_data = """체결일,체결시간,종목명,매수매도구분,체결수량,체결단가,수수료,세금
2025-11-07,10:30:00,삼성전자,매수,100,50000,500,0
2025-11-07,11:45:00,삼성전자,매도,50,51000,500,100"""
        
        file_content = csv_data.encode('utf-8')
        
        standard_df = parse_transaction_file(
            file_content=file_content,
            file_extension='.csv',
            password=None
        )
        
        assert 'transaction_date' in standard_df.columns
        assert len(standard_df) == 2
        assert standard_df.iloc[0]['type'] == 'buy'
    
    def test_parse_csv_kb(self):
        """KB증권 CSV 파일 파싱 테스트"""
        csv_data = """거래일자,종목명,거래구분,거래수량,거래단가,수수료
20251107,삼성전자,매수,100,50000,500
20251107,삼성전자,매도,50,51000,500"""
        
        file_content = csv_data.encode('utf-8')
        
        standard_df = parse_transaction_file(
            file_content=file_content,
            file_extension='.csv',
            password=None
        )
        
        assert 'transaction_date' in standard_df.columns
        assert len(standard_df) == 2
        assert standard_df.iloc[0]['type'] == 'buy'
    
    def test_parse_csv_cp949_encoding(self):
        """CP949 인코딩 CSV 파일 파싱 테스트"""
        csv_data = """거래일자,종목명,거래구분,거래수량,거래단가,수수료
20251107,삼성전자,매수,100,50000,500"""
        
        file_content = csv_data.encode('cp949')
        
        standard_df = parse_transaction_file(
            file_content=file_content,
            file_extension='.csv',
            password=None
        )
        
        assert len(standard_df) > 0
        assert '삼성전자' in str(standard_df.iloc[0]['description'])
    
    def test_parse_unsupported_file_extension(self):
        """지원하지 않는 파일 확장자"""
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
            parse_transaction_file(
                file_content=b'dummy',
                file_extension='.txt',
                password=None
            )
    
    def test_parse_unknown_format_error(self):
        """알 수 없는 형식 에러"""
        csv_data = """col1,col2,col3
value1,value2,value3"""
        
        file_content = csv_data.encode('utf-8')
        
        with pytest.raises(ValueError, match="파일 형식을 인식할 수 없습니다"):
            parse_transaction_file(
                file_content=file_content,
                file_extension='.csv',
                password=None
            )


class TestTransactionTypeMappings:
    """거래 유형 매핑 상세 테스트"""
    
    def test_all_toss_bank_types(self):
        """모든 토스뱅크 거래 유형 매핑 테스트"""
        test_data = {
            '거래 일시': ['2025.11.07 10:00:00'] * 10,
            '적요': ['테스트'] * 10,
            '거래 금액': [-1000, -2000, 3000, 4000, -5000, 6000, -7000, 8000, 9000, -1100],
            '거래 유형': ['체크카드결제', '내계좌간자동이체', '프로모션입금', '이자입금', 
                        '자동이체', '입금', '출금', '송금', '이체', '환전'],
            '거래 후 잔액': [10000] * 10,
            '거래 기관': ['토스뱅크'] * 10,
            '계좌번호': ['1234'] * 10,
            '메모': [''] * 10
        }
        
        df = pd.DataFrame(test_data)
        standard_df = transform_toss_bank_to_standard(df)
        
        expected_types = [
            'card_payment',
            'internal_transfer',
            'promotion_deposit',
            'interest',
            'auto_transfer',
            'deposit',
            'withdraw',
            'remittance',
            'transfer_in',
            'exchange'
        ]
        
        for i, expected_type in enumerate(expected_types):
            assert standard_df.iloc[i]['type'] == expected_type, \
                f"Row {i}: Expected {expected_type}, got {standard_df.iloc[i]['type']}"
    
    def test_unknown_type_fallback(self):
        """알 수 없는 거래 유형의 폴백 로직 테스트"""
        test_data = {
            '거래 일시': ['2025.11.07 10:00:00', '2025.11.07 11:00:00'],
            '적요': ['테스트1', '테스트2'],
            '거래 금액': [-1000, 2000],
            '거래 유형': ['알수없는유형', '알수없는유형'],
            '거래 후 잔액': [10000, 12000],
            '거래 기관': ['토스뱅크', '토스뱅크'],
            '계좌번호': ['1234', '1234'],
            '메모': ['', '']
        }
        
        df = pd.DataFrame(test_data)
        standard_df = transform_toss_bank_to_standard(df)
        
        # 금액 부호로 판단
        assert standard_df.iloc[0]['type'] == 'withdraw'  # 음수
        assert standard_df.iloc[1]['type'] == 'deposit'   # 양수


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
