#!/home/sgc/anaconda3/envs/phaseNet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mar 25 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
import csv
from obspy import UTCDateTime
import datetime
import os

# waveforms lenght in seconds
WF_LENGHT = 2.0*3600

def main(input_file='picks.csv', output_file='picks_final.xml', min_prob=0.3):
    """Transform PhaseNet picks.csv file into Seiscomp XML file

    Parameters
    ----------
    input_file : str
        Path to PhaseNet picks.csv file
    output_file : str
        Path to new Sesicomp XML file
    min_prob: float
        Minimun probability to consider a phase pick
    """

    print('Input files is:', input_file)

    # Obtaining list of Picks objects from file
    pick_list = read_picks(input_file, min_prob)

    # Creating xml text
    xml_text = picks2xml(pick_list)

    # Writting in the output file
    with open(output_file, 'w') as f:
        f.write(xml_text)
    
    print(f'\nOutput file: {output_file}')


def read_picks(phaseNet_picks,
               min_prob=0.3):
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
                print(row)
                wf_name = row[0]
                picks_p = row[1].strip('[]').strip().split() 
                prob_p = row[2].strip('[]').strip().split() 
                picks_s = row[3].strip('[]').strip().split() 
                prob_s = row[4].strip('[]').strip().split() 

                P_picks = pick_constructor(picks_p, prob_p, wf_name, 'P', min_prob)
                S_picks = pick_constructor(picks_s, prob_s, wf_name, 'S', min_prob)
            
                picks += P_picks + S_picks
                
                print(f'{len(P_picks)} P picks')
                print(f'{len(S_picks)} S picks')

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


def pick_constructor(picks, prob, wf_name, ph_type, min_prob):
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
            if float(prob) >= min_prob:

                #----------
                # se obtienen los parámetros para la creación del objeto pick
                #----------
                # algunos datos se obtienen del nombre de la forma de onda
                net, station, to, df, loc, *ch_segment = wf_name.split('_')
                ch = ch_segment[0].split('.')[0]
                if len(ch_segment)==2:
                    segment = int(ch_segment[1])
                # se transforma las cuentas asociadas al pick en tiempo
                pick_time, creation_time = sample2time(pick, to, df, segment)
                # se crea el Id usando el tiempo del pick
                ID = id_maker(pick_time, net, station, loc, ch, ph_type)    

                # Se crea el objeto Pick
                p = Pick(ID, pick_time, net, station,
                        loc, ch, ph_type, creation_time)
                
                # Se agrega cada pick a la lista de picks
                picks_list.append(p)
    return picks_list


def sample2time(sample, to, df, segment):
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
    global WF_LENGHT
    df = float(df)

    init_time = UTCDateTime(to[:-2]+'.'+to[-2:])
    # if segment is different to 0 which implies that we are using
    # pred_mseed mode
    if segment is not 0:
        
        # if segment is bigger than the lenght of the waveform; then,
        # the segment is an overlapping one, and then we need to
        # include the 1500 samples (15 s) of shiftfing 
        if segment >= WF_LENGHT*df:
            segment = 0
            init_time -= datetime.timedelta(seconds=1500/df)

    pick_time = init_time + (segment + float(sample))/df
    creation_time = UTCDateTime()
    return pick_time, creation_time


def id_maker(pick_time, net, station, loc, ch, phaseHint):
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
        publicID = dateID+f'-AIC-{net}.{station}.{loc}.{ch}'
    elif phaseHint == 'S':
        publicID = dateID+f'-S-L2-{net}.{station}.{loc}.{ch}'
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
      <filterID>BW(4,1.00,10.00)</filterID>
      <methodID>AIC</methodID>
      <phaseHint>{phaseHint}</phaseHint>
      <evaluationMode>automatic</evaluationMode>
      <creationInfo>
        <agencyID>SGC2</agencyID>
        <author>PhaseNet</author>
        <creationTime>{creation_time}</creationTime>
      </creationInfo>
    </pick>'''

    xml_S_block = '''
    <pick publicID="{publicID}">
      <time>
        <value>{pick_time}</value>
      </time>
      <waveformID networkCode="{net}" stationCode="{station}" locationCode="{loc}" channelCode="{ch}"/>
      <filterID>BW(4,1.00,10.00)</filterID>
      <methodID>L2-AIC</methodID>
      <phaseHint>{phaseHint}</phaseHint>
      <evaluationMode>automatic</evaluationMode>
      <creationInfo>
        <agencyID>SGC2</agencyID>
        <author>PhaseNet</author>
        <creationTime>{creation_time}</creationTime>
      </creationInfo>
      '''

    def __init__(self, publicID, pick_time,
                net, station, loc, ch,
                phaseHint, creation_time):
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
        self.phaseHint = phaseHint
        self.creation_time = creation_time
    
    def toxml(self):
        """Create a seiscomp xml block
        """

        if self.phaseHint == 'P':
            return self.xml_P_block.format(
                publicID = self.publicID,
                pick_time = self.pick_time,
                net = self.net,
                station = self.station,
                loc = self.loc,
                ch = self.ch,
                phaseHint = self.phaseHint,
                creation_time = self.creation_time
                )
        elif self.phaseHint == 'S':
            return self.xml_S_block.format(
                publicID = self.publicID,
                pick_time = self.pick_time,
                net = self.net,
                station = self.station,
                loc = self.loc,
                ch = self.ch,
                phaseHint = self.phaseHint,
                creation_time = self.creation_time
                )

def read_params(par_file='phaseNet.inp'):
    lines = open(par_file).readlines()
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

if __name__=='__main__':
    import sys

    if len(sys.argv) > 1:
        main(sys.argv[1])
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else:
        main()
