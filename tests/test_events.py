"""Event queue and notification consumer."""
from app.events import Event, EventBus, EventType, NotificationConsumer
from tests.factories import move, new_issue, new_suite_with_case


def notification_messages(client, headers):
    return [n["message"] for n in client.get("/api/notifications", headers=headers).json()]


def test_creating_an_issue_publishes_and_notifies(client, app, reporter):
    issue = new_issue(client, reporter)
    assert app.state.bus.published[-1].type == EventType.ISSUE_CREATED
    assert any(f"Issue #{issue['id']} created" in m for m in notification_messages(client, reporter))


def test_state_change_publishes_event_with_increasing_sequence(client, app, reporter, engineer):
    issue = new_issue(client, reporter)
    move(client, engineer, issue["id"], "Integrate")
    move(client, engineer, issue["id"], "Build")
    state_events = [e for e in app.state.bus.published if e.type == EventType.STATE_CHANGED]
    assert [e.sequence for e in state_events] == [1, 2]


def test_test_run_completion_notifies(client, qa):
    suite_id, _ = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    client.post(f"/api/test-runs/{run['id']}/complete", headers=qa)
    assert any("completed" in m for m in notification_messages(client, qa))


def test_queue_is_empty_after_processing(client, app, reporter):
    new_issue(client, reporter)
    assert app.state.bus.pending() == []


def state_event(issue_id, sequence):
    return Event(
        EventType.STATE_CHANGED, {"issue_id": issue_id, "old": "A", "new": "B"}, sequence=sequence
    )


def test_out_of_order_state_event_is_ignored(db):
    consumer = NotificationConsumer(db)
    assert consumer.handle(state_event(1, sequence=2)) is True
    assert consumer.handle(state_event(1, sequence=1)) is False  # arrived late
    assert db.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 1


def test_sequences_are_tracked_per_issue(db):
    consumer = NotificationConsumer(db)
    assert consumer.handle(state_event(1, sequence=5)) is True
    assert consumer.handle(state_event(2, sequence=1)) is True


def test_drain_processes_every_queued_event(db):
    bus, consumer = EventBus(), NotificationConsumer(db)
    bus.publish(Event(EventType.ISSUE_CREATED, {"issue_id": 1, "title": "x"}))
    bus.publish(Event(EventType.TEST_RUN_COMPLETED, {"run_id": 1, "status": "passed"}))
    assert consumer.drain(bus) == 2
