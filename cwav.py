from obspy.clients.fdsn import Client
from obspy import read
from obspy import UTCDateTime
import csv
import itertools
import concurrent.futures
import os
import numpy as np
import MySQLdb
import pandas as pd
from datetime import timedelta
import matplotlib.pyplot as plt

class Cwav(object):
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
                ['PhaseNet_dir']: str
                    Path of the PhaseNet algorithm.
                ['mode']: str
                    mode parameter od phaseNet
                ['data_dir']: str
                    Path to download or where was downloaded the mseed files. 
                    Also, it is the data_dir paramater of PhaseNet.
                ['data_list']: str
                    Path to write or where was write the csv file that contain 
                    the downloaded mseed file names. 
                    Also, it is the data_list paramater of PhaseNet.
                ['model_dir']: str
                    Path of the model_dir parameter of PhaseNet.
                ['output_dir']: str
                    Path of the output
                ['batch_size']: str or int
                    PhaseNet batch size parameter.
                ['input_length]: str or int
                    PhaseNet input length parameter.
                ['plot_figure']:   str or Bolean (default:False)
                    ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True)-plot figures
                    else: -Don't plot the figures
                ['save_result']:    str or Bolean (default:False)
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
        print(parameters)
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
        
        mseed_path = os.path.join(self.pnet_dict['data_dir'], mseed_name)    
        csv_path =  self.pnet_dict['data_list']    

        st.write(mseed_path, format="MSEED")
        with open(csv_path, "a") as f:
            wr = csv.writer(f, dialect='excel')
            pre_channel_name = stats['channel'][:2]
            wr.writerow([mseed_name,f'{pre_channel_name}E',f'{pre_channel_name}N',f'{pre_channel_name}Z'])
            f.close()

        return mseed_name

    def download(self):
        if not os.path.exists(self.pnet_dict['data_dir']):
            os.makedirs(self.pnet_dict['data_dir'])

        with open(self.pnet_dict['data_list'] , "w") as f:
            writer = csv.writer(f)
            writer.writerow(["fname", "E", 'N', 'Z'])
            f.close()

        streams = self.streams
        if streams != None:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                executor.map(self._write_mseed_wavs,streams ) 
        else:
            pass
    
    def run_pnet(self):
        run_execute= os.path.join(self.pnet_dict['PhaseNet_dir'],'run.py')
        command = f"python {run_execute} --mode={self.pnet_dict['mode']} \
            --model_dir={self.pnet_dict['model_dir']} --data_dir={self.pnet_dict['data_dir']} \
            --data_list={self.pnet_dict['data_list']} --output_dir={self.pnet_dict['output_dir']}\
            --batch_size={self.pnet_dict['batch_size']} --input_mseed"
        if self.pnet_dict['plot_figure'] in ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True):
            command += ' ' + '--plot_figure'
        if self.pnet_dict['save_result'] in ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE', True):
            command += ' ' + '--save_result'
        print('\n', command, '\n')
        os.system(command)


if __name__ == "__main__":
    download_data = 'all'
    # download_data = ['CM.URMC.00.*','CM.URMC.00.*','CM.BAR2.00.*']
    pnet_dict = {'PhaseNet_dir': '/mnt/almacenamiento/Emmanuel_Castillo/PhaseNet',
                'mode': 'pred',
                'data_dir':'/mnt/almacenamiento/Emmanuel_Castillo/git_EDCT/SGC/sgc_phasenet/prove/wav',
                'data_list':'/mnt/almacenamiento/Emmanuel_Castillo/git_EDCT/SGC/sgc_phasenet/prove/wav/fname.csv',
                'model_dir': '/mnt/almacenamiento/Emmanuel_Castillo/PhaseNet/model/190703-214543',
                'output_dir': '/mnt/almacenamiento/Emmanuel_Castillo/git_EDCT/SGC/sgc_phasenet/prove/output',
                'batch_size': 10,
                'plot_figure': False,
                'save_result': False}

    client_dict = {'ip': 'http://10.100.100.232', 'port':'8091',
                   'starttime': UTCDateTime('2020-01-01 00:00:00'),
                   'endtime': UTCDateTime('2020-01-01 01:00:00') }

    # filter_data = ['CM.URMC','CM.BAR2']
    filter_data = 'ALL'
    mysqldb_dict = None

    cwav = Cwav(download_data, pnet_dict, client_dict, mysqldb_dict, filter_data=filter_data)

    cwav.download()
    cwav.run_pnet()
        