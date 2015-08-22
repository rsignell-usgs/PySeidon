#!/usr/bin/python2.7
# encoding: utf-8
import numpy as np
import sys
from tidalStats import TidalStats
#from interpolate import interpol
from smooth import smooth
from datetime import datetime, timedelta
from utide import reconstruct
import matplotlib.pyplot as plt
from depthInterp import depthFromSurf
#from save_FlowFile_BPFormat import sign_speed, get_DirFromN

def dn2dt(datenum):
    '''
    Convert matlab datenum to python datetime.
    '''
    return datetime.fromordinal(int(datenum)) + timedelta(days=datenum%1) - \
           timedelta(days=366)

def compareUV(data, threeDim, depth=5, plot=False, save_csv=False,
              debug=False, debug_plot=False):
    '''
    Does a comprehensive validation process between modeled and observed
    data on the following:
        Current speed
        Current direction
        Harmonic constituents (for height and speed)

    Outputs a list of important statistics for each variable, calculated
    using the TidalStats class
    '''
    if debug: print "CompareUV..."
    # take data from input dictionary
    mod_time = data['mod_time']
    obs_time = data['obs_time']
    mod_el = data['mod_timeseries']['elev']
    obs_el = data['obs_timeseries']['elev']

    #Check if 3D simulation
    if threeDim:
        obs_u_all = data['obs_timeseries']['u']
        obs_v_all = data['obs_timeseries']['v']
        mod_u_all = data['mod_timeseries']['u']
        mod_v_all = data['mod_timeseries']['v']
        bins = data['obs_timeseries']['bins']
        siglay = data['mod_timeseries']['siglay']
        # use depth interpolation to get a single timeseries
        mod_depth = mod_el + np.mean(obs_el[~np.isnan(obs_el)])
        (mod_u, obs_u) = depthFromSurf(mod_u_all, mod_depth, siglay,
				       obs_u_all, obs_el, bins, depth=depth,
                                       debug=debug, debug_plot=debug_plot)
        (mod_v, obs_v) = depthFromSurf(mod_v_all, mod_depth, siglay,
                                       obs_v_all, obs_el, bins, depth=depth,
                                       debug=debug, debug_plot=debug_plot)
    else:
        obs_u = data['obs_timeseries']['ua']
        obs_v = data['obs_timeseries']['va']
        mod_u = data['mod_timeseries']['ua']
        mod_v = data['mod_timeseries']['va']        


    if debug: print "...convert times to datetime..."
    mod_dt, obs_dt = [], []
    for i in mod_time:
	mod_dt.append(dn2dt(i))
    for j in obs_time:
	obs_dt.append(dn2dt(j))

    if debug: print "...put data into a useful format..."
    mod_spd = np.sqrt(mod_u**2.0 + mod_v**2.0)
    obs_spd = np.sqrt(obs_u**2.0 + obs_v**2.0)
    mod_dir = np.arctan2(mod_v, mod_u) * 180.0 / np.pi
    obs_dir = np.arctan2(obs_v, obs_u) * 180.0 / np.pi
    obs_el = obs_el - np.mean(obs_el[~np.isnan(obs_el)])

    if debug: print "...check if the modeled data lines up with the observed data..."
    if (mod_time[-1] < obs_time[0] or obs_time[-1] < mod_time[0]):
        print "---time periods do not match up---"
        sys.exit()

    else:
        if debug: print "...interpolate the data onto a common time step for each data type..."
	# elevation
        (mod_el_int, obs_el_int, step_el_int, start_el_int) = \
	    smooth(mod_el, mod_dt, obs_el, obs_dt,
                   debug=debug, debug_plot=debug_plot)

	# speed
        (mod_sp_int, obs_sp_int, step_sp_int, start_sp_int) = \
            smooth(mod_spd, mod_dt, obs_spd, obs_dt,
                   debug=debug, debug_plot=debug_plot)

	# direction
        (mod_dr_int, obs_dr_int, step_dr_int, start_dr_int) = \
            smooth(mod_dir, mod_dt, obs_dir, obs_dt,
                   debug=debug, debug_plot=debug_plot)

	# u velocity
	(mod_u_int, obs_u_int, step_u_int, start_u_int) = \
	    smooth(mod_u, mod_dt, obs_u, obs_dt,
                   debug=debug, debug_plot=debug_plot)

	# v velocity
	(mod_v_int, obs_v_int, step_v_int, start_v_int) = \
	    smooth(mod_v, mod_dt, obs_v, obs_dt,
                   debug=debug, debug_plot=debug_plot)

	# velocity i.e. signed speed
	(mod_ve_int, obs_ve_int, step_ve_int, start_ve_int) = \
	    smooth(mod_spd * np.sign(mod_v), mod_dt, 
		   obs_spd * np.sign(obs_v), obs_dt,
                   debug=debug, debug_plot=debug_plot)

    if debug: print "...separate into ebb and flow..."
    
    ## separate into ebb and flow
    #mod_dir_n = get_DirFromN(mod_u_int, mod_v_int)
    #obs_dir_n = get_DirFromN(obs_u_int, mod_v_int)
    #mod_signed_s, mod_PA = sign_speed(mod_u_int, mod_v_int, mod_sp_int,
    #			      mod_dr_int, 0)
    #obs_signed_s, obs_PA = sign_speed(obs_u_int, obs_v_int, obs_sp_int,
    #			      obs_dr_int, 0)
    #print mod_signed_s[:20], mod_PA[:20]
    #print obs_signed_s[:20], obs_PA[:20]
    
    if debug: print "...remove directions where velocities are small..."
    MIN_VEL = 0.1
    for i in np.arange(obs_sp_int.size):
 	if (obs_sp_int[i] < MIN_VEL):
	    obs_dr_int[i] = np.nan
	if (mod_sp_int[i] < MIN_VEL):
	    mod_dr_int[i] = np.nan

    if debug: print "...get stats for each tidal variable..."
    elev_suite = tidalSuite(mod_el_int, obs_el_int, step_el_int, start_el_int,
			    type='elevation', plot=plot, save_csv=save_csv, 
                            debug=debug, debug_plot=debug_plot)
    speed_suite = tidalSuite(mod_sp_int, obs_sp_int, step_sp_int, start_sp_int,
			    type='speed', plot=plot, save_csv=save_csv, 
                            debug=debug, debug_plot=debug_plot)
    dir_suite = tidalSuite(mod_dr_int, obs_dr_int, step_dr_int, start_dr_int,
			   type='direction', plot=plot, save_csv=save_csv, 
                           debug=debug, debug_plot=debug_plot)
    u_suite = tidalSuite(mod_u_int, obs_u_int, step_u_int, start_u_int,
			 type='u velocity', plot=plot, save_csv=save_csv, 
                         debug=debug, debug_plot=debug_plot)
    v_suite = tidalSuite(mod_v_int, obs_v_int, step_v_int, start_v_int,
			 type='v velocity', plot=plot, save_csv=save_csv, 
                         debug=debug, debug_plot=debug_plot)
    vel_suite = tidalSuite(mod_ve_int, obs_ve_int, step_ve_int, start_ve_int,
			   type='velocity', plot=plot, save_csv=save_csv, 
                           debug=debug, debug_plot=debug_plot)
    #ebb_suite = tidalSuite(mod_ebb, obs_ebb, step_ebb_int, start_ebb_int,
    #     		    type='ebb', plot=True, save_csv=save_csv, 
    #                       debug=debug, debug_plot=debug_plot)
    #flo_suite = tidalSuite(mod_flo, obs_flo, step_flo_int, start_flo_int,
    #	         	    type='flow', plot=True, save_csv=save_csv, 
    #                        debug=debug, debug_plot=debug_plot)
    # output statistics in useful format

    if debug: print "...CompareUV done."

    return (elev_suite, speed_suite, dir_suite, u_suite, v_suite, vel_suite)

def tidalSuite(model, observed, step, start, type, plot=False,
               save_csv=False, debug=False, debug_plot=False):
    '''
    Create stats classes for a given tidal variable.

    Accepts interpolated model and observed data, the timestep, and start
    time. Type is a string representing the type of data. If plot is set
    to true, a time plot and regression plot will be produced.
    
    Returns a dictionary containing all the stats.
    '''
    if debug: print "tidalSuite..."
    stats = TidalStats(model, observed, step, start, type=type,
                       debug=debug, debug_plot=debug_plot)
    stats_suite = stats.getStats()
    stats_suite['r_squared'] = stats.linReg()['r_2']
    stats_suite['phase'] = stats.getPhase()

    if plot or debug_plot:
        stats.plotData()
	stats.plotRegression(stats.linReg())

    if save_csv:
        stats.save_data()    

    if debug: print "...tidalSuite done."

    return stats_suite

def compareTG(data, plot=False, save_csv=False, debug=False, debug_plot=False):
    '''
    Does a comprehensive comparison between tide gauge height data and
    modeled data, much like the above function.

    Input is a dictionary containing all necessary tide gauge and model data.
    Outputs a dictionary of useful statistics.
    '''
    if debug: print "CompareTG..."
    # load data
    mod_elev = data['mod_timeseries']['elev']
    obs_elev = data['obs_timeseries']['elev']
    obs_datenums = data['obs_time']
    mod_datenums = data['mod_time']
    #TR: comment out
    #mod_harm = data['elev_mod_harmonics']

    # convert times and grab values
    obs_time, mod_time = [], []
    for i, v in enumerate(obs_datenums):
	obs_time.append(dn2dt(v))
    for j, w in enumerate(mod_datenums):
	mod_time.append(dn2dt(w))

    if debug: print "...check if they line up in the time domain..."
    if (mod_time[-1] < obs_time[0] or obs_time[-1] < mod_time[0]):
        print "---time periods do not match up---"
        sys.exit()

    else:

        if debug: print "...interpolate timeseries onto a common timestep..."
        (mod_elev_int, obs_elev_int, step_int, start_int) = \
            smooth(mod_elev, mod_time, obs_elev, obs_time,
                   debug=debug, debug_plot=debug_plot)

    if debug: print "...get validation statistics..."
    stats = TidalStats(mod_elev_int, obs_elev_int, step_int, start_int, type='elevation',
                       debug=debug, debug_plot=debug_plot)


    elev_suite = tidalSuite(mod_elev_int, obs_elev_int, step_int, start_int,
			    type='elevation', plot=plot, save_csv=save_csv,
                            debug=debug, debug_plot=debug_plot)

    if debug: print "...CompareTG done."

    return elev_suite
