#!/home/siervod/anaconda3/envs/eqt/bin/python

import sys
sys.path.append("/home/siervod/sc3_ai_picker/utils/")
from main_ai_scheduler import EventTypeChanger


if __name__ == '__main__':
    orginid = sys.argv[1]
    
    evtch = EventTypeChanger('scdb.beg.utexas.edu', user='sysro', passwd='0niReady', database='seiscomp',
                    scroot='/home/siervod/seiscomp')
    
    print(evtch.get_event_id(orginid))


