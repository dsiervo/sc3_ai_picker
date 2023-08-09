#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sep 2020

@author: Daniel Siervo P. [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import os
import logging
import time
import datetime
import random
from icecream import ic
from main_ai_scheduler import *
log_file_name = os.path.basename(__file__).replace('.py', '.log')
logging.basicConfig(filename=log_file_name, level=logging.DEBUG, format='%(message)s')


def test_runner(starttime, endtime, db='10.100.100.13:4803', ai_picker='ai_picker.py'):
    """Excecute ai_picker.py every every_m hours with a 5 min buffer

    Parameters
    ----------
    every_m : int
        Time delta in hours between init and end time
    delay : int
        Delay in minutes, default: 0
    """

    params = read_params('ai_picker_scdl.inp')
    main_path = params['general_output_dir']
    os.system('rm -fr %s' % main_path)

    end = datetime.datetime.utcnow()
    t_i = datetime.datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
    t = datetime.datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')
    every_m = int((t - t_i).seconds*0.8)
    # change the init, end time and dt in ai_picker.inp
    change_times(t_i.strftime("%Y-%m-%d %H:%M:%S"),
                 t.strftime("%Y-%m-%d %H:%M:%S"),
                 every_m)

    print(f'\n\n\trunning from {t_i} to {t}\n\n')
    os.system('head -10 ai_picker.inp')
    cmd = f'time {ai_picker}'
    ic(os.system(cmd))

    # getting the origins path
    output_path = get_origins_path(main_path, 'origenes_preferidos.xml')
    # getting the picks path
    #picks_path = get_origins_path(main_path, 'picks.xml')

    #cmd_picks = 'scdispatch -i %s -H %s -u ai_texnet' % (picks_path, db)
    #print(cmd_picks)
    #os.system(cmd_picks)

    if output_path is not None:
        # if the file is not empty
        if os.path.getsize(output_path):
            print('xml a modificar:', output_path)
            # changing the xml version of the origins file
            change_xml_version(output_path)

            print('\n\n\tUploading to db\n\n')
            os.system('head -3 %s' % output_path)

            # random number to avoid repetead users
            num = random.randint(1, 10)
            cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scdispatch -i %s -H %s -u aitexnet%d' % (output_path, db, num)
            ic(os.system(cmd))
            # send to sc5
            send_to_sc5(output_path, f'eqcct{num}')

            # wait 15 seconds
            ic(time.sleep(30))
            
            # change the event type to earthquake in sc3
            EventTypeChanger(db).run()
            # change the event type to earthquake in sc5
            EventTypeChanger('scdb.beg.utexas.edu', user='sysro', passwd='0niReady', database='seiscomp',
                              scroot='/home/siervod/seiscomp').run()
        else:
            print('\n\n\tArchivo vacio!\n\n')
    else:
        print('\n\n\tNo existe mag.xml!\n\n')
    print('\n\tSiguiente ejecucion a las: ',
          t + datetime.timedelta(minutes=(every_m)), 'UT\n')

    now = datetime.datetime.utcnow()

    logger(end, now, t_i, t)


if __name__ == "__main__":

    every_minutes = 30  # period of excecution in minutes
    #every_minutes = 1  # period of excecution in minutes

    minutes = 40  # period of excecution in minutes
    #delay = 30    # delay in minutes
    delay = 0    # delay in minutes

    test_runner('2021-01-01 00:00:00', '2021-01-01 00:40:00', db='sc3primary.beg.utexas.edu')


