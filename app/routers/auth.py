from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import AccountDep, DbDep
from app.models import Account
from app.schemas import LoginIn, MeOut, PreferencesIn
from app.security import make_token, verify_password

router = APIRouter(tags=["auth"])
settings = get_settings()
COOKIE = "access_token"


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        COOKIE,
        token,
        max_age=settings.jwt_expiry_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain or None,
        path="/",
    )


@router.post("/auth/login", response_model=MeOut)
async def login(body: LoginIn, resp: Response, db: DbDep):
    account = await db.scalar(select(Account).where(Account.username == body.username))
    if account is None or not verify_password(body.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    _set_cookie(resp, make_token(str(account.id)))
    return account


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(resp: Response):
    resp.delete_cookie(COOKIE, path="/", domain=settings.cookie_domain or None)


@router.get("/auth/me", response_model=MeOut)
async def me(account: AccountDep):
    return account


@router.patch("/me/preferences", response_model=MeOut)
async def update_preferences(body: PreferencesIn, account: AccountDep, db: DbDep):
    if body.theme_pref is not None:
        account.theme_pref = body.theme_pref
    if body.lang_pref is not None:
        account.lang_pref = body.lang_pref
    await db.flush()
    return account
