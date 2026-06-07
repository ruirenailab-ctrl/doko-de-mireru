#!/bin/bash
# Netflix公式Top10(日本・映画)を再生成し、変化があればcommit/push。
# launchdから週次実行（pushはosxkeychainに保存した認証を使用）。
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
REPO="/Users/kokiito/Desktop/tmdb_app"
cd "$REPO"

/usr/bin/python3 tools/netflix_top10_gen.py

if ! git diff --quiet -- assets/netflix_jp_top10.json; then
  git add assets/netflix_jp_top10.json
  git commit -q -m "chore: Netflix Top10 週次更新 ($(date +%F))"
  git push -q origin main
  echo "$(date '+%F %T') pushed"
else
  echo "$(date '+%F %T') no change"
fi
