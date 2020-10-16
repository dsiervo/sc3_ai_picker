#!/home/dsiervo/anaconda3/envs/pnet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Jul 2020

@author: Emanuel Castillo T. [ecastillot@unal.edu.co], Daniel Siervo P. [ddsiervop@unal.edu.co]
"""

from main_picker import read_params
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

    assert picker in ('pnet', 'eqt'), 'El picker debe ser "eqt" o "pnet", usó "%s"\n'%picker

    exc_env = '#!/home/dsiervo/anaconda3/envs/%s/bin/python\n'%picker
    lines[0] = exc_env

    with open(os.path.join(main_dir, 'main_picker.py'), 'w') as f:
        f.writelines(lines)
    

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
    change_env(par['picker'], main_dir)

    # runing ai_picker 
    os.system('main_picker.py')
