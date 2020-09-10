import os
import sys

try:
    env = os.environ['CONDA_DEFAULT_ENV']
except KeyError:
    env = 'none'

if (env == 'pnet' 
  or sys.executable == '/home/dsiervo/anaconda3/envs/pnet/bin/python'):

    from obspy.clients.fdsn import Client
    from obspy import read
    from obspy import UTCDateTime
    import csv
    import itertools
    import concurrent.futures
    from functools import reduce
    import numpy as np
    import pandas as pd
    from datetime import timedelta
    import matplotlib.pyplot as plt
    from utils.playback import playback
    from utils.picks2xml import main_picks

elif os.environ['CONDA_DEFAULT_ENV'] == 'eqt':
    from EQTransformer.utils.downloader import makeStationList
    from EQTransformer.utils.downloader import downloadMseeds
    from EQTransformer.utils.hdf5_maker import preprocessor
    from EQTransformer.core.predictor import predictor
    from utils.playback import playback
    from utils.picks2xml import main_picks

class Cwav_PhaseNet(object):
    """

    Atributes
    ----------
    db_sc : str
        Full path to seiscomp3 main database
    """
    db_sc = 'mysql://sysop:sysop@10.100.100.232/seiscomp3'
    
    def __init__(self, download_data, pnet_dict, client_dict,
                 mysqldb_dict=None, filter_data='no', download_max_workers=8,**kwargs):

        """Download mseed files and run them in PhaseNet algorithm
        Parameters
        ----------
        download_data: str or list
            ('all', 'All', 'ALL') - download all stations, 
            ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE') -Don't download mseed files
            ['CM.URMC','CM.CLEJA']-list of the stations to download
        pnet_dict: dict
            Dictionary of the PhaseNet parameters
                ['pnet_repository_dir']: str
                    Path of the PhaseNet algorithm.
                ['pnet_mode']: str
                    mode parameter od phaseNet
                ['pnet_data_dir']: str
                    Path to download or where was downloaded the mseed files. 
                    Also, it is the data_dir paramater of PhaseNet.
                ['pnet_data_list']: str
                    Path to write or where was write the csv file that contain 
                    the downloaded mseed file names. 
                    Also, it is the data_list paramater of PhaseNet.
                ['pnet_model_dir']: str
                    Path of the model_dir parameter of PhaseNet.
                ['pnet_output_dir']: str
                    Path of the output
                ['pnet_batch_size']: str 
                    PhaseNet batch size parameter.
                ['pnet_input_length]: str 
                    PhaseNet input length parameter.
                ['pnet_plot_figure']:   str or Bolean (default:False)
                    ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True)-plot figures
                    else: -Don't plot the figures
                ['pnet_save_result']:    str or Bolean (default:False)
                    ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True) -save results
                    else: -Don't save results

        client_dict : dict
            Dictionary of the FDSN Client parameters
                ['ip']: str
                    ip parameter of Client object from obspy
                ['port']: str
                    port parameter of Client object from obspy
                ['starttime']: UTCDateTime
                    Limit results to time series samples on or after the specified start time
                ['endtime']: UTCDateTime
                    Limit results to time series samples on or before the specified end time
        mysqldb_dict: dict
            Dictionary of the MySQLdb parameters
                ['host']: str
                ['user']: str
                ['passwd']: str
                ['db']: str
        filter_data: str or list
            ('all', 'All', 'ALL') - use filter in all stations, 
            ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE')-Don't use filter 
            ['CM.URMC','CM.CLEJA']-list of the stations to filter
        download_max_workers: int
            the max workers for download the mseed files in parallel mode.
        **kwargs: 
            kwargs for filter method of stream object from obspy
        """

        self.download_data = download_data
        self.pnet_dict = pnet_dict
        self.client_dict = client_dict
        self.mysqldb_dict = mysqldb_dict
        self.filter_data = filter_data
        self.download_max_workers = download_max_workers
        self.pick_csv_path = os.path.join(self.pnet_dict['pnet_output_dir'], 'picks.csv')
        self.pick_xml_path = os.path.join(self.pnet_dict['pnet_output_dir'], 'picks.xml')
        self.__dict__.update(kwargs)

    @property
    def client(self):
        """
        Returns
        -------
        client object
            Returns the client object according to the 'ip' and 'port' client parameters
        """
        return Client(self.client_dict['ip']+":"+self.client_dict['port'])

    @property
    def stations_to_download(self):
        """
        Returns
        -------
        list or None
            Returns the stations that gonna be downloaded according to the information in download parameter.
            -all: all stations to downlaod, -no: no download, 
            -['CM.URMC.00.*','CM.CLEJA.*.*'] download only these stations
        """
        if self.download_data not in ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE'):
            if self.download_data in ('all', 'All', 'ALL'):
                inv = self.client.get_stations(network="CM", channel = "*",
                                        starttime=self.client_dict['starttime'], 
                                        endtime=self.client_dict['endtime'], 
                                        level="channel").get_contents()
                stations = inv['channels']
                stations = list(map(lambda x: x.split('.'), stations)) 
                stations = self._cluster_duplicate_stations(stations,level='location')
            
            if isinstance(self.download_data, list):
                stations = list(map(lambda x: x.split('.'),self.download_data))
        else:
            stations = None
        
        return stations

    @property
    def streams(self):
        """
        Returns
        -------
        list
            list of streams object according to the stations_to_download attribute.
        """
        if self.download_data not in ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE'):
            with concurrent.futures.ProcessPoolExecutor() as executor:
                streams= list( executor.map(self._get_wavs, self.stations_to_download) )

            sts=[]
            for item in streams:
                if item != 'None':
                    sts.append(item)
        else:
            sts = None

        return sts
    
    def _cluster_duplicate_stations(self, stations, level):
        """
        Cluster duplicate stations in stations parameter according to the 'level' parameter

        Parameters
        ----------
        stations: list of lists
            A list of all stations lists. The bottom list contain four elements 
            corresponding to the [network,station,location,channel]
        level: str
            After this level, cluster the information. 
            level can be network or station or location or channel

        Returns
        ----------
        list
            list of station parameters clustered by level parameter

            example:
            1) [['CM','BAR2','00','HHZ'],['CM','BAR2','00','HHN']] according to level='location'
                returns [['CM','BAR2','00','HH*']]
            2)  [['CM','BAR2','00','HHZ'],['CM','BAR2','20','EHZ']] according to level='station'
                 returns [['CM','BAR2','*','*']]
        
        """
        columns = ['network','station','location','channel']
        index_level = columns.index(level)
        df = pd.DataFrame(stations,columns=columns)
        df_level = df[~df.duplicated(columns[:index_level+1])]

        for index in range(index_level+1,len(columns)):
            df_level[f'{columns[index ] }'] = df_level[f'{columns[index ] }'].apply(lambda x: '*')

        list_level = df_level.values.tolist()

        return list_level

    def _filter_wavs(self,st,**kwargs):
        st.detrend('linear')
        st.taper(max_percentage=0.05, type="hann")
        st.filter('highpass', freq=1.3, **kwargs)
        return st

    def _get_wavs(self, parameters):
        """
        Gets waveforms according to the station parameters

        Parameters
        ----------
        parameters: list
            list of stations parameters for get the respective waveforms

        Returns
        ----------
        stream object
            stream object loaded with the parameters variable and between the dates
            given by the client dictionary in init.
        """
        to_msg = '.'.join( (parameters[0],parameters[1],parameters[2]))
        filt_msg = f'\n\t\t\t\t FILTERED STREAM: {to_msg}'
        no_filt_msg = f'\n\t\t\t\t STREAM: {to_msg}'
        no_st = f'\n\t\t\t\t NO STREAM: {to_msg}'

        try:
            st = self.client.get_waveforms( network=parameters[0], station=parameters[1], 
                location= parameters[2], channel=parameters[3],
                starttime=self.client_dict['starttime'],
                endtime=self.client_dict['endtime']  )
        except:
            st= 'None'
            print(no_st)

        if st != 'None':    
            if self.filter_data in ('all', 'All', 'ALL'):
                st = self._filter_wavs(st)
                print(filt_msg,st)

            if isinstance(self.filter_data, list):
                stats = st[0].stats
                station = '.'.join( (stats['network'], stats['station']))
                if station in self.filter_data:
                    st = self._filter_wavs(st)
                    print(filt_msg,st)
                else: 
                    print(no_filt_msg,st)
                    pass

        return st

    def _write_mseed_wavs(self,st):
        stats = st[0].stats
        mseed_name = str(stats['network']) + '_' + str(stats['station']) + '_'\
                    + str(stats['location']) + '_' + str(stats['channel']) + '_'\
                    + str(int(stats['sampling_rate'])) + '_'\
                    + str(stats['starttime'].strftime('%Y%m%d%H%M%S%f')[:-4])\
                    + '.mseed'
        
        mseed_path = os.path.join(self.pnet_dict['pnet_data_dir'], mseed_name)    
        csv_path =  self.pnet_dict['pnet_data_list']    

        st.write(mseed_path, format="MSEED")
        with open(csv_path, "a") as f:
            wr = csv.writer(f, dialect='excel')
            pre_channel_name = stats['channel'][:2]
            wr.writerow([mseed_name,f'{pre_channel_name}E',f'{pre_channel_name}N',f'{pre_channel_name}Z'])
            f.close()

        return mseed_name

    def download(self):
        if self.download_data not in ('No','no'):
            if not os.path.exists(self.pnet_dict['pnet_data_dir']):
                os.makedirs(self.pnet_dict['pnet_data_dir'])

            with open(self.pnet_dict['pnet_data_list'] , "w") as f:
                writer = csv.writer(f)
                writer.writerow(["fname", "E", 'N', 'Z'])
                f.close()

            streams = self.streams
            if streams != None:
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    executor.map(self._write_mseed_wavs,streams ) 
            else:
                pass
        else:
            pass

    def run_pnet(self):
        run_execute= os.path.join(self.pnet_dict['pnet_repository_dir'],'run.py')
        command = f"{run_execute} --mode={self.pnet_dict['pnet_mode']} \
            --model_dir={self.pnet_dict['pnet_model_dir']} --data_dir={self.pnet_dict['pnet_data_dir']} \
            --data_list={self.pnet_dict['pnet_data_list']} --output_dir={self.pnet_dict['pnet_output_dir']}\
            --batch_size={self.pnet_dict['pnet_batch_size']} --input_mseed"
        if self.pnet_dict['pnet_plot_figure'] in ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True):
            command += ' ' + '--plot_figure'
        if self.pnet_dict['pnet_save_result'] in ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True):
            command += ' ' + '--save_result'
        print('\n', command, '\n')
        os.system(command)
    
    def picks2xml(self, dt):
        """Transform PhaseNet picks.csv file into Seiscomp XML file

        Parameters
        ----------
        dt : int
            Waveform length in seconds
        """
        
        main_picks(input_file=self.pick_csv_path, output_file=self.pick_xml_path, dt=dt)
    
    def playback(self):
        """Excecute seiscomp playback from picks.xml:
            * Group picks
            * Localize events from grouped picks to generate origins
            * Compute amplitudes
            * Compute magnitudes using amplitudes
            * Group origins into events
        """
        
        xml_picks_file = self.pick_xml_path

        # Verifing if the xml file with picks from phasenet exist
        assert os.path.isfile(xml_picks_file), \
            '\n\n\tNo existe el archivo %s en el directorio\n'%xml_picks_file

        print('creando objeto playback')
        my_playback = playback(
                sc_scanloc='scanloc',
                wf_dir=self.pnet_dict['pnet_data_dir'],
                db=self.db_sc,
                picks ='none',
                xml_picks_file=xml_picks_file,
                out_dir=self.pnet_dict['pnet_output_dir']
                )
        
        """# list with waveforms paths
        wfs=[]
        with open(self.pnet_dict['pnet_data_list']) as f:
            reader = csv.reader(f, delimiter=',')
            # skiping header
            next(reader)
            for row in reader:
                wfs.append(os.path.join(self.pnet_dict['pnet_data_dir'], row[0]))"""
        
        os.system('rm -fr xml_events/* events_final.xml')
        
        """# Creating a list with streams of the station waveforms
        streams = list(map(read_merge, wfs))
        # Joining all streams in one stream
        main_st = reduce(lambda x, y: x + y, streams)

        # writing stream in mseed file
        wf_path = os.path.join(self.pnet_dict['pnet_data_dir'], 'all.mseed')
        main_st.write(wf_path, format='MSEED')"""

        # excecuting playback commands
        my_playback.playback_commands()

class Cwav_EQTransformer(object):
    """

    Atributes
    ----------
    db_sc : str
        Full path to seiscomp3 main database
    """
    db_sc = 'mysql://sysop:sysop@10.100.100.232/seiscomp3'
    
    def __init__(self, download_data, eqt_dict, client_dict,
                 mysqldb_dict=None):
        """Download mseed files and run them in PhaseNet algorithm
        Parameters
        ----------
        download_data: str or list
            ('all', 'All', 'ALL') - download all stations, 
            ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE') -Don't download mseed files
            ['CM.URMC','CM.CLEJA']-list of the stations to download

        eqt_dict: dict
            Dictionary of the EQTransformer parameters

        client_dict : dict
            Dictionary of the FDSN Client parameters
                ['ip']: str
                    ip parameter of Client object from obspy
                ['port']: str
                    port parameter of Client object from obspy
                ['starttime']: UTCDateTime
                    Limit results to time series samples on or after the specified start time
                ['endtime']: UTCDateTime
                    Limit results to time series samples on or before the specified end time
        mysqldb_dict: dict
            Dictionary of the MySQLdb parameters
                ['host']: str
                ['user']: str
                ['passwd']: str
                ['db']: str
        """

        self.download_data = download_data
        self.eqt_dict = eqt_dict
        self.client_dict = client_dict
        self.mysqldb_dict = mysqldb_dict
        self.pick_xml_path = os.path.join(self.eqt_dict['eqt_output_dir'], 'picks.xml')

    @property
    def client(self):
        """
        Returns
        -------
        client object
            Returns the client object according to the 'ip' and 'port' client parameters
        """
        return Client(self.client_dict['ip']+":"+self.client_dict['port'])

    @property
    def stations_to_download(self):
        """
        Returns
        -------
        list or None
            Returns the stations that gonna be downloaded according to the information in download parameter.
            -all: all stations to downlaod, -no: no download, 
            -['CM.URMC.00.*','CM.CLEJA.*.*'] download only these stations
        """
        if self.download_data not in ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE'):
            if self.download_data in ('all', 'All', 'ALL'):
                stations = [['CM','*','*','*']]
            elif self.download_data in ('all_seismometer', 'All_Seismometer', 'ALL_SEISMOMETER'):
                stations = [['CM','*','00','*'],['CM','*','20','*']]
            elif self.download_data in ('all_acelerometer', 'All_Acelerometer', 'ALL_ACELEROMETER'):
                stations = [['CM','*','10','*']]
            elif isinstance(self.download_data, list):
                stations = list(map(lambda x: x.split('.'),self.download_data))
        else:
            stations = None
        
        return stations

    @property
    def prepare_eqt_stations(self):
        keys = list(zip(*self.stations_to_download))
        network,station,location,channel = (list(set(key)) for key in keys)
        network,station,location,channel = list(map( lambda x: ",".join(x),
                                                    [network,station,location,channel]))
        return network,station,location,channel

    def create_json(self):
        if self.eqt_dict['eqt_create_json'] in ('True', 'true','TRUE', True):
            # jsondir = os.path.dirname(self.eqt_dict['eqt_data_dir'])
            if not os.path.exists(self.eqt_dict['eqt_data_dir']):
                os.makedirs(self.eqt_dict['eqt_data_dir'])

            network,station,location,channel = self.prepare_eqt_stations
            json_list = makeStationList(
                    json_path=os.path.join(self.eqt_dict['eqt_data_dir'],'station_list.json'),
                    client_list=[f"{self.client_dict['ip']}:{self.client_dict['port']}"], 
                    min_lat=None, max_lat=None, 
                    min_lon=None, max_lon=None, 
                    network=network, station=station,
                    location=location, channel=channel,
                    start_time=self.client_dict['starttime'], end_time=self.client_dict['endtime'], 
                    channel_list=[], filter_network=[], filter_station=[])
        else:   
            pass

    def download_mseed(self):
        if self.download_data not in ('No','no','n','False',False):
            network,station,location,channel = self.prepare_eqt_stations
            downloadMseeds(client_list=[f"{self.client_dict['ip']}:{self.client_dict['port']}"],
                    network=network, station=station,
                    location=location, channel=channel,
                    stations_json= os.path.join(self.eqt_dict['eqt_data_dir'],'station_list.json'),
                    output_dir=os.path.join( self.eqt_dict['eqt_data_dir'],'mseed'), 
                    min_lat=None, max_lat=None, 
                    min_lon=None, max_lon=None,
                    start_time=self.client_dict['starttime'], end_time=self.client_dict['endtime'],
                    chunk_size= self.eqt_dict['eqt_chunk_size'] / (3600*24), #se divide sobre 3600*24 para convertir horas a dias
                    channel_list=[], 
                    n_processor=self.eqt_dict['eqt_n_processor'])
        else: 
            pass

    def preprocessor(self):
        if self.eqt_dict['eqt_create_hdf5'] in ('True', 'true','TRUE', True):
            
            preprocessor(
                preproc_dir=os.path.join( self.eqt_dict['eqt_data_dir'],'preproc_files'),
                mseed_dir=os.path.join( self.eqt_dict['eqt_data_dir'],'mseed'), 
                stations_json=os.path.join(self.eqt_dict['eqt_data_dir'],'station_list.json'), 
                overlap=self.eqt_dict['eqt_preproc_overlap'], 
                n_processor=self.eqt_dict['eqt_n_processor'])
        else:
            pass

    def predictor(self):

        predictor(input_dir= os.path.join( self.eqt_dict['eqt_data_dir'],'mseed_processed_hdfs'), 
                input_model=self.eqt_dict['eqt_model_dir'], 
                output_dir=self.eqt_dict['eqt_output_dir'], 
                detection_threshold=self.eqt_dict['eqt_detection_threshold'], 
                P_threshold=self.eqt_dict['eqt_P_threshold'],
                S_threshold=self.eqt_dict['eqt_S_threshold'], 
                number_of_plots=self.eqt_dict['eqt_number_of_plots'],
                plot_mode=self.eqt_dict['eqt_plot_mode'])

    def picks2xml(self):
        """Transform EQTransformer output file into Seiscomp XML file

        Parameters
        ----------
        dt : int
            Waveform length in seconds
        """
        
        main_picks(input_file=self.eqt_dict['eqt_output_dir'],
                   output_file=self.pick_xml_path, ai='eqt')

    def playback(self):
        """Excecute seiscomp playback from picks.xml:
            * Group picks
            * Localize events from grouped picks to generate origins
            * Compute amplitudes
            * Compute magnitudes using amplitudes
            * Group origins into events
        """
        
        xml_picks_file = self.pick_xml_path

        # Verifing if the xml file with picks from phasenet exist
        assert os.path.isfile(xml_picks_file), \
            '\n\n\tNo existe el archivo %s en el directorio\n'%xml_picks_file

        print('creando objeto playback')
        my_playback = playback(
                sc_scanloc='scanloc',
                wf_dir=self.eqt_dict['eqt_data_dir'],
                db=self.db_sc,
                picks ='none',
                xml_picks_file=xml_picks_file,
                out_dir=self.eqt_dict['eqt_output_dir'],
                ai_type='eqt'
                )
        
        os.system('rm -fr xml_events/* events_final.xml')
        
        # excecuting playback commands
        my_playback.playback_commands()


def read_merge(path):
    """Read and merge waveforms. Returns Obspy Stream.

    Parameters
    ----------
    path : str
        Waveform path
    
    Returns
    ------
    Obspy.Stream
        Merged obspy stream
    """
    st = read(path)
    return st.merge(fill_value='interpolate')
    
if __name__ == "__main__":
    # download_data = 'all'
    download_data = ['CM.URMC.00.*']
    pnet_dict = {'pnet_repository_dir': '/home/dsiervo/PhaseNet',
                'pnet_mode': 'pred',
                'pnet_data_dir':'/home/dsiervo/ecastillo/EQT_prove/wav/pnet',
                'pnet_data_list':'/home/dsiervo/ecastillo/EQT_prove/wav/pnet',
                'pnet_output_dir': '/home/dsiervo/ecastillo/EQT_prove/output/pnet',
                'pnet_model_dir': '/home/dsiervo/PhaseNet/model/190703-214543',
                'pnet_batch_size': 10,
                'pnet_plot_figure': False,
                'pnet_save_result': False}

    eqt_dict = {'eqt_data_dir':'/home/dsiervo/sgc_autopicker/wav',
                'eqt_output_dir':'/home/dsiervo/sgc_autopicker/output',
                'eqt_model_dir':'/home/dsiervo/EQTransformer/ModelsAndSampleData/EqT_model.h5',
                'eqt_chunk_size':4*3600,
                'eqt_n_processor':2,
                'eqt_preproc_overlap': 0.3,
                'eqt_detection_threshold': 0.3,
                'eqt_P_threshold':0.1,
                'eqt_S_threshold':0.1, 
                'eqt_number_of_plots':1, 
                'eqt_plot_mode':'time'}

    client_dict = {'ip': 'http://10.100.100.232', 'port':'8091',
                   'starttime': UTCDateTime('2020-01-01 00:00:00'),
                   'endtime': UTCDateTime('2020-01-01 04:00:00') }

    filter_data = ['CM.URMC']
    # filter_data = 'ALL'
    mysqldb_dict = None

    # cwav_phasenet = Cwav_phasenet(download_data, pnet_dict, client_dict, mysqldb_dict, filter_data=filter_data)
    # cwav_phasenet.download()
    # cwav_phasenet.run_pnet()

    cwav_eqt = Cwav_EQTransformer(download_data, eqt_dict, client_dict, mysqldb_dict=None)  
    # cwav_eqt.create_json()      
    # cwav_eqt.download_mseed()      
    # cwav_eqt.preprocessor()    
    # cwav_eqt.predictor()  