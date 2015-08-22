#!/usr/bin/python2.7
# encoding: utf-8

from __future__ import division
import numpy as np
import sys
import numexpr as ne
from datetime import datetime
from datetime import timedelta
from miscellaneous import *
from BP_tools import *
from utide import solve, reconstruct
import time
from miscellaneous import mattime_to_datetime 

class FunctionsAdcp:
    ''''Utils' subset of FVCOM class gathers useful functions""" '''
    def __init__(self, variable, plot, History, debug=False):
        self._debug = debug
        self._var = variable
        self._plot = plot
        self._History = History
        #Create pointer to FVCOM class
        variable = self._var
        History = self._History

    def flow_dir(self, t_start=[], t_end=[], time_ind=[],
                 exceedance=False, debug=False):
        """
        Flow directions and associated norm

        Outputs:
        -------
           - flowDir = flowDir at station, 1D array
           - norm = velocity norm at station, 1D array

        Keywords:
        --------
          - t_start = start time, as string ('yyyy-mm-ddThh:mm:ss'),
                      or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
          - time_ind = time indices to work in, list of integers
          - excedance = True, compute associated exceedance curve

        Notes:
        -----
          - directions between -180 and 180 deg., i.e. 0=East, 90=North,
            +/-180=West, -90=South
        """
        debug = debug or self._debug
        if debug:
            print 'Computing flow directions at point...'

        # Find time interval to work in
        argtime = []
        if not time_ind==[]:
            argtime = time_ind
        elif not t_start==[]:
            if type(t_start)==str:
                argtime = time_to_index(t_start, t_end, self._var.matlabTime, debug=debug)
            else:
                argtime = arange(t_start, t_end)

        #Choose the right pair of velocity components
        if not argtime==[]:
            U = self._var.ua[argtime]
            V = self._var.va[argtime]
        else:
            U = self._var.ua[:]
            V = self._var.va[:]
   
        #Compute directions
        if debug:
            print 'Computing arctan2 and norm...'
        dirFlow = np.rad2deg(np.arctan2(V,U))

        #Compute velocity norm
        norm = ne.evaluate('sqrt(U**2 + V**2)')
        if debug:
            print '...Passed'
        #Rose diagram
        self._plot.rose_diagram(dirFlow, norm)
        if exceedance:
            self.exceedance(norm)

        return dirFlow, norm

    def ebb_flood_split(self, t_start=[], t_end=[], time_ind=[], debug=False):
        """
        Compute time indices for ebb and flood but also the 
        principal flow directions and associated variances for (lon, lat) point

        Outputs:
        -------
          - floodIndex = flood time index, 1D array of integers
          - ebbIndex = ebb time index, 1D array of integers
          - pr_axis = principal flow ax1s, float number in degrees
          - pr_ax_var = associated variance, float number

        Keywords:
        --------
          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
                      or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
          - time_ind = time indices to work in, 1D array of integers 
        
        Notes:
        -----
          - may take time to compute if time period too long
          - directions between -180 and 180 deg., i.e. 0=East, 90=North,
            +/-180=West, -90=South
          - use time_ind or t_start and t_end, not both
          - assume that flood is aligned with principal direction
        """
        debug = debug or self._debug
        if debug:
            start = time.time()
            print 'Computing principal flow directions...'

        # Find time interval to work in
        argtime = []
        if not time_ind==[]:
            argtime = time_ind
        elif not t_start==[]:
            if type(t_start)==str:
                argtime = time_to_index(t_start, t_end,
                                        self._var.matlabTime,
                                        debug=debug)
            else:
                argtime = arange(t_start, t_end)

        #Choose the right pair of velocity components
        if not argtime==[]:
            U = self._var.ua[argtime]
            V = self._var.va[argtime]
        else:
            U = self._var.ua[:]
            V = self._var.va[:]

        #WB version of BP's principal axis
        if debug:
            print 'Computin principal axis at point...'
        pr_axis, pr_ax_var = principal_axis(U, V)

        #ebb/flood split
        if debug:
            print 'Splitting ebb and flood at point...'
        # reverse 0-360 deg convention
        ra = (-pr_axis - 90.0) * np.pi /180.0
        if ra>np.pi:
            ra = ra - (2.0*np.pi)
        elif ra<-np.pi:
            ra = ra + (2.0*np.pi)    
        dirFlow = np.arctan2(V,U)
        #Define bins of angles
        if ra == 0.0:
            binP = [0.0, np.pi/2.0]
            binP = [0.0, -np.pi/2.0]
        elif ra > 0.0:
            if ra == np.pi:
                binP = [np.pi/2.0 , np.pi]
                binM = [-np.pi, -np.pi/2.0 ]        
            elif ra < (np.pi/2.0):
                binP = [0.0, ra + (np.pi/2.0)]
                binM = [-((np.pi/2.0)-ra), 0.0]
            else:
                binP = [ra - (np.pi/2.0), np.pi]
                binM = [-np.pi, -np.pi + (ra-(np.pi/2.0))]
        else:
            if ra == -np.pi:
                binP = [np.pi/2.0 , np.pi]
                binM = [-np.pi, -np.pi/2.0]
            elif ra > -(np.pi/2.0):
                binP = [0.0, ra + (np.pi/2.0)]
                binM = [ ((-np.pi/2.0)+ra), 0.0]
            else:
                binP = [np.pi - (ra+(np.pi/2.0)) , np.pi]
                binM = [-np.pi, ra + (np.pi/2.0)]
                                
        test = (((dirFlow > binP[0]) * (dirFlow < binP[1])) +
                ((dirFlow > binM[0]) * (dirFlow < binM[1])))
        floodIndex = np.where(test == True)[0]
        ebbIndex = np.where(test == False)[0]

        #TR fit with Rose diagram angle convention
        #pr_axis = pr_axis - 90.0
        #if pr_axis<0.0:
        #    pr_axis[ind] = pr_axis[ind] + 360   

        if debug:
            end = time.time()
            print "...processing time: ", (end - start)

        return floodIndex, ebbIndex, pr_axis, pr_ax_var

    def exceedance(self, var, debug=False):
        """
        This function calculate the excedence curve of a var(time).

        Inputs:
        ------
          - var = given quantity, 1 array of n elements

        Keywords:
        --------
          - graph: True->plots curve; False->does not

        Outputs:
        -------
          - Exceedance = list of % of occurences, 1D array
          - Ranges = list of signal amplitude bins, 1D array

        Notes:
        -----
          - This method is not suitable for SSE
        """
        debug = (debug or self._debug)
        if debug:
            print 'Computing exceedance...'

        signal=var
        
        Max = max(signal)	
        dy = (Max/30.0)
        Ranges = np.arange(0,(Max + dy), dy)
        Exceedance = np.zeros(Ranges.shape[0])
        dt = self._var.matlabTime[1] - self._var.matlabTime[0]
        Period = var.shape[0] * dt
        time = np.arange(0.0, Period, dt)

        N = len(signal)
        M = len(Ranges)

        for i in range(M):
            r = Ranges[i]
            for j in range(N-1):
                if signal[j] > r:
                    Exceedance[i] = Exceedance[i] + (time[j+1] - time[j])

        Exceedance = (Exceedance * 100) / Period

        if debug:
            print '...Passed'
       
        #Plot
        self._plot.plot_xy(Exceedance, Ranges, yLabel='Amplitudes',
                           xLabel='Exceedance probability in %')

        return Exceedance, Ranges

    def speed_histogram(self, t_start=[], t_end=[], time_ind=[], debug=False):
        """
        This function plots the histogram of occurrences for the signed
        flow speed.

        Keywords:
        --------
          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
                      or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
          - time_ind = time indices to work in, 1D array of integers 
        
        Notes:
        -----
          - use time_ind or t_start and t_end, not both
        """
        debug = debug or self._debug
        if debug:
            start = time.time()
            print 'Computing speed histogram...'

        pI, nI, pa, pav = self.ebb_flood_split(t_start=t_start, t_end=t_end,
                          time_ind=time_ind, debug=debug)
        dirFlow, norm = self.flow_dir(t_start=t_start, t_end=t_end,
                        time_ind=time_ind, exceedance=False, debug=debug)
        norm[nI] = -1.0 * norm[nI]

        #compute bins
        #minBound = norm.min()
        #maxBound = norm.max()
        #step = round((maxBound-minBound/51.0),1)
        #bins = np.arange(minBound,maxBound,step)

        #plot histogram
        self._plot.Histogram(norm,
                             xLabel='Signed flow speed (m/s)',
                             yLabel='Occurrences (%)')
   
        if debug:
            end = time.time()
            print "...processing time: ", (end - start)


    def Harmonic_analysis(self,
                          time_ind=[], t_start=[], t_end=[],
                          elevation=True, velocity=False,
                          debug=False, **kwarg):
        '''
        Description:
        -----------
        This function performs a harmonic analysis on the sea surface elevation
        time series or the velocity components timeseries.

        Outputs:
        -------
          - harmo = harmonic coefficients, dictionary

        Keywords:
        --------
          - time_ind = time indices to work in, list of integers
          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
                     or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
          - elevation=True means that solve will be done for elevation.
          - velocity=True means that solve will be done for velocity.

        Options:
        -------
        Options are the same as for solve, which are shown below with
        their default values:
            conf_int=True; cnstit='auto'; notrend=0; prefilt=[]; nodsatlint=0;
            nodsatnone=0; gwchlint=0; gwchnone=0; infer=[]; inferaprx=0;
            rmin=1; method='cauchy'; tunrdn=1; linci=0; white=0; nrlzn=200;
            lsfrqosmp=1; nodiagn=0; diagnplots=0; diagnminsnr=2;
            ordercnstit=[]; runtimedisp='yyy'

        Notes:
        -----
        For more detailed information about solve, please see
        https://github.com/wesleybowman/UTide

        '''
        debug = (debug or self._debug)

        argtime = []
        if not time_ind==[]:
            argtime = time_ind
        elif not t_start==[]:
            if type(t_start)==str:
                argtime = time_to_index(t_start, t_end,
                                        self._var.matlabTime,
                                        debug=debug)
            else:
                argtime = arange(t_start, t_end)
        
        if velocity:
            time = self._var.matlabTime[:]
            u = self._var.ua[:]
            v = self._var.va[:]

            if not argtime==[]:
                time = time[argtime[:]]
                u = u[argtime[:]]
                v = v[argtime[:]]

            lat = self._var.lat
            harmo = solve(time, u, v, lat, **kwarg)

        if elevation:
            time = self._var.matlabTime[:]
            el = self._var.el[:]

            if not argtime==[]:
                time = time[argtime[:]]
                el = el[argtime[:]]

            lat = self._var.lat
            harmo = solve(time, el, [], lat, **kwarg)
            #Write meta-data only if computed over all the elements

            return harmo

    def Harmonic_reconstruction(self, harmo, elevation=True, velocity=False,
                                time_ind=slice(None), debug=False, **kwarg):
        '''
        Description:
        ----------
        This function reconstructs the velocity components or the surface elevation
        from harmonic coefficients.
        Harmonic_reconstruction calls reconstruct. This function assumes harmonics
        (solve) has already been executed.

        Inputs:
        ------
          - Harmo = harmonic coefficient from harmo_analysis
          - elevation =True means that reconstruct will be done for elevation.
          - velocity =True means that ut_reconst will be done for velocity.
          - time_ind = time indices to process, list of integers
        
        Output:
        ------         
          - Reconstruct = reconstructed signal, dictionary

        Options:
        -------
        Options are the same as for reconstruct, which are shown below with
        their default values:
            cnstit = [], minsnr = 2, minpe = 0

        Notes:
        -----
        For more detailed information about reconstruct, please see
        https://github.com/wesleybowman/UTide

        '''
        debug = (debug or self._debug)
        time = self._var.matlabTime[time_ind]
        #TR_comments: Add debug flag in Utide: debug=self._debug
        Reconstruct = {}
        if velocity:
            U_recon, V_recon = reconstruct(time,harmo)
            Reconstruct['U'] = U_recon
            Reconstruct['V'] = V_recon
        if elevation:
            elev_recon, _ = reconstruct(time,harmo)
            Reconstruct['el'] = elev_recon
        return Reconstruct  

    def verti_shear(self, t_start=[], t_end=[],  time_ind=[],
                    graph=True, debug=False):
        """
        Compute vertical shear

        Outputs:
        -------
          - dveldz = vertical shear (1/s), 2D array (time, nlevel - 1)

        Keywords:
        --------
          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
                      or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
          - time_ind = time indices to work in, list of integers
          - graph = plots graph if True

        Notes:
        -----
          - use time_ind or t_start and t_end, not both
        """
        debug = debug or self._debug
        if debug:
            print 'Computing vertical shear at point...'

        # Find time interval to work in
        argtime = []
        if not time_ind==[]:
            argtime = time_ind
        elif not t_start==[]:
            if type(t_start)==str:
                argtime = time_to_index(t_start, t_end, self._var.matlabTime, debug=debug)
            else:
                argtime = np.arange(t_start, t_end) 

        #Compute depth
        depth = self._var.depth[:]
          
        #Extracting velocity at point
        if not argtime==[]:
            U = self._var.east_vel[argtime,:]
            V = self._var.north_vel[argtime,:]
        else:
            U = self._var.east_vel[:,:]
            V = self._var.north_vel[:,:]

        norm = ne.evaluate('sqrt(U**2 + V**2)')     

        # Compute shear
        dz = depth[1:] - depth[:-1]
        dvel = norm[:,1:] - norm[:,:-1]           
        dveldz = dvel / dz

        if debug:
            print '...Passed'

        #Plot mean values
        if graph:
            mean_depth = (depth[1:] + depth[:-1]) / 2.0
            mdat = np.ma.masked_array(dveldz,np.isnan(dveldz))
            mean_dveldz = np.mean(mdat,0)
            error = np.std(mdat,axis=0)
            self._plot.plot_xy(mean_dveldz, mean_depth, xerror=error[:],
                               title='Shear profile ',
                               xLabel='Shear (1/s) ', yLabel='Depth (m) ')

        return dveldz             

    def velo_norm(self, t_start=[], t_end=[], time_ind=[],
                  graph=True, debug=False):
        """
        Compute the velocity norm

        Outputs:
        -------
          - velo_norm = velocity norm, 2D array (time, level)

        Keywords:
        --------
          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
                      or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
          - time_ind = time indices to work in, list of integers
          - graph = plots vertical profile averaged over time if True

        Notes:
        -----
          - use time_ind or t_start and t_end, not both
        """
        debug = debug or self._debug
        if debug:
            print 'Computing velocity norm at point...'
       
        # Find time interval to work in
        argtime = []
        if not time_ind==[]:
            argtime = time_ind
        elif not t_start==[]:
            if type(t_start)==str:
                argtime = time_to_index(t_start, t_end, self._var.matlabTime, debug=debug)
            else:
                argtime = arange(t_start, t_end)

        #Computing velocity norm
        if not argtime==[]:          
            U = self._var.east_vel[argtime, :]
            V = self._var.north_vel[argtime, :]
            velo_norm = ne.evaluate('sqrt(U**2 + V**2)')
        else:            
            U = self._var.east_vel[:, :]
            V = self._var.north_vel[:, :]
            velo_norm = ne.evaluate('sqrt(U**2 + V**2)')

        if debug:
            print '...passed'

        #Plot mean values
        if graph:
            depth = self._var.depth
            mdat = np.ma.masked_array(velo_norm,np.isnan(velo_norm))
            vel = np.mean(mdat,0)
            error = np.std(mdat,axis=0)
            self._plot.plot_xy(vel, depth, xerror=error[:],
                               title='Velocity norm profile ',
                               xLabel='Velocity (m/s) ', yLabel='Depth (m) ')
      

        return velo_norm 

    def mattime2datetime(self, mattime, debug=False):
        """
        Description:
        ----------
        Output the time (yyyy-mm-dd, hh:mm:ss) corresponding to
        a given matlab time

        Inputs:
        ------
          - mattime = matlab time (floats)
        """  
        time = mattime_to_datetime(mattime, debug=debug)   
        print time[0]

#TR_comments: templates
#    def whatever(self, debug=False):
#        if debug or self._debug:
#            print 'Start whatever...'
#
#        if debug or self._debug:
#            print '...Passed'
