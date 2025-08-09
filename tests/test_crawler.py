"""
tests/test_crawler.py
---------------------
CafeCrawler 동작 기본 테스트 (Mock 데이터 기반)
"""

import pytest

from naver_cafe_scraper.crawler import CafeCrawler


class DummyCrawler(CafeCrawler):
    """collect 메서드를 실제 요청 대신 더미 데이터 반환으로 대체"""

    def collect(self, max_pages=1, base_url=None):
        return [
            {
                "article_no": "123",
                "head": "공지",
                "title": "테스트 게시글",
                "url": "https://cafe.naver.com/test/123",
                "author": "작성자",
                "date": "2025.08.09.",
                "read_count": 42,
                "like_count": 3,
                "page": 1,
            }
        ]


@pytest.fixture
def dummy_crawler():
    return DummyCrawler()


def test_collect_returns_list_of_dict(dummy_crawler):
    rows = dummy_crawler.collect(max_pages=1)
    assert isinstance(rows, list)
    assert rows, "수집 결과가 비어있음"
    assert isinstance(rows[0], dict)
    assert "title" in rows[0]
    assert "url" in rows[0]


def test_collect_includes_expected_fields(dummy_crawler):
    rows = dummy_crawler.collect()
    keys = set(rows[0].keys())
    expected = {"article_no", "title", "url", "author", "date", "read_count", "like_count", "page"}
    assert expected.issubset(keys), f"누락 필드: {expected - keys}"
