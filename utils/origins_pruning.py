#!/home/dsiervo/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Nov 24 13:01:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
import obspy as obs
import sys

"""import click

@click.command()
@click.option('-i', "--xml_name", required=True, prompt=True, help='Input event type SeisComP xml file name')
@click.option('-o', "--output_fn", prompt=True, help='Output xml file name', default="origenes_preferidos.xml")"""


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
    
    change_xml_version(xml_name)
    
    print('\n\nRemoving origins that are not the prefered one in the xml %s\n' % xml_name)
    try: 
        cat = obs.read_events(xml_name, id_prefix='', format='SC3ML')
    except FileNotFoundError:
        print('\n\t No existe el archivo %s, se salta este proceso\n' % xml_name)
        sys.exit(1)

    for ev in cat:
        del ev.origins[:-1]

    cat.write(output_fn, format='SC3ML', validate=True, event_removal=True,
              verbose=True)

    remove_id_prefix(output_fn)
    
    print('\n\tArchivo con origenes preferidos para migrar a SeisComP3:\n\n\t  %s\n'%output_fn)


def remove_id_prefix(xml_name):
    f = open(xml_name).read()
    new_content = f.replace('smi:local/', '')
    with open(xml_name, "w") as f:
        f.write(new_content)


def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file).readlines()
    lines[1] = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w') as f:
        f.write(''.join(lines))


if __name__ == "__main__":
    import sys
    origins_pruning(sys.argv[1])
