"""Request/response models (pydantic)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Priority = Literal["P1", "P2", "P3", "P4"]
Role = Literal["reporter", "engineer", "qa"]


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=4)
    role: Role


class ComponentCreate(BaseModel):
    name: str = Field(min_length=1)
    parent: Optional[str] = None  # full path of the parent, e.g. "Mail"


class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    steps_to_reproduce: str = ""
    expected_result: str = ""
    actual_result: str = ""
    component: str  # full path, e.g. "Mail > Sync"
    priority: Priority = "P3"
    assignee: Optional[str] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    assignee: Optional[str] = None
    state: Optional[str] = None  # PLANTED-DEFECT-1 lives in how this is handled


class TransitionRequest(BaseModel):
    target: str


class DuplicateRequest(BaseModel):
    duplicate_of: int


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


class TestCaseCreate(BaseModel):
    title: str = Field(min_length=3)
    component: str
    steps: str = ""
    expected: str = ""


class SuiteCreate(BaseModel):
    name: str = Field(min_length=2)
    case_ids: list[int] = []


class TestRunCreate(BaseModel):
    suite_id: int


class TestResultCreate(BaseModel):
    case_id: int
    status: Literal["passed", "failed", "skipped"]
    issue_id: Optional[int] = None
    duration_ms: int = Field(default=0, ge=0)
