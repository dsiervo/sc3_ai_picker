#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sep 2020

@author: Daniel Siervo P. [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import sys

# append /home/siervod/sc3_ai_picker/utils/ to sys.path
sys.path.append('/home/siervod/sc3_ai_picker/utils/')
from test_ai_scheduler import test_runner

if __name__ == "__main__":

    every_minutes = 30  # period of excecution in minutes
    #every_minutes = 1  # period of excecution in minutes

    minutes = 40  # period of excecution in minutes
    #delay = 30    # delay in minutes
    delay = 0    # delay in minutes

    test_runner('2022-01-01 01:00:00', '2022-01-01 01:40:00', db='sc3primary.beg.utexas.edu')
