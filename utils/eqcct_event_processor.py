#!/home/siervod/anaconda3/envs/eqcc/bin/python
"""
Author: Daniel Siervo, emetdan@gmail.com
Date: 2024-11-12
"""
import os
import pandas as pd
import mysql.connector # pip install mysql-connector-python
from cwav import Cwav_EQTransformer
import sys
# append 2 directories above the script path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main_picker import prep_Cwav_params

def get_stations_start_and_end_times(eventID: str, picks_dir: str):
    """
    From a given eventID, gets the time window to download the waveforms,
    the station list to download and the difference in seconds between
    starttime and endtime

    Parameters
    ----------
    eventID : str
        Event ID

    Returns
    -------
    start_time : str
        Start time to download the waveforms
    end_time : str
        End time to download the waveforms
    delta_time : int
        Difference in seconds between start_time and end_time
    station_list : list
        List of stations to download the waveforms
    """
    script_path = os.path.dirname(os.path.abspath(__file__))
    print(script_path)
    query_path = os.path.join(script_path, 'stations_from_eventID.sql')
    query_str = open(query_path, 'r').read().format(eventID=eventID)
    
    mydb = mysql.connector.connect(host="scdb.beg.utexas.edu", # sysro:0niReady
                                user="sysro",
                                passwd="0niReady",
                                database="seiscomp")
    
    df = pd.read_sql(query_str, mydb)
    mydb.close()
    # sort by stations
    df.sort_values(by='station', inplace=True)
    # create a new column with net.sta.loc.cha[:2]*
    df['net.sta.loc.cha'] = df['network'] + '.' + df['station'] + '.' + df['location'] + '.' + df['channel'].str[:2] + '*'
    stations = df['net.sta.loc.cha'].to_list()
    
    df['pick_time'] = pd.to_datetime(df['pick_time'])
    
    # P - S time 170 km from the source is 11 seconds, P 20 km from the source to P 170 km from the source is 25 seconds
    start_time = df['pick_time'].min() - pd.Timedelta(seconds=10)
    end_time = df['pick_time'].max() + pd.Timedelta(seconds=20)
    
    delta_time = (end_time - start_time).total_seconds()
    
    # Ensure that the time window is at least 60 seconds
    minimum_duration = 60  # seconds
    if delta_time < minimum_duration:
        # Calculate the additional time needed
        additional_time = minimum_duration - delta_time
        
        end_time += pd.Timedelta(seconds=additional_time)
        delta_time = (end_time - start_time).total_seconds()
    
    print(f'Downloading {stations} from {start_time} to {end_time} with {delta_time} seconds')
    change_inp_file(start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S'), int(delta_time), stations, eventID, picks_dir)


def change_inp_file(ti: str, tf: str, dt: int, stations: list, eventID: str, picks_dir: str):
    """Change starttime, endtim, dt stations and ID in the in ai_picker.inp file

    Parameters
    ----------
    ti : str
        Initial UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    tf : str
        Final UTC datetime in strftime format: %Y-%m-%d %H-%M-%S
    dt : int
        Delta time in seconds (tf-ti)
    stations : list
        List of stations
    eventID : str
        Event ID
    """
    stations_str = ','.join(stations)

    script_path = os.path.dirname(os.path.abspath(__file__))
    inp_path = os.path.join(script_path, 'ai_picker_event.inp')
    f_lines = open(inp_path).readlines()

    for idx, line in enumerate(f_lines):
        if line.startswith('starttime'):
            start_idx = idx
        elif line.startswith('endtime'):
            end_idx = idx
        elif line.startswith('dt'):
            dt_idx = idx
        elif line.startswith('download_data'):
            stations_idx = idx
        elif line.startswith('event_id'):
            event_id_idx = idx
        elif line.startswith('picks_dir'):
            picks_dir_idx = idx
        elif line.startswith('general_data_dir'):
            data_dir_idx = idx
        elif line.startswith('general_output_dir'):
            output_dir_idx = idx

    # replacing start, end and dt time lines
    f_lines[start_idx] = f'starttime = {ti}\n'
    f_lines[end_idx] = f'endtime = {tf}\n'
    f_lines[dt_idx] = f'dt = {dt}\n'
    f_lines[stations_idx] = f'download_data = {stations_str}\n'
    f_lines[event_id_idx] = f'event_id = {eventID}\n'
    f_lines[picks_dir_idx] = f'picks_dir = {picks_dir}\n'
    f_lines[data_dir_idx] = f'general_data_dir = test/data/{eventID}\n'
    f_lines[output_dir_idx] = f'general_output_dir = test/{eventID}\n'

    # writing new file
    with open('ai_picker.inp', 'w') as f:
        text = ''.join(f_lines)
        f.write(text)
    

def run_eqcct():
    client_dict, download_data,filter_data, picker, pnet_dict, eqt_dict, mysqldb_dict = prep_Cwav_params('ai_picker.inp')

    cwav_eqcct = Cwav_EQTransformer(download_data,eqt_dict,client_dict,
                                picker=picker,
                                mysqldb_dict=mysqldb_dict)
    
    print(f'\ncwav_eqt object:\n\t{cwav_eqcct.__dict__}\n')
    cwav_eqcct.create_json()
    cwav_eqcct.download_mseed()
    cwav_eqcct.mseedpredictor()
    cwav_eqcct.picks2xml()

def download_and_run_eqcct(eventID, picks_dir):
    get_stations_start_and_end_times(eventID, picks_dir)
    run_eqcct()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download and run EQCCT for a given event ID.")
    parser.add_argument("event_id", type=str, help="Event ID for which to run EQCCT.")
    parser.add_argument("picks_dir", type=str, help="Directory where picks are stored.")
    
    args = parser.parse_args()
    
    download_and_run_eqcct(args.event_id, args.picks_dir)