from ui_tests.pages.base_page import BasePage
from ui_tests.pages.issue_detail_page import IssueDetailPage


class NewIssuePage(BasePage):
    def wait_until_loaded(self) -> "NewIssuePage":
        self.find("new-issue-form")
        return self

    def create(
        self,
        title: str,
        component: str = "Mail > Sync",
        priority: str = "P3",
        description: str = "",
        steps: str = "",
    ) -> IssueDetailPage:
        self.type_into("title", title)
        self.choose("component", component)
        self.choose("priority", priority)
        if description:
            self.type_into("description", description)
        if steps:
            self.type_into("steps", steps)
        self.click("create-submit")
        return IssueDetailPage(self.driver, self.base_url).wait_until_loaded()
