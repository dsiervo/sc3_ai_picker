#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on August 2023

@author: Daniel Siervo Plata [ddsiervop@unal.edu.co]

Excecutes ai_picker.py in a periodic time
"""
import os
import sys
import logging
import schedule
import time
import datetime
from main_ai_scheduler import runner
import json
from icecream import ic
from main_picker_temp import prep_Cwav_params, run_EQTransformer
log_file_name = os.path.basename(__file__).replace('.py', '.log')
logging.basicConfig(filename=log_file_name, level=logging.DEBUG, format='%(message)s')


def loggin_test(s):
    logging.debug(s)
    print(s, file=sys.stderr)


def time_ic_debug():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S: ')


ic.configureOutput(prefix=time_ic_debug, outputFunction=loggin_test)


class MultiEQCCT:
    def __init__(self, eqcct_instances_json):
        self.eqcct_instances_json = eqcct_instances_json
        self.eqcct_dict_instances = self.get_eqcct_dict_instances()
        self.eqcct_dir_instances = self.get_eqcct_dir_instances()
        # dir path of this script
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
    
    def get_eqcct_dict_instances(self):
        eqcct_instances = {}
        with open(self.eqcct_instances_json, 'r') as f:
            dict_eqcct_instances = json.load(f)
        for key in dict_eqcct_instances:
            if key.startswith('EQCCT'):
                eqcct_instances[key] = dict_eqcct_instances[key]
        return eqcct_instances
        
    def get_eqcct_dir_instances(self):
        eqcct_dir_instances = []
        for key in self.eqcct_dict_instances:
            eqcct_dir_instances.append(self.eqcct_dict_instances[key]['dir'])
        return eqcct_dir_instances
    
    @property
    def all_stations(self):
        """Get all the stations in all the ai_picker_scdl.inp files in the line that starts with 'download_data'
        Like:
        download_data = TX.PB24.00.HH*, 4O.WB03.00.HH*, TX.PB40.00.HH*, TX.PB34.00.HH*
        
        ----------
        Returns
        -------
        list
            List of all the stations in all the ai_picker_scdl.inp files
        """
        self.inp_paths = []
        stations = []
        for eqcct_dir in self.eqcct_dir_instances:
            eqcct_inp = os.path.join(eqcct_dir, 'ai_picker_scdl.inp')
            self.inp_paths.append(eqcct_inp)
            with open(eqcct_inp, 'r') as f:
                for line in f:
                    if line.startswith('download_data'):
                        stations.extend([s.strip() for s in line.split('=')[1].split(',')])
        return stations

    def create_download_inp(self):
        """Create the download_data.inp file which is a copy of ai_picker_scdl.inp, replacing the
        download_data line with the stations provided
        """
        original_inp = self.inp_paths[0]
        self.download_inp = 'download_data.inp'
        with open(original_inp, 'r') as f:
            lines = f.readlines()
        with open(self.download_inp, 'w') as f:
            for line in lines:
                if line.startswith('download_data'):
                    f.write(f'download_data = {", ".join(self.all_stations)}\n')
                else:
                    f.write(line)

    def download_mseed(self):
        """Download mseed files from the stations in the download_data.inp.inp file
        """
        client_dict, download_data,filter_data, picker, pnet_dict, eqt_dict, mysqldb_dict = prep_Cwav_params(self.download_inp)
        run_EQTransformer(client_dict, download_data,
                          eqt_dict, picker=picker,
                          mysqldb_dict=mysqldb_dict,
                          json_filename='download_data.json',
                          predict=False)

    def download(self):
        self.create_download_inp()
        self.download_mseed()

    def predict(self):
        for dict_instance in self.eqcct_dict_instances:
            os.chdir(dict_instance['dir'])
            # runner will look for the configuration in dict_instance['dir']/ai_picker_scdl.inp
            # data_download should be no because we already downloaded the data
            runner(every_m=dict_instance['data_minutes'],
                   db='sc3primary.beg.utexas.edu')

    def download_and_predict(self):
        """Run eqcct in each instance in parallel
        """
        self.download()
        self.predict()



if __name__ == '__main__':
    data_minutes = 40
    eqcct_instances_json = 'multi-eqcct.json'
    
    multi_eqcct = MultiEQCCT(eqcct_instances_json)
    runner(every_m=data_minutes,
           db='sc3primary.beg.utexas.edu')