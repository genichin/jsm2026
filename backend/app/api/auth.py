"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import bcrypt

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password, decode_access_token
from app.schemas.auth import Token, LoginRequest, RegisterRequest, UserResponse, UserUpdateRequest, ChangePasswordRequest
from app.models import User

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """현재 로그인한 사용자 가져오기"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/login", response_model=Token, summary="로그인")
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    이메일 또는 사용자명과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.
    
    - **username**: 사용자 이메일 또는 사용자명
    - **password**: 비밀번호
    
    반환값: access_token과 token_type
    """
    # 사용자 조회 - 이메일 또는 username으로 검색
    user = db.query(User).filter(
        (User.email == login_data.username) | (User.username == login_data.username)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일/사용자명 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 비밀번호 확인
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일/사용자명 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 활성 계정 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    
    # 토큰 생성
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email, 
            "user_id": user.id,
            "username": user.username,
            "is_superuser": user.is_superuser
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/token", response_model=Token, summary="토큰 발급 (OAuth2)")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 호환 토큰 엔드포인트.
    Swagger UI의 "Authorize" 버튼에서 사용됩니다.
    
    - **username**: 이메일 주소
    - **password**: 비밀번호
    """
    # 사용자 조회 (username 필드에 email을 받음)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 비밀번호 확인
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 활성 계정 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    
    # 토큰 생성
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email, 
            "user_id": user.id,
            "username": user.username,
            "is_superuser": user.is_superuser
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserResponse, summary="사용자 등록")
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    새로운 사용자를 등록합니다.
    
    - **email**: 이메일 (고유해야 함)
    - **username**: 사용자명 (고유해야 함)
    - **password**: 비밀번호 (최소 8자)
    - **full_name**: 이름 (선택사항)
    """
    # 이메일 중복 확인
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 이메일입니다"
        )
    
    # 사용자명 중복 확인
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 사용자명입니다"
        )
    
    # 비밀번호 해시
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # 사용자 생성
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/users", response_model=list[UserResponse], summary="사용자 목록 조회 (관리자)")
async def get_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    모든 사용자 목록을 조회합니다.
    
    - 인증 필요: Bearer 토큰 (관리자만)
    """
    # 관리자 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    users = db.query(User).all()
    return users


@router.get("/users/me", response_model=UserResponse, summary="내 정보 조회")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    현재 로그인한 사용자의 정보를 조회합니다.
    
    - 인증 필요: Bearer 토큰
    """
    return current_user


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT, summary="계정 삭제")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자의 계정을 삭제합니다.
    
    - 인증 필요: Bearer 토큰
    - 관련된 모든 데이터(계좌, 거래 등)도 함께 삭제됩니다 (CASCADE)
    """
    # 사용자 삭제 (CASCADE로 관련 데이터 모두 삭제됨)
    db.delete(current_user)
    db.commit()
    
    return None


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="사용자 삭제 (관리자)")
async def delete_user_by_admin(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    관리자가 특정 사용자의 계정을 삭제합니다.
    
    - 인증 필요: Bearer 토큰 (관리자만)
    - **user_id**: 삭제할 사용자 ID (UUID)
    - 관련된 모든 데이터도 함께 삭제됩니다 (CASCADE)
    """
    # 관리자 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    # 대상 사용자 조회
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    # 자기 자신 삭제 방지
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신의 계정은 삭제할 수 없습니다"
        )
    
    # 사용자 삭제
    db.delete(target_user)
    db.commit()
    
    return None


@router.patch("/users/me", response_model=UserResponse, summary="프로필 업데이트")
async def update_profile(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자의 프로필을 업데이트합니다.
    
    - 인증 필요: Bearer 토큰
    - **username**: 사용자명 (선택)
    - **full_name**: 이름 (선택)
    """
    # username 중복 체크 (변경하는 경우)
    if update_data.username and update_data.username != current_user.username:
        existing_user = db.query(User).filter(User.username == update_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 사용자명입니다"
            )
        current_user.username = update_data.username
    
    # full_name 업데이트
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    
    # profit_calc_method 필드는 제거되었습니다.
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/change-password", status_code=status.HTTP_200_OK, summary="비밀번호 변경")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자의 비밀번호를 변경합니다.
    
    - 인증 필요: Bearer 토큰
    - **current_password**: 현재 비밀번호
    - **new_password**: 새 비밀번호 (최소 6자)
    """
    # 현재 비밀번호 확인
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다"
        )
    
    # 새 비밀번호 길이 체크
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호는 최소 6자 이상이어야 합니다"
        )
    
    # 비밀번호 해시화 및 업데이트
    hashed_password = bcrypt.hashpw(password_data.new_password.encode('utf-8'), bcrypt.gensalt())
    current_user.hashed_password = hashed_password.decode('utf-8')
    
    db.commit()
    
    return {"message": "비밀번호가 성공적으로 변경되었습니다"}


@router.patch("/users/{user_id}/toggle-active", response_model=UserResponse, summary="사용자 활성화/비활성화 (관리자)")
async def toggle_user_active(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    관리자가 특정 사용자의 활성화 상태를 토글합니다.
    
    - 인증 필요: Bearer 토큰 (관리자만)
    - **user_id**: 대상 사용자 ID (UUID)
    - 활성 상태이면 비활성으로, 비활성 상태이면 활성으로 변경
    """
    # 관리자 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    # 대상 사용자 조회
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    # 자기 자신의 상태 변경 방지
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신의 계정 상태는 변경할 수 없습니다"
        )
    
    # 활성화 상태 토글
    target_user.is_active = not target_user.is_active
    
    db.commit()
    db.refresh(target_user)
    
    return target_user


@router.patch("/users/{user_id}/toggle-superuser", response_model=UserResponse, summary="사용자 관리자 권한 변경 (관리자)")
async def toggle_user_superuser(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    관리자가 특정 사용자의 관리자 권한을 토글합니다.
    
    - 인증 필요: Bearer 토큰 (관리자만)
    - **user_id**: 대상 사용자 ID (UUID)
    - 일반 사용자이면 관리자로, 관리자이면 일반 사용자로 변경
    """
    # 관리자 권한 확인
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    # 대상 사용자 조회
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    # 자기 자신의 권한 변경 방지
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신의 관리자 권한은 변경할 수 없습니다"
        )
    
    # 관리자 권한 토글
    target_user.is_superuser = not target_user.is_superuser
    
    db.commit()
    db.refresh(target_user)
    
    return target_user
