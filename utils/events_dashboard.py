#!/home/seiscomp/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Feb 19 2021

@author: Daniel Siervo, emetdan@gmail.com
"""

import streamlit as st
import pandas as pd
import pandas_read_xml as pdx
import numpy as np
import plotly.express as px
import pydeck as pdk
from streamlit.file_util import streamlit_write
from cmcrameri import cm
from matplotlib.colors import Normalize
import base64
import os
from datetime import date, timedelta


def load_and_dashboard(xml_path):
    """Create streamlit dashboard where to explore the data
    from a seismic catalog in XML SC3 format

    Parameters
    ----------
    xml_path : str
        SeisComP events xml like file path.
    """

    # SETTING PAGE CONFIG TO WIDE MODE
    st.set_page_config(layout="wide", page_icon='🔞', page_title='Earthquake Explorer')
        
    events_sum = EventSumamry(xml_path)
    csv_path = events_sum.csv_path
    print('\n\tReading', csv_path)

    print('\n\tConvirtiendo xml a csv...')
    events_sum.load_prepare_data()
    
    print('\n\tCreando dashboard interactivo...')
    dashboard = Dashboard(csv_path)
    df = dashboard.load_data()
    dashboard.create_dashboard(df)


class EventSumamry(object):
    
    def __init__(self, xml_path):
        """Load the joined xml file and creates a dataframe with the
        summary of the events

        Parameters
        ----------
        main_xml_path : str
            Path to joined seiscomp events like xml
        """
        self.xml_path = xml_path
        self.csv_path = os.path.join(os.path.dirname(self.xml_path), 'all_events.csv')

    def get_mag(self, x, key):
        try:
            return float(x[0]['magnitude'][key])
        except TypeError:
            return -2
        except KeyError:
            print('It returned the dict instead of the list of dicts (get_mag)')
            return float(x['magnitude'][key])

    def get_mag_count(self, x):
        try:
            return int(x[0]['stationCount'])
        except TypeError:
            return -2
        except KeyError:
            print('It returned the dict instead of the list of dicts (get_mag_count)')
            return int(x['stationCount'])

    def get_from_dict(self, x, key, time=False):
        if not time:
            try:
                return float(x[key])
            except KeyError:
                return 'fixed'
        else:
            return x[key]

    def get_region_author(self, x, key):
        return x[key]

    def load_prepare_data(self):
        """
        Prepare dataframe with useful information from event xml

        Parameters
        ----------
        xml_name : str
            Name of seiscomp like event xml file

        Returns
        -------
        pandas.Dataframe
            Dataframe with useful information about events in the xml
        """
        # loading events dataframe
        df = pdx.read_xml(self.xml_path, ['seiscomp', 'EventParameters', 'event'])
        # loading origins dataframe
        df_or = pdx.read_xml(self.xml_path, ['seiscomp', 'EventParameters', 'origin'])

        # preparing events dataframe
        df['region'] = df['description'].apply(self.get_region_author, key='text')
        df['author'] = df['creationInfo'].apply(self.get_region_author, key='author')
        
        pref_cols = ['@publicID', 'preferredOriginID', 'author', 'region']
        if "type" in df.columns:
            pref_cols.append("type")
        df = df[pref_cols]

        # preparing origins dataframe
        df_or['lat'] = df_or['latitude'].apply(self.get_from_dict, key='value')
        df_or['lon'] = df_or['longitude'].apply(self.get_from_dict, key='value')
        df_or['z'] = df_or['depth'].apply(self.get_from_dict, key='value')
        df_or['orig_time'] = df_or['time'].apply(self.get_from_dict, key='value', time=True)
        df_or['orig_time'] = pd.to_datetime(df_or['orig_time'])

        df_or['lat_e'] = df_or['latitude'].apply(self.get_from_dict, key='uncertainty')
        df_or['lon_e'] = df_or['longitude'].apply(self.get_from_dict, key='uncertainty')
        df_or['z_e'] = df_or['depth'].apply(self.get_from_dict, key='uncertainty')
        df_or['t_e'] = df_or['quality'].apply(self.get_from_dict, key='standardError')

        df_or['min_dis'] = df_or['quality'].apply(self.get_from_dict, key='minimumDistance')
        df_or['phasecount'] = df_or['quality'].apply(self.get_from_dict, key='usedPhaseCount')
        df_or['stationcount'] = df_or['quality'].apply(self.get_from_dict, key='usedStationCount')

        df_or['mag'] = df_or['magnitude'].apply(self.get_mag, key='value')
        df_or['mag_e'] = df_or['magnitude'].apply(self.get_mag, key='uncertainty')
        df_or['mag_count'] = df_or['magnitude'].apply(self.get_mag_count)

        df_or = df_or[['@publicID', 'orig_time', 'mag', 'lat', 'lon', 'z',
                    'lat_e', 'lon_e', 'z_e', 'min_dis', 'phasecount',
                    'stationcount', 'mag_e', 't_e']]
        df_or.rename(columns={'@publicID': 'originID'}, inplace=True)

        # mergin the two dataframes
        df_merge = pd.merge(df, df_or, how='inner',
                            left_on='preferredOriginID',
                            right_on='originID')
        
        n = len(df_merge)
        print(f'\nGuarndando eventos ene el archivo {self.csv_path}\n')
        print(f'\n\n\tSe encontraron un total de {n} eventos\n')
        df_merge.to_csv(self.csv_path)


class Dashboard(object):
    def __init__(self, csv_path):
        self.csv_path = csv_path

    @st.cache(persist=False)
    def load_data(self):
        # Loading data as a pandas DataFrame retriving only the columns of our interest
        df = pd.read_csv(self.csv_path, index_col=0, parse_dates=[6])
        df.sort_values(by='mag', ascending=False, inplace=True)
        df['mag_scale'] = 800 * (2 ** df.mag)
        df.rename(columns={'z':'depth [km]', 'mag':'magnitude', 'lat':'latitude', 'lon':'longitude',
                'phasecount':'phase count', 'stationcount':'station count',
                'z_e':'depth error [km]', 'lat_e':'latitude error [km]',
                'lon_e':'longitude error [km]', 't_e':'rms [s]', 'orig_time': 'date',
                'min_dis':'minimum station distance [km]'}, inplace=True)
        df['date'] = df['date'].astype('datetime64[ns]')
        return df

    def get_table_download_link(self, df):
        """Generates a link allowing the data in a given panda dataframe to be downloaded
        in:  dataframe
        out: href string
        """
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
        href = f'<a href="data:file/csv;base64,{b64}" download="data.csv">Download csv file</a>'
        return href

    def create_dashboard(self, df):
        """Have the streamlit front code
        """
        
        st.title("Catalog Exploration")

        st.sidebar.header('Data filter')
        print('len(df)', len(df))
        filter_type = st.sidebar.radio('Filter type', ('slider', 'number input'))
        #st.sidebar.subheader("Magnitude")
        if filter_type == 'slider':
            mag_range = st.sidebar.slider("Magnitude range", -1.0, 10.0, (0.0, 7.0), 0.1)
        else:
            st.sidebar.markdown("### Magnitude")
            min_mag = st.sidebar.number_input('Minimun magnitude', value=-1.0, step=0.1)
            max_mag = st.sidebar.number_input('Maximun magnitude', value=10.0, step=0.1)
            mag_range = (min_mag, max_mag)
        #st.sidebar.markdown(f"Magnitude range: {mag_range}")
        
        #st.sidebar.subheader("Latitude")
        lat_min, lat_max = float(df.latitude.min()), float(df.latitude.max())
        if filter_type == 'slider':
            lat_range = st.sidebar.slider("Latitude range", lat_min, lat_max, (lat_min, lat_max), 0.1)
        else:
            st.sidebar.markdown("### Latitude")
            min_lat = st.sidebar.number_input('Minimun latitude', value=lat_min, step=0.01)
            max_lat = st.sidebar.number_input('Maximun latitude', value=lat_max, step=0.01)
            lat_range = (min_lat, max_lat)

        lon_min, lon_max = float(df.longitude.min()), float(df.longitude.max())
        if filter_type == 'slider':
            lon_range = st.sidebar.slider("Longitude range", lon_min, lon_max, (lon_min, lon_max), 0.1)
        else:
            st.sidebar.markdown("### Longitude")
            min_lon = st.sidebar.number_input('Minimun Longitude', value=lon_min, step=0.01)
            max_lon = st.sidebar.number_input('Maximun Longitude', value=lon_max, step=0.01)
            lon_range = (min_lon, max_lon)

        depth_min, depth_max = float(df['depth [km]'].min()), float(df['depth [km]'].max())
        if filter_type == 'slider':
            depth_range = st.sidebar.slider("Depth range [km]", depth_min, depth_max, (depth_min, depth_max), 0.1)
        else:
            st.sidebar.markdown("### Depth")
            min_depth = st.sidebar.number_input('Minimun Depth', value=depth_min, step=0.01)
            max_depth = st.sidebar.number_input('Maximun Depth', value=depth_max, step=0.01)
            depth_range = (min_depth, max_depth)

        rms_min, rms_max = float(df['rms [s]'].min()), float(df['rms [s]'].max())
        if filter_type == 'slider':
            rms_range = st.sidebar.slider("RMS range [s]", rms_min, rms_max, (rms_min, rms_max), 0.1)
        else:
            st.sidebar.markdown("### RMS")
            min_rms = st.sidebar.number_input('Minimun RMS', value=rms_min, step=0.01)
            max_rms = st.sidebar.number_input('Maximun RMS', value=rms_max, step=0.01)
            rms_range = (min_rms, max_rms)

        min_date, max_date = df['date'].min().to_pydatetime(), df['date'].max().to_pydatetime()
        min_date, max_date = min_date.replace(hour=0, minute=0, second=0), max_date.replace(hour=23, minute=59, second=59)
        dt = timedelta(days=1)
        if filter_type == 'slider':
            date_min, date_max = st.sidebar.slider("Date range", df['date'].min(), df['date'].max(),
                                                   (min_date, max_date), dt)
            date_min, date_max = date_min - dt, date_max - dt
        else:
            st.sidebar.markdown("### Date")
            date_min, date_max = st.sidebar.date_input('Date range', [min_date, max_date],
                                                       min_value=df['date'].min(),
                                                       max_value=df['date'].max())
            
        query = f'latitude >= {lat_range[0] - 1} and latitude < {lat_range[1] + 2} \
                and longitude >= {lon_range[0] - 1} and longitude < {lon_range[1]+ 2}\
                and magnitude >= {mag_range[0] - 1} and magnitude < {mag_range[1]+ 2}\
                and `depth [km]` >= {depth_range[0] - 1} and `depth [km]` < {depth_range[1]+ 2}\
                and `rms [s]` >= {rms_range[0] - 1} and `rms [s]` < {rms_range[1]+ 2}\
                and date >= "{date_min}" and date < "{date_max}"'

        df = df.query(query)
        print('len(df) after query:', len(df))
        
        show_table = st.checkbox("Show raw data", True)
        if show_table:
            col_list = [col for col in df.columns.to_list() if col not in ['mag_scale',
                                                                           'author',
                                                                           'originID']]
            columns = st.multiselect(
                'Columns to show:',
                col_list,
                col_list
            )
            styler = df[columns].style.format(
                        {
                            'date': lambda x: x.strftime("%d-%m-%Y %H:%M:%S")
                        }).set_table_styles('styles')
            st.dataframe(styler)
            downlad_link = self.get_table_download_link(df[columns])
            st.markdown(downlad_link, unsafe_allow_html=True)
        
        st.markdown(f"Selected earthquakes: **{len(df)}**.")
        
        st.header('Graphics')
        st.subheader('Number of Earthquakes by ...')
        col1, col2, col3 = st.beta_columns(3)
        for col, type_ in zip([col1, col2, col3],
                             ['magnitude', 'rms [s]', 'depth [km]']):
            with col:
                print(type_)
                bins = range(int(df[type_].min()), int(df[type_].max()+1))
                print(list(bins))
                if len(bins) == 1:
                    bins = range(0, 2)
                counts, bins = np.histogram(df[type_], bins=bins)
                bins = 0.5 * (bins[:-1] + bins[1:])

                fig = px.bar(x=bins, y=counts, labels={'x': type_, 'y': 'Number of EQ'}, height=500)
                # Option-1:  using fig.update_yaxes()
                fig.update_yaxes(visible=False, showticklabels=True)
                st.plotly_chart(fig, use_container_width=True)
        
        # date histogram
        colt1, colt2 = st.beta_columns(2)
        with colt1:
            trange = st.selectbox('Time range',
                                  ['days', 'weeks', 'months', 'years'])
        with colt2:
            pass

        y_name = f'Earthquakes by {trange}'
        count = df['date'].groupby([df['date'].dt.to_period(f'1{trange[0]}')]).count()
        count_df = pd.DataFrame({'date':count.index, y_name:count.values})
        count_df['date'] = count_df['date'].astype('str')
        fig = px.bar(count_df, x='date', y=y_name, height=600)
        st.plotly_chart(fig, use_container_width=True)

        st.header('Depth Profiles')
        cold1, cold2 = st.beta_columns(2)
        df['depth [km]'] = -1 * df['depth [km]']
        with cold1:
            fig = px.scatter(df, x="latitude", y="depth [km]", 
                            size='mag_scale', color="rms [s]", hover_name="date")
            st.plotly_chart(fig, use_container_width=True)
        with cold2:
            fig = px.scatter(df, x="longitude", y="depth [km]", 
                            size='mag_scale', color="rms [s]", hover_name="date")
            st.plotly_chart(fig, use_container_width=True)
        df['depth [km]'] = -1 * df['depth [km]']

        st.header('Map')
        colm1, colm2 = st.beta_columns(2)
        with colm1:
            style = st.selectbox('Style', ['outdoors-v11', 'streets-v11',
                                           'light-v9', 'light-v10',
                                           'dark-v10', 'satellite-v9',
                                           'satellite-streets-v11'])
            opacity = st.slider('Color opacity', 0.0, 1.0, value=0.6)
        with colm2:
            mag_scale = st.slider('Magnitude scale', 1.0, 5.0, value=2.0)
            pass

        self.map(df, opacity, style, mag_scale)
    
    def map(self, data, opacity, style, mag_scale):
        # custom map
        cmap = cm.batlow_r

        # we need to normalize the depth in order to use
        # matplotlib cmap properly
        norm = Normalize(vmin=0, vmax=300)
        data['norm'] = data['depth [km]'].apply(norm)

        # magnitude scale for the map
        data['mag_scale2'] = 800 * (mag_scale ** data.magnitude)

        def get_color(depth_norm):
            # cmap returns a tuple of normalized rgba elements
            # we desnormalize and keep with the first three (rgb)
            c = cmap(depth_norm)
            return [x*255 for x in c][:-1]

        data['color'] = data['norm'].apply(get_color)

        data['dates_str'] = data['date'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
        data['magnitude'] = data['magnitude'].round(1)
        data['depth [km]'] = data['depth [km]'].round(1)
        data['latitude_str'] = data['latitude'].round(2)
        data['longitude_str'] = data['longitude'].round(2)

        layers = [
            pdk.Layer(
                'ScatterplotLayer',
                data=data,
                pickable=True,
                stroked=True,
                opacity=opacity,
                get_position='[longitude, latitude]',
                get_radius='mag_scale2',
                get_fill_color='color',
                get_line_color=[0, 0, 0],
                line_width_min_pixels=0.3
            )
        ]

        r = pdk.Deck(
            tooltip={"text": "{latitude_str}, {longitude_str} \n {dates_str}\n Magnitude: {magnitude}\n Depth: {depth [km]} km"},
            map_style=f'mapbox://styles/mapbox/{style}',
            initial_view_state=pdk.ViewState(
                latitude=data['latitude'].median(),
                longitude=data['longitude'].median(),
                zoom=7,
                pitch=0,
            ),
            layers=layers
        )
        st.pydeck_chart(r, use_container_width=True)


if __name__ == '__main__':
    import sys
    
    load_and_dashboard(sys.argv[1])
