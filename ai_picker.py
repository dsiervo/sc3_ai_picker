#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Jul 2020

@author: Emanuel Castillo T. [ecastillot@unal.edu.co], Daniel Siervo P. [ddsiervop@unal.edu.co]
"""

import os


def change_env(picker, main_dir):
    """Change the environment excecution in the first line in the original ai_picker.py
    
    Parameters
    ----------
    pick_time : str
        Picker type, can be eqt or pnet
    main_dir: str
        Directory of the main script
    
    Returns
    ------
        void
    """
    script_path = os.path.join(main_dir, 'utils/main_picker_temp.py')

    lines = open(script_path).readlines()

    assert picker in ('pnet', 'eqt', 'eqcc', 'eqcctps'), 'El picker debe ser "eqt" o "pnet", usó "%s"\n'%picker

    anaconda_path = read_params(os.path.join(main_dir, 'anaconda_path.txt'))['anaconda_path']
    #anaconda_path = '/home/dsiervo/anaconda3/'
    exc_env_path = os.path.join(anaconda_path, 'envs/%s/bin/python'%picker)
    exc_env = '#!%s\n'%exc_env_path
    #exc_env = '#!/home/dsiervo/anaconda3/envs/%s/bin/python\n'%picker
    lines[0] = exc_env

    with open(os.path.join(main_dir, 'main_picker.py'), 'w') as f:
        f.writelines(lines)


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

if __name__ == '__main__':

    # script directory for ai_picker.inp searching
    main_dir = os.path.dirname(os.path.abspath(__file__))
    par_fn = 'ai_picker.inp'
    rel_par_path = os.path.join('../', par_fn)
    main_par_path = os.path.join(main_dir, par_fn)

    # verifying if ai_picker.inp exist in any of the following 3 paths. 
    check_inp_dirs = [par_fn, rel_par_path, main_par_path]
    for rel_path in check_inp_dirs:
        if os.path.isfile(rel_path):
            inp_path = rel_path
            break
    
    par = read_params(inp_path)

    # changing the excecution line
    # using eqt as environment if the picker is eqcc or eqcctps
    if par['picker'] in ('eqcc', 'eqcctps'):
        par['picker'] = 'eqcc'
    change_env(par['picker'], main_dir)

    # runing ai_picker
    main_picker_path = os.path.join(main_dir, 'main_picker.py')
    # excecuting the main_picker.py
    os.system(main_picker_path) 