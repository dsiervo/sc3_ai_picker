#!/home/dsiervo/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Nov 24 13:01:33 2020

@author: Daniel Siervo, emetdan@gmail.com
"""
import os
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
                    check_db=False, quadrant="None"):
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

    cat2 = Catalog()
    # para acada evento en el xml de eventos
    for i, ev in enumerate(cat):
        magnitude = ev.preferred_magnitude().mag
        pref_orig = cat[i].preferred_origin()

        if not pass_origin_quality(pref_orig, magnitude):
            # imprime en rojo que el evento no pasó el filtro de calidad
            print(
                f'\033[91m Evento {pref_orig.time} no pasó el filtro de calidad \033[0m')
            continue

        # Si check_db es True se verifica si el evento ya esta en la base de datos
        # en caso de que si devuelve True, se elimina el evento del xml
        if check_db or quadrant != "None":
            watcher = Watcher(pref_orig)
            region = ev.event_descriptions[0].text.encode('utf-8')
            if check_db and watcher.exist_in_db():
                print(
                    f'\n\n\t El evento\033[91m {pref_orig.time} - {region}\033[0m ya existe en la base de datos, se elimina del xml\n\n')
                continue
            if quadrant != "None" and not watcher.check_in_region(quadrant):
                print(f'region {region}')
                print(
                    f'\n\n\t El evento\033[91m {pref_orig.time} : {pref_orig.latitude}, {pref_orig.longitude} : {region}\033[0m fuera del cuadrante {quadrant}, se elimina del xml\n\n')
                continue

        del cat[i].origins[:-1]
        cat2.append(cat[i])

    # se escribe xml con solo los orígenes preferidos
    cat2.write(output_fn, format='SC3ML', validate=True, event_removal=True,
               verbose=True)

    remove_id_prefix(output_fn)

    print('\n\tArchivo con origenes preferidos para migrar a SeisComP3:\n\n\t  %s\n' % output_fn)


def remove_id_prefix(xml_name):
    f = open(xml_name).read()
    new_content = f.replace('smi:local/', '')
    with open(xml_name, "w") as f:
        f.write(new_content)


def change_xml_version(ev_file='events_final.xml'):
    lines = open(ev_file, encoding='utf-8').readlines()
    lines[1] = '<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">\n'
    with open(ev_file, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))


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
        host="10.100.100.232",
        user="consulta",
        passwd="consulta",
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
        return datetime.datetime.now() + datetime.timedelta(hours=5)

    @property
    def ti(self):
        # tf - 2 hours
        return self.tf - datetime.timedelta(hours=2)

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

    def check_in_quadrant(self, quadrant):
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

        if region.split('.')[-1] == 'bna':
            polygon = self.get_polygon(region)
            return is_inside_polygon(polygon, (self.lon, self.lat))
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


if __name__ == "__main__":
    import sys

    assert len(sys.argv) >= 2, 'Insuficent arguments. Needs to provide the xml name or\
        the xml name and the name of the output file'

    if len(sys.argv) == 2:
        origins_pruning(sys.argv[1], check_db=True)
    elif len(sys.argv) == 3:
        origins_pruning(sys.argv[1], sys.argv[2], check_db=True)
    elif len(sys.argv) == 4:
        print('en cuadrante')
        origins_pruning(sys.argv[1], sys.argv[2],
                        check_db=False, quadrant='zonavmm_border.bna')
    else:
        print('\n\tTo many arguments you need to provide the xml name \
            or the xml name and the name of the input file. Example:\n\
            \t\torigins_pruning.py events_final.xml\n\t or\n\
            \t\torigins_pruning.py events_final.xml only_prefered_origins.xml')
