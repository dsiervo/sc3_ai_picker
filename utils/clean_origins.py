import obspy as obs
import sys
import os


def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file, encoding='utf-8').readlines()
    new_line = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith('<seiscomp xmlns='):
                line = new_line
            f.write(line)


def keep_just_preferd_orgin(event_xml_file):
    cat = obs.read_events(event_xml_file, id_prefix='', format='SC3ML')
    for event in cat:
        event.preferred_origin_id = event.origins[0].resource_id
        event.origins = [event.origins[0]]

    # write events with only preferred origins
    cat.write(event_xml_file, format='SC3ML', event_removal=False)
    # write only the preferred origins only
    origins_xml_path = os.path.join(os.path.dirname(event_xml_file), 'origenes_preferidos.xml')
    cat.write(origins_xml_path, format='SC3ML', event_removal=True)


if __name__ == '__main__':
    event_xml_file = sys.argv[1]
    change_xml_version(event_xml_file)
    keep_just_preferd_orgin(event_xml_file)