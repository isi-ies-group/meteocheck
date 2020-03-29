# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 15:42:46 2016

@author: ruben
"""
import datetime as dt

import pandas as pd
import numpy as np
from numpy import sin, cos, pi, arccos, radians

from meteocheck.settings import (DRADIATION_DT, LENGTH_VALLEY, DEPTH_VALLEY_MIN,
                                 DEPTH_VALLEY_MAX)

def solpos(time, latitude=40.45, longitude=-3.73, timezone=+1):
    """
    Returns azimuth and zenith angles (radians ) of the solar position for a given location.

    Parameters
    ----------
    time : pandas.Index.DatetimeIndex o pandas.tslib.Timestamp (1 isntant) civil time
        List of instants
    latitude : float, default=40.45 (Madrid)
        Latitude of the location in decimal degrees and with sign
    longitude : float, default=-3.73 (Madrid)
        Longitude of the location in decimal degrees and with sign
    timezone : integer, default=+1 (Madrid)
        Timezone respect UTC
    Returns
    -------
    az : numpy.array
        List of azimuth angles (radians)
    zz : numpy.array
        List of zenith angles (radians)

    See Also
    --------

    Examples
    --------
    >>> import pandas as pd

    >>> time = pd.date_range(start='2014/01/01', end='2014/05/01', freq='1H')
    >>> az, zz = solpos(time, latitude=40.45, longitude=-3.73)
    """

    # If a single element is received, it will be converted to array
    if isinstance(time, pd.tslib.Timestamp):
        time = pd.DatetimeIndex([time])
        
    def time_from_moment(moment):
        return np.array([mom.hour + mom.minute/60 + mom.second/3600 for mom in moment.time])
    
    def equation_time(moment):
        return -7.64 * sin(radians(moment.dayofyear - 2)) + 9.86 * sin(radians(2 * (moment.dayofyear - 80)))
        
    def solar_time_radians(moment):
        hora = time_from_moment(moment)
        
        DT = is_dst(moment) # Daylight Saving Time
        ET = equation_time(moment) / 60
        
        apparent_solar_time = hora - DT + ET - (timezone - longitude / 15)
        
        return (apparent_solar_time - 12) * (2 * pi / 24)
        
    def declination(moment):
        return radians(23.45) * sin(2 * pi * (moment.dayofyear + 284) / 365)
        
    def zenith(moment):
        return arccos(cos(declination(moment)) * cos(solar_time_radians(moment)) * cos(radians(latitude)) + sin(declination(moment)) * sin(radians(latitude)))
    
    def azimuth(moment):
        ang_azimuth = arccos((cos(zenith(moment)) * sin(radians(latitude)) - sin(declination(moment))) / (sin(zenith(moment)) * cos(radians(latitude))))

        mom_inc_zz = np.diff(zenith(moment)) > 0
        mom_inc_zz = np.append(mom_inc_zz, mom_inc_zz[-1])

        ang_azimuth[mom_inc_zz] *= -1 # reverses the sign of those moments when zz is increasing. It means that az should be not changing trend
        
        return ang_azimuth
    
    az, zz = azimuth(time), zenith(time)
    
    if len(az) == 1:
        az = az[0]
    
    if len(zz) == 1:
        zz = zz[0]
    
    return az, zz

def is_dst(time):

    delta = np.array([], dtype=bool)
    
    for year in np.unique(time.year):
    
        day_change_time_march = dt.date(year, 3, 31) - dt.timedelta(days=dt.date(year, 3, 31).isoweekday())
        day_change_time_october = dt.date(year, 10, 31) - dt.timedelta(days=dt.date(year, 10, 31).isoweekday())
            # isoweekday() Return the day of the week as an integer, where Monday is 1 and Sunday is 7
        
        time_year = time[time.year == year]
        dst_period = ((time_year.date >= day_change_time_march) & (time_year.date <= day_change_time_october))
        
        delta_year = np.zeros(len(time_year), dtype=bool)
        delta_year[dst_period] = True
                
        delta = np.append(delta, delta_year)
    
    return delta


def change_datetimeindex(data_series, mode, winter_delta, summer_delta):
    """
    Converts UTC <-> civil time (accounts for DST) as per 'mode'
    """
    delta_dst = is_dst(data_series.index)

    if mode == 'utc->civil':
        time_changed_summer = data_series[delta_dst].index + dt.timedelta(hours=summer_delta)
        time_changed_winter = data_series[~delta_dst].index + dt.timedelta(hours=winter_delta)
    elif mode == 'civil->utc':
        time_changed_summer = data_series[delta_dst].index - dt.timedelta(hours=summer_delta)
        time_changed_winter = data_series[~delta_dst].index - dt.timedelta(hours=winter_delta)
    else:
        raise ValueError("Set correct mode: 'utc->civil' or 'civil->utc'")
    
    data_series.index = pd.Index(np.concatenate([time_changed_summer, time_changed_winter])).sort_values()
    
    return data_series


def num_radiation_transitions(data_series, dradiation_dt=DRADIATION_DT):
    
    if len(data_series) < 2:
        return 0

    d_radiation = data_series.diff()
    d_radiation[0] = d_radiation[1]

    return len(d_radiation[d_radiation > dradiation_dt])


def daily_irradiation(series, samples_per_hour):

    return np.trapz(series, dx=(1 / samples_per_hour)) / 1000 # [kWh]


def valleys_radiation(dni_series, dratiation_dt=DRADIATION_DT,
                      length_valley_pattern=LENGTH_VALLEY,
                      depth_valley_min=DEPTH_VALLEY_MIN,
                      depth_valley_max=DEPTH_VALLEY_MAX):
    
    lista_delta = dni_series.diff().shift(-1)
    lista_delta[-1] = lista_delta[-2]
    
    in_valley = False
    moments_misalign = []
    moments_valley = []
    num_valleys_misalign = 0
    
    for moment in dni_series.index:
        if abs(lista_delta[moment]) <= dratiation_dt: # flat zone
            in_valley = False
            
        elif not in_valley: # a valley starts
            if lista_delta[moment] <= -dratiation_dt:
                in_valley = True
                
                moments_valley.append(moment)
        else: # inside a valley
            moments_valley.append(moment)
    
        if in_valley == False and moments_valley: # a valley ends
            moments_valley.append(moment)
            
            energy_valley_actual = dni_series[moments_valley].sum()
            energy_valley_ideal = dni_series[moments_valley[0]] * len(moments_valley)
            
            depth_valley = energy_valley_actual / energy_valley_ideal
            
            is_closed = abs(dni_series[moments_valley[0]] - dni_series[moments_valley[-1]]) < 3 * dratiation_dt
            
            if (len(moments_valley) in length_valley_pattern and 
                (depth_valley_min < depth_valley < depth_valley_max) and 
                is_closed):
                moments_misalign.extend(moments_valley)
                num_valleys_misalign += 1
            
            moments_valley = []

    return num_valleys_misalign, moments_misalign

def dew_at_morning(df, label_temp, label_dni):
    df[label_temp].loc[0]
