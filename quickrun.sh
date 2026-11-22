python3 -m src.review_cli
python3 -m src.stage2_worklist #--recheck-automatic #only use recheck flag if changing logic.
python3 -m src.stage2_review
#Repeat a couple times to allow user to quit and let it catch auto-fills.
python3 -m src.stage2_review
python3 -m src.stage2_review
