#!/home/siervod/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Nov 24 13:01:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
import os
import lxml.etree as ET
from matplotlib.pyplot import magnitude_spectrum
import numpy as np
import obspy as obs
from obspy import Catalog
import sys
import pandas as pd
import datetime
import mysql.connector
from obspy.geodetics import gps2dist_azimuth
from utils.in_or_out import is_inside_polygon
import obsplus

"""import click

@click.command()
@click.option('-i', "--xml_name", required=True, prompt=True, help='Input event type SeisComP xml file name')
@click.option('-o', "--output_fn", prompt=True, help='Output xml file name', default="origenes_preferidos.xml")"""


def origins_pruning(xml_name, output_fn='origenes_preferidos.xml',
                    check_db=False, quadrant="None", check_quality=True,
                    change_to_reported = False):
    """Delete all origins that are not the prefered origin
    in a seiscomp event xml file. Returns a xml with origins only

    Parameters
    ----------
    xml_name : str
        Name of events type SeisComP3 xml file.
    output_fn : str
        Name of output SeisComP3 xml file.
    """
    try:
        params = read_params()
        if "write_reported" in params:
            if params["write_reported"] in ["True", "true", "TRUE", "yes", "Yes", "YES"]:
                change_to_reported = True
    except FileNotFoundError:
        print("File ai_picker.inp not found, using change_to_reported = False")

    print('\n\nRemoving origins that are not the prefered one in the xml %s\n' % xml_name)
    try:
        change_xml_version(xml_name)
        cat = obs.read_events(xml_name, id_prefix='', format='SC3ML')
    except FileNotFoundError:
        print('\n\t No existe el archivo %s, se salta este proceso\n' % xml_name)
        sys.exit(1)

    # text file with the origins ids of the reported origins
    f_reported = open('reported_origins.txt', 'w')
    # automatic
    cat2 = Catalog()
    reported_cat = Catalog()
    # para acada evento en el xml de eventos
    for i, ev in enumerate(cat):
        magnitude = ev.preferred_magnitude().mag
        pref_orig = cat[i].preferred_origin()

        if check_quality and not pass_origin_quality(pref_orig, magnitude):
            # imprime en rojo que el evento no pasó el filtro de calidad
            print(
                f'\033[91m Evento {pref_orig.time} no pasó el filtro de calidad \033[0m')
            continue

        # Si check_db es True se verifica si el evento ya esta en la base de datos
        # en caso de que si devuelve True, se elimina el evento del xml
        if check_db in ("yes", "YES", "Yes", "true", "True", "TRUE") or quadrant != "None":
            watcher = Watcher(pref_orig)
            region = ev.event_descriptions[0].text.encode('utf-8')
            if check_db and watcher.exist_in_db():
                print(
                    f'\n\n\t El evento\033[91m {pref_orig.time} - {region}\033[0m ya existe en la base de datos, se elimina del xml\n\n')
                continue
            if quadrant != "None":
                if not watcher.check_in_region(quadrant):
                    print(f'region {region}')
                    print(
                        f'\n\n\t El evento\033[91m {pref_orig.time} : {pref_orig.latitude}, {pref_orig.longitude} : {region}\033[0m fuera del cuadrante {quadrant}, se elimina del xml\n\n')
                    continue
        
        # if the origin will be written as reported
        if change_to_reported:
            print('change to reported')
            # check if the quality meets the requirements for reported
            if pass_reported_quality(pref_orig):
                print(f'\n\tEl origen preferido del evento {pref_orig.time} cumple con los criterios para ser reportado\n')
                # if so, keep just the preferred origin, append it to the reported catalog
                del_append_pref_origins(cat[i], reported_cat)
                # adding a new line to the text file with the reported origin id
                f_reported.write(f'{pref_orig.resource_id.id}\n')
            else:
                print(f'\n\tEl origen preferido del evento {pref_orig.time} no cumple con los criterios para ser reportado\n')
                # if not, write it as automatic
                del_append_pref_origins(cat[i], cat2)
        else:
            del_append_pref_origins(cat[i], cat2)

    if change_to_reported:
        output_rep_fn = output_fn.replace('.xml', '_reported.xml')
        write_and_remove_id_prefix(reported_cat, output_rep_fn)
        # change xml version
        change_xml_version(output_rep_fn)
        change_status_and_eval_mode(output_rep_fn, status='reported', eval_mode='manual')

        # write the xml for automatic origins
        output_auto_fn = output_fn.replace('.xml', '_auto.xml')
        write_and_remove_id_prefix(cat2, output_auto_fn)
        # change xml version
        #change_xml_version(output_auto_fn)

        # merge the xmls
        merge_xmls(output_auto_fn, output_rep_fn, output_fn)
    
        f_reported.close()
    else:
        write_and_remove_id_prefix(cat2, output_fn)
        # change xml version
        #change_xml_version(output_fn)
    print('\n\tFiles with preferred origins to migrate to SeisComP3:\n\n\t  %s\n' % output_fn)


def merge_xmls(xml1, xml2, output_fn):
    """Merge two xmls into one using the seiscomp module scxmlmerge

    Parameters
    ----------
    xml1 : str
        Name of first xml file.
    xml2 : str
        Name of second xml file.
    output_fn : str
        Name of output xml file.
    """
    cmd = f'{os.environ["SEISCOMP_ROOT"]}/bin/seiscomp exec scxmlmerge {xml1} {xml2} > {output_fn}'
    print(cmd)
    os.system(cmd)


def del_append_pref_origins(event, new_cat):
    """Delete all origins that are not the prefered origin
    in a seiscomp event xml file. Returns a xml with origins only

    Parameters
    ----------
    event : obspy.core.event.event.Event
        Event to be written in the new xml.
    new_cat : obspy.core.event.catalog.Catalog
        Catalog where the event will be appended.
    output_fn : str
        Name of output SeisComP3 xml file.
    """
    del event.origins[:-1]
    new_cat.append(event)


def write_and_remove_id_prefix(cat, output_fn):
    cat.write(output_fn, format='SC3ML', validate=True, event_removal=True,
                    verbose=True)
    remove_id_prefix(output_fn)


def remove_id_prefix(xml_name):
    f = open(xml_name).read()
    new_content = f.replace('smi:local/', '')
    with open(xml_name, "w") as f:
        f.write(new_content)


def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file, encoding='utf-8').readlines()
    new_line = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith('<seiscomp xmlns='):
                line = new_line
            f.write(line)


def change_status_and_eval_mode(xml_path, status='reported', eval_mode='manual'):
    """
    Changes the evaluation mode and status of origins in an XML file.

    Parameters
    ----------
    xml_path : str
        The path to the XML file.
    status : str, optional
        The evaluation status to set. Default is 'reported'.
    eval_mode : str, optional
        The evaluation mode to set. Default is 'manual'.

    Returns
    -------
    None

    Notes
    -----
    This function modifies the input XML file in-place.
    """
    ns = {'seiscomp': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10'}
    tree = ET.parse(xml_path)
    root = tree.getroot()
    origins = root.findall('seiscomp:EventParameters/seiscomp:origin', ns)
    print(len(origins))
    for i, origin in enumerate(origins):
        print(i, origin)
        #evaluationMode = origin.find('seiscomp:evaluationMode', ns)
        #evaluationMode.text = 'manual'
        evaluationStatus = origin.find('seiscomp:evaluationStatus', ns)
        if evaluationStatus is None:
            evaluationStatus = ET.SubElement(origin, 'evaluationStatus')
        evaluationStatus.text = 'reported'
    tree.write(xml_path, pretty_print=True)  


def pass_reported_quality(origin):
    # check if the depth (m) is less than 20 km and lon, lat and depth (m) uncertainties are less than 20 km
    # if not, return False
    print(origin.depth, origin.longitude_errors.uncertainty, origin.latitude_errors.uncertainty, origin.depth_errors.uncertainty)
    # check that none of the values are None
    if any([x is None for x in [origin.depth, origin.longitude_errors.uncertainty, origin.latitude_errors.uncertainty, origin.depth_errors.uncertainty]]):
        return False
    if origin.depth > 20000 or origin.longitude_errors.uncertainty > 20 \
        or origin.latitude_errors.uncertainty > 20 or origin.depth_errors.uncertainty > 20000:
        return False
    # if azimuthal gap is greater than 270 return False
    if origin.quality.azimuthal_gap > 270:
        return False
    try:
        # if the number of used phases is less than 8 return False
        if origin.quality.used_phase_count < 8:
            return False
    except TypeError:
        return False
    return True


def pass_origin_quality(origin, magnitude):
    """Check if at least 2 stations have P and S phases picked, if not
    check if magnitude is greater than 2.5 and if has at least 12 P phases picked

    Parameters
    ----------
    origin : obspy.core.event.origin
        Origin to be checked
    magnitude : float
        Magnitude of the event
    Returns
    -------
    bool
        True if origin is good, False if not
    """
    # get arrivals in dataframe format
    arrivals = obsplus.arrivals_to_df(origin)
    try:
        # check if at least 2 stations have P and S phases picked (two phases picked)
        ps_count = arrivals.groupby(
            'station')['phase'].count().value_counts()[2]
    except KeyError:
        return False
    if ps_count < 2:
        # count P phases
        p_count = arrivals['phase'].value_counts()['P']
        if p_count > 12 and magnitude > 2.5:
            return True
        else:
            return False
    else:
        return True


class Watcher:
    origin: obs.core.event.Origin
    mydb = mysql.connector.connect(
        host="sc3primary.beg.utexas.edu",
        user="sysop",
        passwd="sysop",
        database="seiscomp3"
    )

    def __init__(self, origin):
        self.origin = origin

    @property
    def origin_time(self):
        return self.origin.time.datetime

    @property
    def main_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    @property
    def sql_path(self):
        return os.path.join(self.main_dir, 'latest_events.sql')

    @property
    def tf(self):
        # current time in UTC
        #return datetime.datetime.utcnow()
        # returning origin time + 2 minutes
        return self.origin_time + datetime.timedelta(minutes=2)


    @property
    def ti(self):
        # tf - 2 hours
        #return self.tf - datetime.timedelta(hours=2)
        # returning origin time - 2 minutes
        return self.origin_time - datetime.timedelta(minutes=2)

    @property
    def lat(self):
        return self.origin.latitude

    @property
    def lon(self):
        return self.origin.longitude

    @property
    def query(self):
        return open(self.sql_path).read().format(**{'ti': self.ti, 'tf': self.tf})

    @property
    def df(self):
        return pd.read_sql(self.query, self.mydb, parse_dates=['orig_time'])

    def exist_in_db(self):
        """Compare event time and geographic localization with events in seiscomp db
        Inspects events in the last 5 hours


        Returns
        -------
        bool
            True if event is in db, False if not
        """
        if self.check_time() and self.check_location():
            return True
        else:
            return False

    def check_time(self):
        """Check if event time is in db

        Returns
        -------
        bool
            True if event is in db, False if not
        """
        diff_sec = (self.df['orig_time']
                    - self.origin_time).abs().dt.total_seconds()

        return np.any(diff_sec < 60)

    def check_location(self):
        """Check if event location less than 50 km to an event in db

        Returns
        -------
        bool
            True if event is in db, False if not
        """
        # distance in meters between event and db events
        dist_m = self.df.apply(lambda row: gps2dist_azimuth(row['lat'], row['lon'],
                                                            self.lat, self.lon)[0], axis=1)
        # check if any distance is less than 50 km
        return np.any(dist_m < 50000)

    def check_in_quadrant(self, quadrant: tuple) -> bool:
        """Check if event location is in a quadrant

        Parameters
        ----------
        quadrant : Tuple
            Quadrant to check in format (lat_min, lat_max, lon_min,  lon_max)

        Returns
        -------
        bool
            True if event is in quadrant, False if not
        """
        assert len(quadrant) == 4, 'Quadrant must be a tuple with 4 elements'
        assert quadrant[0] < quadrant[1], 'The minimum latitude must be less than the maximum latitude'
        assert quadrant[2] < quadrant[3], 'The minimum longitude must be less than the maximum longitude'
        return (quadrant[0] <= self.lat <= quadrant[1]
                and quadrant[2] <= self.lon <= quadrant[3])

    def check_in_region(self, region):
        """Check if event location is in a region given.
        Could be a quadrant or a polygon

        Parameters
        ----------
        region : Tuple or str
            Region to check in format (lat_min, lat_max, lon_min,  lon_max) or the name of a
            bna file with the polygon
        """
        if isinstance(region, str):
            if region.split('.')[-1] == 'bna':
                try:
                    polygon = self.get_polygon(region)
                    return is_inside_polygon(polygon, (self.lon, self.lat))
                except FileNotFoundError:
                    print(f'\n\n\t {region} file not found\n\n')
                    raise ValueError('Debe proporcionar un cuadrante o un archivo bna')
            elif len(region.split(',')) == 4:
                quadrant = region.split(',')
                quadrant = tuple(map(float, quadrant))
                return self.check_in_quadrant(quadrant)
            else:
                raise ValueError('Debe proporcionar un cuadrante o un archivo bna')
        elif isinstance(region, tuple):
            return self.check_in_quadrant(region)
        else:
            raise ValueError('Debe proporcionar un cuadrante o un archivo bna')

    def get_polygon(self, region):
        """Get polygon from bna file

        Parameters
        ----------
        region : str
            Name of the bna file with the polygon

        Returns
        -------
        polygon : List
            List of points in the polygon
        """
        vmm = open(region, 'r').readlines()
        polygon1 = []
        for i in vmm:
            try:
                j = i.split(',')
                x = float(j[0])
                y = float(j[1])
                pvmm = (x, y)
                polygon1.append(pvmm)
            except:
                pass
        return polygon1


def read_params(par_file='ai_picker.inp'):
    lines = open(par_file, encoding='utf-8').readlines()
    par_dic = {}
    for line in lines:
        if line[0] == '#' or line.strip('\n').strip() == '':
            continue
        else:
            #print(line)
            l = line.strip('\n').strip()
            key, value = l.split('=')
            par_dic[key.strip()] = value.strip()
    return par_dic


if __name__ == "__main__":
    import sys

    assert len(sys.argv) >= 2, 'Insuficent arguments. Needs to provide the xml name or\
        the xml name and the name of the output file'

    if len(sys.argv) == 2:
        origins_pruning(sys.argv[1])
    elif len(sys.argv) == 3:
        #origins_pruning(sys.argv[1], sys.argv[2], quadrant=(31.5722,31.66405,-104.04678,-103.9269), check_db=False)
        origins_pruning(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        print('en cuadrante')
        origins_pruning(sys.argv[1], sys.argv[2], quadrant=sys.argv[3])
        
        # running scevent to create an event xml
        change_xml_version(sys.argv[2])
        scevent_cmd = 'scevent -u playback --ep %s  > %s'%(sys.argv[2], sys.argv[2].split('.')[0]+'_ev.xml')
        print(scevent_cmd)
        os.system(scevent_cmd)
    else:
        print('\n\tTo many arguments you need to provide the xml name \
            or the xml name and the name of the input file. Example:\n\
            \t\torigins_pruning.py events_final.xml\n\t or\n\
            \t\torigins_pruning.py events_final.xml only_prefered_origins.xml')
