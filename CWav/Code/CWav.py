# By: Emmanuel Castillo- ecastillo@sgc.gov.co

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


from obspy.clients.fdsn import Client
from obspy import read
from obspy import UTCDateTime
import csv
import itertools
import concurrent.futures
import os
import numpy as np


class CWav(object):

    def __init__(self,inp_file):
        inp_file= read_params(inp_file)

        self.CWav_stations_dir= inp_file['CWav_stations_dir']
        self.CWav_dir= inp_file['CWav_dir']
        self.CWav_format= inp_file['CWav_format']
        self.CWav_download= inp_file['CWav_download']
        self.CWav_download_mode= inp_file['CWav_download_mode']
        self.CWav_one_name= inp_file['CWav_one_name']
        self.ip_fdsn= inp_file['ip_fdsn']
        self.port_fdsn= inp_file['port_fdsn']
        self.host= inp_file['host']
        self.client= Client(inp_file['ip_fdsn']+":"+inp_file['port_fdsn'])
        self.CWav_init_time= inp_file['CWav_init_time']
        self.CWav_end_time= inp_file['CWav_end_time']
        self.CWav_csv_path= inp_file['CWav_csv_path']

        if self.CWav_download in ('yes', 'Yes', 'Y', 'True', 'true', 'TRUE'):   self.download_CWavs()

    @property
    def CWav_stations(self):
        stations=  [line.strip('\n').split(',') for line in open(self.CWav_stations_dir).readlines()]
        return stations

    @property
    def CWav_names(self):
        CWav_names=[]
        for station in self.CWav_stations:
            station_name= "_".join(station)
            CWav_names.append(station_name)
        return CWav_names

    @property
    def CWav_names_dir(self):
        date_name= (self.CWav_init_time+'_'+self.CWav_end_time).replace(':','').replace(' ','').replace('-','')
        build_names= lambda x,y: os.path.join(self.CWav_dir,x.replace('*','-'))+\
        '_'+y.replace(':','')
        CWav_names_dir= list(map(build_names, self.CWav_names,itertools.repeat(date_name)))
        return CWav_names_dir

    @property
    def CWav_one_name_dir(self):
        CWav_one_name_dir= os.path.join(self.CWav_dir,self.CWav_one_name)+'.'+self.CWav_format
        return CWav_one_name_dir

    @property
    def CWav_streams(self):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            if self.CWav_download in ('yes', 'Yes', 'Y', 'True', 'true', 'TRUE'):
                streams= list( executor.map(self._get_CWavs, self.CWav_stations) )
            else:
                streams= list( executor.map(self._get_CWavs, self.CWav_names_dir) )
        return streams

    @CWav_stations.setter
    def CWav_stations(self,new_stations):
        self.CWav_stations= new_stations
    
    def download_CWavs(self):
        with open(self.CWav_csv_path, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["fname", "E", 'N', 'Z'])
            f.close()

        if self.CWav_download_mode == 'all_in_one':
            total_st = self.CWav_streams[0]
            for i in range(1,len(self.CWav_streams)):
                total_st += self.CWav_streams[i]
            to_write= [total_st,self.CWav_one_name_dir]
            self._write_CWavs(to_write)
        
        if self.CWav_download_mode == 'by_station':
            if len(self.CWav_streams)==len(self.CWav_names_dir):
                to_write= [ [self.CWav_streams[i], self.CWav_names_dir[i] ] for i in range (0,len(self.CWav_streams)) ]
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    executor.map(self._write_CWavs, self.CWav_streams) 
            else:
                "Algo anda mal en self._get_CWavs"

    def _write_CWavs(self,st):
        date_name= (self.CWav_init_time+'_'+self.CWav_end_time).replace(':','').replace(' ','').replace('-','')
        
        stats= st[0].stats
        st_name_mseed= "_".join((stats.network, stats.station, stats.location, stats.channel, date_name))+ f'.{self.CWav_format}'
        mseed_path= os.path.join(self.CWav_dir,st_name_mseed)

        st.write(mseed_path, format="MSEED")
        with open(self.CWav_csv_path, "a") as f:
            wr = csv.writer(f, dialect='excel')
            wr.writerow([st_name_mseed,'HHE','HHN','HHZ'])
            f.close()

        # return  mseed_path,    st_name_mseed  

    def _get_CWavs(self, parameters):

        if self.CWav_download in ('yes', 'Yes', 'Y', 'True', 'true', 'TRUE'): 
            st = self.client.get_waveforms( network=parameters[0], station=parameters[1], 
                location= parameters[2], channel=parameters[3],
                starttime=UTCDateTime(self.CWav_init_time),
                endtime=UTCDateTime(self.CWav_end_time)  )
        else:
            st=read(parameters)

        # if len(st) != 1: #Try to correct overlappings and gaps with the method:0 and fill_value:0 respectively
            # try:
                # st= st[0]
                # for i in range(1,len(st)):  
                    # st += st[i]
                # st.merge(method=0,fill_value=0)
            # except: pass
        # else:   pass

        return st

        
if __name__ == "__main__":
    inp_file= '/mnt/almacenamiento/Emmanuel_Castillo/git_EDCT/UNAL/Tesis/mseed_PhaseNet/Code/CWav.inp'
    a= CWav(inp_file)
    # a._write_csv(path='/mnt/almacenamiento/Emmanuel_Castillo/git_EDCT/UNAL/Tesis/mseed_PhaseNet/Code/fname.csv' )
    # b= a.CWav_streams[0]
    # print(a._write_CWavs(b))
    print(a.CWav_streams)
    print(a.CWav_names_dir)
    
    # print('streams:',a.CWav_streams )