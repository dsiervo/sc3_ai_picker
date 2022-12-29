#!/home/daniel/anaconda3/envs/eqt/bin/python
# -*- coding: utf-8 -*-
"""
Created on Feb 19 2021

@author: Daniel Siervo, emetdan@gmail.com
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh # pip install streamlit-autorefresh
import mysql.connector
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from streamlit.file_util import streamlit_write
from cmcrameri import cm
from matplotlib.colors import Normalize
import base64
import time
from datetime import datetime, timedelta


def load_and_dashboard(ti, min_lat, max_lat, min_lon, max_lon):
    """Create streamlit dashboard where to explore the data
    from a seismic catalog in XML SC3 format

    Parameters
    ----------
    xml_path : str
        SeisComP events xml like file path.
    """
    
    # SETTING PAGE CONFIG TO WIDE MODE
    st.set_page_config(layout="wide", page_icon='🔞', page_title='Earthquake Explorer')
    st.title("Catalog Exploration (Montebello - Antioquia)")

    # update every 10 seconds
    st_autorefresh(interval= 5 * 60 * 1000, key="dataframerefresh")
    
    # get current date time in format YYYY-MM-DD hh:mm:ss
    now = datetime.now() + timedelta(hours=5)
    tf = now.strftime("%Y-%m-%d %H:%M:%S")
    # query events data
    csv_path = query_and_df(ti, tf, min_lat, max_lat, min_lon, max_lon)
    st.markdown(f"### Data showed from {ti} to {tf} UTC")

    print('\n\tCreando dashboard interactivo...')
    dashboard = Dashboard(csv_path, ti, tf)
    df = dashboard.load_data()
    print(df.info())
    dashboard.create_dashboard(df)


def query_and_df(ti, tf, min_lat, max_lat, min_lon, max_lon):
    mydb = mysql.connector.connect(host="begws142.beg.utexas.edu",
                                   user="stantonrw",
                                   passwd="writestnyes",
                                   database="stanton")

    query_str = '''
    SELECT 
    POEv.publicID AS 'ID',
    DATE_FORMAT(Origin.time_value, '%Y/%m/%d %H:%i:%S') AS 'orig_time', 
    Origin.latitude_value AS lat,
    Origin.longitude_value AS lon,
    ROUND(Origin.depth_value) AS z,
    ROUND(Magnitude.magnitude_value, 1) AS mag,
    Origin.creationInfo_author as 'author',
    Origin.quality_usedStationCount as 'stationcount',
    Origin.quality_usedPhaseCount as 'phasecount',
    Origin.latitude_uncertainty as 'lat_e',
    Origin.longitude_uncertainty as 'lon_e',
    Origin.depth_uncertainty as 'z_e',
    Origin.quality_minimumDistance as 'min_dis',
    Origin.quality_standardError as 'rms [s]',
    convert(cast(convert(EventDescription.text using latin1) as binary) using utf8) AS 'region'
    FROM  
    Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid
    left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID 
    left join Origin ON POOri._oid=Origin._oid
    left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID  
    left join Magnitude ON Magnitude._oid = POMag._oid 
    left join EventDescription ON EvMF._oid=EventDescription._parent_oid  
    WHERE  
    Origin.time_value BETWEEN '{ti}' AND '{tf}' 
    AND Origin.latitude_value BETWEEN {min_lat} AND {max_lat} AND Origin.longitude_value BETWEEN {min_lon} AND {max_lon}

    # =====================================================
    # localizables (descomentar/comentar la siguiente línea para solo localizables/no localizables
    # =====================================================
    #AND (EvMF.type like 'earthquake' or EvMF.type is null or EvMF.type like 'volcanic eruption'or AreaOfInfluence.area is not null) AND Magnitude.magnitude_value IS NOT null AND Origin.latitude_uncertainty IS NOT NULL AND Origin.longitude_uncertainty IS NOT NULL AND Origin.quality_azimuthalGap IS NOT NULL 
    # =====================================================
    # no localizables
    # =====================================================
    #and (EvMF.type like 'not locatable' or EvMF.type like 'explosion' or EvMF.type like 'earthquake' or EvMF.type is null or EvMF.type like 'volcanic eruption' or AreaOfInfluence.area is not null) 
    AND EvMF.type like 'earthquake'
    ORDER BY Origin.time_value
    '''
    
    query = query_str.format(ti=ti, tf=tf,
                             min_lat=min_lat, max_lat=max_lat,
                             min_lon=min_lon, max_lon=max_lon)

    print(query)
    df = pd.read_sql(query, con=mydb)
    print(df.info())

    #writting the dataframe to a csv file
    #csv_path = 'events_data.csv'
    #df.to_csv('events_data.csv', index=False)
    return df


class Dashboard(object):
    def __init__(self, df, ti, tf):
        self.df = df
        self.ti = ti
        self.tf = tf

    #@st.cache(persist=True)
    def load_data(self):
        # Loading data as a pandas DataFrame retriving only the columns of our interest
        #df = pd.read_csv(self.csv_path, index_col=0, parse_dates=[6])
        df = self.df
        df.sort_values(by='mag', ascending=False, inplace=True)
        df['mag_scale'] = 800 * (4 ** df.mag)
        df.rename(columns={'z':'depth [km]', 'mag':'magnitude', 'lat':'latitude', 'lon':'longitude',
                'phasecount':'phase count', 'stationcount':'station count',
                'z_e':'depth error [km]', 'lat_e':'latitude error [km]',
                'lon_e':'longitude error [km]', 'orig_time': 'date',
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

        """st.sidebar.header('Data filter')
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
            
        query = f'latitude >= {lat_range[0]} and latitude < {lat_range[1]} \
                and longitude >= {lon_range[0]} and longitude < {lon_range[1]}\
                and magnitude >= {mag_range[0]} and magnitude < {mag_range[1]}\
                and `depth [km]` >= {depth_range[0]} and `depth [km]` < {depth_range[1]}\
                and `rms [s]` >= {rms_range[0]} and `rms [s]` < {rms_range[1]}\
                and date >= "{date_min}" and date < "{date_max}"'

        df = df.query(query)"""
        
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
            df.sort_values(by='date', ascending=False, inplace=True)
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
                counts, bins = np.histogram(df[type_], bins=np.arange(int(df[type_].min()), int(df[type_].max()+1),0.5))
                bins = 0.5 * (bins[:-1] + bins[1:])
                fig = px.bar(x=bins, y=counts, labels={'x':type_, 'y':'Number of EQ'}, height=500)
                # Option-1:  using fig.update_yaxes()
                #fig.update_yaxes(visible=False, showticklabels=True)
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
        fig = px.bar(count_df, x='date', y=y_name, height=600,
                     range_x=[self.ti, self.tf])
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
            pass

        self.map(df, opacity, style)
    
    def map(self, data, opacity, style):
        # custom map
        cmap = cm.batlow_r
        data.sort_values(by='magnitude', ascending=False, inplace=True)
        # we need to normalize the depth in order to use
        # matplotlib cmap properly
        norm = Normalize(vmin=data['depth [km]'].min(), vmax=data['depth [km]'].max())
        data['norm'] = data['depth [km]'].apply(norm)

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
                get_radius='mag_scale',
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
    
    # streamlit run real_time_events_dashboard.py
    load_and_dashboard(min_lat=30.6, max_lat=34, min_lon=-103, max_lon=-101,
                    ti='2020-01-01 00:00:00')
        
