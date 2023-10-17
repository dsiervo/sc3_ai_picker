#!/home/siervod/anaconda3/envs/eqcc/bin/python
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
from ai_picker import read_params


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

    # check if starttime - endtime is larger than dt
    assert timedelta(params['endtime'] - params['starttime']) > params['dt'], "The time window needs to be larger than dt"

    client_params = ['ip', 'port', 'starttime', 'endtime', 'dt', 'locator_dict']
    try:
        client_dict = dict((key, params[key]) for key in client_params)
    # default value for locator_dict
    except KeyError as missing_key:
        client_dict = dict((key, params[key]) for key in client_params[:-1])
        if missing_key.args[0] == 'locator_dict':
            client_dict['locator_dict'] = '{"LOCSAT": "iasp91"}'
    
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
                'eqt_plot_mode','eqcc_P_model_dir','eqcc_S_model_dir',\
                'eqt_predictor']
    eqt_gpu = ['eqt_gpu_limit', 'eqt_gpuid']
    # get script path directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    model_default_path = os.path.join(script_dir, 'model', 'EqT_model.h5')
    model_eqcc_P_path = os.path.join(script_dir, 'model', 'ModelPS', 'test_trainer_024.h5')
    model_eqcc_S_path = os.path.join(script_dir, 'model', 'ModelPS', 'test_trainer_021.h5')
    
    eqt_dict = {'eqt_n_processor': 2,
                'eqt_model_dir': model_default_path,
                'eqcc_P_model_dir': model_eqcc_P_path,
                'eqcc_S_model_dir': model_eqcc_S_path,
                'eqt_gpuid':None,
                'eqt_gpu_limit':None}
    
    for key in eqt_gpu:
        if key in params:
            if key == 'eqt_gpu_limit':
                eqt_float.append(key)
            elif key == 'eqt_gpuid':
                eqt_int.append(key)

    for key in eqt_int: params[f'{key}'] = int(params[f'{key}'])
    for key in eqt_float: params[f'{key}'] = float(params[f'{key}'])

    eqt_params = eqt_int + eqt_float + eqt_str

    # eqt_dict = dict((key, params[key]) for key in eqt_params)
    for key in eqt_params:
        if key in params.keys():
            if key == 'general_data_dir' or key == 'general_output_dir':
                g,x,_dir = key.split("_")
                new_key = "_".join((x,_dir))
                eqt_dict['eqt_'+str(new_key)] = os.path.join(params[key],'eqt')
            if key == 'dt':
                eqt_dict['eqt_chunk_size'] = params[key]
            else:
                eqt_dict[str(key)] = params[key]

    # print in green and bold the eqcc_P_model_dir and eqcc_S_model_dir
    print(f'\n\033[92m\033[1m eqcc_P_model_dir: {eqt_dict["eqcc_P_model_dir"]}\033[0m')
    print(f'\033[92m\033[1m eqcc_S_model_dir: {eqt_dict["eqcc_S_model_dir"]}\033[0m\n')

    # if file params['eqt_model_dir'] does not exist, set it to default
    if not os.path.exists(eqt_dict['eqt_model_dir']):
        params['eqt_model_dir'] = model_default_path
    return eqt_dict

def prep_mysqldb_params(params):
    params = params.copy()
    
    # value by default. It will be replaced if it exist in ai_picker.inp
    mysql_dict = {'db_sc': 'mysql://sysop:sysopp@10.100.100.13/seiscomp3',
                  'check_db': False,
                  'check_quadrant': "None"}
    for key in mysql_dict:
        if key in params.keys():
            if key == 'check_db':
                if params[key] in ('Yes', 'yes', 'YES', 'True', 'true', 'TRUE'):
                    mysql_dict[key] = True
                else:
                    mysql_dict[key] = False
            elif key == 'check_quadrant':
                # if a BNA file is provided
                if params[key].split('.')[-1] == 'bna':
                    mysql_dict[key] = params[key]
                else:
                    quadrant = params[key].split(',')
                    quadrant = tuple(map(float, quadrant))
                    # check if quadrant has 4 values
                    assert len(quadrant) == 4, "The quadrant must have 4 values"
                    params[key] = quadrant
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
        cwav_pnet.playback(eval(client_dict['locator_dict']))

        starttime += dt

    # mergin all seiscomp .xml events
    events_dir = os.path.join(OUTPUT_PATH, 'xml_events')
    evf_path = os.path.join(OUTPUT_PATH, "events_final.xml")
    merge_xml_picks(events_dir, evf_path)

    # pruning origins that are not the prefered
    pref_orig_path = os.path.join(OUTPUT_PATH, "origenes_preferidos.xml")
    origins_pruning(evf_path, pref_orig_path, check_db=mysqldb_dict["check_db"],
                    quadrant=mysqldb_dict['check_quadrant'])


def run_EQTransformer(client_dict, download_data,eqt_dict, picker, mysqldb_dict):

    cwav_eqt = Cwav_EQTransformer(download_data,eqt_dict,client_dict,
                                picker=picker,
                                mysqldb_dict=mysqldb_dict)
    
    print(f'\ncwav_eqt object:\n\t{cwav_eqt.__dict__}\n')
    cwav_eqt.create_json()
    cwav_eqt.download_mseed()
    if eqt_dict['eqt_predictor'] in ('mseed','MSEED'):
        cwav_eqt.mseedpredictor()
        pass
    elif eqt_dict['eqt_predictor'] in ('hdf5','HDF5'):
        cwav_eqt.preprocessor()
        cwav_eqt.predictor()
    cwav_eqt.picks2xml()
    cwav_eqt.playback(eval(client_dict['locator_dict']))
    
    OUTPUT_PATH = eqt_dict['eqt_output_dir']
    # mergin all seiscomp .xml events
    events_dir = os.path.join(OUTPUT_PATH, 'xml_events')
    evf_path = os.path.join(OUTPUT_PATH, "events_final.xml")
    merge_xml_picks(events_dir, evf_path)

    # pruning origins that are not the prefered
    pref_orig_path = os.path.join(OUTPUT_PATH, "origenes_preferidos.xml")
    print(f'\n\n\033[95m check_db in main_picker_temp: {mysqldb_dict["check_db"]}\033[0m')
    origins_pruning(evf_path, pref_orig_path, check_db=mysqldb_dict["check_db"],
                    quadrant=mysqldb_dict['check_quadrant'])


def run(inp_file):

    client_dict, download_data,filter_data, picker, pnet_dict, eqt_dict, mysqldb_dict = prep_Cwav_params(inp_file)

    if picker in ('PhaseNet','pnet','phasenet'):
        run_PhaseNet(client_dict, download_data, filter_data, pnet_dict, mysqldb_dict=mysqldb_dict)

    elif picker in ('EQTransformer','eqt','eqtransformer', 'eqcctps', 'eqcc', 'eqcct'):
        run_EQTransformer(client_dict, download_data, eqt_dict, picker=picker, mysqldb_dict=mysqldb_dict)

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
