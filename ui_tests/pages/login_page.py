from ui_tests.pages.base_page import BasePage
from ui_tests.pages.issues_page import IssuesPage


class LoginPage(BasePage):
    def load(self) -> "LoginPage":
        self.open("/login")
        self.find("login-submit")
        return self

    def log_in(self, username: str, password: str) -> IssuesPage:
        self.type_into("username", username)
        self.type_into("password", password)
        self.click("login-submit")
        self.wait_for_url_contains("/issues")
        return IssuesPage(self.driver, self.base_url)

    def log_in_expecting_error(self, username: str, password: str) -> str:
        self.type_into("username", username)
        self.type_into("password", password)
        self.click("login-submit")
        return self.text_of("login-error")
