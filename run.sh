git submodule update --remote
python3 -m src.review_candidates
python3 -m src.stage2_worklist --recheck-automatic
./quickrun.sh
python3 -m src.stage3_report
