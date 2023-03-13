#!/home/siervod/anaconda3/envs/eqcc/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mar 25 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
import csv
from obspy import UTCDateTime
import datetime
import os
import numpy as np
import pandas as pd
import glob
import sys


def main_picks(input_file='picks.csv', output_file=None, min_prob_p=0.6,
               min_prob_s=0.5,
               dt=3000, ai='pnet'):
    """Transform PhaseNet picks.csv file into Seiscomp XML file

    Parameters
    ----------
    input_file : str
        Path to PhaseNet picks.csv file or Path to EQTransformer 
        X_prediction_results.csv file, by default 'picks.csv'
    output_file : str
        Path to new Sesicomp XML file
    min_prob_p: float
        Minimun probability to consider a P phase pick
    min_prob_s: float
        Minimun probability to consider a S phase pick
    dt: int
        Waveform length in seconds
    ai: str
        AI type, can be: pnet or eqt (phasenet or eqtransformer)
    """

    # Obtaining list of Picks objects from file
    if ai == 'pnet':
        pick_list = read_picks(input_file, dt, min_prob_p, min_prob_s)
    elif ai in ('eqt', 'eqcc', 'eqcctps', 'eqcct'):
        pick_list = prepare_eqt(input_file, ai)

    # Creating xml text
    xml_text = picks2xml(pick_list)

    # Using the YYmmdd_HH to name the output xml if the
    # output_file name is not provided
    if output_file is None:
        t_pick_1 = pick_list[0].pick_time
        output_file = t_pick_1.strftime('%Y%m%d_%H_pick.xml')

    # Writting in the output file
    with open(output_file, 'w') as f:
        f.write(xml_text)
    
    print(f'\nOutput file: {output_file}')


def prepare_eqt(input_dir, ai):
    """Merge X_prediction_results.csv files of each station in a list of Picks objects

    Parameters
    ----------
    input_file : str
        Directory path which contains station_outputs folders
    min_prob : float
        Mimimum probability to consider a pick
    """
    sta_dirs = glob.glob(os.path.join(input_dir, '*_outputs'))
    df = pd.concat([pd.read_csv(os.path.join(sta, 'X_prediction_results.csv')) \
                for sta in sta_dirs])
    
    if ai == 'eqt':
        interest_col = ['network', 'station', 'instrument_type', 'detection_probability',
                        'p_arrival_time', 'p_probability', 'p_snr',
                        's_arrival_time', 's_probability', 's_snr']

    elif ai in ('eqcc', 'eqcctps'):
        interest_col = ['file_name', 'station',
                        'p_arrival_time', 'p_probability',
                        's_arrival_time', 's_probability']

    # Keeping with columns of interest
    df = df[interest_col]
    # Deleting rows without P phase
    df = df.dropna(subset=['p_probability'])
    # Changing NaN for "no pick"
    df = df.fillna('no pick')
    # Removing white spaces arround station name
    df['station'] = df['station'].str.strip()

    # Writting in csv the data
    df.to_csv(os.path.join(input_dir, 'all_picks.csv'), index=False)

    if ai == 'eqt':
        # Create a list of picks
        p_list = read_eqt_picks(df['network'].tolist(), df['station'].tolist(),
                                df['instrument_type'].tolist(),
                                df['p_arrival_time'].tolist(),
                                df['p_probability'].tolist(),
                                df['s_arrival_time'].tolist(),
                                df['s_probability'].tolist(),
                                p_snrs=df['p_snr'].tolist(),
                                s_snrs=df['p_snr'].tolist())
    elif ai in ('eqcc', 'eqcctps', 'eqcct'):
        # exctracting from the file_name column the network, location and channel
        # the file_name column has the following format: station/network.station.location.channel__starttime__endtime.mseed
        df['network'] = df['file_name'].str.split('/').str[1].str.split('.').str[0]
        df['location'] = df['file_name'].str.split('/').str[1].str.split('.').str[2]
        df['channel'] = df['file_name'].str.split('/').str[1].str.split('.').str[3].str.split('__').str[0].str[:-1]


        # Create a list of picks
        p_list = read_eqcc_picks(df['network'].tolist(), df['station'].tolist(),
                                df['channel'].tolist(), df['location'].tolist(),
                                df['p_arrival_time'].tolist(),
                                df['p_probability'].tolist(),
                                df['s_arrival_time'].tolist(),
                                df['s_probability'].tolist())

    return p_list

def read_eqcc_picks(nets, stations, chs, locs, p_times, p_probs, s_times, s_probs):
    """Iterate over picks to generate list of Picks objects

    Parameters
    ----------
    nets : list
        Networks list
    stations : list
        Stations list
    chs : list
        Channels list
    p_times : list
        P pick times
    p_probs : list
        P picks probabilities
    s_times : list
        S picks times
    s_probs : list
        S picks probabilities
    """
    picks_list = []

    key = 'eqt_station_thr_dict'
    if key in read_params():
        thr_dict = eval(read_params()[key])
    else:
        thr_dict = None

    for i in range(len(s_times)):
        net, station, ch, loc = nets[i], stations[i], chs[i], locs[i]
        s_pick = None

        ch += 'Z'

        p_t, p_prob = p_times[i], p_probs[i]
        
        if thr_dict is not None:
            if station in thr_dict:
                try:
                    thr = float(thr_dict[station])
                except ValueError:
                    thr = 0.001
                    # print in red and bold that the threshold is not a float
                    print(f'\033[1;31m{station} threshold is not a float, using {thr}\033[0m')
                if p_prob < thr:
                    # print in red and bold that the pick will be discarded because of the threshold
                    print(f'\033[1;33m{station} {p_t} picks discarded, p_prob:{p_prob} < {thr}\033[0m')
                    continue
                    
        p_pick = eqt_pick_constructor(p_t, p_prob, net,
                                        station, loc, ch, 'P', 'EQCCT')
        picks_list.append(p_pick)

        s_t, s_prob = s_times[i], s_probs[i]
        if s_t != 'no pick':
            s_pick = eqt_pick_constructor(s_t, s_prob, net, station, loc, ch, 'S', 'EQCCT')
            picks_list.append(s_pick)

        print(f'{i}. {station}, p_t:{p_t}, p_prob:{p_prob}, s_t:{s_t}, s_prob:{s_prob}')

    return picks_list

def read_eqt_picks(nets, stations, chs, p_times, p_probs, s_times, s_probs,
                   p_snrs, s_snrs):
    """Iterate over picks to generate list of Picks objects

    Parameters
    ----------
    nets : list
        Networks list
    stations : list
        Stations list
    chs : list
        Channels list
    p_times : list
        P pick times
    p_probs : list
        P picks probabilities
    s_times : list
        S picks times
    s_probs : list
        S picks probabilities
    """
    picks_list = []

    for i in range(len(s_times)):
        net, station, ch = nets[i], stations[i], chs[i]
        s_pick = None
        loc = '00'
        if ch == 'EH':
            loc = '20'
        elif ch == 'HN':
            loc = '10'

        ch += 'Z'

        p_t, p_prob, p_snr = p_times[i], p_probs[i], p_snrs[i]

        # filtering bad picks according to statistical analysis doing in
        # the notebook EDA_EQTransformer_probs.ipynb
        if p_snr == 'no pick':
            p_snr = 0
        p_snr = float(p_snr)
        if p_prob >= 0.01 and p_snr >= -1.7:
            p_pick = eqt_pick_constructor(p_t, p_prob, net,
                                          station, loc, ch, 'P')
            picks_list.append(p_pick)

        s_t, s_prob, s_snr = s_times[i], s_probs[i], p_snrs[i]
        if s_t != 'no pick':
            if s_snr == 'no pick':
                s_snr = 0
            s_snr = float(s_snr)
            if float(s_prob) >= 0.01 and s_snr >= 0:
                s_pick = eqt_pick_constructor(s_t, s_prob, net,
                                              station, loc, ch, 'S')
                picks_list.append(s_pick)

        print(f'{i}. {station}, p_t:{p_t}, p_prob:{p_prob}, s_t:{s_t}, s_prob:{s_prob}, p_snr:{p_snr}, s_snr:{s_snr}')

    return picks_list


def read_picks(phaseNet_picks, dt, min_prob_p=0.3, min_prob_s=0.3):
    '''Read phaseNet picks and returns list of Pick objects

    Parameters
    ----------
    phaseNet_picks : str
        Path to generated PhaseNet picks csv
    min_prob : float
        Minimum probability to consider a pick.
    
    Returns
    -------
    list
        List of Pick objects
    '''
    """
    # script directory for phaseNet.inp searching
    main_dir = os.path.dirname(os.path.abspath(__file__))
    par_fn = 'phaseNet.inp'
    rel_par_path = os.path.join('../', par_fn)
    main_par_path = os.path.join(main_dir, par_fn)

    # verifying if phaseNet.inp exist in any of the following 3 paths. 
    check_inp_dirs = [par_fn, rel_par_path, main_par_path]
    for path in check_inp_dirs:
        if os.path.isfile(path):
            print(f'Reading params for: {path} \n')
            params = read_params(path)
            break
    
    mode = params['mode']
    """
    picks = []
    with open(phaseNet_picks, newline='') as csvfile: 
        reader = csv.reader(csvfile, delimiter=',') 
        for i, row in enumerate(reader): 
            if i != 0: 
                wf_name = row[0]
                picks_p = row[1].strip('[]').strip().split() 
                prob_p = row[2].strip('[]').strip().split() 
                picks_s = row[3].strip('[]').strip().split() 
                prob_s = row[4].strip('[]').strip().split() 

                P_picks = pick_constructor(picks_p, prob_p, wf_name, 'P', min_prob_p, dt)
                S_picks = pick_constructor(picks_s, prob_s, wf_name, 'S', min_prob_s, dt)
            
                picks += P_picks + S_picks
                
                #print(f'{len(P_picks)} P picks')
                #print(f'{len(S_picks)} S picks')

    return picks


def picks2xml(pick_list):
    """Transform pick list into an Seiscomp3 XML file

    Parameters
    ----------
    pick_list : list
        List with Pick objects
    
    Returns
    -------
    str
        Returns the string of the XML file
    """
    xml_top = '''<?xml version="1.0" encoding="UTF-8"?>
<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">
  <EventParameters>'''

    xml_bottom = '''
  </EventParameters>
</seiscomp>'''

    xml_S_bottom = '''<comment>
        <text>{}</text>
        <id>RefPickID</id>
      </comment>
    </pick>'''

    xml_file = xml_top

    pick_dic = {}
    for pick in pick_list:
        if pick.phaseHint == 'S':
            try:
                P_pick = pick_dic[pick.station+'_'+'P']
            except KeyError:
                print('No se encontro fase P de referencia para:')
                print(f'\t{pick.publicID}')
                continue
            xml_file += pick.toxml()+xml_S_bottom.format(P_pick.publicID)
        elif pick.phaseHint == 'P':
            # se crea un diccionario para almacenar las fases P a las que
            # luego se relacionaran las fases S. (Seiscomp lo exige)
            pick_dic[pick.station+'_'+pick.phaseHint] = pick 
            xml_file += pick.toxml()
    
    xml_file += xml_bottom

    return xml_file


def eqt_pick_constructor(time, prob, net, station, loc, ch, ph, author='EQTransformer'):
    time = UTCDateTime(time)
    id_ = id_maker(time, net, station, loc, ch, ph, author)
    creation_t = UTCDateTime()

    evaluation = 'automatic'
    if prob >= 1.95:
        evaluation = 'manual'

    pick = Pick(id_, time, net, station, loc, ch, prob,
                ph, creation_t, evaluation, author)

    return pick


def read_params(par_file='ai_picker.inp'):
    lines = open(par_file, encoding='utf-8').readlines()
    par_dic = {}
    for line in lines:
        if line[0] == '#' or line.strip('\n').strip() == '':
            continue
        else:
            #print(line)
            l = line.strip('\n').strip()
            key, value = l.split('=')
            par_dic[key.strip()] = value.strip()
    return par_dic

def pick_constructor(picks, prob, wf_name, ph_type, min_prob, dt):
    """Construct Pick objects

    Parameters
    ----------
    picks : list
        List of phase pick sample point in a specific waveform
    prob : list
        List of probabilities associated with the picks
    wf_name : str
        Waveform name
    ph_type : str
        Pick phase type. Can be P or S
    min_prob : str
        Minimum probability to consider a pick
    
    Returns
    -------
    list
        List of picks objects
    """
    segment = 0.0
    picks_list = []
    if picks != ['']:
        for pick, prob in zip(picks, prob):
            prob = float(prob)
            if prob >= min_prob:

                #----------
                # se obtienen los parámetros para la creación del objeto pick
                #----------
                # algunos datos se obtienen del nombre de la forma de onda
                net, station, loc, ch, df, *to_segment = wf_name.split('_')

                to = to_segment[0].split('.')[0]
                if len(to_segment)==2:
                    segment = int(to_segment[1])
                # se transforma las cuentas asociadas al pick en tiempo
                pick_time, creation_time = sample2time(pick, to, df, segment, dt)
                # se crea el Id usando el tiempo del pick
                ID = id_maker(pick_time, net, station, loc, ch, ph_type, 'PhaseNet')    

                # Se evalua si la probabilidad es lo suficientemente buena 
                # como para considerarlo manual
                evaluation = 'automatic'
                if prob >= 0.98:
                    evaluation = 'manual'
                # Se crea el objeto Pick
                p = Pick(ID, pick_time, net, station, loc, ch, prob,
                        ph_type, creation_time, evaluation)
                
                # Se agrega cada pick a la lista de picks
                picks_list.append(p)
    return picks_list


def sample2time(sample, to, df, segment, dt):
    """Transforma las cuentas de un pick de PhaseNet en fecha
    
    Parameters
    ----------
    sample : str
        Sample point of PhaseNet pick
    to : str
        Initial time of the waveform that contains the pick in format
        YYYYmmddHHmmssff. Whit ff as deciseconds
    df : str
        Sampling rate
    
    Returns
    -------
    pick_time : Obspy UTCDateTime object
        Time for phase pick
    creation_time : UTCDateTime
        Time for creation time
    """
    df = float(df)

    init_time = UTCDateTime(to[:-2]+'.'+to[-2:])
    # if segment is different to 0 which implies that we are using
    # pred_mseed mode
    if segment is not 0:

        # if segment is bigger than the lenght of the waveform; then,
        # the segment is an overlapping one, and then we need to
        # include the 1500 samples (15 s) of shiftfing
        if segment >= dt*df:
            segment = segment - dt*df
            init_time -= datetime.timedelta(seconds=1500/df)

    pick_time = init_time + (segment + float(sample))/df
    creation_time = UTCDateTime()
    return pick_time, creation_time


def id_maker(pick_time, net, station, loc, ch, phaseHint, ai_type):
    """Creates the seiscomp Pick PublicID
    
    Parameters
    ----------
    pick_time : Obspy UTCDateTime object
        Time for phase pick
    
    Returns
    ------
    str
       Seiscomp pick PublicID
    """
    dateID = pick_time.strftime('%Y%m%d.%H%M%S.%f')[:-4]
    if phaseHint == 'P':
        publicID = dateID+f'-{ai_type}-{net}.{station}.{loc}.{ch}'
    elif phaseHint == 'S':
        publicID = dateID+f'-{ai_type}-{net}.{station}.{loc}.{ch}'
    return publicID


class Pick:
    '''Class to represent a phase pick

    Atributes
    ---------
    xml_P_block : str
        Template of a pick XML block

    Methods
    -------
    toxml()
        Create seiscomp3 xml block
    '''
    xml_P_block = '''
    <pick publicID="{publicID}">
      <time>
        <value>{pick_time}</value>
      </time>
      <waveformID networkCode="{net}" stationCode="{station}" locationCode="{loc}" channelCode="{ch}"/>
      <filterID>Probability_{prob}</filterID>
      <methodID>{author}</methodID>
      <phaseHint>{phaseHint}</phaseHint>
      <evaluationMode>{evaluation}</evaluationMode>
      <creationInfo>
        <agencyID>TEXNET</agencyID>
        <author>{author}</author>
        <creationTime>{creation_time}</creationTime>
      </creationInfo>
    </pick>'''

    xml_S_block = '''
    <pick publicID="{publicID}">
      <time>
        <value>{pick_time}</value>
      </time>
      <waveformID networkCode="{net}" stationCode="{station}" locationCode="{loc}" channelCode="{ch}"/>
      <filterID>Probability_{prob}</filterID>
      <methodID>{author}</methodID>
      <phaseHint>{phaseHint}</phaseHint>
      <evaluationMode>{evaluation}</evaluationMode>
      <creationInfo>
        <agencyID>TEXNET</agencyID>
        <author>{author}</author>
        <creationTime>{creation_time}</creationTime>
      </creationInfo>
      '''

    def __init__(self, publicID, pick_time,
                 net, station, loc, ch, prob,
                 phaseHint, creation_time,
                 evaluation, author='PhaseNet'):
        """
        Parameters
        ----------
        publicID : str
            Seiscomp3 pick pubicID
        pick_time : Obspy UTCDateTime object
            Time for phase pick.
        net : str
            Agency network.
        station : str
            Station name.
        loc : str
            Location code.
        ch : str
            Channel
        phaseHint : str
            Phase type, can be P or S.
        creation_time : Obspy UTCDateTime object
            Time for creation time.
        """
        self.publicID = publicID
        self.pick_time = pick_time
        self.net = net
        self.station = station
        self.loc = loc
        self.ch = ch
        self.prob = prob
        self.phaseHint = phaseHint
        self.creation_time = creation_time
        self.evaluation = evaluation
        self.author = author
    
    def toxml(self):
        """Create a seiscomp xml block
        """

        if self.phaseHint == 'P':
            return self.xml_P_block.format(
                publicID=self.publicID,
                pick_time=self.pick_time,
                net=self.net,
                station=self.station,
                loc=self.loc,
                ch=self.ch,
                prob=self.prob,
                phaseHint=self.phaseHint,
                creation_time=self.creation_time,
                evaluation=self.evaluation,
                author=self.author
                )
        elif self.phaseHint == 'S':
            return self.xml_S_block.format(
                publicID = self.publicID,
                pick_time = self.pick_time,
                net = self.net,
                station = self.station,
                loc = self.loc,
                ch = self.ch,
                prob = self.prob,
                phaseHint = self.phaseHint,
                creation_time = self.creation_time,
                evaluation = self.evaluation,
                author = self.author
                )

if __name__=='__main__':
    
    import sys

    if len(sys.argv) == 2:
        main_picks(sys.argv[1], ai='eqcct')
    elif len(sys.argv) == 3:
        main_picks(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        main_picks(sys.argv[1], sys.argv[2], ai='eqt')
    else:
        main_picks()

