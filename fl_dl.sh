#!/bin/bash
cd /home/claude/bf/fl; start=$(date +%s)
while read -r u; do n=$(basename "$u"); [ -s "nal/$n" ] && continue; [ $(( $(date +%s) - start )) -gt 250 ] && exit 0
  curl -sL -A "Mozilla/5.0" -o "nal/$n" "https://floridarevenue.com$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$u")"; echo "$n $(stat -c %s "nal/$n")"; done < nal_urls.txt; echo ALLDONE
