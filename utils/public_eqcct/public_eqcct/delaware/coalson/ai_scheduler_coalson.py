#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sep 2023

@author: Daniel Siervo P. [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import sys
import schedule
import time
# append /home/siervod/sc3_ai_picker/utils/ to sys.path
sys.path.append('/home/siervod/sc3_ai_picker/utils/')
from main_ai_scheduler import runner


if __name__ == "__main__":

    every_minutes = 20 # period of excecution in minutes
    #every_minutes = 1  # period of excecution in minutes
    
    minutes = 40  # 15 minutes of data
    #delay = 30    # delay in minutes
    delay = 0    # delay in minutes

    schedule.every(every_minutes).minutes.do(runner,
                                             every_m=minutes,
                                             delay=delay,
                                             db='sc3primary.beg.utexas.edu')

    while True:
        schedule.run_pending()
        time.sleep(1)  # wait one second
