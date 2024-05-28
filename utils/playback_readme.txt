
1. Remove test subfolders and main_events_pruned.xml files
find /home/siervod/projects/realtime/public_eqcct/delaware -type d -name "test" -exec rm -fr {} \; -o -type f -name "main_events_pruned.xml" -exec rm -fr {} \;

2. Iniciate seiscomp env:
sc5

2. Run:
 python parallel_test_regions_as_discontinuos.py delaware '2023-10-01 00:00:00' '2023-10-01 01:59:59'

Wich will run in each subfolder of delaware mv ai_apicker_scd.inp temp_ai_picker.inp and then run discontinous picker every 40 min

3. Enter to delaware folder and run (default author and db are EQCCT and scdb respectevly):
 dispatch_walk.py
