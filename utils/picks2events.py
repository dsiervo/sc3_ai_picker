#!/home/daniel/anaconda3/envs/eqt/bin/python
from playback import playback
from merge_xml_picks import merge_xml_picks # also merge events
import sys
import os
import multiprocessing
from multiprocessing import Pool
import obspy as obs

def picks2events(picks_file, locator_dict, events_dir):
    """
    Convert a picks file to an events file using the specified locator.
    """

    my_playback = playback(
            sc_scanloc='scanloc',
            locator_dict=locator_dict,
            wf_dir=None,
            db='mysql://sysop:sysop@sc3primary.beg.utexas.edu/seiscomp3',
            picks ='none',
            xml_picks_file=picks_file,
            out_dir=events_dir,
            ai_type='eqt')
    
    my_playback.playback_commands(picks2events=True)

    return events_dir

def automatic2manual(picks_file):
    """Replace <evaluationMode>automatic</evaluationMode> for <evaluationMode>manual</evaluationMode>
    in the picks file. Write the result to a new file in the same directory."""
    with open(picks_file, 'r') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        if '<evaluationMode>automatic</evaluationMode>' in line:
            line = line.replace('<evaluationMode>automatic</evaluationMode>', '<evaluationMode>manual</evaluationMode>')
        new_lines.append(line)
    new_picks_file = picks_file.replace('.xml', '_manual.xml')
    with open(new_picks_file, 'w') as f:
        f.writelines(new_lines)
    return new_picks_file

def change_xml_version(picks_file):
    """Change the seiscomp xml schema version from 0.12 to 0.10 in the picks file. Write the result to a new file in the same directory."""
    with open(picks_file, 'r') as f:
        lines = f.readlines()
    
    new_schema_line = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    lines[1] = new_schema_line

    with open(picks_file, 'w') as f:
        f.writelines(lines)

def picks2events_wrapper(args):
    """Wrapper for multiprocessing."""
    return picks2events(*args)

def keep_just_preferd_orgin(event_xml_file):
    cat = obs.read_events(event_xml_file, id_prefix='', format='SC3ML')
    for event in cat:
        event.preferred_origin_id = event.origins[0].resource_id
        event.origins = [event.origins[0]]
    cat.write(event_xml_file, format='SC3ML')

if __name__ == '__main__':
    
    locator_dict = {"LOCSAT": "iasp91"}
    picks_dir = sys.argv[1]
    output_dir = sys.argv[2]
    events_dir = os.path.join(output_dir, 'xml_events')


    """# Loop over all picks files in the directory
    for picks_file in os.listdir(picks_dir):
        if picks_file.endswith('.xml') and "_manual" not in picks_file:
            picks_path = os.path.join(picks_dir, picks_file)
            change_xml_version(picks_path)
            manual_picks_path = automatic2manual(picks_path)
            
            picks2events(manual_picks_path, locator_dict, output_dir)"""
    
    # a multiprocessing version of the above for loop
    n_jobs = multiprocessing.cpu_count()
    pool = Pool(n_jobs)
    args = []
    for picks_file in os.listdir(picks_dir):
        if picks_file.endswith('.xml') and "_manual" not in picks_file:
            picks_path = os.path.join(picks_dir, picks_file)
            change_xml_version(picks_path)
            manual_picks_path = automatic2manual(picks_path)
            args.append((manual_picks_path, locator_dict, output_dir))
    pool.map(picks2events_wrapper, args)

    # Merge all events files into one xml file
    final_events_file = os.path.join(output_dir, 'all_events.xml')
    merge_xml_picks(events_dir, final_events_file)

    change_xml_version(final_events_file)

