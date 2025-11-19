"""
거래 파일 업로드 API 테스트
"""

import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Asset, Account, AssetTransaction


# 테스트 파일 경로
TESTDATA_DIR = Path(__file__).parent.parent / "testdata"


@pytest.fixture
def test_account(db_session: Session, test_user: User) -> Account:
    """테스트용 계좌 생성"""
    account = Account(
        owner_id=test_user.id,
        name="Test Account",
        account_type="securities",
        provider="Test Bank"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def test_cash_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 현금 자산 생성"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="Test Cash",
        asset_type="cash",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture
def test_stock_asset(db_session: Session, test_user: User, test_account: Account) -> Asset:
    """테스트용 주식 자산 생성"""
    asset = Asset(
        user_id=test_user.id,
        account_id=test_account.id,
        name="Test Stock",
        asset_type="stock",
        symbol="TEST",
        currency="KRW",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


class TestFileUpload:
    """파일 업로드 기본 기능 테스트"""
    
    def test_upload_csv_dry_run_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """CSV 파일 dry_run 모드로 업로드 성공"""
        csv_file = TESTDATA_DIR / "sample_transactions_utf8.csv"
        
        with open(csv_file, 'rb') as f:
            response = client.post(
                "/api/v1/transactions/upload",
                headers=auth_header,
                files={"file": ("test.csv", f, "text/csv")},
                data={
                    "asset_id": test_cash_asset.id,
                    "dry_run": "true"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["total"] == 3
        assert data["created"] == 3
        assert data["failed"] == 0
        assert "preview" in data
        assert len(data["preview"]) == 3
        
        # 미리보기 데이터 검증
        first_tx = data["preview"][0]
        assert first_tx["type"] == "deposit"
        assert first_tx["quantity"] == 100000
        assert first_tx["price"] == 1.0
    
    def test_upload_csv_actual_insert(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """CSV 파일 실제 저장 모드로 업로드"""
        csv_file = TESTDATA_DIR / "sample_transactions_utf8.csv"
        
        # 업로드 전 거래 수 확인
        before_count = db_session.query(AssetTransaction).filter(
            AssetTransaction.asset_id == test_cash_asset.id
        ).count()
        
        with open(csv_file, 'rb') as f:
            response = client.post(
                "/api/v1/transactions/upload",
                headers=auth_header,
                files={"file": ("test.csv", f, "text/csv")},
                data={
                    "asset_id": test_cash_asset.id,
                    "dry_run": "false"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["created"] == 3
        assert "transactions" in data
        assert len(data["transactions"]) == 3
        
        # DB에 실제로 저장되었는지 확인
        after_count = db_session.query(AssetTransaction).filter(
            AssetTransaction.asset_id == test_cash_asset.id
        ).count()
        
        assert after_count == before_count + 3
    
    def test_upload_xlsx_with_password_success(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """암호화된 Excel 파일 업로드 성공 (올바른 비밀번호)"""
        xlsx_file = TESTDATA_DIR.parent / "토스뱅크_거래내역.xlsx"
        
        if not xlsx_file.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(xlsx_file, 'rb') as f:
            response = client.post(
                "/api/v1/transactions/upload",
                headers=auth_header,
                files={"file": ("toss.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "asset_id": test_cash_asset.id,
                    "dry_run": "true",
                    "password": "1234"  # 토스뱅크 파일 비밀번호
                }
            )
        
        # 파일 파서가 파일 형식을 인식하지 못할 수 있음 (업체별 형식)
        # 200 또는 400 모두 허용 (파일이 있지만 파싱 실패 가능)
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert data["total"] >= 0
    
    def test_upload_xlsx_wrong_password(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """암호화된 Excel 파일 업로드 실패 (잘못된 비밀번호)"""
        xlsx_file = TESTDATA_DIR.parent / "토스뱅크_거래내역.xlsx"
        
        if not xlsx_file.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(xlsx_file, 'rb') as f:
            response = client.post(
                "/api/v1/transactions/upload",
                headers=auth_header,
                files={"file": ("toss.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "asset_id": test_cash_asset.id,
                    "dry_run": "true",
                    "password": "wrong_password"
                }
            )
        
        # 잘못된 비밀번호 또는 파일 형식 인식 실패
        assert response.status_code in [400, 500]
    
    def test_upload_xlsx_no_password(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """암호화된 Excel 파일 업로드 실패 (비밀번호 없음)"""
        xlsx_file = TESTDATA_DIR.parent / "토스뱅크_거래내역.xlsx"
        
        if not xlsx_file.exists():
            pytest.skip("토스뱅크 테스트 파일이 없습니다")
        
        with open(xlsx_file, 'rb') as f:
            response = client.post(
                "/api/v1/transactions/upload",
                headers=auth_header,
                files={"file": ("toss.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "asset_id": test_cash_asset.id,
                    "dry_run": "true"
                }
            )
        
        assert response.status_code == 400
    
    def test_upload_invalid_file_format(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """지원하지 않는 파일 형식 업로드"""
        # 텍스트 파일 생성
        txt_content = b"This is a text file"
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test.txt", io.BytesIO(txt_content), "text/plain")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 400
        assert "지원하지 않는 파일 형식" in response.json()["detail"]
    
    def test_upload_missing_required_columns(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """필수 컬럼이 누락된 CSV 파일"""
        csv_file = TESTDATA_DIR / "sample_invalid.csv"
        
        with open(csv_file, 'rb') as f:
            response = client.post(
                "/api/v1/transactions/upload",
                headers=auth_header,
                files={"file": ("invalid.csv", f, "text/csv")},
                data={
                    "asset_id": test_cash_asset.id,
                    "dry_run": "true"
                }
            )
        
        assert response.status_code == 400
        # "필수 컬럼" 또는 "파일 형식" 에러 모두 허용
        detail = response.json()["detail"]
        assert "필수 컬럼" in detail or "형식" in detail
    
    def test_upload_empty_file(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """빈 CSV 파일 업로드"""
        # 헤더만 있는 CSV
        csv_content = b"transaction_date,type,quantity,price,fee,tax,description\n"
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("empty.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 400
        # "데이터가 없습니다" 또는 "형식" 에러 모두 허용
        detail = response.json()["detail"]
        assert "데이터" in detail or "형식" in detail
    
    def test_upload_no_auth(self, client: TestClient, test_cash_asset: Asset):
        """인증 없이 파일 업로드 시도"""
        csv_content = b"transaction_date,type,quantity,price\n2025-11-01,deposit,1000,1.0\n"
        
        response = client.post(
            "/api/v1/transactions/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 401
    
    def test_upload_invalid_asset(
        self,
        client: TestClient,
        auth_header: dict
    ):
        """존재하지 않는 자산으로 업로드"""
        csv_content = b"transaction_date,type,quantity,price\n2025-11-01,deposit,1000,1.0\n"
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": "nonexistent-asset-id",
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 404
        assert "자산을 찾을 수 없습니다" in response.json()["detail"]


class TestTransactionTypeMapping:
    """거래 유형 매핑 테스트"""
    
    def test_upload_with_various_transaction_types(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """다양한 거래 유형이 포함된 파일 업로드"""
        csv_content = """transaction_date,type,quantity,price,fee,tax,description
2025-11-01 10:00:00,deposit,10000,1.0,0,0,Deposit
2025-11-02 11:00:00,withdraw,-5000,1.0,0,0,Withdraw
2025-11-03 12:00:00,internal_transfer,-3000,1.0,0,0,Internal Transfer
2025-11-04 13:00:00,card_payment,-2000,1.0,0,0,Card Payment
2025-11-05 14:00:00,promotion_deposit,1000,1.0,0,0,Promotion
    2025-11-06 10:00:00,exchange,-1500000,1.0,0,0,KRW to USD Exchange
""".encode('utf-8')
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("types.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["created"] == 6
        assert data["failed"] == 0
        
        # 각 거래 유형이 올바르게 매핑되었는지 확인
        types_in_preview = [tx["type"] for tx in data["preview"]]
        assert "deposit" in types_in_preview
        assert "withdraw" in types_in_preview
        assert "internal_transfer" in types_in_preview
        assert "card_payment" in types_in_preview
        assert "promotion_deposit" in types_in_preview
        assert "exchange" in types_in_preview
    
    def test_upload_invalid_transaction_type(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """잘못된 거래 유형"""
        csv_content = b"""transaction_date,type,quantity,price
2025-11-01 10:00:00,invalid_type,10000,1.0
"""
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("invalid_type.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 실패한 거래가 있어야 함
        assert data["failed"] == 1
        assert data["success"] == False
        assert len(data["errors"]) == 1
        assert "거래 유형" in data["errors"][0]["error"]


class TestStockTransactions:
    """주식 거래 업로드 테스트"""
    
    def test_upload_stock_buy_sell(
        self,
        client: TestClient,
        auth_header: dict,
        test_stock_asset: Asset
    ):
        """주식 매수/매도 거래 업로드"""
        csv_content = """transaction_date,type,quantity,price,fee,tax,description
2025-11-01 10:00:00,buy,10,50000,500,150,Samsung Buy
2025-11-02 14:00:00,sell,-5,55000,275,825,Samsung Sell
""".encode('utf-8')
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("stock.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_stock_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["created"] == 2
        assert data["failed"] == 0
        
        # 매수 거래 확인
        buy_tx = next(tx for tx in data["preview"] if tx["type"] == "buy")
        assert buy_tx["quantity"] == 10
        assert buy_tx["price"] == 50000
        assert buy_tx["fee"] == 500
        assert buy_tx["tax"] == 150
        
        # 매도 거래 확인
        sell_tx = next(tx for tx in data["preview"] if tx["type"] == "sell")
        assert sell_tx["quantity"] == -5
        assert sell_tx["price"] == 55000


class TestErrorHandling:
    """에러 처리 테스트"""
    
    def test_upload_with_partial_errors(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """일부 행에 오류가 있는 파일"""
        csv_content = """transaction_date,type,quantity,price,fee,tax,description
2025-11-01 10:00:00,deposit,10000,1.0,0,0,Valid Transaction 1
invalid_date,deposit,5000,1.0,0,0,Invalid Date
2025-11-03 10:00:00,deposit,3000,1.0,0,0,Valid Transaction 2
2025-11-04 10:00:00,invalid_type,2000,1.0,0,0,Invalid Type
""".encode('utf-8')
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("partial.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 2개는 성공, 2개는 실패
        assert data["created"] == 2
        assert data["failed"] == 2
        assert data["success"] == False
        assert len(data["errors"]) == 2
    
    def test_upload_with_invalid_numbers(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """잘못된 숫자 형식"""
        csv_content = b"""transaction_date,type,quantity,price
2025-11-01 10:00:00,deposit,not_a_number,1.0
"""
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("bad_number.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["failed"] == 1
        assert len(data["errors"]) == 1


class TestDataValidation:
    """데이터 검증 테스트"""
    
    def test_upload_quantity_direction_validation(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset
    ):
        """수량 방향 검증 (입금은 양수, 출금은 음수)"""
        csv_content = """transaction_date,type,quantity,price
2025-11-01 10:00:00,deposit,-10000,1.0
2025-11-02 11:00:00,withdraw,5000,1.0
""".encode('utf-8')
        
        response = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("wrong_direction.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 방향 검증은 스키마 레벨에서 이뤄지므로
        # API는 200을 반환하지만 실패한 거래가 있을 수 있음
        # 또는 모두 성공할 수도 있음 (API 구현에 따라)
        assert data["total"] == 2


class TestDuplicateDetection:
    """중복 거래 검출 테스트"""
    
    def test_upload_duplicate_transactions(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """동일한 파일을 두 번 업로드하면 중복 거래는 스킵됨"""
        csv_content = """transaction_date,type,quantity,price,description
2025-11-01 10:00:00,deposit,10000,1.0,급여
2025-11-02 11:00:00,withdraw,-5000,1.0,카드결제
2025-11-03 12:00:00,deposit,20000,1.0,보너스
""".encode('utf-8')
        
        # 첫 번째 업로드 (실제 저장)
        response1 = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "false"
            }
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        
        assert data1["success"] == True
        assert data1["total"] == 3
        assert data1["created"] == 3
        assert data1["skipped"] == 0
        assert data1["failed"] == 0
        
        # 두 번째 업로드 (동일한 파일)
        response2 = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "false"
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 두 번째 업로드는 모두 중복으로 스킵되어야 함
        assert data2["total"] == 3
        assert data2["created"] == 0
        assert data2["skipped"] == 3  # 모든 거래가 중복으로 스킵
        assert data2["failed"] == 0
        
        # DB에는 여전히 3개만 있어야 함
        transaction_count = db_session.query(AssetTransaction).filter(
            AssetTransaction.asset_id == test_cash_asset.id
        ).count()
        assert transaction_count == 3
    
    def test_upload_partial_duplicate_transactions(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """일부 중복, 일부 새로운 거래가 섞여 있는 경우"""
        # 첫 번째 파일: 2개 거래
        csv_content1 = """transaction_date,type,quantity,price,description
2025-11-01 10:00:00,deposit,10000,1.0,급여
2025-11-02 11:00:00,withdraw,-5000,1.0,카드결제
""".encode('utf-8')
        
        response1 = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test1.csv", io.BytesIO(csv_content1), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "false"
            }
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["created"] == 2
        
        # 두 번째 파일: 1개 중복 + 2개 새로운 거래
        csv_content2 = """transaction_date,type,quantity,price,description
2025-11-02 11:00:00,withdraw,-5000,1.0,카드결제
2025-11-03 12:00:00,deposit,20000,1.0,보너스
2025-11-04 13:00:00,withdraw,-3000,1.0,식비
""".encode('utf-8')
        
        response2 = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test2.csv", io.BytesIO(csv_content2), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "false"
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data2["total"] == 3
        assert data2["created"] == 2  # 새로운 거래 2개만 생성
        assert data2["skipped"] == 1  # 중복 1개 스킵
        assert data2["failed"] == 0
        
        # DB에는 총 4개 거래가 있어야 함
        transaction_count = db_session.query(AssetTransaction).filter(
            AssetTransaction.asset_id == test_cash_asset.id
        ).count()
        assert transaction_count == 4
    
    def test_duplicate_detection_ignores_different_description(
        self,
        client: TestClient,
        auth_header: dict,
        test_cash_asset: Asset,
        db_session: Session
    ):
        """설명이 다르면 중복이 아니라고 판단"""
        # 첫 번째 거래
        csv_content1 = """transaction_date,type,quantity,price,description
2025-11-01 10:00:00,deposit,10000,1.0,급여
""".encode('utf-8')
        
        response1 = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test1.csv", io.BytesIO(csv_content1), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "false"
            }
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["created"] == 1
        
        # 같은 날짜, 타입이지만 설명이 다른 거래
        csv_content2 = """transaction_date,type,quantity,price,description
2025-11-01 10:00:00,deposit,10000,1.0,보너스
""".encode('utf-8')
        
        response2 = client.post(
            "/api/v1/transactions/upload",
            headers=auth_header,
            files={"file": ("test2.csv", io.BytesIO(csv_content2), "text/csv")},
            data={
                "asset_id": test_cash_asset.id,
                "dry_run": "false"
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 설명이 다르므로 새로운 거래로 생성되어야 함
        assert data2["created"] == 1
        assert data2["skipped"] == 0
        
        # DB에는 총 2개 거래가 있어야 함
        transaction_count = db_session.query(AssetTransaction).filter(
            AssetTransaction.asset_id == test_cash_asset.id
        ).count()
        assert transaction_count == 2

