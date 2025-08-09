from pathlib import Path

from naver_cafe_scraper.utils import (
    ensure_dir,
    build_page_url,
    load_storage_state,
    save_storage_state,
)


def test_build_page_url_replace():
    out = build_page_url("https://x?menu=1&page=3&size=15", 7)
    assert "page=7" in out


def test_build_page_url_append():
    out = build_page_url("https://x?menu=1", 5)
    assert out.endswith("page=5")
    out2 = build_page_url("https://x", 2)
    assert out2.endswith("?page=2")


def test_ensure_dir(tmp_path):
    d = tmp_path / "a" / "b"
    ensure_dir(str(d))
    assert d.exists() and d.is_dir()


class FakeContext:
    def __init__(self):
        self.saved = None

    def storage_state(self, path=None, **_):
        if path:
            Path(path).write_text("{}", encoding="utf-8")
            self.saved = path
        return {}


class FakeBrowser:
    def __init__(self):
        self.created = []

    def new_context(self, storage_state=None, **_):
        # storage_state가 파일 경로면 존재하지 않아도 예외 없이 생성하도록 처리
        self.created.append(storage_state)
        return FakeContext()


def test_load_and_save_storage_state(tmp_path):
    fake_browser = FakeBrowser()
    state_path = tmp_path / "state.json"

    # 파일 없을 때도 context 생성
    ctx = load_storage_state(fake_browser, str(state_path))
    assert isinstance(ctx, FakeContext)

    # 저장 호출
    save_storage_state(ctx, str(state_path))
    assert state_path.exists()

    # 다음 호출에서 로드 경로가 new_context에 전달되는지 확인
    ctx2 = load_storage_state(fake_browser, str(state_path))
    # FakeBrowser.new_context가 받은 첫 인자가 storage_state
    assert fake_browser.created[-1] == str(state_path)
