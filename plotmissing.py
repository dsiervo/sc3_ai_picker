#!/home/sgc/anaconda3/envs/phaseNet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Aug 25 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
from obspy.clients.fdsn import Client
from obspy import UTCDateTime

def plot_missing(station, time):
    # Se define la dirección y el puerto 
    url_fdsn = "http://10.100.100.232:8091"
    # se crea el cliente 
    client = Client(url_fdsn)

    t = UTCDateTime(time)
    
    st = client.get_waveforms(network='CM',
                            station=station,
                            location='20,00',
                            channel='EH*,HH*',
                            starttime=t - 150,
                            endtime=t + 150)
    
    st.detrend('linear')
    st.taper(max_percentage=0.05, type="hann")
    
    st2 = st.copy()
    st3 = st.copy()
    st.filter('bandpass', freqmin=1, freqmax=10)
    st2.filter('bandpass', freqmin=5, freqmax=10)
    
    st.plot(method='full')
    st2.plot(method='full')
    st3.plot(method='full')

if __name__ == "__main__":
    import sys

    plot_missing(sys.argv[1], sys.argv[2])

