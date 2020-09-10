#!/home/sgc/anaconda3/envs/phaseNet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Aug 25 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""

import os
import glob

def joincsv(prefix, out_filename='all_picks_phasenet.csv'):
    """Join in one csv the picks.csv generated for sgc_phasenet. The script
    needs to be run in the general_data_dir.

    Parameters
    ----------
    prefix : str
        prefix of the sgc_phasenet output folders. Like '20200712_'
    out_filename : str
        File name or path of the ouput csv
    """
    dirs = glob.glob(prefix+'*')
    
    paths = [os.path.join(d, 'picks.csv') for d in dirs]

    for idx, csv in enumerate(paths):
        if idx == 0:
            text = open(csv).read()
            with open(out_filename, 'w') as f_out:
                f_out.write(text)
        else:
            lines = open(csv).readlines()
            text = ''.join(lines[1:])
            with open(out_filename, 'a') as f_out:
                f_out.write(text)
    
    print(f'\n\tSe genero el archivo {out_filename}')


if __name__ == "__main__":
    import sys
    
    assert len(sys.argv) >= 2, 'Insuficent arguments. Needs to provide at least the folders suffix.\n\n\
        Example: joinpicks.py 20200105\n'
    if len(sys.argv) == 2:
        joincsv(sys.argv[1])
    elif len(sys.argv) == 3:
        joincsv(sys.argv[1], sys.argv[2])