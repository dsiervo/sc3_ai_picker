import sys
sys.path.append('/home/siervod/projects/developing/test/eqcct_repot/ai_scheduler.py')
from ai_scheduler import EventTypeChanger

if __name__ == '__main__':
    host = 'sc3primary.beg.utexas.edu'
    #EventTypeChanger(host, ev_type='not locatable',orig_ids_file='test_origins.txt').run()
    EventTypeChanger(host, orig_ids_file='test_origins.txt').run()