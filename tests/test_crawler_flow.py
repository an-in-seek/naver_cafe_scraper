import types

from naver_cafe_scraper.crawler import CafeCrawler


class FakePage:
    def __init__(self):
        self.urls = []

    def goto(self, url, **kwargs):
        self.urls.append(url)

    def frames(self):
        return []

    # parser가 직접 page를 받아도 되도록 최소 메서드 제공
    def wait_for_selector(self, *a, **kw):
        return


class FakeContext:
    def __init__(self):
        self.page = FakePage()

    def new_page(self):
        return self.page

    def storage_state(self, **kw):
        return {}

    def close(self):
        pass


class FakeBrowser:
    def __init__(self):
        self.ctx = FakeContext()

    def new_context(self, **kw):
        return self.ctx

    def close(self):
        pass


class FakePlaywright:
    def __init__(self):
        self.chromium = types.SimpleNamespace(launch=lambda **kw: FakeBrowser())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_crawler_collect_monkeypatch(monkeypatch):
    # sync_playwright() 몽키패치
    import naver_cafe_scraper.crawler as crawler_mod

    monkeypatch.setattr(crawler_mod, "sync_playwright", lambda: FakePlaywright())

    # extract_posts_from_frame이 호출되면 더미 rows 반환
    def fake_extract(target):
        # 호출 대상이 page인지 frame인지와 무관하게 리스트 리턴
        return [
            {"title": "A", "url": "u1"},  # page 1
            {"title": "A", "url": "u1"},  # 중복 제거 테스트
        ]

    monkeypatch.setattr(crawler_mod, "extract_posts_from_frame", fake_extract)

    c = CafeCrawler(base_url="https://x?page=1", headless=True)
    rows = c.collect(max_pages=2)
    # 각 페이지마다 결과가 붙되, (title,url) 중복 제거되어 1개만 남음
    assert len(rows) == 1
    assert rows[0]["page"] in (1, 2)  # page 필드가 설정되어 있음
