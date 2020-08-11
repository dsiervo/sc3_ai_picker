#!/home/sgc/anaconda3/envs/tf_2.0/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mar 5 11:25:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""

import numpy as np
import matplotlib.pyplot as plt
import glob


def main():
    for npz in glob.glob('*.npz'):
        
        print('\n\t', npz)
        data = np.load(npz)
        
        y = data['data'][:,1]
        p = data['itp']
        s = data['its']
        
        y_min = min(y)
        y_max = max(y)
        
        plt.figure()
        plt.plot(y)
        plt.vlines(p, y_min, y_max, colors='black', label='P')
        plt.vlines(s, y_min, y_max, colors='r', label='S')
        plt.legend()
        plt.show()
        
if __name__ == "__main__":
    main()
