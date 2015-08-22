#!/usr/bin/python2.7
# encoding: utf-8

from __future__ import division
import numpy as np
import pandas as pd
import csv

from datetime import datetime, timedelta
import cPickle as pickle
import sys
import os
from utide import solve
import scipy.io as sio

#Local import
from interpolation_utils import *
from stationClass import Station
from adcpClass import ADCP
from fvcomClass import FVCOM
from tidegaugeClass import TideGauge


class _load_validation:
    """
'Variables' subset in Validation class contains the following items:
-----------------------------------------------------------

                           _obs. = measurement/observational variables
    Validation.Variables._|_sim. = simulated variables
                          |_struct. = dictionnary structure for validation purposes 
    """
    def __init__(self, observed, simulated, debug=False, debug_plot=False):
        if debug: print "..variables.."
        self.obs = observed.Variables
        self.sim = simulated.Variables
        self.struct = np.array([])

        #Check if times coincide
        obsMax = self.obs.matlabTime[~np.isnan(self.obs.matlabTime)].max()
        obsMin = self.obs.matlabTime[~np.isnan(self.obs.matlabTime)].min()
        simMax = self.sim.matlabTime.max()
        simMin = self.sim.matlabTime.min()
        absMin = max(obsMin, simMin)
        absMax = min(obsMax, simMax)
        A = set(np.where(self.sim.matlabTime[:] >= absMin)[0].tolist()) 
        B = set(np.where(self.sim.matlabTime[:] <= absMax)[0].tolist())
        C = list(A.intersection(B))
        #-Correction by J.Culina 2014-
        C = sorted(C)
        #-end-
        self._C = C

        a = set(np.where(self.obs.matlabTime[:] >= absMin)[0].tolist()) 
        b = set(np.where(self.obs.matlabTime[:] <= absMax)[0].tolist())
        c = list(a.intersection(b))
        #-Correction by J.Culina 2014-
        c = sorted(c)
        #-end-
        self._c = c
        
        if len(C) == 0:
           print "---Time between simulation and measurement does not match up---"
           sys.exit()

        #Check what kind of simulated data it is
        if simulated.__module__=='pyseidon.stationClass.stationClass':
            self._simtype = 'station'
            #Find closest point to ADCP
            ind = closest_point([self.obs.lon], [self.obs.lat],
                                simulated.Grid.lon[:],
                                simulated.Grid.lat[:])
            nameSite = ''.join(simulated.Grid.name[ind,:][0,:])
            print "Station site: " + nameSite
            self.sim.lat = simulated.Grid.lat[ind]
            el = self.sim.el[:, ind].flatten()
            ua = self.sim.ua[:, ind].flatten()
            va = self.sim.va[:, ind].flatten()
            if self.sim._3D:
                u = np.squeeze(self.sim.u[:, :,ind])
                v = np.squeeze(self.sim.v[:, :,ind])
                sig = np.squeeze(simulated.Grid.siglay[:, ind])

        #Alternative simulation type
        elif simulated.__module__=='pyseidon.fvcomClass.fvcomClass':
            self._simtype = 'fvcom'
            #Interpolation at measurement location
            el=simulated.Util2D.interpolation_at_point(self.sim.el,
                                                       self.obs.lon, self.obs.lat)
            ua=simulated.Util2D.interpolation_at_point(self.sim.ua,
                                                       self.obs.lon, self.obs.lat)
            va=simulated.Util2D.interpolation_at_point(self.sim.va,
                                                       self.obs.lon, self.obs.lat)
            if self.sim._3D:
               u=simulated.Util3D.interpolation_at_point(self.sim.u,
                                                         self.obs.lon, self.obs.lat)
               v=simulated.Util3D.interpolation_at_point(self.sim.v,
                                                         self.obs.lon, self.obs.lat)
               sig=simulated.Util3D.interpolation_at_point(simulated.Grid.siglay,
                                                           self.obs.lon, self.obs.lat)
        else:
            print "-This type of simulations is not supported yet-"
            sys.exit()

        #Store in dict structure for compatibility purposes
        if not self.sim._3D:
            sim_mod={'ua':ua[C],
                     'va':va[C],
                     'elev':el[C]}
        else:
            sim_mod={'ua':ua[C],
                     'va':va[C],
                     'elev':el[C],
                     'u':u[C,:],
                     'v':v[C,:],
                     'siglay':sig[:]}
             

        #Check what kind of observed data it is
        if observed.__module__=='pyseidon.adcpClass.adcpClass':
            self._obstype = 'adcp'
            obstype='ADCP'
            obs_mod={'ua':self.obs.ua[c],
                     'va':self.obs.va[c],
                     'elev':self.obs.surf[c],
                     'u':self.obs.east_vel[c,:],
                     'v':self.obs.north_vel[c,:],
                     'bins':self.obs.bins[:]}

        #Alternative measurement type
        elif observed.__module__=='pyseidon.tidegaugeClass.tidegaugeClass':
            self._obstype = 'tidegauge'
            obstype='TideGauge'
            obs_mod = {'data':self.obs.RBR.data, 'elev':self.obs.el[c]}

        else:
            print "-This type of measurements is not supported yet-"
            sys.exit()

        #Store in dict structure for compatibility purposes
        #Common block for 'struct'
        self.struct = {'name': observed.History[0].split(' ')[-1],
                       'type':obstype,
                       'lat':self.obs.lat,
                       'lon':self.obs.lon,
                       'obs_timeseries':obs_mod,
                       'mod_timeseries':sim_mod,
                       'obs_time':self.obs.matlabTime[c],
                       'mod_time':self.sim.matlabTime[C]}

        if debug: print "..done"
