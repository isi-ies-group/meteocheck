# -*- coding: utf-8 -*-
"""
Created on Fri Jan 13 17:39:10 2017

@author: Ruben
"""
import configparser
from pathlib import Path
import datetime as dt
import os

import pandas as pd

# List of supported meteo stations.
# It affects 'open_meteo_file()' to automate file opening
SUPPORTED_STATIONS = ['helios', 'geonica', 'meteo']

config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes='#')

module_path = os.path.dirname(__file__)
config.read(str(Path(module_path, 'config_meteo_stations_ies.txt')))

UNIT = config.get('stations_configuration', 'UNIT')

DATA_PATH_HELIOS = Path(UNIT, config.get('stations_configuration', 'PATH_HELIOS'))
DATA_PATH_GEONICA = Path(UNIT, config.get('stations_configuration', 'PATH_GEONICA'))
DATA_PATH_METEO = Path(UNIT, config.get('stations_configuration', 'PATH_METEO'))

def open_meteo_file(date, type_data_station):
    """
    Tries to automatically open a meteo file of the supported meteo stations.
    Extended it to supported extra types.
    """
    if type_data_station == 'helios':
        file_name = 'data' + dt.datetime.strftime(date, '%Y_%m_%d') + '.txt'
    
        if date.year == dt.date.today().year:
            file_path = DATA_PATH_HELIOS.joinpath(Path(file_name))
        else:
            file_path = DATA_PATH_HELIOS.joinpath(
                Path('Data' + str(date.year), file_name))
        
        df = pd.read_csv(file_path, parse_dates=[
                              ['yyyy/mm/dd', 'hh:mm']], index_col=0, delimiter='\t')
        
        # only takes valuable variables
        df = df[['G(0)', 'G(41)', 'D(0)', 'B', 'Wvel', 'Wdir', 'Tamb']]
    
    elif type_data_station == 'geonica':
        file_name = 'geonica' +  dt.datetime.strftime(date, '%Y_%m_%d') + '.txt'
        
        if date.year == dt.date.today().year:
            file_path = DATA_PATH_GEONICA.joinpath(Path(file_name))
        else:
            file_path = DATA_PATH_GEONICA.joinpath(
                Path(str(date.year), file_name))

        df = pd.read_csv(file_path, parse_dates=[
                                  ['yyyy/mm/dd', 'hh:mm']], index_col=0, delimiter='\t')
                                  
    elif type_data_station == 'meteo':
        file_name = 'meteo' +  dt.datetime.strftime(date, '%Y_%m_%d') + '.txt'
        
        if date.year == dt.date.today().year:
            file_path = DATA_PATH_METEO.joinpath(Path(file_name))
        else:
            file_path = DATA_PATH_METEO.joinpath(
                Path(str(date.year), file_name))

        df = pd.read_csv(file_path, parse_dates=[0], index_col=0, delimiter='\t')
    
    return df, file_path