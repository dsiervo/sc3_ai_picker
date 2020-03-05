#!/home/sgc/anaconda3/envs/tf_2.0/bin/ python
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 11:25:33 2019

@author: Daniel Siervo, emetdan@gmail.com
"""
import os
from prepare_data import Picks

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


def init():
    print('\n\tObtaning parameters\n')
    params = read_params()
    
    print(params)

    if params['download'] in ('yes', 'Yes', 'Y', 'True', 'true', 'TRUE'):
        print('\n\tDownloading waveforms\n')
        my_picks = Picks(
                    event_ID=params['event_id'],
                    ip_fdsn=params['ip_fdsn'],
                    port_fdsn=params['port_fdsn'],
                    host=params['host'],
                    wf_file=params['data_list'],
                    data_dir=params['data_dir'],
                    stations=params['stations'],
                    init_time = params['init_time'],
                    end_time = params['end_time'],
                    lat_min=params['lat_min'],
                    lat_max=params['lat_max'],
                    lon_min=params['lon_min'],
                    lon_max=params['lon_max'],
                    limit=params['limit'])

        my_picks.get_picks()

    print('\n\tExcecuting PhaseNet\n')
    command = f"python run.py --mode={params['mode']} --model_dir={params['model_dir']} \
        --data_dir={params['data_dir']} --data_list={params['data_list']} \
        --output_dir={params['output_dir']} --plot_figure --save_result \
        --batch_size={params['batch_size']} --input_length={params['input_length']}"
    print('\n', command, '\n')
    os.system(command)


if __name__ == "__main__":
    init()