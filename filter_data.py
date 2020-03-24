#!/home/sgc/anaconda3/envs/tf_2.0/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mar 5 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""

import sys
from obspy import read
import glob

def filter_data(dir, freq):
    out_dir = '/home/sgc/mesetas/PhaseNet/dataset/mseed_filtered/'
    for wf in glob.glob('*.mseed'):
        st = read(wf)
        st.detrend('linear')
        st.taper(max_percentage=0.05, type="hann")
        st.write(out_dir+wf.split('/')[-1])


if __name__ == '__main__':
    dir = sys.argv[1]
    freq = sys.argv[2]

    filter_data(dir, freq)
