#!/usr/bin/env python3
"""Netflix公式Top10(日本・映画)を取得しTMDBと突合してJSON出力。
週次でlaunchd等から実行 → assets/netflix_jp_top10.json を更新する。
データ元: https://www.netflix.com/tudum/top10/data/all-weeks-countries.tsv (公式・無料)
"""
import csv, io, json, os, sys, time, datetime, urllib.request, urllib.parse

KEY = "aa9cb50c43ec1d77e920aa78e66e32e9"
TSV_URL = "https://www.netflix.com/tudum/top10/data/all-weeks-countries.tsv"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "netflix_jp_top10.json")

def http_get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)

def download_tsv():
    """転送が途中で切れることがあるため、完全長になるまでリトライ。"""
    last = b""
    for attempt in range(20):
        try:
            with http_get(TSV_URL, timeout=180) as r:
                expected = int(r.headers.get("Content-Length", "0"))
                data = r.read()
            if data and (expected == 0 or len(data) >= expected):
                return data.decode("utf-8", "replace")
            last = data
            print(f"  partial {len(data)}/{expected} (retry {attempt+1})", file=sys.stderr)
        except Exception as e:
            print(f"  dl error: {e} (retry {attempt+1})", file=sys.stderr)
        time.sleep(2)
    if last:
        return last.decode("utf-8", "replace")
    raise SystemExit("Netflix TSVのダウンロードに失敗しました")

def tmdb(path, **params):
    params["api_key"] = KEY
    url = "https://api.themoviedb.org/3" + path + "?" + urllib.parse.urlencode(params)
    for _ in range(3):
        try:
            with http_get(url, timeout=20) as r:
                return json.load(r)
        except Exception:
            time.sleep(1)
    return {}

def best_match(title):
    """完全一致を優先 → なければ票数最大。ポスター有りを必須。"""
    d = tmdb("/search/movie", language="ja-JP", query=title, include_adult="false")
    res = [r for r in d.get("results", []) if r.get("poster_path")]
    if not res:
        return None
    tl = title.strip().lower()
    exact = [r for r in res if (r.get("title", "").strip().lower() == tl
                                or r.get("original_title", "").strip().lower() == tl)]
    pool = exact if exact else res
    pool.sort(key=lambda r: (r.get("vote_count", 0), r.get("popularity", 0)), reverse=True)
    r = pool[0]
    date = r.get("release_date") or ""
    return {
        "rank": None, "type": "movie", "id": r["id"],
        "title": r.get("title") or r.get("original_title") or "(タイトル不明)",
        "poster": r.get("poster_path"),
        "year": date[:4] if date else "—",
    }

def main():
    print("Netflix Top10 TSV ダウンロード中...", file=sys.stderr)
    text = download_tsv()
    rows = [r for r in csv.DictReader(io.StringIO(text), delimiter="\t")
            if r.get("country_iso2") == "JP"]
    if not rows:
        raise SystemExit("JPデータが見つかりません")
    latest = max(r["week"] for r in rows)
    films = sorted([r for r in rows if r["week"] == latest and r["category"] == "Films"],
                   key=lambda r: int(r["weekly_rank"]))[:10]
    print(f"最新週 {latest} / 映画 {len(films)}件 を突合中...", file=sys.stderr)
    out = []
    for r in films:
        m = best_match(r["show_title"])
        time.sleep(0.2)
        if not m:
            print(f"  ❌ 突合失敗: {r['show_title']}", file=sys.stderr)
            continue
        m["rank"] = int(r["weekly_rank"])
        m["netflix_title"] = r["show_title"]
        out.append(m)
    out.sort(key=lambda x: x["rank"])
    payload = {
        "source": "Netflix Top 10 (公式) × TMDB",
        "region": "JP",
        "week": latest,
        "generated_at": datetime.date.today().isoformat(),
        "films": out,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 書き出し {OUT} ({len(out)}件 / 週 {latest})", file=sys.stderr)

if __name__ == "__main__":
    main()
