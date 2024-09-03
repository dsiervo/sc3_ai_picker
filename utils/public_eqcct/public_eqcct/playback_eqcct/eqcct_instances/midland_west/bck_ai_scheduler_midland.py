#!/home/siervod/anaconda3/envs/eqt/bin/python
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
import sys
import mysql.connector # pip install mysql-connector-python
# append /home/siervod/sc3_ai_picker/utils/ to sys.path
sys.path.append('/home/siervod/sc3_ai_picker/utils/')
from send_to_sc5 import send_to_sc5


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


def change_times(ti: str, tf: str, dt: int):
    """Change starttime and endtime in ai_picker.inp file

    Parameters
    ----------
    ti : str
        Initial UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    tf : str
        Final UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    dt : int
        Delta time in seconds (tf-ti)
    """

    f_lines = open('ai_picker_scdl.inp').readlines()

    for idx, line in enumerate(f_lines):
        if line.startswith('starttime'):
            start_idx = idx
        elif line.startswith('endtime'):
            end_idx = idx
        elif line.startswith('dt'):
            dt_idx = idx

    # replacing start, end and dt time lines
    f_lines[start_idx] = f'starttime = {ti}\n'
    f_lines[end_idx] = f'endtime = {tf}\n'
    f_lines[dt_idx] = f'dt = {dt}\n'

    # writing new file
    with open('ai_picker.inp', 'w') as f:
        text = ''.join(f_lines)
        f.write(text)


def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file, encoding='utf-8').readlines()
    new_line = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith('<seiscomp xmlns='):
                line = new_line
            f.write(line)


def get_origins_path(path, xmlfile):
    orig_path = None
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if filename == xmlfile:
                orig_path = os.path.join(dirpath, filename)
                break

    print(xmlfile, orig_path)
    return orig_path


def logger(ti, tf):
    logfile = 'scheduler.log'
    if not os.path.isfile('scheduler.log'):
        f = open(logfile, 'w')
    else:
        f = open(logfile, 'a')

    print(f'Inició ejecución a las: {ti}, terminó la ejecución a las: {tf}',
          file=f)

    f.close()


class EventTypeChanger:
    """Reads the list of origins ids from reported_origins.txt iterates over them,
    searches the event id and changes the event type to 'earthquake'
    using scsendjournal (scsendjournal -H sc3primary.beg.utexas.edu texnet2023attj EvType "earthquake" --debug)
    """

    query_str_evID = """
    select POE.publicID,
    Origin.quality_usedPhaseCount
    from Event left join PublicObject AS POE ON Event._oid = POE._oid
    inner join OriginReference on Event._oid=OriginReference._parent_oid
    inner join PublicObject POO on POO.publicID=OriginReference.originID
    inner join Origin on POO._oid=Origin._oid
    where OriginReference.originID = '{origin_id}'"""

    query_str_eval_mode = """
    select
    Origin.evaluationMode, Origin.creationInfo_author, Origin.quality_usedPhaseCount
    from Event left join PublicObject AS POE ON Event._oid = POE._oid
    left join PublicObject as POOri ON Event.preferredOriginID=POOri.publicID 
    left join Origin ON POOri._oid=Origin._oid
    where
    POE.publicID = '{event_id}'"""

    def __init__(self, host, ev_type='earthquake', orig_ids_file='reported_origins.txt'):
        self.host = host
        self._mydb = mysql.connector.connect(host=host,
                                    user="sysop",
                                    passwd="sysop",
                                    database="seiscomp3")
        self.ev_type = ev_type
        self.orig_ids_file = orig_ids_file

    @property
    def reported_origins(self):
        if not os.path.isfile(self.orig_ids_file):
            return []
        with open(self.orig_ids_file, 'r') as f:
            lines = f.readlines()
        return [line.strip().strip('\n') for line in lines]
    
    def get_event_id(self, origin_id):
        mycursor = self._mydb.cursor()
        mycursor.execute(self.query_str_evID.format(origin_id=origin_id))
        myresult = mycursor.fetchall()
        # if myresult is empty, return None
        if not myresult:
            return None, None
        return myresult[0]
    
    def get_eval_mode(self, event_id):
        print('In get_eval_mode')
        mycursor = self._mydb.cursor()
        mycursor.execute(self.query_str_eval_mode.format(event_id=event_id))
        # the query returns a tuple with the evaluation mode and the author
        myresult = mycursor.fetchall()
        return myresult[0]

    def change_event_type(self, event_id):
        cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scsendjournal -H {self.host} {event_id} EvType "{self.ev_type}" --debug'
        # print in red and bold the command
        print(f'\n\033[1;32m{cmd}\033[0m\n')
        os.system(cmd)
    
    def fix_as_prefered(self, origin_id, event_id):
        # scsendjournal -H sc3primary.beg.utexas.edu texnet2023attj EvPrefOrgID Origin/20230111205800.706844.48175 --debug
        cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scsendjournal -H {self.host} {event_id} EvPrefOrgID {origin_id} --debug'
        # print in red and bold the command
        print(f'\n\033[1;32m{cmd}\033[0m\n')
        os.system(cmd)
    
    def run(self):
        print(self.reported_origins)
        for origin_id in self.reported_origins:
            # Check if origin_id is not an empty string
            if not origin_id:
                continue
            event_id, orig_phases = self.get_event_id(origin_id)
            # print in blue and bold the origin_id and origin phases
            print(f'\n\033[1;34m{origin_id} {orig_phases}\033[0m\n')
            # if event_id is not None, change event type
            if event_id:
                eval_mode, author, pref_phases = self.get_eval_mode(event_id)
                # print evaluation mode and event_id in red and bold
                print(f'\n\n\033[1;31m{eval_mode} {event_id} {author} {pref_phases}\033[0m\n\n')
                if eval_mode == 'manual':
                    if author == 'EQCCT' and int(orig_phases) > int(pref_phases):
                        print(f'\033[1;31m new EQCCT origin has more phases than the preferred one, changing preferred origin\033[0m')
                        self.fix_as_prefered(origin_id, event_id)
                    print(f'\033[1;31m{event_id} has a manual solution already, skiping...\033[0m')
                    continue
                # print in green and bold that the event type will is being changed to earthquake
                print(f'\n\n\033[1;32mChanging event type to {self.ev_type} for {event_id}\033[0m\n\n')
                self.change_event_type(event_id)
                self.fix_as_prefered(origin_id, event_id)
            else:
                # print in red and bold that the origin_id was not found in the database
                print(f'\033[1;31m{origin_id} not found in the database\033[0m')


def runner(every_m, delay=0, db='10.100.100.13:4803', ai_picker='ai_picker.py'):
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

    # taking current time in UTC
    t = datetime.datetime.utcnow() - datetime.timedelta(minutes=delay)
    t_i = t - datetime.timedelta(minutes=(every_m))

    # change the init, end time and dt in ai_picker.inp
    change_times(t_i.strftime("%Y-%m-%d %H:%M:%S"),
                 t.strftime("%Y-%m-%d %H:%M:%S"),
                 (every_m)*60)

    print(f'\n\n\trunning from {t_i} to {t}\n\n')
    os.system('head -10 ai_picker.inp')
    cmd = f'time {ai_picker}'
    # print in red and bold the command
    print(f'\033[1;31m{cmd}\033[0m')
    os.system(cmd)

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
            print(cmd)
            os.system(cmd)
            # send to sc5
            send_to_sc5(output_path, f'midtx{num}', test=True)

            # wait 15 seconds 
            time.sleep(15)
            
            # change the event type to earthquake
            EventTypeChanger(db).run()

        else:
            print('\n\n\tArchivo vacio!\n\n')
    else:
        print('\n\n\tNo existe mag.xml!\n\n')
    print('\n\tSiguiente ejecucion a las: ',
          t + datetime.timedelta(minutes=(every_m)), 'UT\n')

    tf = datetime.datetime.now() + datetime.timedelta(hours=(5))

    logger(t, tf)


if __name__ == "__main__":

    every_minutes = 30  # period of excecution in minutes
    #every_minutes = 1  # period of excecution in minutes
    minutes = 60  # period of excecution in minutes
    #delay = 60    # delay in minutes
    delay = 0    # delay in minutes
    schedule.every(every_minutes).minutes.do(runner, every_m=minutes, delay=delay, db='sc3primary.beg.utexas.edu')

    while True:
        schedule.run_pending()
        time.sleep(1)  # wait one second
