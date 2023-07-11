#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sep 2020

@author: Daniel Siervo P. [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import os
import sys
import logging
import schedule
import time
import datetime
import random
import mysql.connector # pip install mysql-connector-python
from icecream import ic
log_file_name = os.path.basename(__file__).replace('.py', '.log')
#log_file_name = '/home/siervod/projects/realtime/delaware_culberson/ai_scheduler_culberson.log'
logging.basicConfig(filename=log_file_name, level=logging.DEBUG, format='%(message)s')


def loggin_test(s):
    logging.debug(s)
    print(s, file=sys.stderr)


def time_ic_debug():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S: ')


ic.configureOutput(prefix=time_ic_debug, outputFunction=loggin_test)


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

    ic(xmlfile, orig_path)
    return orig_path


def logger(ti, tf, start, end):
    logfile = 'scheduler_times.log'
    if not os.path.isfile(logfile):
        f = open(logfile, 'w')
    else:
        f = open(logfile, 'a')

    msg = f'From {ti} to {tf} with: {start} to {end}'

    print(msg,
          file=f)

    f.close()


class EventTypeChanger:
    """Reads the list of origins ids from reported_origins.txt iterates over them,
    searches the event id and changes the event type to 'earthquake'
    using scsendjournal (scsendjournal -H sc3primary.beg.utexas.edu texnet2023attj EvType "earthquake" --debug)
    """

    query_str_evID = """
    select POE.publicID,
    Origin.quality_usedPhaseCount, Magnitude.magnitude_value
    from Event left join PublicObject AS POE ON Event._oid = POE._oid
    inner join OriginReference on Event._oid=OriginReference._parent_oid
    inner join PublicObject POO on POO.publicID=OriginReference.originID
    inner join Origin on POO._oid=Origin._oid
    left join Magnitude ON Magnitude._parent_oid = POO._oid
    where
    OriginReference.originID = '{origin_id}'
    and Magnitude.type = 'ML(TexNet)'"""

    query_str_eval_mode = """
    select
    Origin.evaluationMode, Origin.creationInfo_author, Origin.quality_usedPhaseCount,
    Origin.evaluationStatus, Event.type, Magnitude.magnitude_value
    from Event left join PublicObject AS POE ON Event._oid = POE._oid
    left join PublicObject as POOri ON Event.preferredOriginID=POOri.publicID 
    left join Origin ON POOri._oid=Origin._oid
    left join PublicObject as POMag on Event.preferredMagnitudeID=POMag.publicID  
    left join Magnitude ON Magnitude._oid = POMag._oid 
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
        mycursor = self._mydb.cursor()
        mycursor.execute(self.query_str_eval_mode.format(event_id=event_id))
        # the query returns a tuple with the evaluation mode and the author
        myresult = mycursor.fetchall()
        return myresult[0]

    def change_event_type(self, event_id):
        cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scsendjournal -H {self.host} {event_id} EvType "{self.ev_type}" --debug'
        # print in red and bold the command
        ic(cmd)
        ic(os.system(cmd))
    
    def fix_as_prefered(self, origin_id, event_id):
        # scsendjournal -H sc3primary.beg.utexas.edu texnet2023attj EvPrefOrgID Origin/20230111205800.706844.48175 --debug
        cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scsendjournal -H {self.host} {event_id} EvPrefOrgID {origin_id} --debug'
        # print in red and bold the command
        ic(cmd)
        ic(os.system(cmd))
    
    def run(self):
        ic(self.reported_origins)
        for origin_id in self.reported_origins:
            ic(origin_id)
            print(f'\n\n\033[1;31m Origin {origin_id} \033[0m\n\n')
            # Check if origin_id is not an empty string
            if not origin_id:
                continue
            try:
                event_id, orig_phases, mag = ic(self.get_event_id(origin_id))
            except ValueError:
                ic(print(f'\n\n\033[1;31m Origin {origin_id} not found in the database. Skiping.. \033[0m\n\n'))
                continue
            # print in blue and bold the origin_id and origin phases
            ic(print(f'\n\033[1;34m{origin_id} {orig_phases}\033[0m\n'))
            # if event_id is not None, change event type
            if event_id:
                # get preferred origin values
                eval_mode, author, pref_phases, pref_status, ev_type, pref_mag = ic(self.get_eval_mode(event_id))
                # print evaluation mode and event_id in red and bold
                ic(print(f'\n\n\033[1;31m{eval_mode} {event_id} {author} {pref_phases} {ev_type} \033[0m\n\n'))
                if eval_mode == 'manual' or pref_status == 'reported':
                    ic(orig_phases)
                    ic(pref_phases)
                    ic(pref_mag)
                    ic(mag)
                    if author == 'EQCCT':
                        # probably the EQCCT origin is the only one for this event
                        if ev_type != self.ev_type:
                            ic(print(f'\033[1;32mChanging event type to {self.ev_type} on {event_id}. New event added!\033[0m'))
                            self.change_event_type(event_id)
                        if float(pref_mag) < 1.9:
                            ic(print(f'\033[1;31mPreferred EQCCT origin {origin_id} has magnitude less than 1.9, checking phases {event_id}\033[0m'))
                            if (ic(int(orig_phases) > int(pref_phases))):
                                ic(print(f'\033[1;31mEQCCT origin {origin_id} has more phases than previous EQCCT one, setting it as preferred on {event_id}\033[0m'))
                                self.fix_as_prefered(origin_id, event_id)
                        else:
                            ic(print(f'\033[1;31mPreferred EQCCT origin {origin_id} has magnitude greater or equal to 1.9 {event_id}\033[0m'))
                            # if the magnitude of the prefered EQCCT origin is greater or equal to 1.9,
                            # the new origin will be set as preferred only if it has a magnitude greater or equal to 1.9
                            if (ic(int(orig_phases) > int(pref_phases))) and (float(mag) >= 1.9):
                                ic(print(f'\033[1;31mEQCCT origin {origin_id} has more phases than previous EQCCT one, setting it as preferred on {event_id}\033[0m'))
                                self.fix_as_prefered(origin_id, event_id)
                            else:
                                print(f'\033[1;31m{origin_id} has less phases or magnitude less than 1.9, not setting it as preferred on {event_id}\033[0m')
                    print(f'\033[1;31m{event_id} has a manual solution already, skiping...\033[0m')
                    continue
                # the status is rejected and the event type is duplicate skip
                elif pref_status == 'rejected' and ev_type in ('duplicate', 'not existing'):
                    print(f'\033[1;31m{event_id} has a rejected solution, skiping...\033[0m')
                    continue
                # print in green and bold that the event type is being changed to earthquake
                print(f'\n\n\033[1;32mChanging event type to {self.ev_type} on {event_id}\033[0m\n\n')
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

    # taking current time in UTC - delay
    end = datetime.datetime.utcnow()
    t = end - datetime.timedelta(minutes=delay)
    t_i = t - datetime.timedelta(minutes=(every_m))

    # change the init, end time and dt in ai_picker.inp
    change_times(t_i.strftime("%Y-%m-%d %H:%M:%S"),
                 t.strftime("%Y-%m-%d %H:%M:%S"),
                 (every_m)*60)

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

            # wait 15 seconds
            ic(time.sleep(30))
            
            # change the event type to earthquake
            EventTypeChanger(db).run()

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

    schedule.every(every_minutes).minutes.do(runner,
                                             every_m=minutes,
                                             delay=delay,
                                             db='sc3primary.beg.utexas.edu')

    while True:
        schedule.run_pending()
        time.sleep(10)  # wait one minute
