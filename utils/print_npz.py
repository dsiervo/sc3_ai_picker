#!/home/sgc/anaconda3/envs/tf_2.0/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mar 5 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""

import numpy as np
import glob
import os


def main():
    """
    for npz in glob.glob('*.npz'):

        meta = np.load(npz)

        data = np.copy(meta['data'])
        its = meta['its'] 
        itp = meta['itp']

        start_tp = itp

        X_shape = [3000, 1, 3]
        sample = np.zeros(X_shape)

        m_window = 0.4
        sampling_rate = 100

        mask_window = int(m_window * sampling_rate)

        shift = np.random.randint(-(X_shape[0]-mask_window), min([its-start_tp, X_shape[0]])-mask_window)

        try:
            sample[:, :, :] = data[start_tp+shift:start_tp+X_shape[0]+shift, np.newaxis, :]
        except ValueError:
            print(f'{start_tp+shift}:{start_tp+X_shape[0]+shift}, np.newaxis, :')"""
    
    
    for npz in glob.glob('*.npz'):
        meta = np.load(npz)
        y = meta['data']
        
        if y.shape != (9001,3):
            print(npz, y.shape)
            os.system(f'rm -fr {npz}')
        
if __name__ == "__main__":
    main()