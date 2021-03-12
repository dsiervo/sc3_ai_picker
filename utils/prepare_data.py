import MySQLdb
import datetime
import csv
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
import numpy as np
import os


class Picks:
    def __init__(self, event_ID='SGC2020aicxhi',
                stations='False', 
                ip_fdsn="http://10.100.100.232",
                port_fdsn="8091",
                host='10.100.100.232',
                wf_file='my_waveforms.csv',
                data_dir='dataset/waveform_pred/',
                magnitude=10.0,
                input_length=3000,
                **kwargs):
        
        self.event_ID = event_ID
        self.stations = stations
        self.ip_fdsn = ip_fdsn
        self.port_fdsn = port_fdsn
        self.data_dir = data_dir
        self.wf_file = wf_file
        self.host = host
        self.magnitude = magnitude
        self.input_length = float(input_length)
        
        self.__dict__.update(kwargs)
        
        # for write phase times in csv data list (for train)
        self.write_phase_times = False


    def get_picks(self):
        """[summary]
        """
        self.client = Client(self.ip_fdsn+":"+self.port_fdsn)
        self.db = MySQLdb.connect(host=self.host,    # your host
                            user="consulta",         # your username
                            passwd="consulta",  # your password
                            db="seiscomp3")        # name of the data base

        if self.stations in ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE'):
            self.query_event()
        else:
            self.write_phase_times = True
            self.query_stations()


    def query_event(self):
        quer = "Select POEv.publicID, Pick.waveformID_networkCode, \
        Pick.waveformID_stationCode,\
        Pick.waveformID_locationCode,\
        Pick.waveformID_channelCode, \
        Arrival.phase_code, Pick.time_value, Pick.time_value_ms\
        from Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid \
        left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID \
        left join Origin ON POOri._oid=Origin._oid \
        left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID \
        left join Magnitude ON Magnitude._oid = POMag._oid \
        left join Arrival on Arrival._parent_oid=Origin._oid \
        left join PublicObject as POOri1 on POOri1.publicID = Arrival.pickID \
        left join Pick on Pick._oid= POOri1._oid \
        where \
        Pick.phaseHint_used = 1 \
        AND Pick.evaluationMode = 'manual' \
        AND Arrival.phase_code = 'P' \
        AND POEv.PublicID = '{0}'".format(self.event_ID)
        
        self.download_picks(quer)


    def query_stations(self):
        quer = "Select POEv.publicID, pick_p.waveformID_networkCode, \
        pick_p.waveformID_stationCode, \
        pick_p.waveformID_locationCode, pick_p.waveformID_channelCode, \
        A_p.phase_code, pick_p.time_value, pick_p.time_value_ms, \
        A_s.phase_code, pick_s.time_value, pick_s.time_value_ms \
        from Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid \
        left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID \
        left join Origin ON POOri._oid=Origin._oid \
        left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID \
        left join Magnitude ON Magnitude._oid = POMag._oid \
        left join Arrival A_p on A_p._parent_oid=Origin._oid  and A_p.phase_code = 'P' \
        inner join Arrival A_s on A_s._parent_oid=A_p._parent_oid and A_s.phase_code = 'S' \
        left join PublicObject as POOri1 on POOri1.publicID = A_p.pickID \
        left join PublicObject as POOri2 on POOri2.publicID = A_s.pickID \
        left join Pick pick_p on pick_p._oid = POOri1._oid \
        left join Pick pick_s on pick_s._oid = POOri2._oid \
        where \
        pick_p.phaseHint_used = 1 \
        AND pick_p.evaluationMode = 'manual' \
        AND pick_s.evaluationMode = 'manual' \
        AND pick_p.waveformID_stationCode = pick_s.waveformID_stationCode \
        AND Origin.time_value between '{0}' and '{1}' \
		AND Origin.latitude_value between {2} and {3} \
        AND Origin.longitude_value between {4} AND {5} \
        AND pick_p.waveformID_stationCode in ({6}) \
        AND Magnitude.magnitude_value <= {8} LIMIT {7} \
            ".format(self.init_time, self.end_time, self.lat_min, self.lat_max,
                     self.lon_min, self.lon_max, self.stations, self.limit, self.magnitude)
        
        self.download_picks(quer)


    def download_picks(self, quer):

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        cur = self.db.cursor()
        
        dt1 = 20
        
        cur.execute(quer)
        c = [list(x) for x in cur.fetchall()]
        
        print('\n\t\t\tTotal waveforms to download:', len(c), '\n')
        
        ph_file = []

        for i in range(len(c)):
            row = c[i]
            print(i+1, row)
            # phase time
            
            net, station, loc, ch = row[1:5]
            df = 100

            if ch[:2] == 'BH': df = 50
            elif ch[:2] == 'HN': df = 200

            # en 100 hz: Una ventana que empieza de 5 a 15 segundos
            # antes de la P de tamaño 5000 (muestras)
            #sample_1 = 1000 + np.random.uniform(-1, 1)*500
            # se divide en la frecuencia de muestreo para obtener segundos
            dt1 = 3001/df
            dt2 = (self.input_length-3001)/df 
            
            t_ = row[6]
            t_ms_ = row[7]

            t = UTCDateTime(
                    t_+datetime.timedelta(milliseconds=float(t_ms_)/1000)
                            ) 

            try:
                # Descarga las componentes disponibles en el instrumento que fue picada la P
                st = self.client.get_waveforms(net, station, loc, ch[:2]+'*', t-dt1, t+dt2)
            except:
                print("\n #######################################################")
                print(net, station, loc, ch[:2]+'*', t-dt1, t+dt2)
                print('No se encontraron datos!\n')
                continue

            st.trim(t-dt1, t+dt2-0.01)
            st.merge(fill_value="interpolate")

            if self.filter in ('Yes', 'yes', 'Y', 'y', 'True', 'true', 'TRUE'):
                if self.filter_only_this in ('no', 'No', 'NO', 'N', 'n' 'False', 'false'):
                    st.detrend('linear')
                    st.taper(max_percentage=0.05, type="hann")
                    #st.filter('bandpass', freqmin=5, freqmax=10)
                    st.filter('highpass', freq=1.3)
                else:
                    # lista de estaciones a filtrar
                    sta_to_fil = self.filter_only_this.replace(' ', '').split(',')
                    if station in sta_to_fil:
                        #print(f'\n\n\t\t filtrando {station}!!')
                        st.detrend('linear')
                        st.taper(max_percentage=0.05, type="hann")
                        #st.filter('bandpass', freqmin=5, freqmax=10)
                        st.filter('highpass', freq=0.8)
                    else: pass

            tr = st[0]
            
            #st.write('/home/sgc/mesetas/PhaseNet/dataset/mseed/'+f"{net}_{station}_{t.strftime('%Y%m%d%H%M%S%f')[:-4]}.mseed", 'mseed')
            
            #t_i = tr.stats.starttime
            #df = tr.stats.sampling_rate
            #n_p = self.phase_point(t, t_i, df)
            
            # convirtiendo en stream de obspy en un array de numpy
            # data es un array de dimensión canales*3000 
            for i, tr in enumerate(st):
                if i == 0:
                    data = tr.data
                else:
                    try:
                        data = np.c_[data, tr.data]
                    except ValueError:
                        continue
            
            # solo tiene una traza
            try: data.shape[1]
            except IndexError:
                print(station)
                N = data.size
                z = np.zeros((N,2))
                print(data.shape, z.shape)
                re_data = data.reshape((N,1))
                data = np.concatenate((re_data, z), axis=1)

            t_i = tr.stats.starttime
            npz_name = f"{net}_{station}_{t_i.strftime('%Y%m%d%H%M%S%f')[:-4]}_{int(tr.stats.sampling_rate)}_{loc}_{ch[:2]+'Z'}.npz"
            data_float = data.astype('float64')
            
            if self.write_phase_times:

                ch_list = []
                for tr in st:
                    ch_list.append(tr.stats.channel)
                    channels = '_'.join(ch_list)
                
                #print(channels) 
                
                df = tr.stats.sampling_rate
                t_s = UTCDateTime(
                    row[9]+datetime.timedelta(milliseconds=float(row[10])/1000)
                            )
                
                n_p = self.phase_point(t, t_i, df)
                n_s = self.phase_point(t_s, t_i, df)

                if self.mode in ('train', 'tune', 'test'):
                    if data_float.shape != (9001, 3):
                        continue

                np.savez_compressed(os.path.join(self.data_dir,npz_name),
                                    data=data_float,
                                    itp=n_p,
                                    its=n_s,
                                    channels=channels)

                ph_file.append([npz_name, n_p, n_s, channels])
            else:
                np.savez_compressed(os.path.join(self.data_dir, npz_name), data=data_float)

                ph_file.append([npz_name])
        
        # Guardando los nombres de los npz en un csv
        with open(self.wf_file, "w") as f:
            writer = csv.writer(f)
            if self.write_phase_times:
                writer.writerow(["fname", "itp", 'its', 'channels'])
            else:
                writer.writerow(["fname"])
            writer.writerows(ph_file)


    def phase_point(self, t, t_i, df):
        """Calcula los extremos de un intervalo de puntos del tiempo ingresado""" 
        t_r = t-t_i

        n_p = int(t_r*df)

        
        return n_p


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

        self.query_picks= inp_file['query_picks']
        self.query_host= inp_file['query_host']
        self.query_user= inp_file['query_user']
        self.query_passwd= inp_file['query_passwd']
        self.query_db= inp_file['query_db']
        self.level = 'location'


        if self.CWav_download in ('yes', 'Yes', 'Y', 'True', 'true', 'TRUE'):   self.download_CWavs()

    @property
    def picks(self):

        stations= tuple(map(lambda x: str(x[1]),self.CWav_stations))
        _codex = phpmyAdmin(self.query_picks)
        codex= _codex.picks_query( initial_date=self.CWav_init_time, final_date=self.CWav_end_time, stations=stations)
        db= MySQLdb.connect(host=self.query_host, user=self.query_user,\
                             passwd=self.query_passwd, db=self.query_db)
        df = pd.read_sql_query(codex,db)
        df['time_pick_p'] = df.apply(lambda x: self._timepick(x,'p'), axis=1)
        df['time_pick_s'] = df.apply(lambda x: self._timepick(x,'s'), axis=1)
        df = df.drop(columns=['time_ms_pick_p','time_ms_pick_s'])
        return df
        # return codex

    def _timepick(self,df,pick):
        pick = UTCDateTime(df[f'time_pick_{pick}']) + timedelta(milliseconds=float(df[f'time_ms_pick_{pick}']/1000))
        return pick

    def _grep_CWav_stations(self, stations, level):
        columns = ['network','station','location','channel']
        index = columns.index(level)

        df = pd.DataFrame(stations,columns=columns)
        df_level = df[~df.duplicated(columns[:index+1])]
        df_level[f'{columns[index+1] }'] = df_level[f'{columns[index+1] }'].map(lambda x: x[:2]+'*')

        list_level = df_level.values.tolist()
        
        return list_level 

    @property
    def CWav_stations(self):
        if self.CWav_stations_dir not in ['False','false','None','none','','FALSE','NONE']:
            stations=  [line.strip('\n').split(',') for line in open(self.CWav_stations_dir).readlines()]
            #################
            # ARREGLAR ESTO, para que seleccione si 3 canales o uno solo
            #################
        else: 
            stations = self.client.get_stations(network="CM", channel = "*",starttime=self.CWav_init_time,    #para descargar canales por separado
                                             endtime=self.CWav_end_time ,level="channel").get_contents()
            stations = stations['channels']
            stations = list(map(lambda x: x.split('.'), stations)) 
            
            if self.level == 'location':
                stations = self._grep_CWav_stations(stations,level='location')
            # stations = self.client.get_stations(network="CM", station = "*",starttime=self.CWav_init_time,
                                            #  endtime=self.CWav_end_time ,level="station").get_contents()
            # stations = stations['stations']
            # stations = list(map(lambda x: x.split(' '), stations)) 
            # stations = list(map(lambda x: x[0].split('.'), stations)) 
            # # stations = list(map(lambda x: x.append(), stations)) 
            
            # print(stations)
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

        sts=[]
        for item in streams:
            if item != 'None':
                sts.append(item)

        return sts

    """def _write_CWavs(self,st):
        date_name= (self.CWav_init_time+'_'+self.CWav_end_time).replace(':','').replace(' ','').replace('-','')
        stats= st[0].stats
        st_name_mseed= "_".join((stats.network, stats.station, stats.location,str(int(stats.sampling_rate)), stats.channel,date_name))+ f'.{self.CWav_
        mseed_path= os.path.join(self.CWav_dir,st_name_mseed)

        st.write(mseed_path, format="MSEED")
        with open(self.CWav_csv_path, "a") as f:
            wr = csv.writer(f, dialect='excel')
            pre_channel_name = stats.channel[:2]
            wr.writerow([st_name_mseed,f'{pre_channel_name}E',f'{pre_channel_name}N',f'{pre_channel_name}Z'])
            f.close()

        # return  mseed_path,    st_name_mseed  

    def _get_CWavs(self, parameters):

        if self.CWav_download in ('yes', 'Yes', 'Y', 'True', 'true', 'TRUE'): 
            try:
                st = self.client.get_waveforms( network=parameters[0], station=parameters[1], 
                    location= parameters[2], channel=parameters[3],
                    starttime=UTCDateTime(self.CWav_init_time),
                    endtime=UTCDateTime(self.CWav_end_time)  )
                print(st)
            except:
                st= 'None'
                print('No stream:', parameters)
        else:
            st=read(parameters)
        return st"""

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
            with concurrent.futures.ProcessPoolExecutor() as executor:
                executor.map(self._write_CWavs, self.CWav_streams) 

    def picks_to_csv(self):
        date_name= (self.CWav_init_time+'_'+self.CWav_end_time).replace(':','').replace(' ','').replace('-','')
        csv_name = ("Picks_"+f'{date_name}'+".csv").replace(" ","")
        csv_path = os.path.join(self.CWav_dir,csv_name)
        with open(csv_path,'w') as csv:   csv.write(f'#{self.CWav_init_time},{self.CWav_end_time}\n')
        self.picks.to_csv(csv_path, mode='a', index=False)





if __name__ == "__main__":
    # SGC2020aicxhi M=0.8
    print('\n\t\tCreando Objeto Picks')
    my_picks = Picks('SGC2020czvlgy',
                     ip_fdsn='http://10.100.100.232',
                     port_fdsn='8091',
                     host='10.100.100.232',
                     wf_file='dataset/waveforms_test_train.csv',
                     data_dir='dataset/wf_mesetas_0.8/',
                     #stations="'CLEJA', 'URMC', 'CLBC', 'PRA', 'VIL', 'TAPM', 'PIRM', 'MACC'",#
                     init_time ="2020-01-01 00:00:00",#
                     end_time='2020-03-04 23:59:59',#
                     lat_min=3.3,#
                     lat_max=3.57,#
                     lon_min=-74.366,#
                     lon_max=-73.907,
                     limit=100,
                     mode='train',
                     filter=False,
                     filter_only_this='no')#
    print('\n\t\tObteniendo formas de onda y tiempo de arribo')
    my_picks.get_picks()
