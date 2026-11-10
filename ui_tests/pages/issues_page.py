from selenium.webdriver.common.by import By

from ui_tests.pages.base_page import BasePage


class IssuesPage(BasePage):
    def load(self) -> "IssuesPage":
        self.open("/issues")
        self.find("issue-table")
        return self

    def search(self, text: str = "", state: str = "", priority: str = "") -> "IssuesPage":
        self.type_into("search-q", text)
        if state:
            self.choose("filter-state", state)
        if priority:
            self.choose("filter-priority", priority)
        self.click_and_wait_for_reload("search-submit", "result-count")
        self.find("result-count")
        return self

    def titles(self) -> list[str]:
        return [e.text for e in self.driver.find_elements(By.CSS_SELECTOR, "a.issue-link")]

    def open_issue(self, title: str):
        from ui_tests.pages.issue_detail_page import IssueDetailPage

        for link in self.driver.find_elements(By.CSS_SELECTOR, "a.issue-link"):
            if link.text == title:
                link.click()
                return IssueDetailPage(self.driver, self.base_url).wait_until_loaded()
        raise AssertionError(f"No issue titled {title!r} in the list: {self.titles()}")

    def start_new_issue(self):
        from ui_tests.pages.new_issue_page import NewIssuePage

        self.click("nav-new")
        return NewIssuePage(self.driver, self.base_url).wait_until_loaded()
