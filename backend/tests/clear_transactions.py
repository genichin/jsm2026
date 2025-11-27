"""
거래 데이터 삭제 스크립트

사용법:
    python tests/clear_transactions.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import Transaction


def clear_all_transactions():
    """모든 거래 레코드 삭제"""
    db: Session = SessionLocal()
    
    try:
        # 거래 개수 확인
        count = db.query(Transaction).count()
        print(f"현재 거래 레코드 수: {count}")
        
        if count == 0:
            print("삭제할 거래가 없습니다.")
            return
        
        # 삭제 확인
        confirm = input(f"\n{count}개의 거래를 모두 삭제하시겠습니까? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("삭제가 취소되었습니다.")
            return
        
        # 모든 거래 삭제
        deleted = db.query(Transaction).delete()
        db.commit()
        
        print(f"\n✓ {deleted}개의 거래가 삭제되었습니다.")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ 오류 발생: {str(e)}")
        raise
    finally:
        db.close()


def clear_transactions_by_user(user_id: str = None, username: str = None):
    """특정 사용자의 거래만 삭제 (user_id 또는 username 사용)"""
    db: Session = SessionLocal()
    
    try:
        from app.models import Asset, User
        
        # username으로 user_id 찾기
        if username and not user_id:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                print(f"사용자 '{username}'을 찾을 수 없습니다.")
                return
            user_id = user.id
            print(f"사용자 '{username}' (ID: {user_id}) 발견")
        
        # 사용자의 거래 개수 확인
        count = db.query(Transaction).join(Asset).filter(
            Asset.user_id == user_id
        ).count()
        
        identifier = username if username else user_id
        print(f"사용자 {identifier}의 거래 레코드 수: {count}")
        
        if count == 0:
            print("삭제할 거래가 없습니다.")
            return
        
        # 삭제 확인
        confirm = input(f"\n{count}개의 거래를 모두 삭제하시겠습니까? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("삭제가 취소되었습니다.")
            return
        
        # 사용자의 자산 ID 목록
        asset_ids = [a.id for a in db.query(Asset).filter(Asset.user_id == user_id).all()]
        
        # 해당 자산들의 거래 삭제
        deleted = db.query(Transaction).filter(
            Transaction.asset_id.in_(asset_ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        print(f"\n✓ {deleted}개의 거래가 삭제되었습니다.")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ 오류 발생: {str(e)}")
        raise
    finally:
        db.close()


def clear_transactions_by_asset(asset_id: str):
    """특정 자산의 거래만 삭제"""
    db: Session = SessionLocal()
    
    try:
        # 자산의 거래 개수 확인
        count = db.query(Transaction).filter(
            Transaction.asset_id == asset_id
        ).count()
        
        print(f"자산 {asset_id}의 거래 레코드 수: {count}")
        
        if count == 0:
            print("삭제할 거래가 없습니다.")
            return
        
        # 삭제 확인
        confirm = input(f"\n{count}개의 거래를 모두 삭제하시겠습니까? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("삭제가 취소되었습니다.")
            return
        
        # 자산의 거래 삭제
        deleted = db.query(Transaction).filter(
            Transaction.asset_id == asset_id
        ).delete()
        
        db.commit()
        
        print(f"\n✓ {deleted}개의 거래가 삭제되었습니다.")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ 오류 발생: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="거래 데이터 삭제 스크립트")
    parser.add_argument(
        "--user-id",
        type=str,
        help="특정 사용자 ID의 거래만 삭제"
    )
    parser.add_argument(
        "--username",
        type=str,
        help="특정 사용자명의 거래만 삭제"
    )
    parser.add_argument(
        "--asset-id",
        type=str,
        help="특정 자산의 거래만 삭제"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 거래 삭제"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("거래 데이터 삭제 스크립트")
    print("=" * 60)
    print()
    
    if args.user_id or args.username:
        if args.user_id and args.username:
            print("오류: --user-id와 --username은 동시에 사용할 수 없습니다.")
        else:
            clear_transactions_by_user(user_id=args.user_id, username=args.username)
    elif args.asset_id:
        clear_transactions_by_asset(args.asset_id)
    elif args.all:
        clear_all_transactions()
    else:
        print("사용법:")
        print("  모든 거래 삭제:           python tests/clear_transactions.py --all")
        print("  특정 사용자 거래 삭제:     python tests/clear_transactions.py --user-id <USER_ID>")
        print("  사용자명으로 거래 삭제:    python tests/clear_transactions.py --username <USERNAME>")
        print("  특정 자산 거래 삭제:       python tests/clear_transactions.py --asset-id <ASSET_ID>")
        print()
        print("예시:")
        print("  python tests/clear_transactions.py --all")
        print("  python tests/clear_transactions.py --user-id user123")
        print("  python tests/clear_transactions.py --username john_doe")
        print("  python tests/clear_transactions.py --asset-id asset456")
