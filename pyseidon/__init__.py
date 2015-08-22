#!/usr/bin/python2.7
# encoding: utf-8

from __future__ import division
import os
import sys

local = os.path.dirname(__file__)
sys.path.append(os.path.join(local,'fvcomClass'))
sys.path.append(os.path.join(local,'adcpClass'))
#sys.path.append(os.path.join(local,'drifterClass'))
sys.path.append(os.path.join(local,'stationClass'))
sys.path.append(os.path.join(local,'tidegaugeClass'))
sys.path.append(os.path.join(local,'validationClass'))
sys.path.append(os.path.join(local,'utilities'))

#Local import
from fvcomClass import *
from adcpClass import *
#from drifterClass import *
from tidegaugeClass import *
from validationClass import *
from stationClass import *
from utilities import *

#Permission info for OpenDap server
#print "OpenDap server connexion info:"

__version__ = '1.1'
#__all__ = ["FVCOM", "ADCP", "Drifter", "TideGauge",\
#          "Validation", "Station", "utilities" ]
__all__ = ["FVCOM", "ADCP", "TideGauge",\
          "Validation", "Station", "utilities" ]
__authors__ = ['Wesley Bowman, Thomas Roc, Jonathan Smith']
__licence__ = 'GNU Affero GPL v3.0'
__copyright__ = 'Copyright (c) 2014 EcoEnergyII'

