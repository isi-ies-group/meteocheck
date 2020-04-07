# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 13:12:43 2017

@author: Ruben
"""

MINIMUM_ERROR_LEVEL_TO_SEND_EMAIL = 'WARNING'

# Logs' filenames
FILENAME_SESSION_LOG = 'meteocheck_session.log'
FILENAME_HISTORY_LOG = 'meteocheck_history.log'

# THRESHOLD for derivative of radiation with respect time. Used when
# calculating cloudy moments [per minute]
DRADIATION_DT = 10

# THRESHOLD for cloudy moments allowed per day (usually for dni > DNI_RADIATION_THRESHOLD).
# If is higher than THRESHOLD it disables 'radiation_coherence' and 'radiation_source'
# setting error_level=INFO
NUM_RADIATION_TRANSITIONS_THRESHOLD = 10

# THRESHOLD of DNI when comparing several radiations, so ignores
# low-radiation values with more probabilities of missmatch
DNI_RADIATION_THRESHOLD = 700

# THRESHOLD of GHI when comparing several radiations, so ignores
# low-radiation values with more probabilities of missmatch
GHI_RADIATION_THRESHOLD = 300

# THRESHOLD of daily irradiation in kWh to perform comparison. Low levels
# have low Signal-noise ratio
DAILY_IRRADIATION_THRESHOLD = 1.0

######## Parameters for valleys_radiation(), used to check tracker misalignment
# These are concrete the concrete values for Geonica tracker
LENGTH_VALLEY = [6, 7, 8]
DEPTH_VALLEY_MIN = 0.80
DEPTH_VALLEY_MAX = 0.95

# THRESHOLD onf number of valleys (as defined in solar_functions.num_valleys_radiation())
# If the number is higher, it is highly probable that the tracker is misaligned
NUM_VALLEYS_THRESHOLD = 5
