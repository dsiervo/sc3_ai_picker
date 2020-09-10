#!/home/sgc/anaconda3/envs/phaseNet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Aug 25 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""

import os
import glob
from merge_xml_picks import merge_xml_picks

def joinpicks(prefix, out_filename='all_picks_phasenet.xml'):
    """Join in one xml the picks.xml generated for sgc_phasenet. The script
    needs to be run in the general_data_dir.

    Parameters
    ----------
    prefix : str
        prefix of the sgc_phasenet output folders. Like '20200712_'
    out_filename : str
        File name or path of the ouput xml
    """
    dirs = glob.glob(prefix+'*')
    
    # Creating folder that will contains the xml of the picks
    picks_dir = 'xml_picks'
    if not os.path.isdir(picks_dir):
        os.mkdir(picks_dir)

    # Copying all the picks to picks_dir
    for idx, d in enumerate(dirs):
        source_path = os.path.join(d, 'picks.xml')
        target_path = os.path.join(picks_dir, f'picks_{idx}.xml')

        cmd = f'cp {source_path} {target_path}'
        print(cmd)
        os.system(cmd)

    # Applying merge_xml_picks to picks_dir
    merge_xml_picks(picks_dir+'/', out_filename)

if __name__ == "__main__":
    import sys
    
    assert len(sys.argv) >= 2, 'Insuficent arguments. Needs to provide at least the folders suffix.\n\n\
        Example: joinpicks.py 20200105\n'
    if len(sys.argv) == 2:
        joinpicks(sys.argv[1])
    elif len(sys.argv) == 3:
        joinpicks(sys.argv[1], sys.argv[2])