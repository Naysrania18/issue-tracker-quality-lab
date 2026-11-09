"""Server-rendered web UI (Jinja). Element ids are stable so Selenium tests can rely on them."""
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.deps import get_db, get_issue_service, get_user_service
from app.services import ComponentService, Conflict, Forbidden, NotFound
from app.workflow import InvalidTransition

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

DOMAIN_ERRORS = (NotFound, Conflict, Forbidden, InvalidTransition)


def web_user(request: Request, users=Depends(get_user_service)):
    token = request.cookies.get("token")
    return users.by_token(token) if token else None


def _login_redirect() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


@router.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/issues", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "login.html", {"error": error, "user": None})


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...), users=Depends(get_user_service)):
    try:
        token = users.login(username, password)
    except Forbidden:
        return RedirectResponse("/login?error=Invalid+username+or+password", status_code=303)
    response = RedirectResponse("/issues", status_code=303)
    response.set_cookie("token", token, httponly=True)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("token")
    return response


@router.get("/issues", response_class=HTMLResponse)
def issue_list(
    request: Request,
    q: str = "",
    state: str = "",
    priority: str = "",
    component: str = "",
    user=Depends(web_user),
    issues=Depends(get_issue_service),
    conn=Depends(get_db),
):
    if user is None:
        return _login_redirect()
    found = issues.search(q or None, state or None, priority or None, component or None)
    ctx = {
        "user": user, "issues": found, "q": q, "state": state, "priority": priority,
        "component": component, "components": ComponentService(conn).list_paths(),
    }
    return templates.TemplateResponse(request, "issues.html", ctx)


@router.get("/issues/new", response_class=HTMLResponse)
def new_issue_page(request: Request, user=Depends(web_user), conn=Depends(get_db), error: str = ""):
    if user is None:
        return _login_redirect()
    ctx = {"user": user, "components": ComponentService(conn).list_paths(), "error": error}
    return templates.TemplateResponse(request, "new_issue.html", ctx)


@router.post("/issues/new")
def create_issue(
    title: str = Form(...),
    description: str = Form(""),
    steps_to_reproduce: str = Form(""),
    expected_result: str = Form(""),
    actual_result: str = Form(""),
    component: str = Form(...),
    priority: str = Form("P3"),
    user=Depends(web_user),
    issues=Depends(get_issue_service),
):
    if user is None:
        return _login_redirect()
    if len(title.strip()) < 3:
        return RedirectResponse("/issues/new?error=Title+must+be+at+least+3+characters", status_code=303)
    created = issues.create(
        {
            "title": title, "description": description, "steps_to_reproduce": steps_to_reproduce,
            "expected_result": expected_result, "actual_result": actual_result,
            "component": component, "priority": priority,
        },
        user,
    )
    return RedirectResponse(f"/issues/{created['id']}", status_code=303)


@router.get("/issues/{issue_id}", response_class=HTMLResponse)
def issue_detail(
    request: Request, issue_id: int, error: str = "", user=Depends(web_user),
    issues=Depends(get_issue_service),
):
    if user is None:
        return _login_redirect()
    try:
        issue = issues.get(issue_id)
    except NotFound:
        return HTMLResponse("<h1 id='not-found'>Issue not found</h1>", status_code=404)
    ctx = {
        "user": user, "issue": issue, "history": issues.history(issue_id),
        "comments": issues.comments(issue_id), "error": error,
    }
    return templates.TemplateResponse(request, "issue_detail.html", ctx)


def _back(issue_id: int, error: Optional[str] = None) -> RedirectResponse:
    suffix = f"?error={quote(error)}" if error else ""
    return RedirectResponse(f"/issues/{issue_id}{suffix}", status_code=303)


@router.post("/issues/{issue_id}/transition")
def transition(issue_id: int, target: str = Form(...), user=Depends(web_user), issues=Depends(get_issue_service)):
    if user is None:
        return _login_redirect()
    try:
        issues.transition(issue_id, target, user)
    except DOMAIN_ERRORS as exc:
        return _back(issue_id, str(exc))
    return _back(issue_id)


@router.post("/issues/{issue_id}/comment")
def comment(issue_id: int, body: str = Form(...), user=Depends(web_user), issues=Depends(get_issue_service)):
    if user is None:
        return _login_redirect()
    if not body.strip():
        return _back(issue_id, "Comment cannot be empty")
    issues.add_comment(issue_id, body, user)
    return _back(issue_id)


@router.post("/issues/{issue_id}/duplicate")
def duplicate(issue_id: int, duplicate_of: int = Form(...), user=Depends(web_user), issues=Depends(get_issue_service)):
    if user is None:
        return _login_redirect()
    if user["role"] == "reporter":
        return _back(issue_id, "Reporters cannot mark duplicates")
    try:
        issues.mark_duplicate(issue_id, duplicate_of, user)
    except DOMAIN_ERRORS as exc:
        return _back(issue_id, str(exc))
    return _back(issue_id)
