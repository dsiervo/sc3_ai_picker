#!/home/dsiervo/anaconda3/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sep 2020

@author: Daniel Siervo P. [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import os
import schedule
import time
import datetime
import random


def read_params(par_file='phaseNet.inp'):
    """Read params from .inp file

    Parameters
    ----------
    par_file : str, optional
        File name of parameter file, by default 'phaseNet.inp'

    Returns
    -------
    dic
        Dictionary with parameters and values from params file
    """
    lines = open(par_file).readlines()
    par_dic = {}
    for line in lines:
        if line[0] == '#' or line.strip('\n').strip() == '':
            continue
        else:
            l = line.strip('\n').strip()
            key, value = l.split('=')
            par_dic[key.strip()] = value.strip()
    return par_dic

def change_times(ti:str, tf:str):
    """Change starttime and endtime in ai_picker.inp file

    Parameters
    ----------
    ti : str
        Initial UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    tf : str
        Final UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    """
    
    f_lines = open('ai_picker_scdl.inp').readlines()
     
    for idx, line in enumerate(f_lines):
        if line.startswith('starttime'):
            start_idx = idx
        elif line.startswith('endtime'):
            end_idx = idx
    
    # replacing start and end time lines 
    f_lines[start_idx] = f'starttime = {ti}\n'
    f_lines[end_idx] = f'endtime = {tf}\n'
    
    # writing new file
    with open('ai_picker.inp', 'w') as f:
        text = ''.join(f_lines)
        f.write(text)

def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file).readlines()
    lines[1] = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w') as f:
        f.write(''.join(lines))


def get_origins_path(path, xmlfile):
    orig_path = None
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if filename == xmlfile:
                orig_path = os.path.join(dirpath, filename)
                break
    
    print(xmlfile, orig_path)
    return orig_path


def runner(every_h):
    """Excecute ai_picker.py every every_h hours with a 5 min buffer

    Parameters
    ----------
    every_h : int
        Time delta in hours between init and end time
    """
    
    params = read_params('ai_picker_scdl.inp')
    main_path = params['general_output_dir']
    os.system('rm -fr %s'%main_path)
    
    # taking current time in UTC
    t = datetime.datetime.now() + datetime.timedelta(hours=(5))
    t_i = t - datetime.timedelta(minutes=(60*every_h + 5))
    
    # change the init and end time in ai_picker.inp
    change_times(t_i.strftime("%Y-%m-%d %H:%M:%S"),
                 t.strftime("%Y-%m-%d %H:%M:%S"))
    
    print(f'\n\n\trunning from {t_i} to {t}\n\n')
    os.system('head -10 ai_picker.inp')
    os.system('time ai_picker.py')

    # getting the origins path
    output_path = get_origins_path(main_path, 'origenes_preferidos.xml')

    if output_path is not None:
        # if the file is not empty
        if os.path.getsize(output_path):
            print('xml a modificar:', output_path)
            # changing the xml version of the origins file (mags.xml)
            #change_xml_version(output_path)
    
            print('\n\n\tUploading to db\n\n')
            os.system('head -3 %s'%output_path)

            # random number to avoid repetead users
            num = random.randint(1, 10)
            cmd = 'scdispatch -i %s -H 10.100.100.13:4803 -u ai_sgc_%d'%(output_path, num)
            print(cmd)
            os.system(cmd)
        else:
            print('\n\n\tArchivo vacio!\n\n')
    else:
        print('\n\n\tNo existe mag.xml!\n\n')
    print('Siguiente ejecucion a las: ', t + datetime.timedelta(hours=(every_h)), 'UT')


if __name__ == "__main__":

    hours = 2 # period of excecution in hours
    schedule.every(hours).hours.do(runner, every_h=hours)
    #schedule.every(hours).minutes.do(runner, every_h=1/6)
    
    while True:
        #print('esperando: ', datetime.datetime.now() + datetime.timedelta(hours=(5)), 'UT')
        schedule.run_pending()
        time.sleep(1) # wait one second

    #runner(2)

