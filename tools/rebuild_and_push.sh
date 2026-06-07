#!/bin/bash
# 作品別ページ＋sitemapを週次で再生成し、差分があれば自動コミット＆プッシュする。
# launchd（com.dokomiru.rebuild）から定期実行される。配信先は日々変わるため。
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

REPO="/Users/kokiito/Desktop/tmdb_app"
cd "$REPO" || exit 1

LOG="$REPO/tools/rebuild.log"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 再生成開始 ===" >> "$LOG"

python3 tools/build_title_pages.py 15 10 >> "$LOG" 2>&1 || { echo "ビルド失敗" >> "$LOG"; exit 1; }

git add title sitemap.xml
if git diff --cached --quiet; then
  echo "差分なし。スキップ。" >> "$LOG"
else
  git commit -q -m "chore: 作品ページ・配信先を週次自動再生成" >> "$LOG" 2>&1
  git push >> "$LOG" 2>&1 && echo "プッシュ完了。" >> "$LOG" || echo "プッシュ失敗。" >> "$LOG"
fi
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 完了 ===" >> "$LOG"
