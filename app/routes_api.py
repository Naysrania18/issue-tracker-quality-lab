"""JSON API. Domain errors are translated into HTTP status codes in main.py."""
from typing import Optional

from fastapi import APIRouter, Depends

from app.deps import (
    current_user, get_db, get_issue_service, get_test_service, get_user_service, require_roles,
)
from app.schemas import (
    CommentCreate, ComponentCreate, DuplicateRequest, IssueCreate, IssueUpdate, LoginRequest,
    SuiteCreate, TestCaseCreate, TestResultCreate, TestRunCreate, TransitionRequest, UserCreate,
)
from app.services import ComponentService

router = APIRouter()


@router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@router.post("/auth/login", tags=["auth"])
def login(body: LoginRequest, users=Depends(get_user_service)):
    return {"token": users.login(body.username, body.password)}


@router.post("/users", status_code=201, tags=["auth"])
def create_user(body: UserCreate, users=Depends(get_user_service)):
    return users.create(body.username, body.password, body.role)


@router.get("/me", tags=["auth"])
def me(user=Depends(current_user)):
    return {"username": user["username"], "role": user["role"]}


@router.get("/components", tags=["components"])
def list_components(conn=Depends(get_db), user=Depends(current_user)):
    return ComponentService(conn).list_paths()


@router.post("/components", status_code=201, tags=["components"])
def create_component(
    body: ComponentCreate, conn=Depends(get_db), user=Depends(require_roles("engineer", "qa"))
):
    return {"id": ComponentService(conn).create(body.name, body.parent)}


@router.get("/issues", tags=["issues"])
def search_issues(
    q: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None,
    component: Optional[str] = None,
    assignee: Optional[str] = None,
    issues=Depends(get_issue_service),
    user=Depends(current_user),
):
    return issues.search(q, state, priority, component, assignee)


@router.post("/issues", status_code=201, tags=["issues"])
def create_issue(body: IssueCreate, issues=Depends(get_issue_service), user=Depends(current_user)):
    return issues.create(body.model_dump(), user)


@router.get("/issues/{issue_id}", tags=["issues"])
def get_issue(issue_id: int, issues=Depends(get_issue_service), user=Depends(current_user)):
    return issues.get(issue_id)


@router.patch("/issues/{issue_id}", tags=["issues"])
def update_issue(
    issue_id: int,
    body: IssueUpdate,
    issues=Depends(get_issue_service),
    user=Depends(require_roles("engineer", "qa")),
):
    return issues.update(issue_id, body.model_dump(exclude_unset=True), user)


@router.post("/issues/{issue_id}/transition", tags=["issues"])
def transition_issue(
    issue_id: int, body: TransitionRequest, issues=Depends(get_issue_service), user=Depends(current_user)
):
    return issues.transition(issue_id, body.target, user)


@router.post("/issues/{issue_id}/duplicate", tags=["issues"])
def mark_duplicate(
    issue_id: int,
    body: DuplicateRequest,
    issues=Depends(get_issue_service),
    user=Depends(require_roles("engineer", "qa")),
):
    return issues.mark_duplicate(issue_id, body.duplicate_of, user)


@router.get("/issues/{issue_id}/history", tags=["issues"])
def issue_history(issue_id: int, issues=Depends(get_issue_service), user=Depends(current_user)):
    return issues.history(issue_id)


@router.get("/issues/{issue_id}/comments", tags=["issues"])
def list_comments(issue_id: int, issues=Depends(get_issue_service), user=Depends(current_user)):
    return issues.comments(issue_id)


@router.post("/issues/{issue_id}/comments", status_code=201, tags=["issues"])
def add_comment(
    issue_id: int, body: CommentCreate, issues=Depends(get_issue_service), user=Depends(current_user)
):
    return issues.add_comment(issue_id, body.body, user)


@router.get("/test-cases", tags=["tests"])
def list_cases(component: Optional[str] = None, tests=Depends(get_test_service), user=Depends(current_user)):
    return tests.list_cases(component)


@router.post("/test-cases", status_code=201, tags=["tests"])
def create_case(body: TestCaseCreate, tests=Depends(get_test_service), user=Depends(require_roles("qa"))):
    return tests.create_case(body.title, body.component, body.steps, body.expected)


@router.get("/suites", tags=["tests"])
def list_suites(tests=Depends(get_test_service), user=Depends(current_user)):
    return tests.list_suites()


@router.post("/suites", status_code=201, tags=["tests"])
def create_suite(body: SuiteCreate, tests=Depends(get_test_service), user=Depends(require_roles("qa"))):
    return tests.create_suite(body.name, body.case_ids)


@router.get("/test-runs", tags=["tests"])
def list_runs(tests=Depends(get_test_service), user=Depends(current_user)):
    return tests.list_runs()


@router.post("/test-runs", status_code=201, tags=["tests"])
def start_run(body: TestRunCreate, tests=Depends(get_test_service), user=Depends(require_roles("qa"))):
    return tests.start_run(body.suite_id)


@router.get("/test-runs/{run_id}", tags=["tests"])
def get_run(run_id: int, tests=Depends(get_test_service), user=Depends(current_user)):
    return tests.get_run(run_id)


@router.post("/test-runs/{run_id}/results", status_code=201, tags=["tests"])
def add_result(
    run_id: int, body: TestResultCreate, tests=Depends(get_test_service), user=Depends(require_roles("qa"))
):
    return tests.add_result(run_id, body.model_dump())


@router.post("/test-runs/{run_id}/complete", tags=["tests"])
def complete_run(run_id: int, tests=Depends(get_test_service), user=Depends(require_roles("qa"))):
    return tests.complete_run(run_id)


@router.get("/notifications", tags=["meta"])
def notifications(conn=Depends(get_db), user=Depends(current_user)):
    rows = conn.execute("SELECT * FROM notifications ORDER BY id").fetchall()
    return [dict(r) for r in rows]
