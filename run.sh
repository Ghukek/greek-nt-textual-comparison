git submodule update --remote
python3 -m src.review_candidates
./quickrun.sh
python3 -m src.stage3_report
