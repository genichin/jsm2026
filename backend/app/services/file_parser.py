"""
Transaction File Parser Service
거래 내역 파일 파싱 서비스

다양한 금융기관의 거래 내역 파일 형식을 감지하고 표준 형식으로 변환
"""

import pandas as pd
import io
import msoffcrypto
from typing import Optional, Dict, Any
import re
from pathlib import Path


def read_encrypted_excel(
    file_content: bytes,
    password: Optional[str] = None,
    skiprows=None,
    header: int = 0
) -> pd.DataFrame:
    """
    암호화된 Excel 파일을 읽는 함수
    
    Args:
        file_content: Excel 파일의 바이트 내용
        password: 파일 암호 (선택)
        skiprows: 건너뛸 행 (int, list, range 등)
        header: 헤더 행 인덱스
        
    Returns:
        pandas DataFrame
    """
    file_buffer = io.BytesIO(file_content)
    
    try:
        # 먼저 암호 없이 읽기 시도
        return pd.read_excel(file_buffer, engine='openpyxl', skiprows=skiprows, header=header)
    except Exception:
        # 암호화되어 있으면 msoffcrypto로 해제
        if not password:
            raise ValueError("암호화된 파일입니다. 비밀번호가 필요합니다.")
        
        file_buffer.seek(0)
        decrypted = io.BytesIO()
        
        office_file = msoffcrypto.OfficeFile(file_buffer)
        office_file.load_key(password=password)
        office_file.decrypt(decrypted)
        
        decrypted.seek(0)
        return pd.read_excel(decrypted, engine='openpyxl', skiprows=skiprows, header=header)


def detect_file_format(df: pd.DataFrame) -> str:
    """
    파일 형식을 자동 감지
    
    Args:
        df: pandas DataFrame
        
    Returns:
        형식 이름 ('toss_bank', 'mirae', 'kb_securities', 'kb_bank', 'standard', 'unknown')
    """
    if df.empty:
        return 'unknown'
    
    columns = [str(col).strip() for col in df.columns]
    columns_lower = [col.lower() for col in columns]
    
    # 토스뱅크 형식 감지
    if detect_toss_bank_format(df):
        return 'toss_bank'
    
    # 미래에셋 형식 감지
    if '체결일' in columns and '체결시간' in columns and '매수매도구분' in columns:
        return 'mirae'
    
    # KB증권 형식 감지 (투자 거래)
    if '거래일자' in columns and '종목명' in columns and '거래구분' in columns:
        return 'kb_securities'
    
    # KB은행 형식 감지 (은행 거래 - HTML 테이블)
    if '거래일시' in columns and '적요' in columns and ('출금액' in columns or '입금액' in columns):
        return 'kb_bank'
    
    # 표준 형식 감지 (이미 변환된 형식)
    if 'transaction_date' in columns_lower and 'type' in columns_lower and 'quantity' in columns_lower:
        return 'standard'
    
    return 'unknown'


def detect_toss_bank_format(df: pd.DataFrame) -> bool:
    """
    토스뱅크 형식인지 감지
    
    토스뱅크 파일 특징:
    - 첫 7행이 메타데이터 (성명, 계좌번호, 조회기간 등)
    - 8행째가 실제 컬럼 헤더
    - "토스뱅크 거래내역" 텍스트 포함
    
    Args:
        df: pandas DataFrame
        
    Returns:
        토스뱅크 형식 여부
    """
    # 컬럼에 "토스뱅크 거래내역" 텍스트가 있는지 확인
    for col in df.columns:
        if '토스뱅크' in str(col) and '거래내역' in str(col):
            return True
    
    # 또는 첫 행 데이터에서 확인
    if len(df) > 0:
        first_row_text = ' '.join([str(val) for val in df.iloc[0].values])
        if '토스뱅크' in first_row_text or '성명' in first_row_text:
            return True
    
    return False


def _find_toss_bank_header_row(df_raw: pd.DataFrame) -> Optional[int]:
    """
    토스뱅크 엑셀을 header=0으로 읽은 df_raw에서 실제 헤더 행의 인덱스를 추정

    전략:
    - 각 행의 셀 문자열 집합에 필수 컬럼명이 얼마나 포함되는지 스코어링
    - 먼저 전체 일치(모두 포함)를 찾고, 없으면 임계치(>=5)로 완화
    """
    if df_raw is None or len(df_raw) == 0:
        return None

    required_columns = ['거래 일시', '적요', '거래 금액', '거래 유형', '거래 후 잔액', '거래 기관', '계좌번호', '메모']

    # 검사 범위를 처음 20행으로 제한 (메타 영역 내에서 헤더가 나타나는 특성 고려)
    max_scan = min(len(df_raw), 20)

    def row_values(i: int) -> set:
        vals = []
        try:
            vals = df_raw.iloc[i].values
        except Exception:
            return set()
        normalized = []
        for v in vals:
            if pd.isna(v):
                continue
            s = str(v).strip()
            if not s:
                continue
            normalized.append(s)
        return set(normalized)

    # 1) 전부 일치하는 행 우선
    for i in range(max_scan):
        rv = row_values(i)
        if set(required_columns).issubset(rv):
            return i

    # 2) 일부 일치(임계치 5 이상)하는 행 후보 중 최댓값 선택
    best_idx = None
    best_score = 0
    for i in range(max_scan):
        rv = row_values(i)
        score = sum(1 for c in required_columns if c in rv)
        if score > best_score:
            best_score = score
            best_idx = i
    if best_score >= 5:
        return best_idx

    return None


def _reconstruct_toss_bank_from_df_raw(df_raw: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    df_raw(header=0로 읽힘)에서 실제 헤더 행을 찾아 표 형식의 DataFrame을 복원.
    성공 시 표준 변환 전 단계의 df를 반환, 실패 시 None.
    """
    header_row = _find_toss_bank_header_row(df_raw)
    if header_row is None:
        return None

    # 헤더로 사용할 행의 값들을 컬럼으로 설정하고, 그 다음 행부터 데이터를 사용
    header_vals = df_raw.iloc[header_row].tolist()
    df = df_raw.iloc[header_row + 1 :].copy()

    # 컬럼 문자열화 및 공백 정리 + 별칭 정규화
    def _canon(col: str) -> str:
        if col is None or (isinstance(col, float) and pd.isna(col)):
            return 'nan'
        s = str(col).strip()
        # 내부 공백 제거하여 키 정규화
        key = re.sub(r"\s+", "", s)
        # 무공백 키를 기준으로 표준명 매핑
        alias = {
            '거래일시': '거래 일시',
            '적요': '적요',
            '거래금액': '거래 금액',
            '거래유형': '거래 유형',
            '거래후잔액': '거래 후 잔액',
            '거래기관': '거래 기관',
            '계좌번호': '계좌번호',
            '계좌번호': '계좌번호',
            '메모': '메모',
        }
        return alias.get(key, s)

    df.columns = [_canon(c) for c in header_vals]

    # 전처리: 완전 공백 컬럼 제거 (모든 값이 NaN이거나 공백 문자열)
    drop_cols = []
    for col in df.columns:
        series = df[col]
        if series.isna().all():
            drop_cols.append(col)
        else:
            # 문자열 칼럼인 경우 공백만 있는지 검사
            try:
                if series.apply(lambda x: str(x).strip() == '' if not pd.isna(x) else True).all():
                    drop_cols.append(col)
            except Exception:
                pass
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # 인덱스 리셋
    df = df.reset_index(drop=True)
    return df


def transform_toss_bank_to_standard(df: pd.DataFrame) -> pd.DataFrame:
    """
    토스뱅크 형식을 표준 형식으로 변환
    
    Args:
        df: 토스뱅크 형식의 DataFrame (header=7로 읽은 상태)
        
    Returns:
        표준 형식의 DataFrame
        
    Raises:
        ValueError: 필수 컬럼이 없거나 데이터 형식이 잘못된 경우
    """
    # 헤더가 merged cell 때문에 Unnamed 또는 NaN으로 나왔을 수 있음
    # 첫 행에서 실제 헤더 값을 가져와서 컬럼명으로 설정
    try:
        col0 = str(df.columns[0])
        col1 = str(df.columns[1]) if len(df.columns) > 1 else ''
    except Exception:
        col0 = ''
        col1 = ''
    if ('Unnamed' in col0) or ('Unnamed' in col1) or all(pd.isna(c) for c in df.columns):
        new_columns = df.iloc[0].tolist()
        df = df.iloc[1:].copy()  # 첫 행 제외
        df.columns = new_columns
    
    # 컬럼명에서 공백 제거 및 별칭 정규화
    def _canon2(col: Any) -> str:
        if col != col:  # NaN 체크
            return 'nan'
        s = str(col).strip()
        key = re.sub(r"\s+", "", s)
        alias = {
            '거래일시': '거래 일시',
            '적요': '적요',
            '거래금액': '거래 금액',
            '거래유형': '거래 유형',
            '거래후잔액': '거래 후 잔액',
            '거래기관': '거래 기관',
            '계좌번호': '계좌번호',
            '메모': '메모',
        }
        return alias.get(key, s)

    df.columns = [_canon2(col) for col in df.columns]
    
    # 필수 컬럼 확인 ("메모"는 선택 컬럼으로 간주)
    required_columns = ['거래 일시', '적요', '거래 금액', '거래 유형', '거래 후 잔액', '거래 기관', '계좌번호']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}. 현재 컬럼: {df.columns.tolist()}")
    
    # 토스뱅크 거래 유형 -> DB 거래 유형 매핑
    def map_toss_transaction_type(row):
        """토스뱅크 거래 유형을 DB 거래 유형으로 매핑"""
        transaction_type = str(row['거래 유형'])
        amount = float(row['거래 금액'])
        
        # 거래 유형별 매핑 (각 유형을 개별 타입으로)
        type_mapping = {
            '체크카드결제': 'card_payment',
            '내계좌간자동이체': 'internal_transfer',
            '프로모션입금': 'promotion_deposit',
            '이자입금': 'interest',
            '자동이체': 'auto_transfer',
            '입금': 'deposit',
            '출금': 'withdraw',
            '송금': 'remittance',
            '이체': 'transfer_in',
            '환전': 'exchange',
        }
        
        # 매핑된 유형이 있으면 사용, 없으면 금액으로 판단
        return type_mapping.get(transaction_type, 'withdraw' if amount < 0 else 'deposit')
    
    # 표준 형식으로 변환
    # 메모 컬럼이 없을 수 있으므로 안전하게 구성
    memo_series = df['메모'].astype(str) if '메모' in df.columns else pd.Series([''] * len(df))
    standard_df = pd.DataFrame({
        'transaction_date': pd.to_datetime(df['거래 일시'], format='%Y.%m.%d %H:%M:%S'),
        'description': df['적요'],
        'quantity': df['거래 금액'].astype(float),
        'price': 1.0,  # 은행 거래는 항상 단가 1
        'fee': 0.0,  # 은행 거래는 수수료 없음
        'tax': 0.0,  # 은행 거래는 세금 없음
        'type': df.apply(map_toss_transaction_type, axis=1),
        'balance_after': df['거래 후 잔액'].astype(float),
        'memo': memo_series.astype(str) + ',' + df['거래 기관'].astype(str) + ',' + df['계좌번호'].astype(str),
    })
    
    # NaN 값 정리
    standard_df['memo'] = standard_df['memo'].str.replace('nan', '', regex=False)
    standard_df['memo'] = standard_df['memo'].str.replace('None', '', regex=False)
    standard_df['memo'] = standard_df['memo'].str.replace(',+', ',', regex=True)
    standard_df['memo'] = standard_df['memo'].str.strip(',')
    standard_df['memo'] = standard_df['memo'].fillna('')
    
    return standard_df


def transform_mirae_to_standard(df: pd.DataFrame) -> pd.DataFrame:
    """
    미래에셋 형식을 표준 형식으로 변환
    
    Args:
        df: 미래에셋 형식의 DataFrame
        
    Returns:
        표준 형식의 DataFrame
    """
    # 거래 유형 매핑
    type_mapping = {
        '매수': 'buy',
        '매도': 'sell',
    }
    
    standard_df = pd.DataFrame({
        'transaction_date': pd.to_datetime(df['체결일'] + ' ' + df['체결시간']),
        'description': df['종목명'],
        'quantity': df['체결수량'].astype(float),
        'type': df['매수매도구분'].map(type_mapping),
        'price': df['체결단가'].astype(float) if '체결단가' in df.columns else 0,
        'fee': df['수수료'].astype(float) if '수수료' in df.columns else 0,
        'tax': df['세금'].astype(float) if '세금' in df.columns else 0,
        'memo': '',
    })
    
    return standard_df


def transform_kb_securities_to_standard(df: pd.DataFrame) -> pd.DataFrame:
    """
    KB증권 형식을 표준 형식으로 변환 (투자 거래)
    
    Args:
        df: KB증권 형식의 DataFrame
        
    Returns:
        표준 형식의 DataFrame
    """
    # 거래일자 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
    df['거래일자'] = pd.to_datetime(df['거래일자'].astype(str), format='%Y%m%d')
    
    # 거래 유형 매핑
    type_mapping = {
        '매수': 'buy',
        '매도': 'sell',
    }
    
    standard_df = pd.DataFrame({
        'transaction_date': df['거래일자'],
        'description': df['종목명'],
        'quantity': df['거래수량'].astype(float),
        'type': df['거래구분'].map(type_mapping),
        'price': df['거래단가'].astype(float) if '거래단가' in df.columns else 0,
        'fee': df['수수료'].astype(float) if '수수료' in df.columns else 0,
        'memo': '',
    })
    
    return standard_df


def transform_kb_bank_to_standard(df: pd.DataFrame) -> pd.DataFrame:
    """
    KB은행 형식을 표준 형식으로 변환 (은행 거래)
    
    KB은행 파일 특징:
    - HTML 테이블 형식 (.xls 확장자지만 실제로는 HTML)
    - 컬럼: 거래일시, 적요, 보낸분/받는분, 송금메모, 출금액, 입금액, 잔액, 거래점, 구분
    
    Args:
        df: KB은행 형식의 DataFrame
        
    Returns:
        표준 형식의 DataFrame
    """
    # 필수 컬럼 확인
    required_columns = ['거래일시', '적요', '출금액', '입금액', '잔액']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}. 현재 컬럼: {df.columns.tolist()}")
    
    # 데이터 정리: 빈 행 제거
    df = df[df['거래일시'].notna() & (df['거래일시'] != '')].copy()
    
    # 숫자 컬럼 변환 (천단위 콤마 제거)
    for col in ['출금액', '입금액', '잔액']:
        df[col] = df[col].astype(str).str.replace(',', '').replace('', '0').astype(float)
    
    # 거래 타입 매핑 (적요 기반)
    def map_kb_transaction_type(row):
        """KB은행 적요를 거래 타입으로 매핑"""
        description = str(row['적요'])
        withdraw = float(row['출금액'])
        deposit = float(row['입금액'])
        
        # 거래 타입 매핑
        type_mapping = {
            '체크카드': 'card_payment',
            '국민카드': 'card_payment',
            '전자금융': 'transfer_in',  # 전자금융은 입금으로 처리
            '스마트출금': 'transfer_out',
            '오픈뱅킹출금': 'transfer_out',
            '급여입금': 'deposit',
            'ATM입금': 'deposit',
            '지로출금': 'auto_transfer',
            'CMS 공동': 'auto_transfer',
            'CMS공동': 'auto_transfer',
            'FBS출금': 'auto_transfer',
            '현금IC': 'card_payment',
            '기일출금': 'auto_transfer',
        }
        
        # 적요 매칭
        for key, value in type_mapping.items():
            if key in description:
                # 전자금융은 입출금 여부로 세분화
                if key == '전자금융':
                    if withdraw > 0:
                        return 'transfer_out'
                    elif deposit > 0:
                        return 'transfer_in'
                return value
        
        # 매칭 안되면 입출금 기준으로 판단
        if withdraw > 0:
            return 'withdraw'
        elif deposit > 0:
            return 'deposit'
        else:
            return 'other'
    
    # quantity 계산 (입금은 양수, 출금은 음수)
    df['quantity'] = df['입금액'] - df['출금액']
    
    # description: 보낸분/받는분 사용 (없으면 적요)
    if '보낸분/받는분' in df.columns:
        description_series = df['보낸분/받는분'].astype(str)
    else:
        description_series = df['적요'].astype(str)
    
    # 메모 구성 (적요, 송금메모, 거래점 포함)
    memo_parts = [df['적요'].astype(str)]  # 적요를 메모에 추가
    
    if '송금메모' in df.columns:
        memo_parts.append(df['송금메모'].astype(str))
    if '거래점' in df.columns:
        memo_parts.append(df['거래점'].astype(str))
    
    # Series 결합
    if memo_parts:
        memo_series = memo_parts[0]
        for part in memo_parts[1:]:
            memo_series = memo_series + ',' + part
    else:
        memo_series = pd.Series([''] * len(df))
    
    # 표준 형식으로 변환
    standard_df = pd.DataFrame({
        'transaction_date': pd.to_datetime(df['거래일시'], format='%Y.%m.%d %H:%M:%S'),
        'description': description_series,
        'quantity': df['quantity'],
        'price': 1.0,  # 은행 거래는 항상 단가 1
        'fee': 0.0,
        'tax': 0.0,
        'type': df.apply(map_kb_transaction_type, axis=1),
        'balance_after': df['잔액'],
        'memo': memo_series,
    })
    
    # NaN 값 정리
    standard_df['memo'] = standard_df['memo'].str.replace('nan', '', regex=False)
    standard_df['memo'] = standard_df['memo'].str.replace('None', '', regex=False)
    standard_df['memo'] = standard_df['memo'].str.replace(',+', ',', regex=True)
    standard_df['memo'] = standard_df['memo'].str.strip(',')
    standard_df['memo'] = standard_df['memo'].fillna('')
    
    return standard_df


def transform_to_standard(df: pd.DataFrame, file_format: str) -> pd.DataFrame:
    """
    감지된 형식에 따라 표준 형식으로 변환
    
    Args:
        df: 원본 DataFrame
        file_format: 파일 형식 ('toss_bank', 'mirae', 'kb_securities', 'kb_bank', 'standard')
        
    Returns:
        표준 형식의 DataFrame
        
    Raises:
        ValueError: 지원하지 않는 형식이거나 변환 실패
    """
    if file_format == 'toss_bank':
        return transform_toss_bank_to_standard(df)
    elif file_format == 'mirae':
        return transform_mirae_to_standard(df)
    elif file_format == 'kb_securities':
        return transform_kb_securities_to_standard(df)
    elif file_format == 'kb_bank':
        return transform_kb_bank_to_standard(df)
    elif file_format == 'kb':  # 하위 호환성
        return transform_kb_securities_to_standard(df)
    elif file_format == 'standard':
        return df  # 이미 표준 형식
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {file_format}")


def parse_transaction_file(
    file_content: bytes,
    file_extension: str,
    password: Optional[str] = None
) -> pd.DataFrame:
    """
    거래 내역 파일을 파싱하고 표준 형식으로 변환
    
    전체 파이프라인:
    1. 파일 읽기 (암호화 지원)
    2. 형식 감지
    3. 표준 형식으로 변환
    
    Args:
        file_content: 파일의 바이트 내용
        file_extension: 파일 확장자 ('.xlsx', '.csv' 등)
        password: Excel 파일 암호 (선택)
        
    Returns:
        표준 형식의 DataFrame
        
    Raises:
        ValueError: 파일 읽기 실패, 형식 감지 실패, 변환 실패 등
    """
    # 1. 파일 읽기
    if file_extension.lower() in ['.xlsx', '.xls']:
        # .xls 파일이 HTML일 수 있으므로 먼저 HTML 파싱 시도
        if file_extension.lower() == '.xls':
            try:
                # HTML 테이블로 읽기 시도 (KB 은행 등)
                tables = pd.read_html(io.BytesIO(file_content), encoding='utf-8')
                if tables:
                    # 가장 큰 테이블을 거래내역으로 간주
                    df_raw = max(tables, key=lambda t: len(t))
                    
                    # 첫 행이 헤더인지 확인
                    if len(df_raw) > 0:
                        first_row = df_raw.iloc[0]
                        if any('거래일시' in str(v) or '적요' in str(v) for v in first_row.values):
                            # 첫 행을 헤더로 설정
                            df_raw.columns = df_raw.iloc[0]
                            df_raw = df_raw[1:].reset_index(drop=True)
                    
                    file_format = detect_file_format(df_raw)
                    df = df_raw
                else:
                    # HTML 파싱 실패 시 Excel로 읽기
                    df_raw = read_encrypted_excel(file_content, password, header=0)
                    file_format = detect_file_format(df_raw)
                    df = df_raw
            except (ValueError, ImportError):
                # HTML 파싱 실패 시 Excel로 읽기
                df_raw = read_encrypted_excel(file_content, password, header=0)
                file_format = detect_file_format(df_raw)
                df = df_raw
        else:
            # .xlsx 파일은 Excel로 처리
            df_raw = read_encrypted_excel(file_content, password, header=0)
            file_format = detect_file_format(df_raw)
            
            # 토스뱅크인 경우 header=7로 재읽기
            if file_format == 'toss_bank':
                df = read_encrypted_excel(file_content, password, header=7)
            else:
                df = df_raw
            
    elif file_extension.lower() == '.csv':
        # CSV 파일 처리 (인코딩 자동 감지)
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(file_content), encoding='cp949')
        
        file_format = detect_file_format(df)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {file_extension}")
    
    # 2. 형식 감지 (이미 위에서 수행)
    if file_format == 'unknown':
        raise ValueError("파일 형식을 인식할 수 없습니다. 지원하는 형식인지 확인해주세요.")
    
    # 3. 표준 형식으로 변환
    standard_df = transform_to_standard(df, file_format)
    
    if standard_df.empty:
        raise ValueError("변환된 데이터가 비어있습니다.")
    
    return standard_df
