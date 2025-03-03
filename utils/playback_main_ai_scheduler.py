#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on August 2023

@author: Daniel Siervo Plata [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import os
import sys
import logging
import glob
import time
import datetime
import random
import mysql.connector # pip install mysql-connector-python
from icecream import ic
log_file_name = os.path.basename(__file__).replace('.py', '.log')
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


def change_times(ti: str, tf: str, dt: int, ai_scheduler_file: str):
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

    schduler_dir = os.path.dirname(ai_scheduler_file)
    f_lines = open(ai_scheduler_file).readlines()

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
    ai_picker_inp = os.path.join(schduler_dir, 'ai_picker.inp')
    with open(ai_picker_inp, 'w') as f:
        text = ''.join(f_lines)
        f.write(text)

    return ai_picker_inp

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

    def __init__(self, host, ev_type='earthquake', orig_ids_file='reported_origins.txt',
                 user='sysop', passwd='sysop', database='seiscomp3',
                 #scroot=os.environ["SEISCOMP_ROOT"]):
                 scroot='/home/siervod/seiscomp3'):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.database = database
        self.ev_type = ev_type
        self.orig_ids_file = orig_ids_file
        self.scroot = scroot

    @property
    def reported_origins(self):
        if not os.path.isfile(self.orig_ids_file):
            return []
        with open(self.orig_ids_file, 'r') as f:
            lines = f.readlines()
        return [line.strip().strip('\n') for line in lines]
    
    def mysql_connect(self):
        self._mydb = mysql.connector.connect(host=self.host,
                                            user=self.user,
                                            passwd=self.passwd,
                                            database=self.database)
        ic(self.host)
        ic(self.user)
        ic(self.database)
        return self._mydb.cursor()

    def get_event_id(self, origin_id):
        mycursor = self.mysql_connect()
        mycursor.execute(self.query_str_evID.format(origin_id=origin_id))
        myresult = mycursor.fetchall()
        # if myresult is empty, return None
        if not myresult:
            return None, None
        return myresult[0]

    def get_eval_mode(self, event_id):
        mycursor = self.mysql_connect()
        mycursor.execute(self.query_str_eval_mode.format(event_id=event_id))
        # the query returns a tuple with the evaluation mode and the author
        myresult = mycursor.fetchall()
        return myresult[0]

    def change_event_type(self, event_id):
        cmd = f'{self.scroot}/bin/seiscomp exec scsendjournal -H {self.host} {event_id} EvType "{self.ev_type}" --debug'
        # print in red and bold the command
        ic(cmd)
        ic(os.system(cmd))
    
    def fix_as_prefered(self, origin_id, event_id):
        # scsendjournal -H sc3primary.beg.utexas.edu texnet2023attj EvPrefOrgID Origin/20230111205800.706844.48175 --debug
        cmd = f'{self.scroot}/bin/seiscomp exec scsendjournal -H {self.host} {event_id} EvPrefOrgID {origin_id} --debug'
        # print in red and bold the command
        ic(cmd)
        ic(os.system(cmd))
    
    def run(self):
        ic(self.reported_origins)
        for origin_id in self.reported_origins:
            ic(origin_id)
            #print_ic(f'\n\n\033[1;31m Origin {origin_id} \033[0m\n\n')
            # Check if origin_id is not an empty string
            if not origin_id:
                continue
            
            not_found = False
            # get event_id, origin phases and magnitude
            max_tries = 20
            for i in range(max_tries):
                try:
                    event_id, orig_phases, mag = ic(self.get_event_id(origin_id))
                    break
                except ValueError:
                    if i == max_tries - 1:
                        msg = f'\n\n\033[1;31m Origin {origin_id} not found in the database after {max_tries} attempts. Skipping.. \033[0m\n\n'
                        msg_2 = f'Origin {origin_id} not found in the database after {max_tries} attempts. Skipping..'
                        print_ic(msg_2)
                        not_found = True
                        break
                    else:
                        msg = f'\n\n\033[1;31m Origin {origin_id} not found in the database. Retrying in 10 seconds.. \033[0m\n\n'
                        msg_2 = f'Origin {origin_id} not found in the database after {i} attempts. Retrying in 10 seconds..'
                        print_ic(msg_2)
                        time.sleep(10)

            ic(not_found)
            print_ic(f'\ni: {i}\n')
            if not_found:
                continue

            # print in blue and bold the origin_id and origin phases
            #print_ic(f'\n\033[1;34m{origin_id} {orig_phases}\033[0m\n')
            #print_ic(f'\n{origin_id} {orig_phases}\n')
            # if event_id is not None, change event type
            if event_id:
                # get preferred origin values
                eval_mode, author, pref_phases, pref_status, ev_type, pref_mag = self.get_eval_mode(event_id)
                # print evaluation mode and event_id in red and bold
                #print_ic(f'\n\n\033[1;31m{eval_mode} {event_id} {author} {pref_phases} {ev_type} \033[0m\n\n')
                #print_ic(f'{eval_mode} {event_id} {author} {pref_phases} {ev_type}')
                ic(eval_mode)
                ic(event_id)
                ic(author)
                ic(pref_phases)
                ic(ev_type)
                if eval_mode == 'manual' or pref_status == 'reported':
                    ic(orig_phases)
                    ic(pref_mag)
                    ic(mag)
                    if author == 'EQCCT':
                        # probably the EQCCT origin is the only one for this event
                        if ev_type != self.ev_type:
                            #print_ic(f'\033[1;32mChanging event type to {self.ev_type} on {event_id}. New event added!\033[0m')
                            print_ic(f'Changing event type to {self.ev_type} on {event_id}. New event added!')
                            self.change_event_type(event_id)
                        if float(pref_mag) < 1.9:
                            #print_ic(f'\033[1;31mPreferred EQCCT origin {origin_id} has magnitude less than 1.9, checking phases {event_id}\033[0m')
                            print_ic(f'Preferred EQCCT origin {origin_id} has magnitude less than 1.9, checking phases {event_id}')
                            if (ic(int(orig_phases) > int(pref_phases))):
                                #print_ic(f'\033[1;31mEQCCT origin {origin_id} has more phases than previous EQCCT one, setting it as preferred on {event_id}\033[0m')
                                print_ic(f'EQCCT origin {origin_id} has more phases than previous EQCCT one, setting it as preferred on {event_id}')
                                self.fix_as_prefered(origin_id, event_id)
                        else:
                            #print_ic(f'\033[1;31mPreferred EQCCT origin {origin_id} has magnitude greater or equal to 1.9 {event_id}\033[0m')
                            print_ic(f'Preferred EQCCT origin {origin_id} has magnitude greater or equal to 1.9 {event_id}')
                            # if the magnitude of the prefered EQCCT origin is greater or equal to 1.9,
                            # the new origin will be set as preferred only if it has a magnitude greater or equal to 1.9
                            if (ic(int(orig_phases) > int(pref_phases))) and (float(mag) >= 1.9):
                                #print_ic(f'\033[1;31mEQCCT origin {origin_id} has more phases than previous EQCCT one, setting it as preferred on {event_id}\033[0m')
                                print_ic(f'EQCCT origin {origin_id} has more phases than previous EQCCT one, setting it as preferred on {event_id}')
                                self.fix_as_prefered(origin_id, event_id)
                            else:
                                #print_ic(f'\033[1;31m{origin_id} has less phases or magnitude less than 1.9, not setting it as preferred on {event_id}\033[0m')
                                print_ic(f'{origin_id} has less phases or magnitude less than 1.9, not setting it as preferred on {event_id}')
                    #print_ic(f'\033[1;31m{event_id} has a manual solution already, skiping...\033[0m')
                    print_ic(f'{event_id} has a manual solution already, skiping...')
                    continue
                # the status is rejected and the event type is duplicate skip
                elif pref_status == 'rejected' and ev_type in ('duplicate', 'not existing'):
                    #print_ic(f'\033[1;31m{event_id} has a rejected solution, skiping...\033[0m')
                    print_ic(f'{event_id} has a rejected solution, skiping...')
                    continue
                # print in green and bold that the event type is being changed to earthquake
                #print_ic(f'\n\n\033[1;32mChanging event type to {self.ev_type} on {event_id}\033[0m\n\n')
                print_ic(f'Changing event type to {self.ev_type} on {event_id}')
                self.change_event_type(event_id)
                self.fix_as_prefered(origin_id, event_id)
            else:
                # print in red and bold that the origin_id was not found in the database
                #print_ic(f'\033[1;31m{origin_id} not found in the database\033[0m')
                print_ic(f'{origin_id} not found in the database')


def runner(starttime: str, endtime: str, ai_scheduler_file: str, every_m: int = 40, dispatch: bool = False):
    """Excecute ai_picker.py between starttime and endtime using the parameters in ai_scheduler_file

    Parameters
    ----------
    starttime : str
        Start time in strftime format: %Y-%m-%d %H-%M-%S
    endtime : str
        endtime time in strftime format: %Y-%m-%d %H-%M-%S
    ai_scheduler_file : str
        Path to the ai_picker_scdl.inp file
    """

    params = read_params(ai_scheduler_file)
    # extract folder containing ai_scheduler_file
    scheduler_dir = os.path.dirname(ai_scheduler_file)
    # change working directory to scheduler_dir
    os.chdir(scheduler_dir)
    
    # output folder
    main_path= os.path.join(scheduler_dir, params['general_output_dir'])
    os.system('rm -fr %s' % main_path)

    t = datetime.datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S")
    t_i = datetime.datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S")

    # check that the end time is greater than the start time
    if t < t_i:
        print_ic(f'End time must be greater than start time: {t} < {t_i}')
        raise ValueError(f'End time must be greater than start time: {t} < {t_i}')
    
    # check that every_m is less than t - t_i
    if (every_m*60) > (t - t_i).total_seconds():
        print_ic(f'every_m must be less than t - t_i: {every_m*60} > {(t - t_i).total_seconds()}')
        raise ValueError(f'every_m must be less than t - t_i: {every_m*60} > {(t - t_i).total_seconds()}')
    
    # change the init, end time and dt in ai_picker.inp
    ai_picker_inp = change_times(t_i.strftime("%Y-%m-%d %H:%M:%S"),
                 t.strftime("%Y-%m-%d %H:%M:%S"),
                 (every_m)*60, ai_scheduler_file)

    print_ic(f'\nrunning from {t_i} to {t}\\n')
    #os.system('head -10 ai_picker.inp')
    os.system(f'head -10 {ai_picker_inp}')
    cmd = f'time ai_picker.py'
    print_ic(cmd)
    os.system(cmd)

    # getting the origins path
    output_path = get_origins_path(main_path, 'origenes_preferidos.xml')
    # getting the picks path
    picks_path = get_origins_path(main_path, 'picks.xml')

    #cmd_picks = 'scdispatch -i %s -H %s -u aitx' % (picks_path, db)
    #print_ic(cmd_picks)
    #+os.system(cmd_picks)
    if dispatch:
        # print in green and bold that the picks file will be sent to sc5
        print_ic(f'\033[1;32mSending picks file to sc5\033[0m')
        num = random.randint(1, 100)
        send_to_sc5(picks_path, f'aitx{num}')
    else:
        # print in red and bold that the picks file won't be sent to sc5
        print_ic(f'\033[1;31mPicks file will not be sent to sc5\033[0m')
        # print that to send the dispatch option in the eqcct_playback.cfg file has to be True
        print_ic(f'\033[1;31mTo send the picks file to sc5, set dispatch to True in eqcct_playback.cfg\033[0m')

    if output_path is not None:
        # if the file is not empty
        if os.path.getsize(output_path):
            print_ic(f'xml a modificar: {output_path}')
            # changing the xml version of the origins file
            change_xml_version(output_path)

            os.system('head -3 %s' % output_path)

            # random number to avoid repetead users
            num = random.randint(1, 100)
            #cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scdispatch -i %s -H %s -u aitexnet%d' % (output_path, db, num)
            #cmd = f'/home/siervod/seiscomp3/bin/seiscomp exec scdispatch -i %s -H %s -u aitx%d' % (output_path, db, num)
            #print_ic(cmd)
            #os.system(cmd)
            # send to sc5
            if dispatch:
                print_ic(f'\033[1;32mSending origins file to sc5\033[0m')
                send_to_sc5(output_path, f'aitx{num}')
                
                # wait 45 seconds
                waiting_time = 45
                print_ic(f'waiting {waiting_time} seconds before changing event type')
                time.sleep(waiting_time)
                
                # change the event type to earthquake in sc5
                EventTypeChanger('scdb.beg.utexas.edu', user='sysro', passwd='0niReady', database='seiscomp',
                                scroot='/home/siervod/seiscomp').run()
            else:
                print_ic(f'\033[1;31mOrigins file will not be sent to sc5\033[0m')
                print_ic(f'\033[1;31mTo send the origins file to sc5, set dispatch to True in eqcct_playback.cfg\033[0m')
        else:
            print_ic('\n\n\tEmpty file!\n\n')
    else:
        print_ic('\n\n\tmag.xml not found!\n\n')



def print_ic(msg):
    ic(msg)
    print(msg)


def send_to_sc5(xml_path, usr='aitexnet'):
    """Sends picks or origins xml files to sc5.
    """
    cmd = f"/home/siervod/seiscomp/bin/seiscomp exec scdispatch -i {xml_path} -H scdb.beg.utexas.edu -u {usr}"
    print_ic(cmd)
    os.system(cmd)


if __name__ == "__main__":

    # if SEISCOMP_ROOT is not set, set it to /home/siervod/seiscomp
    if 'SEISCOMP_ROOT' not in os.environ:
        os.environ['SEISCOMP_ROOT'] = '/home/siervod/seiscomp'
    import configparser
    config = configparser.ConfigParser()
    try:
        config.read('eqcct_playback.cfg')
        if not config.read('eqcct_playback.cfg'):
            raise FileNotFoundError
    except FileNotFoundError:
        raise FileNotFoundError('eqcct_playback.cfg not found!')

    starttime = config['playback']['starttime']
    endtime = config['playback']['endtime']
    every_m = config.getint('playback', 'every_m')
    playback_dir = config['playback']['playback_dir']
    # get the dispatch option, default is False
    dispatch = config.getboolean('playback', 'dispatch', fallback=False)
    
    print(f'Running from {starttime} to {endtime} every {every_m} minutes')
    print(f'Playback dir: {playback_dir}')
    
    # check that the directory exists
    if not os.path.exists(playback_dir):
        raise FileNotFoundError(f'EQCCT intances directory {playback_dir} not found!')

    # check that the directory is not empty
    if not os.listdir(playback_dir):
        raise FileNotFoundError(f'EQCCT intances directory {playback_dir} is empty!')

    # run runner function for every subfolder in playback_dir
    # knowing that there should be a ai_picker_scdl.inp file in each subfolder
    scheduler_inp_files = glob.glob(os.path.join(playback_dir, '*', 'ai_picker_scdl.inp'))
    scheduler_inp_files += [os.path.join(playback_dir, 'ai_picker_scdl.inp')]
    for scheduler_inp_file in scheduler_inp_files:
        if os.path.exists(scheduler_inp_file):
            subfolder = os.path.dirname(scheduler_inp_file)
            print(f'Running on {subfolder}')
            runner(starttime=starttime, endtime=endtime, every_m=every_m, ai_scheduler_file=scheduler_inp_file, dispatch=dispatch)
    
        
    
    
