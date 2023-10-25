#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Feb 5 2021

@author: Daniel Siervo, emetdan@gmail.com
"""
import os
from concurrent.futures import ProcessPoolExecutor


def get_xml_path(path: str, xmlfile: str) -> list:
    xml_paths = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if filename == xmlfile:
                xml_paths.append(os.path.join(dirpath, filename))
                break
    return xml_paths


def apply_scevent(xml_paths: list, output_filename: str):
    """Apply parallely scevent to pruned origins

    Parameters
    ----------
    xml_paths : list
        List of xml paths of pruned origins
    output_filename : str
        Name of the output seiscomp event xml
    """
    db = 'mysql://sysop:sysop@sc3primary.beg.utexas.edu/seiscomp3'
    
    N = len(xml_paths)
    with ProcessPoolExecutor(max_workers=8) as excecutor:
        excecutor.map(exc_scevent, [output_filename]*N, xml_paths, [db]*N)


def exc_scevent(output_filename, origin_path, db):
    change_xml_version(origin_path)
    event_path = os.path.join(os.path.dirname(origin_path), output_filename)
    scevent_cmd = 'scevent -u playback --ep %s -d %s  > %s' % (origin_path,
                                                               db, event_path)
    print(scevent_cmd)
    os.system(scevent_cmd)


def join_xml(xml_paths, output_filename):
    """Merge seiscomp events xml in one xml file

    Parameters
    ----------
    xml_paths : list
        List with paths of seiscomp xml events
    output_filename : str
        Name of merged xml event file
    """
    xmls = ' '.join(xml_paths)
    cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scxmlmerge {xmls} --debug > {output_filename}'
    print(cmd)
    os.system(cmd)


def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file).readlines()
    lines[1] = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w') as f:
        f.write(''.join(lines))


def event_summary(joined_xml_path):
    """Load the joined xml file and creates a dataframe with the
    summary of the events

    Parameters
    ----------
    main_xml_path : str
        Path to joined seiscomp events like xml
    """

    cmd = f'run_dashboard.sh {joined_xml_path}'
    print(cmd)
    os.system(cmd)


def prune_and_count(main_path):
    """Creates a daraframe with the summary of events ins subpaths of main_path

    Parameters
    ----------
    main_path : str
        Path that contains the folder that contains the origenes_preferidos.xml
        file
    """
    prefered_origins_list = get_xml_path(main_path, 'origenes_preferidos.xml')

    events_pruned_name = 'events_pruned.xml'
    
    apply_scevent(prefered_origins_list, events_pruned_name)
    
    events_pruned_list = get_xml_path(main_path, events_pruned_name)
    
    main_events_name = 'main_events_pruned.xml'
    
    # split the list in 2 chunks
    N = len(events_pruned_list)
    events_list_1 = events_pruned_list[:N//2]
    events_list_2 = events_pruned_list[N//2:]
    split_list = [events_list_1, events_list_2]
    split_names = [f'main_events_pruned_{i}.xml' for i in range(len(split_list))]
    for events_list, split_name in zip(split_list, split_names):
        join_xml(events_list, split_name)
    
    join_xml(split_names, main_events_name)
    
    change_xml_version(main_events_name)
    
    main_ev_path = os.path.join(main_path, main_events_name)
    event_summary(main_ev_path)


if __name__ == '__main__':
    prune_and_count(os.getcwd())
