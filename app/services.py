"""Business logic. Both the JSON API and the web UI call these classes."""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from app.events import Event, EventBus, EventType
from app.workflow import InvalidTransition, State, validate_transition

SEP = " > "


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class Forbidden(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 10_000).hex()


class UserService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, username: str, password: str, role: str) -> dict[str, Any]:
        if self.conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise Conflict(f"User '{username}' already exists")
        salt = secrets.token_hex(8)
        cur = self.conn.execute(
            "INSERT INTO users (username, role, salt, password_hash) VALUES (?,?,?,?)",
            (username, role, salt, hash_password(password, salt)),
        )
        self.conn.commit()
        return {"id": cur.lastrowid, "username": username, "role": role}

    def login(self, username: str, password: str) -> str:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row is None or row["password_hash"] != hash_password(password, row["salt"]):
            raise Forbidden("Invalid username or password")
        token = secrets.token_urlsafe(24)
        self.conn.execute("UPDATE users SET token=? WHERE id=?", (token, row["id"]))
        self.conn.commit()
        return token

    def by_token(self, token: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()

    def by_username(self, username: str) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row is None:
            raise NotFound(f"User '{username}' not found")
        return row


class ComponentService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, name: str, parent_path: Optional[str] = None) -> int:
        parent_id = self.resolve(parent_path) if parent_path else None
        exists = self.conn.execute(
            "SELECT 1 FROM components WHERE name=? AND parent_id IS ?", (name, parent_id)
        ).fetchone()
        if exists:
            raise Conflict("Component already exists")
        cur = self.conn.execute(
            "INSERT INTO components (name, parent_id) VALUES (?,?)", (name, parent_id)
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def resolve(self, path: str) -> int:
        """Turn 'Mail > Sync' into a component id."""
        parent_id: Optional[int] = None
        for part in [p.strip() for p in path.split(">")]:
            row = self.conn.execute(
                "SELECT id FROM components WHERE name=? AND parent_id IS ?", (part, parent_id)
            ).fetchone()
            if row is None:
                raise NotFound(f"Component '{path}' not found")
            parent_id = row["id"]
        return int(parent_id or 0)

    def path_of(self, component_id: int) -> str:
        parts: list[str] = []
        current: Optional[int] = component_id
        while current is not None:
            row = self.conn.execute(
                "SELECT name, parent_id FROM components WHERE id=?", (current,)
            ).fetchone()
            parts.append(row["name"])
            current = row["parent_id"]
        return SEP.join(reversed(parts))

    def list_paths(self) -> list[str]:
        ids = [r["id"] for r in self.conn.execute("SELECT id FROM components ORDER BY id")]
        return sorted(self.path_of(i) for i in ids)


class IssueService:
    def __init__(self, conn: sqlite3.Connection, bus: EventBus) -> None:
        self.conn = conn
        self.bus = bus
        self.components = ComponentService(conn)
        self.users = UserService(conn)

    # ---------- helpers ----------
    def _log(self, issue_id: int, actor: str, field: str, old: Any, new: Any) -> None:
        self.conn.execute(
            "INSERT INTO history (issue_id, at, actor, field, old_value, new_value) "
            "VALUES (?,?,?,?,?,?)",
            (issue_id, now(), actor, field, None if old is None else str(old), str(new)),
        )

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        assignee = None
        if row["assignee_id"]:
            assignee = self.conn.execute(
                "SELECT username FROM users WHERE id=?", (row["assignee_id"],)
            ).fetchone()["username"]
        reporter = self.conn.execute(
            "SELECT username FROM users WHERE id=?", (row["reporter_id"],)
        ).fetchone()["username"]
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "steps_to_reproduce": row["steps_to_reproduce"],
            "expected_result": row["expected_result"],
            "actual_result": row["actual_result"],
            "component": self.components.path_of(row["component_id"]),
            "priority": row["priority"],
            "assignee": assignee,
            "reporter": reporter,
            "state": row["state"],
            "duplicate_of": row["duplicate_of"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row(self, issue_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
        if row is None:
            raise NotFound(f"Issue {issue_id} not found")
        return row

    # ---------- queries ----------
    def get(self, issue_id: int) -> dict[str, Any]:
        return self._row_to_dict(self._row(issue_id))

    def search(
        self,
        q: Optional[str] = None,
        state: Optional[str] = None,
        priority: Optional[str] = None,
        component: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT issues.* FROM issues WHERE 1=1"
        args: list[Any] = []
        if q:
            # PLANTED-DEFECT-3 (part a): LIKE on SQLite is case-insensitive for ASCII, so
            # use instr() which is case-SENSITIVE -> searching "crash" misses "Crash".
            sql += " AND (instr(title, ?) > 0 OR instr(description, ?) > 0)"
            args += [q, q]
        if state:
            sql += " AND state = ?"
            args.append(state)
        if priority:
            # PLANTED-DEFECT-3 (part b): "<=" instead of "=" returns higher priorities too.
            sql += " AND priority <= ?"
            args.append(priority)
        if component:
            ids = self._component_subtree(self.components.resolve(component))
            sql += f" AND component_id IN ({','.join('?' * len(ids))})"
            args += ids
        if assignee:
            sql += " AND assignee_id = (SELECT id FROM users WHERE username = ?)"
            args.append(assignee)
        sql += " ORDER BY id"
        return [self._row_to_dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def _component_subtree(self, root_id: int) -> list[int]:
        found = [root_id]
        for cid in found:
            found += [
                r["id"]
                for r in self.conn.execute("SELECT id FROM components WHERE parent_id=?", (cid,))
            ]
        return found

    def history(self, issue_id: int) -> list[dict[str, Any]]:
        self._row(issue_id)
        rows = self.conn.execute(
            "SELECT at, actor, field, old_value, new_value FROM history "
            "WHERE issue_id=? ORDER BY id",
            (issue_id,),
        )
        return [dict(r) for r in rows]

    def comments(self, issue_id: int) -> list[dict[str, Any]]:
        self._row(issue_id)
        rows = self.conn.execute(
            "SELECT author, body, created_at FROM comments WHERE issue_id=? ORDER BY id",
            (issue_id,),
        )
        return [dict(r) for r in rows]

    # ---------- commands ----------
    def create(self, data: dict[str, Any], reporter: sqlite3.Row) -> dict[str, Any]:
        component_id = self.components.resolve(data["component"])
        assignee_id = None
        if data.get("assignee"):
            assignee_id = self.users.by_username(data["assignee"])["id"]
        stamp = now()
        cur = self.conn.execute(
            "INSERT INTO issues (title, description, steps_to_reproduce, expected_result, "
            "actual_result, component_id, priority, assignee_id, reporter_id, state, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                data["title"], data.get("description", ""), data.get("steps_to_reproduce", ""),
                data.get("expected_result", ""), data.get("actual_result", ""), component_id,
                data.get("priority", "P3"), assignee_id, reporter["id"], State.ANALYZE.value,
                stamp, stamp,
            ),
        )
        issue_id = int(cur.lastrowid or 0)
        self._log(issue_id, reporter["username"], "created", None, State.ANALYZE.value)
        self.conn.commit()
        self.bus.publish(
            Event(EventType.ISSUE_CREATED, {"issue_id": issue_id, "title": data["title"]})
        )
        return self.get(issue_id)

    def update(self, issue_id: int, changes: dict[str, Any], actor: sqlite3.Row) -> dict[str, Any]:
        row = self._row(issue_id)
        for field in ("title", "description", "priority"):
            if changes.get(field) is not None and changes[field] != row[field]:
                self.conn.execute(
                    f"UPDATE issues SET {field}=?, updated_at=? WHERE id=?",
                    (changes[field], now(), issue_id),
                )
                self._log(issue_id, actor["username"], field, row[field], changes[field])
        if changes.get("assignee") is not None:
            assignee = self.users.by_username(changes["assignee"])
            self.conn.execute(
                "UPDATE issues SET assignee_id=?, updated_at=? WHERE id=?",
                (assignee["id"], now(), issue_id),
            )
            self._log(issue_id, actor["username"], "assignee", row["assignee_id"], assignee["username"])
        if changes.get("state") is not None:
            # PLANTED-DEFECT-1: the state is written directly, skipping validate_transition().
            self.conn.execute(
                "UPDATE issues SET state=?, updated_at=? WHERE id=?",
                (changes["state"], now(), issue_id),
            )
            self._log(issue_id, actor["username"], "state", row["state"], changes["state"])
        self.conn.commit()
        return self.get(issue_id)

    def transition(self, issue_id: int, target: str, actor: sqlite3.Row) -> dict[str, Any]:
        row = self._row(issue_id)
        try:
            target_state = State(target)
        except ValueError:
            raise InvalidTransition(f"Unknown state '{target}'")
        if actor["role"] == "reporter":
            raise Forbidden("Reporters cannot change issue state")
        current = State(row["state"])
        validate_transition(current, target_state, actor["role"])
        self.conn.execute(
            "UPDATE issues SET state=?, updated_at=? WHERE id=?",
            (target_state.value, now(), issue_id),
        )
        self._log(issue_id, actor["username"], "state", current.value, target_state.value)
        self.conn.commit()
        seq = self.bus.next_sequence(issue_id)
        self.bus.publish(
            Event(
                EventType.STATE_CHANGED,
                {"issue_id": issue_id, "old": current.value, "new": target_state.value},
                sequence=seq,
            )
        )
        return self.get(issue_id)

    def mark_duplicate(self, issue_id: int, duplicate_of: int, actor: sqlite3.Row) -> dict[str, Any]:
        row = self._row(issue_id)
        self._row(duplicate_of)  # 404 when the original does not exist
        # PLANTED-DEFECT-2: missing check `issue_id == duplicate_of`.
        self.conn.execute(
            "UPDATE issues SET duplicate_of=?, updated_at=? WHERE id=?",
            (duplicate_of, now(), issue_id),
        )
        self._log(issue_id, actor["username"], "duplicate_of", row["duplicate_of"], duplicate_of)
        self.conn.commit()
        return self.get(issue_id)

    def add_comment(self, issue_id: int, body: str, actor: sqlite3.Row) -> dict[str, Any]:
        self._row(issue_id)
        stamp = now()
        self.conn.execute(
            "INSERT INTO comments (issue_id, author, body, created_at) VALUES (?,?,?,?)",
            (issue_id, actor["username"], body, stamp),
        )
        self.conn.commit()
        return {"author": actor["username"], "body": body, "created_at": stamp}


class TestService:
    """Test case management: cases, suites, runs and results."""

    __test__ = False  # stop pytest from collecting this class

    def __init__(self, conn: sqlite3.Connection, bus: EventBus) -> None:
        self.conn = conn
        self.bus = bus
        self.components = ComponentService(conn)

    def create_case(self, title: str, component: str, steps: str, expected: str) -> dict[str, Any]:
        cid = self.components.resolve(component)
        cur = self.conn.execute(
            "INSERT INTO test_cases (title, component_id, steps, expected) VALUES (?,?,?,?)",
            (title, cid, steps, expected),
        )
        self.conn.commit()
        return {"id": cur.lastrowid, "title": title, "component": component}

    def list_cases(self, component: Optional[str] = None) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM test_cases ORDER BY id").fetchall()
        result = [
            {
                "id": r["id"], "title": r["title"], "steps": r["steps"], "expected": r["expected"],
                "component": self.components.path_of(r["component_id"]),
            }
            for r in rows
        ]
        if component:
            result = [c for c in result if c["component"].startswith(component)]
        return result

    def create_suite(self, name: str, case_ids: list[int]) -> dict[str, Any]:
        if self.conn.execute("SELECT 1 FROM suites WHERE name=?", (name,)).fetchone():
            raise Conflict(f"Suite '{name}' already exists")
        cur = self.conn.execute("INSERT INTO suites (name) VALUES (?)", (name,))
        suite_id = int(cur.lastrowid or 0)
        for case_id in case_ids:
            if not self.conn.execute("SELECT 1 FROM test_cases WHERE id=?", (case_id,)).fetchone():
                self.conn.rollback()
                raise NotFound(f"Test case {case_id} not found")
            self.conn.execute(
                "INSERT INTO suite_cases (suite_id, case_id) VALUES (?,?)", (suite_id, case_id)
            )
        self.conn.commit()
        return {"id": suite_id, "name": name, "case_ids": case_ids}

    def list_suites(self) -> list[dict[str, Any]]:
        out = []
        for s in self.conn.execute("SELECT * FROM suites ORDER BY id").fetchall():
            ids = [
                r["case_id"]
                for r in self.conn.execute(
                    "SELECT case_id FROM suite_cases WHERE suite_id=?", (s["id"],)
                )
            ]
            out.append({"id": s["id"], "name": s["name"], "case_ids": ids})
        return out

    def start_run(self, suite_id: int) -> dict[str, Any]:
        if not self.conn.execute("SELECT 1 FROM suites WHERE id=?", (suite_id,)).fetchone():
            raise NotFound(f"Suite {suite_id} not found")
        cur = self.conn.execute(
            "INSERT INTO test_runs (suite_id, started_at) VALUES (?,?)", (suite_id, now())
        )
        self.conn.commit()
        return self.get_run(int(cur.lastrowid or 0))

    def add_result(self, run_id: int, data: dict[str, Any]) -> dict[str, Any]:
        run = self._run_row(run_id)
        if run["status"] != "running":
            raise Conflict("Run is already completed")
        if not self.conn.execute(
            "SELECT 1 FROM suite_cases WHERE suite_id=? AND case_id=?", (run["suite_id"], data["case_id"])
        ).fetchone():
            raise NotFound(f"Case {data['case_id']} is not part of this run's suite")
        if data.get("issue_id") and not self.conn.execute(
            "SELECT 1 FROM issues WHERE id=?", (data["issue_id"],)
        ).fetchone():
            raise NotFound(f"Issue {data['issue_id']} not found")
        self.conn.execute(
            "INSERT INTO test_results (run_id, case_id, status, issue_id, duration_ms) "
            "VALUES (?,?,?,?,?)",
            (run_id, data["case_id"], data["status"], data.get("issue_id"), data.get("duration_ms", 0)),
        )
        self.conn.commit()
        return self.get_run(run_id)

    def complete_run(self, run_id: int) -> dict[str, Any]:
        run = self._run_row(run_id)
        if run["status"] != "running":
            raise Conflict("Run is already completed")
        statuses = [
            r["status"]
            for r in self.conn.execute("SELECT status FROM test_results WHERE run_id=?", (run_id,))
        ]
        final = "failed" if "failed" in statuses else "passed"
        self.conn.execute(
            "UPDATE test_runs SET status=?, completed_at=? WHERE id=?", (final, now(), run_id)
        )
        self.conn.commit()
        self.bus.publish(Event(EventType.TEST_RUN_COMPLETED, {"run_id": run_id, "status": final}))
        return self.get_run(run_id)

    def _run_row(self, run_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM test_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise NotFound(f"Run {run_id} not found")
        return row

    def get_run(self, run_id: int) -> dict[str, Any]:
        run = self._run_row(run_id)
        results = [
            dict(r)
            for r in self.conn.execute(
                "SELECT case_id, status, issue_id, duration_ms FROM test_results "
                "WHERE run_id=? ORDER BY id",
                (run_id,),
            )
        ]
        return {
            "id": run["id"], "suite_id": run["suite_id"], "status": run["status"],
            "started_at": run["started_at"], "completed_at": run["completed_at"],
            "results": results,
        }

    def list_runs(self) -> list[dict[str, Any]]:
        return [self.get_run(r["id"]) for r in self.conn.execute("SELECT id FROM test_runs ORDER BY id")]
