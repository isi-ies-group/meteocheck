# -*- coding: utf-8 -*-
"""
Created on Fri Sep  2 10:35:37 2016

@author: ruben
"""
import io
import datetime as dt
import os
from pathlib import Path
import inspect

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#from meteocheck.solar_functions import (solpos, num_radiation_transitions,
#                                        daily_irradiation)
import meteocheck.solar_functions as mc_solar
import meteocheck.config_meteo_stations as mc_meteo
import meteocheck.config_email as mc_email
from meteocheck.settings import (MINIMUM_ERROR_LEVEL_TO_SEND_EMAIL, FILENAME_SESSION_LOG,
                                 FILENAME_HISTORY_LOG, NUM_RADIATION_TRANSITIONS_THRESHOLD,
                                 DNI_RADIATION_THRESHOLD, GHI_RADIATION_THRESHOLD,
                                 DAILY_IRRADIATION_THRESHOLD, DRADIATION_DT,
                                 NUM_VALLEYS_THRESHOLD)

#%% Log object
log = pd.DataFrame(
    columns=[
        'time_stamp',
        'error_level',
        'type_data_station',
        'check_type',
        'error_message',
        'file',
        'figure'])


def add_line_log(error_level,
        check_type=None,
        error_message=None,
        type_data_station=None,
        file_path=None,
        figure=None):
    """
    Adds a line incidence to log file.

    Parameters
    ----------
    error_level : String
        label that defines the level of error: ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    check_type : String
        label that describes the type of check that originated the error
    error_message : String
        Text describing the error
    type_data_station : String
        Text describing the data station:
            - 'helios'
            - 'geonica'
            - User defined. Requires a pandas.Dataframe previously read/created.
    file_path : Path
        Path of the analyzed file
    figure : plt.figure()
        MPL's figure describing the error

    Returns
    -------
    None
    """
    new_line = pd.Series({'time_stamp': pd.Timestamp.now().strftime('%Y-%m-%d %X.%f')[:-5],
                          'error_level': error_level,
                          'type_data_station': str(type_data_station),
                          'check_type': check_type,
                          'error_message': error_message,
                          'file': file_path,
                          'figure': figure})

    global log
    log = log.append(new_line, ignore_index=True)

    # sets 'Catergorial' type so it can be ordered
    '''
    log['error_level'] = log['error_level'].astype(
        'category',
        categories=[
            'INFO',
            'WARNING',
            'ERROR',
            'CRITICAL'],
        ordered=True)
    '''
    
    log['error_level'] = pd.Categorical(log['error_level'],
                            categories=[
                                'INFO',
                                'WARNING',
                                'ERROR',
                                'CRITICAL'],
                            ordered=True)
    
    print(new_line.to_frame())


def finish_log():
    global log

    pd.set_option('display.max_colwidth', 1000)

    add_line_log('INFO', error_message='Finishing logging session')

    if (log.error_level >= MINIMUM_ERROR_LEVEL_TO_SEND_EMAIL).any() and mc_email.IS_SENDING_EMAIL:
        date_yesterday = (
            dt.datetime.now() -
            dt.timedelta(
                days=1)).strftime('%Y-%m-%d')

        mc_email.send_email(
            body=log.to_html(),
            subject='Failure in meteo station : {}'.format(date_yesterday),
            list_figures=log.figure.iteritems())

        add_line_log('INFO', error_message='E-mail sent to: {}'.format(mc_email.RECIPIENTS_EMAIL))
    else:
        add_line_log('INFO', error_message='E-mail not sent')
    
    if (log.error_level == 'INFO').all():
        print('\n>> ALL THE LOG ISSUES ARE INFORMATIONAL - NO WARNING EMAIL SHOULD BE SENT')

    module_path = os.path.dirname(__file__)

    log.to_csv(str(Path(module_path, FILENAME_SESSION_LOG)), sep='\t', index=False, header=False, mode='w')
    log.to_csv(str(Path(module_path, FILENAME_HISTORY_LOG)), sep='\t', index=False, header=False, mode='a')
    
    log.to_html('Z:/log_meteocheck.html')
    
    pd.reset_option('display.max_colwidth')


class Checking:

    def __init__(self, type_data_station=None, date=None, df=None):
        self.type_data_station = type_data_station
        self.date = date
        self.df = df
        
        # Time resolution of data timeseries in samples per hour
        # Defaults None, so it should be initialized by user at module use
        self.samples_per_hour = None
        
        self.file_path = None
        
        if self.type_data_station is None:
            add_line_log('CRITICAL', error_message='Undefined type of meteo station', type_data_station=self.type_data_station)
            finish_log()
            raise ValueError("The 'type_data_station' parameter is mandatory")

        add_line_log('INFO', error_message="Analyzing meteo data of type '{}' from {}".format(self.type_data_station, self.date), type_data_station=self.type_data_station)

        # Checks if 'type_data_station' is supported and then opens with the corresponding function
        if self.type_data_station in mc_meteo.SUPPORTED_STATIONS:
            try:
                add_line_log('INFO', error_message='Opening file...', type_data_station=self.type_data_station, file_path=self.file_path)
                
                self.df, self.file_path = mc_meteo.open_meteo_file(self.date, self.type_data_station)
    
            except OSError as e:
                add_line_log('CRITICAL', error_message=e, type_data_station=self.type_data_station, file_path=self.file_path)
                finish_log()
                raise OSError('The file of type={} of {} cannot be opened'.format(self.type_data_station, self.date), self.file_path)
        # open_meteo_file() fills self.df If it was not read or supported, is an error!
        elif self.df is None or not isinstance(self.df, pd.DataFrame):
            add_line_log('CRITICAL', error_message='No dataframe given for unsupported type of meteo station', type_data_station=self.type_data_station)
            finish_log()
            raise ValueError("The 'type_data_station'='{}' is not supported, therefore a "
                             "Pandas 'df' with meteo data is mandatory".format(self.type_data_station))
        # 'self.samples_per_hour' should be obtained for some assertions.
        # If the infer process throws an Exception, is an error!
        try:
            freq_df = pd.Timedelta(pd.tseries.frequencies.to_offset(pd.infer_freq(self.df.index)))
            self.samples_per_hour = pd.Timedelta('1H') / freq_df
        except:
            add_line_log('CRITICAL', error_message="The 'Samples per hour' of the 'df' cannot be infered", type_data_station=self.type_data_station)
            finish_log() 
            raise ValueError("The 'Samples per hour' of the 'df' cannot be infered")
        # If the infer process return 'None', is an error!
        if self.samples_per_hour is None:
            add_line_log('CRITICAL', error_message="The 'Samples per hour' of the 'df' cannot be infered", type_data_station=self.type_data_station)
            finish_log() 
            raise ValueError("The 'Samples per hour' of the 'df' cannot be infered")


    def assertion_base(
            self,
            condition,
            error_message,
            check_type=None,
            error_level='WARNING',
            figure=None):
        try:
            assert condition, error_message
        except AssertionError:
            add_line_log(
                error_level=error_level,
                check_type=check_type,
                error_message=error_message,
                type_data_station=self.type_data_station,
                file_path=self.file_path,
                figure=figure)

    def check_total_irradiation(self, column, total_irradiation_threshold):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        irradiation = mc_solar.daily_irradiation(
            self.df[column], samples_per_hour=self.samples_per_hour)

        self.assertion_base(
            condition=irradiation < total_irradiation_threshold,
            error_message='Total irradiation (daily) from "' +
            column +
            '" is {:.2f}. '.format(irradiation) +
            'This is higher than the threshold: ' +
            str(total_irradiation_threshold),
            check_type=name_check_function)

    def check_format(self, num_columns):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        num_moments = self.samples_per_hour * 24

        # Check dimensions
        condition_shape = (self.df.shape == (num_moments, num_columns))
        error_message_shape = 'Wrong dimensions: ' + \
            str(self.df.shape) + '. It should be: ' + str((num_moments, num_columns))

        self.assertion_base(
            condition=condition_shape,
            error_message=error_message_shape,
            check_type=name_check_function,
            error_level='ERROR')

        # Check columns are numerical (np.float64)
        for column in self.df.columns:
            self.assertion_base(
                condition=self.df.dtypes[column] == np.float64,
                error_message='Column "' +
                column +
                '" is not numerical [np.float64]',
                check_type=name_check_function,
                error_level='ERROR')

    def check_time_index(self):
        # Check index duplicated
    
        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        error_message_index_unique = 'Index not unique. Duplicates: ' + \
            str(self.df.index[self.df.index.duplicated()])

        self.assertion_base(
            condition=self.df.index.is_unique,
            error_message=error_message_index_unique,
            check_type=name_check_function,)

        # Check index monotonic increasing
        self.assertion_base(
            condition=self.df.index.is_monotonic_increasing,
            error_message='Index not monotonic',
            check_type=name_check_function,
            error_level='ERROR')

        # Check index all dates
        self.assertion_base(
            condition=self.df.index.is_all_dates,
            error_message='Index is not all dates',
            check_type=name_check_function,
            error_level='ERROR')

    def check_null(self, column):
        # Check content of NaN's
        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        self.assertion_base(
            condition=self.df[column].notnull().all(),
            error_message='Column "' +
            column +
            '" has some NaN values: ' +
            str(
                self.df[
                    self.df[column].isnull()].index),
            check_type=name_check_function,)

    def check_range(self, column, minimum, maximum):
        
        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        condition_list = self.df[column].dropna().between(minimum, maximum)

        buffer = None
        if not condition_list.all():
            plt.figure()
            self.df[column].plot(style='.')
            self.df[column][~condition_list].plot(style='rP')
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        # Check columns range
        self.assertion_base(
            condition=condition_list.all(),
            error_message='Column "' +
            column +
            '" is not in range [' +
            str(minimum) +
            ', ' +
            str(maximum) +
            ']',
            check_type=name_check_function,
            figure=buffer)

    def check_pct_change(self, column, window, threshold_pct):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        # Check percentage change in a window
        pct_change = self.df[column].pct_change(window).abs() * 100

        # fills NA values, including those generated at the begining by the
        # method 'pct_change' to avoid false values
        condition_list = pct_change.fillna(method='bfill') < threshold_pct

        buffer = None
        if not condition_list.all():
            plt.figure()
            self.df[column].plot(style='.')
            self.df[column][~condition_list].plot(style='rP')
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        self.assertion_base(
            condition=(condition_list).all(),
            error_message='Percent change [%] of column ' +
            column +
            ' is not in window of ' +
            str(window) +
            ' samples and threshold ' +
            str(threshold_pct) +
            '%. List of values: ' +
            (
                self.df[column][
                    ~condition_list]).to_string().replace(
                '\n',
                ' - '),
            check_type=name_check_function,
            figure=buffer)

    def check_abs_change(self, column, window, threshold):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        # Check absolute change in a window
        rolling = self.df[column].rolling(window)

        # fills NA values, including those generated at the begining by the
        # method 'rolling' to avoid false values
        condition_list = (
            rolling.max() -
            rolling.min()).fillna(
            method='bfill') < threshold

        buffer = None
        if not condition_list.all():
            plt.figure()
            self.df[column].plot(style='.')
            self.df[column][~condition_list].plot(style='rP')
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        self.assertion_base(
            condition=(condition_list).all(),
            error_message='Absolute change of column ' +
            column +
            ' is not in window of ' +
            str(window) +
            ' samples and threshold ' +
            str(threshold) +
            '. List of values: ' +
            (
                self.df[column][
                    ~condition_list]).to_string().replace(
                '\n',
                ' - '),
            check_type=name_check_function,
            figure=buffer)

    def check_differential(self, column, threshold):
        # Check diff between 2 samples

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        differential = self.df[column].diff()
        differential[0] = differential[1]

        condition_list = differential.abs() < threshold

        buffer = None
        if not condition_list.all():
            plt.figure()
            self.df[column].plot(style='.')
            self.df[column][~condition_list].plot(style='rP')
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        self.assertion_base(
            condition=(condition_list).all(),
            error_message=('Differential change of column {}'.format(column) +
                           'larger than threshold {}'.format(str(threshold)) +
                           '. List of values: {}'.format(self.df[column][~condition_list].to_string().replace('\n', ' - '))),
                check_type=name_check_function,
                figure=buffer)

    def check_misalignment_geonica(self, column):
        # Check misalignment Geonica station

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        num_valleys_misalign, moments_misalign = mc_solar.valleys_radiation(self.df[column])
        
        print('num_valleys_misalign', num_valleys_misalign)
        
        condition_list = num_valleys_misalign < NUM_VALLEYS_THRESHOLD

        buffer = None
        if not condition_list:
            plt.figure()
            self.df[column].plot(style='.')
            self.df[column][moments_misalign].plot(style='r-P')
            plt.title(name_check_function)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        self.assertion_base(
            condition=(condition_list),
            error_message=('Possible misalignment in Geonica direct radiation due to ' +
                           'the number of suspicious valleys ({})'.format(num_valleys_misalign) +
                           ' larger than threshold, {}'.format(NUM_VALLEYS_THRESHOLD) +
                           '. List of values: {}'.format(self.df[column][moments_misalign].to_string().replace('\n', ' - '))),
                check_type=name_check_function,
                figure=buffer)

    def check_coherence_radiation(self, threshold_pct, dni, ghi, dhi, radiation_threshold=None):
        # Check radiation coherence between GHI and DNI&DHI
        # THRESHOLD is in percentage

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        if radiation_threshold is None:
            radiation_threshold = GHI_RADIATION_THRESHOLD

        df_filt = self.df[self.df[ghi] > GHI_RADIATION_THRESHOLD]

        if len(df_filt) == 0:  # Avoids future errors
            return None

        _, Zz = mc_solar.solpos(df_filt.index)

        ghi_model = (df_filt[dhi] + df_filt[dni] * np.cos(Zz))

        condition_list = (
            ((df_filt[ghi] - ghi_model).abs()) / df_filt[ghi] * 100 < threshold_pct)

        buffer = None
        if not condition_list.all():
            plt.figure()
            df_filt[ghi].plot(style='.')
            df_filt[ghi][~condition_list].plot(style='rP')
#            plt.legend()
            plt.title(name_check_function)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        num_radiation_transitions_value = mc_solar.num_radiation_transitions(self.df[ghi])

        if num_radiation_transitions_value < NUM_RADIATION_TRANSITIONS_THRESHOLD:
            self.assertion_base(
                condition=condition_list.all(),
                error_message='No coherence between radiations considering a percentage threshold of GHI {}% in {}'.format(
                    threshold_pct,
                    df_filt[
                        ~condition_list].index),
                check_type=name_check_function,
                figure=buffer)
        else:
            self.assertion_base(
                condition=False,
                error_message='Radiation coherence based on GHI not checked because the number of cloudy moments={} [with a DRADIATION_DT={}] is higher than threshold={}'.format(
                    num_radiation_transitions_value,
                    DRADIATION_DT,
                    NUM_RADIATION_TRANSITIONS_THRESHOLD),
                error_level='INFO',
                check_type=name_check_function,
                figure=buffer)

    def check_radiation_other_source(
            self,
            column,
            other_radiation,
            threshold_pct,
            radiation_threshold=None,
            label_other='_other'):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function
        
        if radiation_threshold is None:
            radiation_threshold = DNI_RADIATION_THRESHOLD

        other_radiation_copy = other_radiation.copy()

        other_radiation_copy.name += label_other
        column_other = other_radiation_copy.name

        df_joined = self.df.join(other_radiation_copy, how='inner')

        df_filt = df_joined[df_joined[column] > radiation_threshold]

        if len(df_filt) == 0:  # Avoids future errors
            return None

        condition_list = (df_filt[column] - df_filt[column_other]
                          ).abs() / df_filt[column_other] * 100 < threshold_pct

        buffer = None
        if not condition_list.all():
            plt.figure()
            df_filt[column].plot(style='.')
            df_filt[column_other].plot(style='.')
            df_filt[column][~condition_list].plot(style='rP')
            plt.legend([column, column_other])
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        irrad_filt = self.df[column][lambda m: m > DNI_RADIATION_THRESHOLD]
        num_radiation_transitions_value = mc_solar.num_radiation_transitions(irrad_filt)

        if num_radiation_transitions_value < NUM_RADIATION_TRANSITIONS_THRESHOLD:
            self.assertion_base(
                condition=condition_list.all(),
                error_message='No coherence between {} and {} radiation sources considering a percentage THRESHOLD of {} % in {}'.format(
                    column,
                    column_other,
                    threshold_pct,
                    df_filt[column][
                        ~condition_list].index),
                check_type=name_check_function,
                figure=buffer)
        else:
            self.assertion_base(
                condition=False,
                error_message='Comparison of radiation {} and {} from different sources not checked because the number of cloudy moments={} [with a DRADIATION_DT={}] is higher than threshold={}'.format(
                    column,
                    column_other,
                    num_radiation_transitions_value,
                    DRADIATION_DT,
                    NUM_RADIATION_TRANSITIONS_THRESHOLD),
                error_level='INFO',
                check_type=name_check_function,
                figure=buffer)

    def check_total_irradiation_other_source(
            self,
            column,
            other_radiation,
            threshold_pct,
            label_other='_other'):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function

        other_radiation_copy = other_radiation.copy()

        other_radiation_copy.name += label_other
        column_other = other_radiation_copy.name

        df_joined = self.df.join(other_radiation_copy, how='inner')

        irradiation = mc_solar.daily_irradiation(
            df_joined[column], samples_per_hour=self.samples_per_hour)
        irradiation_other = mc_solar.daily_irradiation(
            df_joined[column_other], samples_per_hour=self.samples_per_hour)

        if irradiation < DAILY_IRRADIATION_THRESHOLD:  # Avoids future errors
            return None

        diff_radiation = abs(
            irradiation - irradiation_other) / irradiation * 100

        condition_list = diff_radiation < threshold_pct

        buffer = None
        
        if not (condition_list):
            plt.figure()
            df_joined[column].plot(style='k.')
            df_joined[column_other].plot(style='r.')
            plt.legend([column, column_other])
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)
        
        irrad_filt = self.df[column][lambda m: m > DNI_RADIATION_THRESHOLD]
        num_radiation_transitions_value = mc_solar.num_radiation_transitions(irrad_filt)

        if num_radiation_transitions_value < NUM_RADIATION_TRANSITIONS_THRESHOLD:
            self.assertion_base(
                condition=condition_list,
                error_message='Total irradiation from {} is different to {} in more than {}%. It is {:.1f}% while DAILY_IRRADIATION_THRESHOLD is {:.2} kWh/(m2·day)'.format(
                column,
                column_other,
                threshold_pct,
                diff_radiation,
                DAILY_IRRADIATION_THRESHOLD),
                check_type=name_check_function,
                figure=buffer)
        else:
            self.assertion_base(
                condition=False,
                error_message='Comparison of total irradiations {} and {} not checked because the number of cloudy moments={} [with a DRADIATION_DT={}] is higher than threshold={}'.format(
                    column,
                    column_other,
                    num_radiation_transitions_value,
                    DRADIATION_DT,
                    NUM_RADIATION_TRANSITIONS_THRESHOLD),
                error_level='INFO',
                check_type=name_check_function,
                figure=buffer)

    def check_num_radiation_transitions_other_source(
            self,
            column,
            other_radiation,
            num_diff_radiation_transitions_thresold,
            radiation_threshold=None,
            label_other='_other'):

        name_check_function = inspect.getframeinfo(inspect.currentframe()).function
        
        if radiation_threshold is None:
            radiation_threshold = DNI_RADIATION_THRESHOLD

        column_other = other_radiation.name + label_other
        
        other_radiation_filt = other_radiation.copy()[lambda x: x > radiation_threshold]
        radiation_filt = self.df[column][lambda x: x > radiation_threshold]
        
        if len(radiation_filt) == 0:  # Avoids future errors
            return None

        num_radiation_transitions_value = mc_solar.num_radiation_transitions(radiation_filt)
        num_radiation_transitions_value_other = mc_solar.num_radiation_transitions(other_radiation_filt)

        condition_list = abs(
            num_radiation_transitions_value -
            num_radiation_transitions_value_other) < num_diff_radiation_transitions_thresold
        
        buffer = None
        
        if not condition_list:
            plt.figure()
            radiation_filt.plot(style='.-')
            other_radiation_filt.plot(style='.-')
            plt.legend([column, column_other])
            plt.title(name_check_function + ':' + column)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)
        
        self.assertion_base(
            condition=condition_list,
            error_message='No coherence of cloudy moments between {} and {} radiation sources with {} and {} respectively. Maximum allowed difference: {}'.format(
            column,
            column_other,
            num_radiation_transitions_value,
            num_radiation_transitions_value_other,
            num_diff_radiation_transitions_thresold),
            check_type=name_check_function,
            figure=buffer)

    def check_coherence_isotypes(self, dni, top, mid, bot, threshold_pct, radiation_threshold=None):
        #         Check radiation coherence between DNI and isotypes
        #         THRESHOLD is in percentage
        name_check_function = inspect.getframeinfo(inspect.currentframe()).function
        
        if radiation_threshold is None:
            radiation_threshold = DNI_RADIATION_THRESHOLD

        df_filt = self.df[self.df[dni] > DNI_RADIATION_THRESHOLD]

        if len(df_filt) == 0:  # Avoids future errors
            return None

        dni_model = (
            df_filt[top] *
            0.51 +
            df_filt[mid] *
            0.10 +
            df_filt[bot] *
            0.39)

        condition_list = (
            ((df_filt[dni] - dni_model).abs()) / df_filt[dni] * 100 < threshold_pct)

        buffer = None
        if not condition_list.all():
            plt.figure()
            df_filt[dni].plot(style='k.')
            df_filt[top].plot(style='.')
            df_filt[mid].plot(style='.')
            df_filt[bot].plot(style='.')
            df_filt[dni][
                ~condition_list].plot(
                marker='P',
                markersize=8,
                color='darkred',
                markeredgecolor='yellow',
                markeredgewidth=2)
            plt.legend([top, mid, bot])
            plt.title(name_check_function)
            plt.suptitle(self.type_data_station, fontsize=18)

            buffer = io.BytesIO()
            plt.savefig(buffer)
            buffer.seek(0)

        irrad_filt = self.df[dni][lambda m: m > DNI_RADIATION_THRESHOLD]
        num_radiation_transitions_value = mc_solar.num_radiation_transitions(irrad_filt)

        if num_radiation_transitions_value < NUM_RADIATION_TRANSITIONS_THRESHOLD:
            self.assertion_base(
                condition=condition_list.all(),
                error_message='No coherence between DNI radiation and isotypes considering a percentage threshold of {} % in {}'.format(
                    threshold_pct,
                    df_filt[dni][
                        ~condition_list].index),
                check_type=name_check_function,
                figure=buffer)
        else:
            self.assertion_base(
                condition=False,
                error_message='DNI vs isotypes comparison not checked because the number of cloudy moments={} [with a DRADIATION_DT={}] is higher than threshold={}'.format(
                    num_radiation_transitions_value,
                    DRADIATION_DT,
                    NUM_RADIATION_TRANSITIONS_THRESHOLD),
                error_level='INFO',
                check_type=name_check_function,
                figure=buffer)
