#!/home/dsiervo/anaconda3/envs/pnet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Jul 2020

@author: Emanuel Castillo T. [ecastillot@unal.edu.co], Daniel Siervo P. [ddsiervop@unal.edu.co]
"""
import os
from obspy import UTCDateTime
from datetime import timedelta
from utils.cwav import Cwav_PhaseNet, Cwav_EQTransformer
from utils.merge_xml_picks import merge_xml_picks
from utils.origins_pruning import origins_pruning

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

def prep_download_list(params):
    params = params.copy()
    download_params = params['download_data'].split(',')
    download_data = list(map(str.strip, download_params))

    if len(download_data) == 1:     #change the list type to a str type
        station = download_data[0]
        if station in ('all', 'All', 'ALL'):
            download_data = 'all'
        if station in ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE'):
            download_data = 'No'

    return download_data

def prep_filter_list(params):
    #### ONLY FOR PHASENET
    params = params.copy()
    filter_params = params['filter_data'].split(',')
    filter_data= list(map(str.strip, filter_params))

    if len(filter_data) == 1:     #change the list type to a str type
        station = filter_data[0]
        if station in ('all', 'All', 'ALL'):
            filter_data = 'all'
        if station in ('No', 'no', 'N', 'n', 'False', 'false', 'FALSE'):
            filter_data = 'No'

    return filter_data

def prep_client_params(params):
    params = params.copy()
    try:
        params['starttime'] = UTCDateTime(params['starttime'])
        params['endtime'] = UTCDateTime(params['endtime'])
    except ValueError:
        raise ValueError("\n\nAsegúrese de ingresar fechas válidas con el formato: YYYY-MM-D hh:mm:ss\n")
    params['dt'] = timedelta(seconds=int(params['dt']))

    client_params = ['ip', 'port', 'starttime', 'endtime', 'dt']
    client_dict = dict((key, params[key]) for key in client_params)

    return client_dict

def prep_pnet_params(params):
    params = params.copy()
    pnet_params = ['pnet_repository_dir', 'general_data_dir', 'pnet_model_dir',\
                    'general_output_dir', 'pnet_mode', 'pnet_batch_size', 'pnet_plot_figure',\
                    'pnet_save_result'] 

    pnet_dict = {}
    for key in pnet_params:
        if key == 'general_data_dir' or key == 'general_output_dir':
            pnet_dict['pnet_'+str(key)] = os.path.join(params[key],'pnet')
        else :
            pnet_dict[str(key)] = params[key]

    return pnet_dict
    # pnet_dict = dict((key, params[key]) for key in pnet_params)

def prep_eqt_params(params):
    params = params.copy()
    eqt_int = ['dt', 'eqt_n_processor', 'eqt_number_of_plots',
                'eqt_batch_size']
    eqt_float = ['eqt_overlap',\
                'eqt_detection_threshold',\
                'eqt_P_threshold', 'eqt_S_threshold']
    eqt_str = ['general_data_dir','general_output_dir', \
                'eqt_create_json', 'eqt_create_hdf5',\
                'eqt_model_dir','eqt_plot_mode',\
                'eqt_predictor']
    
    eqt_dict = {'eqt_n_processor':2}
    for key in eqt_int: params[f'{key}'] = int(params[f'{key}'])
    for key in eqt_float: params[f'{key}'] = float(params[f'{key}'])

    eqt_params = eqt_int + eqt_float + eqt_str

    # eqt_dict = dict((key, params[key]) for key in eqt_params)
    for key in eqt_params:
        if key == 'general_data_dir' or key == 'general_output_dir':
            g,x,_dir = key.split("_")
            new_key = "_".join((x,_dir))
            eqt_dict['eqt_'+str(new_key)] = os.path.join(params[key],'eqt')
        if key == 'dt':
            eqt_dict['eqt_chunk_size'] = params[key]
        else :
            eqt_dict[str(key)] = params[key]
    return eqt_dict

def prep_mysqldb_params(params):
    params = params.copy()
    
    # value by default. It will be replaced if it exist in ai_picker.inp
    mysql_dict = {'db_sc':'mysql://sysop:sysopp@10.100.100.13/seiscomp3'}
    for key in mysql_dict:
        if key in params.keys():
            mysql_dict[key] = params[key]
    
    return mysql_dict

def prep_Cwav_params(inp_file):
    params = read_params(inp_file)

    mysqldb_dict = prep_mysqldb_params(params)
    client_dict = prep_client_params(params)   
    download_data = prep_download_list(params)
    filter_data = prep_filter_list(params)
    picker = params['picker']   
    pnet_dict = prep_pnet_params(params)
    eqt_dict = prep_eqt_params(params)

    return client_dict, download_data,filter_data, picker, pnet_dict, eqt_dict, mysqldb_dict

def run_PhaseNet(client_dict, download_data,filter_data,pnet_dict, mysqldb_dict):
    STARTTIME= client_dict['starttime']
    ENDTIME = client_dict['endtime']
    DT = client_dict['dt']

    starttime = STARTTIME

    while starttime < ENDTIME:

        endtime = starttime + DT

        if endtime > ENDTIME:
            endtime = ENDTIME
        else:
            pass

        p = endtime-starttime           #particion
        dt = timedelta(seconds=p)    

        start_strf = starttime.strftime('%Y-%m-%d %H:%M:%S.%f')
        end_strf = endtime.strftime('%Y-%m-%d %H:%M:%S.%f')
        print('####################################\t,START=\t',start_strf,'\t',
                'END=\t',end_strf ,'\t####################################')

        DIR_PATH = pnet_dict['pnet_general_data_dir']
        OUTPUT_PATH = pnet_dict['pnet_general_output_dir']
        folder_name = starttime.strftime('%Y%m%d_%H%M%S') + f'_{int(p)}'

        data_dir = os.path.join(DIR_PATH,folder_name )
        output_dir = os.path.join(OUTPUT_PATH,folder_name )

        pnet_dict['pnet_data_dir'] = data_dir    
        pnet_dict['pnet_data_list'] = os.path.join(data_dir,'fname.csv')
        pnet_dict['pnet_output_dir'] = os.path.join(output_dir)

        client_dict['starttime'] = starttime
        client_dict['endtime'] = endtime

        cwav_pnet = Cwav_PhaseNet(download_data, pnet_dict, 
                                client_dict, 
                                filter_data=filter_data,
                                mysqldb_dict=mysqldb_dict)
        
        cwav_pnet.download()
        cwav_pnet.run_pnet()
        cwav_pnet.picks2xml(p)
        cwav_pnet.playback()

        starttime += dt

    # mergin all seiscomp .xml events
    events_dir = os.path.join(OUTPUT_PATH, 'xml_events')
    evf_path = os.path.join(OUTPUT_PATH, "events_final.xml")
    merge_xml_picks(events_dir, evf_path)

    # pruning origins that are not the prefered
    pref_orig_path = os.path.join(OUTPUT_PATH, "origenes_preferidos.xml")
    origins_pruning(evf_path, pref_orig_path)

def run_EQTransformer(client_dict, download_data,eqt_dict, mysqldb_dict):

    cwav_eqt = Cwav_EQTransformer(download_data,eqt_dict,client_dict,
                                  mysqldb_dict=mysqldb_dict)
    
    print(f'\ncwav_eqt object:\n\t{cwav_eqt.__dict__}\n')
    cwav_eqt.create_json()
    cwav_eqt.download_mseed()
    if eqt_dict['eqt_predictor'] in ('mseed','MSEED'):
        cwav_eqt.mseedpredictor()
    elif eqt_dict['eqt_predictor'] in ('hdf5','HDF5'):
        cwav_eqt.preprocessor()
        cwav_eqt.predictor()
    cwav_eqt.picks2xml()
    cwav_eqt.playback()
    
    OUTPUT_PATH = eqt_dict['eqt_output_dir']
    # mergin all seiscomp .xml events
    events_dir = os.path.join(OUTPUT_PATH, 'xml_events')
    evf_path = os.path.join(OUTPUT_PATH, "events_final.xml")
    merge_xml_picks(events_dir, evf_path)

    # pruning origins that are not the prefered
    pref_orig_path = os.path.join(OUTPUT_PATH, "origenes_preferidos.xml")
    origins_pruning(evf_path, pref_orig_path)

def run(inp_file):

    client_dict, download_data,filter_data, picker, pnet_dict, eqt_dict, mysqldb_dict = prep_Cwav_params(inp_file)

    if picker in ('PhaseNet','pnet','phasenet'):
        run_PhaseNet(client_dict, download_data, filter_data, pnet_dict, mysqldb_dict=mysqldb_dict)

    elif picker in ('EQTransformer','eqt','eqtransformer'):
        run_EQTransformer(client_dict, download_data, eqt_dict, mysqldb_dict=mysqldb_dict)

if __name__ == "__main__":
    
    # script directory for ai_picker.inp searching
    main_dir = os.path.dirname(os.path.abspath(__file__))
    par_fn = 'ai_picker.inp'
    rel_par_path = os.path.join('../', par_fn)
    main_par_path = os.path.join(main_dir, par_fn)

    # verifying if ai_picker.inp exist in any of the following 3 paths. 
    check_inp_dirs = [par_fn, rel_par_path, main_par_path]
    for rel_path in check_inp_dirs:
        if os.path.isfile(rel_path):
            print('Reading params for: {0} \n'.format(rel_path))
            path = rel_path
            break

    run(path)

    # Cwav_params = prep_Cwav_params(path)
    # print(Cwav_params)
    # params = read_params(path)
    # eqt_params = prep_eqt_params(params)
    # print(eqt_params)
