# tests/test_parser.py
from __future__ import annotations

from html.parser import HTMLParser

import pytest


# --- 최소 기능의 DOM 파서/셀렉터 (테스트용) -----------------------------


class Node:
    def __init__(self, tag=None, attrs=None, parent=None, text=""):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []
        self.text = text

    def append(self, child):
        self.children.append(child)
        child.parent = self

    # ---- parser 호환 메서드들 ----
    def inner_text(self):
        return "".join(iter_text(self)).strip()

    def get_attribute(self, name):
        return self.attrs.get(name)

    def query_selector(self, css):
        found = self.query_selector_all(css)
        return found[0] if found else None

    def query_selector_all(self, css):
        # 본 테스트에서 사용하는 셀렉터만 지원:
        # - 태그 조합: "table.article-table tbody tr"
        # - 클래스 선택: ".Board ...", ".nickname", ".type_date" 등
        # - 자손 결합자: 공백
        # - 쉼표로 여러 셀렉터 OR: "td.type_date, td.td_date"
        parts_or = [p.strip() for p in css.split(",")]
        out = []
        for part in parts_or:
            out.extend(select_desc(self, [p for p in part.split() if p]))
        return out


def iter_text(node):
    if node.text:
        yield node.text
    for c in node.children:
        yield from iter_text(c)


def match_simple(node, simple):
    # simple: "tag", "tag.cls", ".cls"
    m_tag = None
    m_class = None
    if simple.startswith("."):
        m_class = simple[1:]
    elif "." in simple:
        m_tag, m_class = simple.split(".", 1)
    else:
        m_tag = simple

    if m_tag and node.tag != m_tag:
        return False
    if m_class:
        cls = node.attrs.get("class", "")
        classes = set(cls.split()) if isinstance(cls, str) else set(cls or [])
        return m_class in classes
    return True


def select_desc(root, tokens):
    # 후손 결합자만 처리
    cur = [root]
    for tok in tokens:
        nxt = []
        for n in cur:
            nxt.extend(find_desc(n, tok))
        cur = nxt
    return cur


def find_desc(node, simple):
    out = []
    for c in node.children:
        if c.tag is not None:
            if match_simple(c, simple):
                out.append(c)
            out.extend(find_desc(c, simple))
    return out


class MiniHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag=tag, attrs=attrs)
        self.stack[-1].append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        # 스택을 적절히 pop (태그 불일치 시 가까운 상위 종료)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].text += data


# Playwright 호환용 FakePage
class FakePage(Node):
    def __init__(self, html: str):
        super().__init__(tag="document")
        p = MiniHTMLParser()
        p.feed(html)
        self.children = p.root.children

    def wait_for_selector(self, selector: str, timeout: int = 8000):
        if not self.query_selector(selector):
            raise TimeoutError(f"selector not found: {selector}")


# --- 테스트 대상 HTML 샘플 ----------------------------------------------

HTML_SAMPLE = """
<div id="cafe_content">
  <div class="article-board">
    <table class="article-table">
      <tbody>
        <tr>
          <td class="td_normal type_articleNumber">13709326</td>
          <td>
            <div class="board-list">
              <div class="inner_list">
                <a class="article" href="https://cafe.naver.com/f-e/cafes/29434212/articles/13709326?boardtype=L">
                  <span class="head">[광고]</span>메가박스 6천원 영화표 구매했어요 오늘까지네요
                </a>
              </div>
            </div>
          </td>
          <td>
            <div class="ArticleBoardWriterInfo">
              <button class="nick_btn"><span class="nickname">탐딜을찾아</span></button>
            </div>
          </td>
          <td class="td_normal type_date">2025.08.08.</td>
          <td class="td_normal type_readCount">1,272</td>
          <td class="td_normal type_likeCount">5</td>
        </tr>
        <tr>
          <td class="td_normal type_articleNumber">13706015</td>
          <td>
            <div class="board-list">
              <div class="inner_list">
                <a class="article" href="https://cafe.naver.com/f-e/cafes/29434212/articles/13706015?boardtype=L">
                  <span class="head">[광고]</span>무무즈) 아이 면 레깅스 1,900원 (배송비 있어요)
                </a>
              </div>
            </div>
          </td>
          <td>
            <div class="ArticleBoardWriterInfo">
              <button class="nick_btn"><span class="nickname">fmoon802</span></button>
            </div>
          </td>
          <td class="td_normal type_date">12:04</td>
          <td class="td_normal type_readCount">76</td>
          <td class="td_normal type_likeCount">0</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
"""


# --- 실제 테스트 ---------------------------------------------------------


def test_extract_posts_from_frame_contract():
    # parser 로드
    from naver_cafe_scraper import parser

    fake_page = FakePage(HTML_SAMPLE)
    rows = parser.extract_posts_from_frame(fake_page)

    assert isinstance(rows, list)
    assert len(rows) == 2

    r0 = rows[0]
    expected_keys = {
        "article_no",
        "head",
        "title",
        "url",
        "author",
        "date",
        "read_count",
        "like_count",
    }
    assert expected_keys.issubset(set(r0.keys()))

    assert r0["article_no"] == "13709326"
    assert r0["head"] == "광고"
    assert "메가박스 6천원 영화표" in r0["title"]
    assert r0["url"].startswith("https://cafe.naver.com/")
    assert r0["author"] == "탐딜을찾아"
    assert r0["date"] == "2025.08.08."
    assert isinstance(r0["read_count"], int) and r0["read_count"] == 1272
    assert isinstance(r0["like_count"], int) and r0["like_count"] == 5

    r1 = rows[1]
    assert r1["article_no"] == "13706015"
    assert r1["author"] == "fmoon802"
    assert r1["date"] == "12:04"
    assert r1["read_count"] == 76
    assert r1["like_count"] == 0
