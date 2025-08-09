import json
from pathlib import Path

import pandas as pd

from naver_cafe_scraper.exporter import save_csv, save_json

ROWS = [
    {
        "page": 1,
        "article_no": "1",
        "title": "t1",
        "url": "u1",
        "author": "a1",
        "date": "d1",
        "read_count": 10,
        "like_count": 1,
    },
    {
        "page": 1,
        "article_no": "2",
        "title": "t2",
        "url": "u2",
        "author": "a2",
        "date": "d2",
        "read_count": 20,
        "like_count": 2,
    },
]


def test_save_csv_with_fields(tmp_path):
    out = tmp_path / "out.csv"
    fields = ["page", "article_no", "title", "url"]
    path = save_csv(ROWS, path=str(out), fields=fields)
    assert Path(path).exists()
    df = pd.read_csv(path)
    assert list(df.columns) == fields
    assert len(df) == 2


def test_save_json_pretty(tmp_path):
    out = tmp_path / "out.json"
    path = save_json(ROWS, path=str(out), fields=["article_no", "title"])
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 2
    assert set(data[0].keys()) == {"article_no", "title"}
