"""Base class for page objects: all waiting is explicit, there are no sleeps."""
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait

TIMEOUT = 10


class BasePage:
    def __init__(self, driver: WebDriver, base_url: str) -> None:
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, TIMEOUT)

    # ----- finding -----
    def find(self, element_id: str) -> WebElement:
        return self.wait.until(ec.visibility_of_element_located((By.ID, element_id)))

    def is_present(self, element_id: str) -> bool:
        return bool(self.driver.find_elements(By.ID, element_id))

    # ----- acting -----
    def type_into(self, element_id: str, text: str) -> None:
        field = self.find(element_id)
        field.clear()
        field.send_keys(text)

    def click(self, element_id: str) -> None:
        self.wait.until(ec.element_to_be_clickable((By.ID, element_id))).click()

    def click_and_wait_for_reload(self, element_id: str, anchor_id: str) -> None:
        """Click a submit button, then wait until the old page is gone (its anchor element goes stale)."""
        anchor = self.find(anchor_id)
        self.click(element_id)
        self.wait.until(lambda _driver: self._is_gone(anchor))

    @staticmethod
    def _is_gone(element: WebElement) -> bool:
        """True once the element belongs to a page that has been replaced.

        Older Chrome raises StaleElementReferenceException; newer Chrome reports
        "Node with given id does not belong to the document". Both mean the same thing.
        """
        try:
            element.is_enabled()
            return False
        except StaleElementReferenceException:
            return True
        except WebDriverException as exc:
            if "does not belong to the document" in str(exc):
                return True
            raise

    def choose(self, element_id: str, visible_text: str) -> None:
        Select(self.find(element_id)).select_by_visible_text(visible_text)

    def text_of(self, element_id: str) -> str:
        return self.find(element_id).text

    # ----- navigation -----
    def open(self, path: str) -> None:
        self.driver.get(self.base_url + path)

    def wait_for_url_contains(self, fragment: str) -> None:
        self.wait.until(ec.url_contains(fragment))

    def wait_for_text(self, element_id: str, text: str) -> None:
        self.wait.until(ec.text_to_be_present_in_element((By.ID, element_id), text))

    # ----- shared header -----
    def current_user(self) -> str:
        return self.text_of("current-user")

    def log_out(self) -> None:
        self.click("logout")
        self.wait_for_url_contains("/login")
