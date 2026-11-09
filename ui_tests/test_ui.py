"""Browser tests. `smoke` = must always pass and run first; `regression` = broader journeys."""
import pytest

from ui_tests.pages.login_page import LoginPage


@pytest.mark.smoke
def test_login_shows_user_and_issue_list(login):
    issues = login("erin")
    assert issues.current_user() == "erin (engineer)"


@pytest.mark.smoke
def test_wrong_password_shows_error(driver, base_url):
    error = LoginPage(driver, base_url).load().log_in_expecting_error("erin", "wrong")
    assert "Invalid username or password" in error


@pytest.mark.smoke
def test_anonymous_user_is_sent_to_login(driver, base_url):
    driver.get(base_url + "/issues")
    assert "/login" in driver.current_url


@pytest.mark.smoke
def test_logout_returns_to_login(login):
    page = login("rita")
    page.log_out()


@pytest.mark.regression
def test_full_issue_journey_create_to_closed(login, driver, base_url, unique):
    title = f"Sync stalls on big mailbox {unique}"
    detail = login("erin").start_new_issue().create(
        title, component="Mail > Sync", priority="P2", description="Spinner never stops", steps="1. Open mailbox"
    )
    assert detail.title == title and detail.state == "Analyze" and detail.priority == "P2"

    for target in ["Integrate", "Build", "Verify"]:
        detail = detail.move_to(target)
        assert detail.state == target

    # Engineers are not allowed to close; QA signs off.
    assert "may not move" in detail.move_expecting_error("Closed")
    detail.log_out()

    qa_detail = login("quinn").open_issue(title)
    assert qa_detail.state == "Verify"
    assert qa_detail.move_to("Closed").state == "Closed"


@pytest.mark.regression
def test_cannot_skip_workflow_steps(login, unique):
    detail = login("erin").start_new_issue().create(f"Skip test {unique}")
    assert "Cannot move from Analyze to Closed" in detail.move_expecting_error("Closed")
    assert detail.state == "Analyze"


@pytest.mark.regression
def test_reporter_sees_no_workflow_controls(login, unique):
    detail = login("rita").start_new_issue().create(f"Reporter issue {unique}")
    assert detail.can_change_workflow() is False


@pytest.mark.regression
def test_search_by_text_and_state(login, unique):
    alpha, beta = f"Alpha calendar glitch {unique}", f"Beta mailbox glitch {unique}"
    issues = login("erin")
    issues.start_new_issue().create(alpha, component="Calendar")
    issues.load()
    issues.start_new_issue().create(beta, component="Mail").move_to("Integrate")

    assert sorted(issues.load().search(unique).titles()) == sorted([alpha, beta])
    assert issues.search(f"calendar glitch {unique}").titles() == [alpha]
    assert issues.search(unique, state="Integrate").titles() == [beta]


@pytest.mark.regression
def test_mark_duplicate(login, unique):
    issues = login("erin")
    original_id = issues.start_new_issue().create(f"Original problem {unique}").issue_id
    issues.load()
    copy = issues.start_new_issue().create(f"Same problem again {unique}")
    copy = copy.mark_duplicate_of(original_id)
    assert f"#{original_id}" in copy.duplicate_note()


@pytest.mark.regression
def test_unknown_original_shows_error(login, unique):
    detail = login("erin").start_new_issue().create(f"Dupe test {unique}")
    detail = detail.mark_duplicate_of(99999)
    assert "not found" in detail.error_message()


@pytest.mark.regression
def test_comment_appears_in_list(login, unique):
    detail = login("rita").start_new_issue().create(f"Comment test {unique}")
    detail = detail.add_comment("Happens on every build")
    assert detail.comments() == ["rita: Happens on every build"]


@pytest.mark.regression
def test_empty_comment_is_rejected(login, unique):
    detail = login("rita").start_new_issue().create(f"Empty comment {unique}")
    detail = detail.add_comment("   ")
    assert "cannot be empty" in detail.error_message()
    assert detail.comments() == []


@pytest.mark.regression
@pytest.mark.xfail(strict=True, reason="BUG-005 docs/bugs/BUG-005.md: description rendered unescaped")
def test_bug005_markup_in_description_is_shown_as_text(login, unique):
    markup = f"<b id='injected'>bold {unique}</b>"
    detail = login("rita").start_new_issue().create(f"XSS check {unique}", description=markup)
    assert detail.description_text() == markup
