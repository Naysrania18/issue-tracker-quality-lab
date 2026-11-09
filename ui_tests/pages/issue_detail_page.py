from selenium.webdriver.common.by import By

from ui_tests.pages.base_page import BasePage


class IssueDetailPage(BasePage):
    def wait_until_loaded(self) -> "IssueDetailPage":
        self.find("issue-title")
        return self

    # ----- reading -----
    @property
    def title(self) -> str:
        return self.text_of("issue-title")

    @property
    def state(self) -> str:
        return self.text_of("issue-state")

    @property
    def priority(self) -> str:
        return self.text_of("issue-priority")

    @property
    def issue_id(self) -> int:
        return int(self.text_of("issue-id").lstrip("#"))

    def description_text(self) -> str:
        return self.text_of("issue-description")

    def description_html(self) -> str:
        return self.find("issue-description").get_attribute("innerHTML") or ""

    def comments(self) -> list[str]:
        return [e.text for e in self.driver.find_elements(By.CSS_SELECTOR, "li.comment")]

    def error_message(self) -> str:
        return self.text_of("action-error")

    def duplicate_note(self) -> str:
        return self.text_of("duplicate-note")

    def can_change_workflow(self) -> bool:
        return self.is_present("transition-form")

    # ----- acting -----
    def move_to(self, target: str) -> "IssueDetailPage":
        self.choose("transition-target", target)
        self.click_and_wait_for_reload("transition-submit", "issue-title")
        return self._reloaded()

    def move_expecting_error(self, target: str) -> str:
        self.choose("transition-target", target)
        self.click_and_wait_for_reload("transition-submit", "issue-title")
        return self.error_message()

    def add_comment(self, text: str) -> "IssueDetailPage":
        self.type_into("comment-body", text)
        self.click_and_wait_for_reload("comment-submit", "issue-title")
        return self._reloaded()

    def mark_duplicate_of(self, issue_id: int) -> "IssueDetailPage":
        self.type_into("duplicate-of", str(issue_id))
        self.click_and_wait_for_reload("duplicate-submit", "issue-title")
        return self._reloaded()

    def _reloaded(self) -> "IssueDetailPage":
        # The forms redirect back to this page; the reload has finished once the title is visible again.
        self.find("issue-title")
        return self
