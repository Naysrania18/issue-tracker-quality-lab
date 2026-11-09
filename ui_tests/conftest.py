"""Selenium fixtures: a real server on a free port, headless Chrome, screenshots on failure."""
import socket
import threading
import time
import uuid
from pathlib import Path

import pytest
import uvicorn
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app.database import connect
from app.main import create_app
from app.services import ComponentService, UserService
from ui_tests.pages.login_page import LoginPage

PASSWORD = "ui-pass"
SCREENSHOT_DIR = Path("screenshots")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("ui") / "ui.db")
    app = create_app(db_path)
    conn = connect(db_path)
    users = UserService(conn)
    for name, role in [("rita", "reporter"), ("erin", "engineer"), ("quinn", "qa")]:
        users.create(name, PASSWORD, role)
    components = ComponentService(conn)
    components.create("Mail")
    components.create("Sync", "Mail")
    components.create("Calendar")
    conn.close()

    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("Test server did not start")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(options=options)
    yield browser
    browser.quit()


@pytest.fixture
def unique():
    """A short unique suffix so tests never collide on titles."""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def login(driver, base_url):
    """login('erin') -> IssuesPage"""

    def _login(username: str):
        return LoginPage(driver, base_url).load().log_in(username, PASSWORD)

    return _login


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed and "driver" in item.funcargs:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        path = SCREENSHOT_DIR / f"{item.name}.png"
        item.funcargs["driver"].save_screenshot(str(path))
        report.sections.append(("screenshot", str(path)))


def pytest_collection_modifyitems(items):
    for item in items:
        if "ui_tests" in str(item.fspath):
            item.add_marker(pytest.mark.ui)
