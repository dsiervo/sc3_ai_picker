import MySQLdb
import datetime
import csv
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
import numpy as np
import os


class Picks:
    def __init__(self, event_ID='SGC2020aicxhi', stations='False', 
                ip_fdsn="http://10.100.100.232",
                port_fdsn="8091",
                host='10.100.100.232',
                wf_file='my_waveforms.csv',
                data_dir='dataset/waveform_pred/',
                **kwargs
                ):
        
        self.event_ID = event_ID
        self.stations = stations
        self.ip_fdsn = ip_fdsn
        self.port_fdsn = port_fdsn
        self.data_dir = data_dir
        self.wf_file = wf_file
        self.host = host
        
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
        AND pick_p.waveformID_stationCode in ({6}) LIMIT {7}\
            ".format(self.init_time, self.end_time, self.lat_min, self.lat_max,
                     self.lon_min, self.lon_max, self.stations, self.limit)
        
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
            sample_1 = 1000 + np.random.uniform(-1, 1)*500
            # se divide en la frecuencia de muestreo para obtener segundos
            dt1 = sample_1/df
            dt2 = (5000-sample_1)/df 
            
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
            #st.filter('highpass', freq=0.1)

            tr = st[0]
            
            #st.write('/home/sgc/mesetas_article/PhaseNet/dataset/mseed/'+f"{net}_{station}_{t.strftime('%Y%m%d%H%M%S%f')[:-4]}.mseed", 'mseed')
            
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

            npz_name = f"{net}_{station}_{t.strftime('%Y%m%d%H%M%S%f')[:-4]}.npz"
            data_float = data.astype('float64')
            
            #print(station)
            if self.write_phase_times:

                ch_list = []
                for tr in st:
                    ch_list.append(tr.stats.channel)
                    channels = '_'.join(ch_list)
                
                #print(channels) 
                
                t_i = tr.stats.starttime
                df = tr.stats.sampling_rate
                t_s = UTCDateTime(
                    row[9]+datetime.timedelta(milliseconds=float(row[10])/1000)
                            )
                
                n_p = self.phase_point(t, t_i, df)
                n_s = self.phase_point(t_s, t_i, df)

                np.savez_compressed(self.data_dir+npz_name,
                                    data=data_float,
                                    itp=n_p,
                                    its=n_s,
                                    channels=channels)
            
                ph_file.append([npz_name, n_p, n_p, channels])
            else:
                np.savez_compressed(self.data_dir+npz_name, data=data_float)

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
                     limit=100)#
    print('\n\t\tObteniendo formas de onda y tiempo de arribo')
    my_picks.get_picks()