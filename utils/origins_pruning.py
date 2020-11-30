#!/home/dsiervo/anaconda3/envs/pnet/bin/python
# -*- coding: utf-8 -*-
"""
Created on Nov 24 13:01:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
import os
import obspy as obs
import click

@click.command()
@click.option('-i', "--xml_name", required=True, prompt=True, help='Input event type SeisComP xml file name')
@click.option('-o', "--output_fn", prompt=True, help='Output xml file name', default="origenes_preferidos.xml")

def origins_pruning(xml_name, output_fn='origenes_preferidos.xml'):
    """Delete all origins that are not the prefered origin
    in a seiscomp event xml file. Returns a xml with origins only

    Parameters
    ----------
    xml_name : str
        Name of events type SeisComP3 xml file.
    output_fn : str
        Name of output SeisComP3 xml file.
    """
    
    print('\n\nEliminando los orígnenes que no son el preferido del archivo %s\n'%xml_name)
    print('\tLeyendo el xml de eventos...')
    cat = obs.read_events(xml_name, id_prefix='', format='SC3ML')
    
    print('\tEliminando orígenes que no son el preferido...')
    for ev in cat:
        del ev.origins[:-1]
    
    print('\tEscribiendo nuevo xml...')
    cat.write(output_fn, format='SC3ML',validate=True, event_removal=True, verbose=True)
    
    print('\tArreglando IDs en nuevo xml')
    remove_id_prefix(output_fn)
    
    print('\n\tArchivo con orígenes preferidos para migrar a SeisComP3:%s'%output_fn)

def remove_id_prefix(xml_name):
    f = open(xml_name).read()
    new_content = f.replace('smi:local/', '')
    with open(xml_name, "w") as f:
        f.write(new_content)

if __name__ == "__main__":
    
    origins_pruning()