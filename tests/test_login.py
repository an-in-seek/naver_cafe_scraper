from pathlib import Path

from naver_cafe_scraper.login import prompt_login_and_persist


class FakeEl:
    def __init__(self):
        self.clicked = False

    def click(self):
        self.clicked = True


class FakePage:
    def __init__(self, has_login=True):
        self.el = FakeEl() if has_login else None
        self.waited = 0

    def query_selector(self, _):
        return self.el

    def wait_for_timeout(self, ms):
        self.waited += ms


class FakeContext:
    def __init__(self):
        self.saved = None

    def storage_state(self, path=None, **_):
        if path:
            Path(path).write_text("{}", encoding="utf-8")
            self.saved = path


def test_prompt_login_and_persist_with_login(tmp_path):
    page = FakePage(has_login=True)
    ctx = FakeContext()
    state = tmp_path / "state.json"
    prompt_login_and_persist(page, ctx, str(state), wait_sec=0)
    assert page.el.clicked
    assert state.exists()


def test_prompt_login_and_persist_already_logged_in(tmp_path):
    page = FakePage(has_login=False)
    ctx = FakeContext()
    state = tmp_path / "state.json"
    prompt_login_and_persist(page, ctx, str(state), wait_sec=0)
    assert state.exists()
