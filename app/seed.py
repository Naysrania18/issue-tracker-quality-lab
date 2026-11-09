"""Fill a database with fake data:  python -m app.seed [--db tracker.db] [--issues 40]"""
import argparse
import random

from faker import Faker

from app.database import connect, init_db
from app.events import EventBus
from app.services import ComponentService, IssueService, TestService, UserService

DEMO_PASSWORD = "demo-pass"
USERS = [("rita", "reporter"), ("rob", "reporter"), ("erin", "engineer"), ("eli", "engineer"),
         ("quinn", "qa"), ("quentin", "qa")]
COMPONENTS = [("Mail", None), ("Sync", "Mail"), ("Compose", "Mail"),
              ("Calendar", None), ("Invites", "Calendar"), ("Search", None)]
PRIORITIES = ["P1", "P2", "P3", "P3", "P3", "P4"]


def seed(db_path: str, issue_count: int = 40, seed_value: int = 7) -> None:
    random.seed(seed_value)
    fake = Faker()
    Faker.seed(seed_value)
    init_db(db_path)
    conn = connect(db_path)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        conn.close()
        return  # already seeded
    users = UserService(conn)
    for name, role in USERS:
        users.create(name, DEMO_PASSWORD, role)
    components = ComponentService(conn)
    for name, parent in COMPONENTS:
        components.create(name, parent)
    paths = components.list_paths()

    bus = EventBus()
    issues = IssueService(conn, bus)
    reporter = users.by_username("rita")
    engineer = users.by_username("erin")
    qa = users.by_username("quinn")
    created_ids = []
    for _ in range(issue_count):
        issue = issues.create(
            {
                "title": fake.sentence(nb_words=6).rstrip("."),
                "description": fake.paragraph(nb_sentences=2),
                "steps_to_reproduce": "1. " + fake.sentence() + "\n2. " + fake.sentence(),
                "expected_result": fake.sentence(),
                "actual_result": fake.sentence(),
                "component": random.choice(paths),
                "priority": random.choice(PRIORITIES),
                "assignee": random.choice(["erin", "eli"]),
            },
            reporter,
        )
        created_ids.append(issue["id"])
    # push some issues through the workflow
    for issue_id in created_ids[:20]:
        steps = random.randint(1, 4)
        for target in ["Integrate", "Build", "Verify", "Closed"][:steps]:
            actor = qa if target == "Closed" else engineer
            issues.transition(issue_id, target, actor)

    tests = TestService(conn, bus)
    case_ids = []
    for path in paths:
        for _ in range(2):
            case = tests.create_case(fake.sentence(nb_words=5).rstrip("."), path, "steps", "expected")
            case_ids.append(case["id"])
    suite = tests.create_suite("Smoke", case_ids[:6])
    full = tests.create_suite("Regression", case_ids)
    for suite_info in (suite, full):
        run = tests.start_run(suite_info["id"])
        for case_id in suite_info["case_ids"]:
            failed = random.random() < 0.15
            tests.add_result(
                run["id"],
                {"case_id": case_id, "status": "failed" if failed else "passed",
                 "issue_id": random.choice(created_ids) if failed else None,
                 "duration_ms": random.randint(50, 900)},
            )
        tests.complete_run(run["id"])
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="tracker.db")
    parser.add_argument("--issues", type=int, default=40)
    args = parser.parse_args()
    seed(args.db, args.issues)
    print(f"Seeded {args.db}. Users: rita/rob (reporter), erin/eli (engineer), "
          f"quinn/quentin (qa). Password: {DEMO_PASSWORD}")
