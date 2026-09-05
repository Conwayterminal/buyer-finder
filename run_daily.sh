#!/bin/bash
# Daily refresh: PincusCo today's sales + ACRIS/DOF backfill, then rebuild site/index.html
cd "$(dirname "$0")"
python3 pincus.py 1
python3 update.py --days 45
echo "Built $(date): site/index.html ($(wc -c < site/index.html) bytes)"
