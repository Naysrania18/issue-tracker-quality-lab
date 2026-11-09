"""FastAPI dependencies: database connection, services, current user, role checks."""
from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Request

from app.database import connect
from app.services import IssueService, TestService, UserService


def get_db(request: Request) -> Iterator:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        # Let the notification consumer process whatever the request published.
        request.app.state.consumer.drain(request.app.state.bus)
        conn.close()


def get_issue_service(request: Request, conn=Depends(get_db)) -> IssueService:
    return IssueService(conn, request.app.state.bus)


def get_test_service(request: Request, conn=Depends(get_db)) -> TestService:
    return TestService(conn, request.app.state.bus)


def get_user_service(conn=Depends(get_db)) -> UserService:
    return UserService(conn)


def _token_from(request: Request) -> Optional[str]:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get("token")


def current_user(request: Request, users: UserService = Depends(get_user_service)):
    token = _token_from(request)
    user = users.by_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_roles(*roles: str):
    def checker(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(roles)}")
        return user

    return checker
