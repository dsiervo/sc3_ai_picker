from obspy import UTCDateTime
from datetime import timedelta
from cwav import Cwav
import os

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


def prep_cwav_params(inp_file):
    params = read_params(inp_file)

    params['starttime'] = UTCDateTime(params['starttime'])
    params['endtime'] = UTCDateTime(params['endtime'])
    params['dt'] = timedelta(seconds=int(params['dt']))

    download_params = params['download_data'].split(',')
    filter_params = params['filter_data'].split(',')
    download_data = list(map(str.strip, download_params))
    filter_data= list(map(str.strip, filter_params))

    pnet_params = ['PhaseNet_dir', 'general_data_dir', 'model_dir',\
                    'general_output_dir', 'mode', 'batch_size', 'plot_figure',\
                    'save_result'] 
    client_params = ['ip', 'port', 'starttime', 'endtime', 'dt']

    pnet_dict = dict((key, params[key]) for key in pnet_params)
    client_dict = dict((key, params[key]) for key in client_params)

    return download_data, pnet_dict, client_dict, filter_data

def run(inp_file):

    download_data, pnet_dict, client_dict, filter_data = prep_cwav_params(inp_file)

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

        DIR_PATH = pnet_dict['general_data_dir']
        OUTPUT_PATH = pnet_dict['general_output_dir']
        folder_name = starttime.strftime('%Y%m%d_%H%M%S') + f'_{int(p)}'

        data_dir = os.path.join(DIR_PATH,folder_name )
        output_dir = os.path.join(OUTPUT_PATH,folder_name )

        pnet_dict['data_dir'] = data_dir    
        pnet_dict['data_list'] = os.path.join(data_dir,'fname.csv')
        pnet_dict['output_dir'] = os.path.join(output_dir)

        client_dict['starttime'] = starttime
        client_dict['endtime'] = endtime

        cwav = Cwav(download_data, pnet_dict, client_dict, filter_data=filter_data)
        cwav.download()
        cwav.run_pnet()

        starttime += dt
    return pnet_dict

if __name__ == "__main__":
    path = '/mnt/almacenamiento/Emmanuel_Castillo/git_EDCT/SGC/sgc_phasenet/sgc.inp'
    run(path)
