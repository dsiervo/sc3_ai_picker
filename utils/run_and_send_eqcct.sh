time discontinuous_picker.py -s "2022-11-26 00:00:00" -e "2022-11-28 13:00:00" -n 0.25
cd test/output
timeout -120 prune_and_count_events.py
origins_pruning.py main_events_pruned.xml prefered_origins.xml
scdispatch -i prefered_origins.xml -H sc3primary.beg.utexas.edu
