"""Router de autenticación: /api/auth/*."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import CurrentUserId
from app.core.config import settings
from app.schemas.auth import (
    LoginRequest,
    MembershipOut,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, *, token: str, expires_at) -> None:
    response.set_cookie(
        key=auth_service.REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        path=auth_service.REFRESH_COOKIE_PATH,
        expires=expires_at,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=auth_service.REFRESH_COOKIE_NAME, path=auth_service.REFRESH_COOKIE_PATH
    )


def _membership_out(row) -> MembershipOut:
    return MembershipOut(
        id=row.id,
        legal_name=row.legal_name,
        trade_name=row.trade_name,
        slug=row.slug,
        status=row.status,
        visibility=row.visibility,
        completion_pct=row.completion_pct,
        member_id=row.member_id,
        role_codes=row.role_codes or [],
        capabilities=row.capabilities or [],
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: RegisterRequest, request: Request, response: Response
) -> RegisterResponse:
    try:
        result = await auth_service.register(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    _set_refresh_cookie(
        response, token=result.refresh_token, expires_at=result.refresh_expires_at
    )

    me = await auth_service.get_me(result.user_id)
    return RegisterResponse(
        access_token=result.access_token,
        user=UserOut(
            id=me.user_id,
            email=me.email,
            first_name=me.first_name,
            last_name=me.last_name,
            full_name=me.full_name,
            locale=me.locale,
            last_org_id=me.last_org_id,
            memberships=[_membership_out(m) for m in me.memberships],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response
) -> TokenResponse:
    try:
        result = await auth_service.login(
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    _set_refresh_cookie(
        response, token=result.refresh_token, expires_at=result.refresh_expires_at
    )
    return TokenResponse(access_token=result.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> TokenResponse:
    token = request.cookies.get(auth_service.REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sin sesión que refrescar"
        )

    try:
        result = await auth_service.refresh(
            refresh_token=token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except auth_service.AuthError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    _set_refresh_cookie(
        response, token=result.refresh_token, expires_at=result.refresh_expires_at
    )
    return TokenResponse(access_token=result.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(auth_service.REFRESH_COOKIE_NAME)
    if token:
        await auth_service.logout(refresh_token=token)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=MeResponse)
async def me(user_id: CurrentUserId) -> MeResponse:
    try:
        result = await auth_service.get_me(user_id)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return MeResponse(
        user=UserOut(
            id=result.user_id,
            email=result.email,
            first_name=result.first_name,
            last_name=result.last_name,
            full_name=result.full_name,
            locale=result.locale,
            last_org_id=result.last_org_id,
            memberships=[_membership_out(m) for m in result.memberships],
        ),
        is_platform_admin=result.is_platform_admin,
    )
