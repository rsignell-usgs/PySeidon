#!/usr/bin/python2.7
# encoding: utf-8

from __future__ import division
import numpy as np
from scipy import linalg as LA
from scipy.interpolate import interp1d
import sys
import numexpr as ne
from datetime import datetime
from datetime import timedelta
from interpolation_utils import *
from miscellaneous import *
from BP_tools import *
from utide import solve, reconstruct
import time

class FunctionsFvcom:
    """
    Description:
    -----------
    'Util2D' subset of FVCOM class gathers
    useful functions and methods for 2D and 3D runs
    """
    def __init__(self, variable, grid, plot, History, debug):
        self._debug = debug
        self._var = variable
        self._grid = grid
        self._plot = plot
        self._History = History
        #Create pointer to FVCOM class
        variable = self._var
        grid = self._grid
        History = self._History

    #TR comment: I don't think I need this anymore  
    def _centers(self, var, debug=False):
        """
        Create new variable 'bathy and elevation at center points' (m)
        -> FVCOM.Grid.hc, elc

        Notes:
        -----
          - Can take time over the full domain
        """
        debug = debug or self._debug
        if debug:
            print 'Computing central bathy...'

        #Interpolation at centers
        size = self._grid.nele
        size1 = self._grid.ntime
        elc = np.zeros((size1, size))
        hc = np.zeros((size))
        #TR comment: I am dubeous about the interpolation method here
        for ind, value in enumerate(self._grid.trinodes):
            elc[:, ind] = np.mean(self._var.el[:, value-1], axis=1)
            hc[ind] = np.mean(self._grid.h[value-1])

        #Custom return    
        self._grid.hc = hc
        self._var.elc = elc
          
        # Add metadata entry
        self._History.append('bathymetry at center points computed')
        self._History.append('elevation at center points computed')
        print '-Central bathy and elevation added to FVCOM.Grid.-'

        if debug:
            print '...Passed'   

    def hori_velo_norm(self, debug=False):
        """
        This method computes  a new variable: 'horizontal velocity norm' (m/s)
        -> FVCOM.Variables.hori_velo_norm

        Notes:
        -----
          - Can take time over the full domain
        """
        debug = debug or self._debug
        if debug:
            print 'Computing horizontal velocity norm...'

        try:
            u = self._var.ua
            v = self._var.va
            vel = ne.evaluate('sqrt(u**2 + v**2)')  
        except MemoryError:
            print '---Data too large for machine memory---'
            print 'Tip: use ax or tx during class initialisation'
            print '---  to use partial data'
            raise

        #Custom return    
        self._var.hori_velo_norm = vel 
          
        # Add metadata entry
        self._History.append('horizontal velocity norm computed')
        print '-Horizontal velocity norm added to FVCOM.Variables.-'

        if debug:
            print '...Passed'

    def flow_dir(self, debug=False):
        """"
        This method create new variable 'depth averaged flow directions' (deg.)
        -> FVCOM.Variables.depth_av_flow_dir

        Notes:
        -----
          - directions between -180 and 180 deg., i.e. 0=East, 90=North,
            +/-180=West, -90=South
          - Can take time over the full domain
        """
        if debug or self._debug:
            print 'Computing flow directions...'

        try:
            u = self._var.ua
            v = self._var.va
            dirFlow = np.rad2deg(np.arctan2(v,u))

        except MemoryError:
            print '---Data too large for machine memory---'
            print 'Tip: use ax or tx during class initialisation'
            print '---  to use partial data'
            raise

        #Custom return    
        self._var.depth_av_flow_dir = dirFlow 

        # Add metadata entry
        self._History.append('depth averaged flow directions computed')
        print '-Depth averaged flow directions added to FVCOM.Variables.-'

        if debug or self._debug:
            print '...Passed'

    def flow_dir_at_point(self, pt_lon, pt_lat, t_start=[], t_end=[], time_ind=[],
                          exceedance=False, debug=False):
        """
        This function computes flow directions and associated norm
        at any give location.

        Inputs:
        ------
          - pt_lon = longitude in decimal degrees East to find, float number 
          - pt_lat = latitude in decimal degrees North to find, float number 

        Outputs:
        -------
           - flowDir = flowDir at (pt_lon, pt_lat), 1D array
           - norm = velocity norm at (pt_lon, pt_lat), 1D array

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
        u = self._var.ua
        v = self._var.va

        #Extraction at point
        # Finding closest point
        index = closest_point([pt_lon], [pt_lat],
                              self._grid.lonc,
                              self._grid.latc, debug=debug)[0]
        if debug:
            print 'Extraction of u and v at point...'
        U = self.interpolation_at_point(u, pt_lon, pt_lat, index=index,
                                        debug=debug)  
        V = self.interpolation_at_point(v, pt_lon, pt_lat, index=index,
                                        debug=debug)       
        #Checking if dir_flow already computed
        if not hasattr(self._var, 'depth_av_flow_dir'):
            #Compute directions
            if debug:
                print 'Computing arctan2 and norm...'
            dirFlow = np.rad2deg(np.arctan2(V,U))#

        else:
            dirFlow = self.interpolation_at_point(self._var.depth_av_flow_dir,
                                                  pt_lon, pt_lat,
                                                  index=index, debug=debug) 

        #Compute velocity norm
        norm = ne.evaluate('sqrt(U**2 + V**2)')

        #use only the time indices of interest
        if not argtime==[]:
            dirFlow = dirFlow[argtime[:]]
            norm = norm[argtime[:]] 

        if debug:
            print '...Passed'
        #Rose diagram
        self._plot.rose_diagram(dirFlow, norm)
        if exceedance:
            self.exceedance(norm, debug=debug)

        return dirFlow, norm

#    def ebb_flood_split_at_point(self, pt_lon, pt_lat,
#                                 t_start=[], t_end=[], time_ind=[], debug=False):
#        """
#        This functions computes time indices for ebb and flood but also the 
#        principal flow directions and associated variances
#        at any given point.
#
#        Inputs:
#        ------
#          - pt_lon = longitude in decimal degrees East to find, float number 
#          - pt_lat = latitude in decimal degrees North to find,float number 
#
#        Outputs:
#        -------
#          - floodIndex = flood time index, 1D array of integers
#          - ebbIndex = ebb time index, 1D array of integers
#          - pr_axis = principal flow ax1s, float number in degrees
#          - pr_ax_var = associated variance, float number
#
#        Keywords:
#        --------
#          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
#                      or time index as an integer
#          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
#                    or time index as an integer
#          - time_ind = time indices to work in, 1D array of integers 
#        
#        Notes:
#        -----
#          - may take time to compute if time period too long
#          - directions between -180 and 180 deg., i.e. 0=East, 90=North,
#            +/-180=West, -90=South
#          - use time_ind or t_start and t_end, not both
#          - assume that flood is aligned with principal direction
#        """
#        debug = debug or self._debug
#        if debug:
#            start = time.time()
#            print 'Computing principal flow directions...'
#
#        # Find time interval to work in
#        argtime = []
#        if not time_ind==[]:
#            argtime = time_ind
#        elif not t_start==[]:
#            if type(t_start)==str:
#                argtime = time_to_index(t_start, t_end,
#                                        self._var.matlabTime,
#                                        debug=debug)
#            else:
#                argtime = arange(t_start, t_end)
#
#        #Choose the right pair of velocity components
#        u = self._var.ua
#        v = self._var.va
#
#        #Extraction at point
#        # Finding closest point
#        index = closest_point([pt_lon], [pt_lat],
#                              self._grid.lonc,
#                              self._grid.latc, debug=debug)[0]
#        if debug:
#            print 'Extraction of u and v at point...'
#        U = self.interpolation_at_point(u, pt_lon, pt_lat, index=index,
#                                        debug=debug)  
#        V = self.interpolation_at_point(v, pt_lon, pt_lat, index=index,
#                                        debug=debug) 
#
#        #use only the time indices of interest
#        if not argtime==[]:
#            U = U[argtime[:]]
#            V = V[argtime[:]] 
#
#        #WB version of BP's principal axis
#        if debug:
#            print 'Computin principal axis at point...'
#        pr_axis, pr_ax_var = principal_axis(U, V)
#
#        #ebb/flood split
#        if debug:
#            print 'Splitting ebb and flood at point...'
#        # reverse 0-360 deg convention
#       ra = (-pr_axis - 90.0) * np.pi /180.0
#        if ra>np.pi:
#            ra = ra - (2.0*np.pi)
#        elif ra<-np.pi:
#            ra = ra + (2.0*np.pi)    
#        dirFlow = np.arctan2(V,U)
#        #Define bins of angles
#        if ra == 0.0:
#            binP = [0.0, np.pi/2.0]
#            binP = [0.0, -np.pi/2.0]
#        elif ra > 0.0:
#            if ra == np.pi:
#                binP = [np.pi/2.0 , np.pi]
#                binM = [-np.pi, -np.pi/2.0 ]        
#            elif ra < (np.pi/2.0):
#                binP = [0.0, ra + (np.pi/2.0)]
#                binM = [-((np.pi/2.0)-ra), 0.0]
#            else:
#                binP = [ra - (np.pi/2.0), np.pi]
#                binM = [-np.pi, -np.pi + (ra-(np.pi/2.0))]
#        else:
#            if ra == -np.pi:
#                binP = [np.pi/2.0 , np.pi]
#                binM = [-np.pi, -np.pi/2.0]
#            elif ra > -(np.pi/2.0):
#                binP = [0.0, ra + (np.pi/2.0)]
#                binM = [ ((-np.pi/2.0)+ra), 0.0]
#            else:
#                binP = [np.pi - (ra+(np.pi/2.0)) , np.pi]
#                binM = [-np.pi, ra + (np.pi/2.0)]
#                               
#        test = (((dirFlow > binP[0]) * (dirFlow < binP[1])) +
#                ((dirFlow > binM[0]) * (dirFlow < binM[1])))
#        floodIndex = np.where(test == True)[0]
#        ebbIndex = np.where(test == False)[0]
#
#        #TR fit with Rose diagram angle convention
#        #pr_axis = pr_axis - 90.0
#        #if pr_axis<0.0:
#        #    pr_axis[ind] = pr_axis[ind] + 360   
#
#        if debug:
#            end = time.time()
#            print "...processing time: ", (end - start)
#
#        return floodIndex, ebbIndex, pr_axis, pr_ax_var

    def ebb_flood_split_at_point(self, pt_lon, pt_lat,
                                 t_start=[], t_end=[], time_ind=[], debug=False):
        """
        This functions computes time indices for ebb and flood but also the 
        principal flow directions and associated variances
        at any given point.

        Inputs:
        ------
          - pt_lon = longitude in decimal degrees East to find, float number 
          - pt_lat = latitude in decimal degrees North to find,float number 

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
        u = self._var.ua
        v = self._var.va

        #Extraction at point
        # Finding closest point
        index = closest_point([pt_lon], [pt_lat],
                              self._grid.lonc,
                              self._grid.latc, debug=debug)[0]
        if debug:
            print 'Extraction of u and v at point...'
        U = self.interpolation_at_point(u, pt_lon, pt_lat, index=index,
                                        debug=debug)  
        V = self.interpolation_at_point(v, pt_lon, pt_lat, index=index,
                                        debug=debug) 

        #use only the time indices of interest
        if not argtime==[]:
            U = U[argtime[:]]
            V = V[argtime[:]] 

        #WB version of BP's principal axis
        #Assuming principal axis = flood heading
        #determine principal axes - potentially a problem if axes are very kinked
        #   since this would misclassify part of ebb and flood
        if debug: print 'Computing principal axis at point...'
        pr_axis, pr_ax_var = principal_axis(U, V)

        if debug: print 'Computing ebb/flood intervals...'
        #Defines interval
        flood_heading = np.array([-90, 90]) + pr_axis
        #initialise matrix
        s_signed_all = np.empty(U.shape)
        s_signed_all.fill(np.nan)
        PA_all = np.zeros(U.shape)
        dir_all = np.arctan2(U,U) * 180 / np.pi
        ind = np.where(dir_all<0)
        dir_all[ind] = dir_all[ind] + 360     

        # sign speed - eliminating wrap-around
        dir_PA = dir_all - pr_axis
        dir_PA[dir_PA < -90] += 360
        dir_PA[dir_PA > 270] -= 360

        #dir_PA[dir_PA<-90] = dir_PA(dir_PA<-90) + 360;
        #dir_PA(dir_PA>270) = dir_PA(dir_PA>270) - 360;

        #general direction of flood passed as input argument
        floodIndex = np.where((dir_PA >= -90) & (dir_PA<90))
        ebbIndex = np.arange(dir_PA.shape[0])
        ebbIndex = np.delete(ebbIndex,floodIndex[:]) 

        if debug:
            end = time.time()
            print "...processing time: ", (end - start)

        return floodIndex, ebbIndex, pr_axis, pr_ax_var

    def speed_histogram(self, pt_lon, pt_lat,
                        t_start=[], t_end=[], time_ind=[], debug=False):
        """
        This function plots the histogram of occurrences for the signed
        flow speed at any given point.

        Inputs:
        ------
          - pt_lon = longitude in decimal degrees East to find, float number 
          - pt_lat = latitude in decimal degrees North to find,float number 

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

        pI, nI, pa, pav = self.ebb_flood_split_at_point(pt_lon, pt_lat,
                          t_start=t_start, t_end=t_end, time_ind=time_ind,
                          debug=debug)
        dirFlow, norm = self.flow_dir_at_point(pt_lon, pt_lat,
                          t_start=t_start, t_end=t_end, time_ind=time_ind,
                          exceedance=False, debug=debug)
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

    def interpolation_at_point(self, var, pt_lon, pt_lat, index=[], debug=False):
        """
        This function interpolates any given variables at any give location.

        Inputs:
        ------
          - var = any FVCOM grid data or variable, numpy array
          - pt_lon = longitude in decimal degrees East to find, float number
          - pt_lat = latitude in decimal degrees North to find, float number

        Outputs:
        -------
           - varInterp = var interpolated at (pt_lon, pt_lat)

        Keywords:
        --------
          - index = element index, integer. Use only if closest element index
                    is already known

        Notes:
        -----
          - use index if closest element already known
        """
        debug = (debug or self._debug)
        if debug:
            print 'Interpolaling at point...'
        lonc = self._grid.lonc[:]
        latc = self._grid.latc[:]
        xc = self._grid.xc[:]
        yc = self._grid.yc[:]
        lon = self._grid.lon[:]
        lat = self._grid.lat[:]
        trinodes = self._grid.trinodes[:]

        if index==[]:
            # Find indices of the closest element
            index = closest_point([pt_lon], [pt_lat], lonc, latc, debug=debug)[0]
        # Conversion (lon, lat) to (x, y)
        pt_x = interp_at_point(self._grid.x, pt_lon, pt_lat, lon, lat,
                               index=index, trinodes=trinodes, debug=debug)
        pt_y = interp_at_point(self._grid.y, pt_lon, pt_lat, lon, lat,
                               index=index, trinodes=trinodes, debug=debug)
        #change in function of the data you dealing with
        if any(i == self._grid.nnode for i in var.shape):
            if debug:
                start = time.time() 
            varInterp = interpN_at_pt(var, pt_x, pt_y, xc, yc, index, trinodes,
                                      self._grid.aw0, self._grid.awx, self._grid.awy,
                                      debug=debug)
            if debug:
                end = time.time()
                print "Processing time: ", (end - start) 
        else:
            triele = self._grid.triele[:]
            if debug:
                start = time.time() 
            varInterp = interpE_at_pt(var, pt_x, pt_y, xc, yc, index, triele,
                                      trinodes, self._grid.a1u, self._grid.a2u,
                                      debug=debug)
            if debug:
                end = time.time()
                print "Processing time: ", (end - start)         

        return varInterp

    def exceedance(self, var, pt_lon=[], pt_lat=[], debug=False):
        """
        This function calculates the excedence curve of a var(time)
        at any given point.

        Inputs:
        ------
          - var = given quantity, 1 or 2D array of n elements, i.e (time) or (time,ele)

        Keywords:
        --------
          - pt_lon, pt_lat = coordinates, float numbers.
                             Necessary if var = 2D (i.e. [time, nnode or nele]
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

        #Distinguish between 1D and 2D var
        if len(var.shape)>1:
            if pt_lon==[] or pt_lat==[]:
                print 'Lon, lat coordinates are needed'
                sys.exit()
            signal = self.interpolation_at_point(var, pt_lon, pt_lat, debug=debug)
        else:
            signal=var
        
        Max = max(signal)	
        dy = (Max/30.0)
        Ranges = np.arange(0,(Max + dy), dy)
        Exceedance = np.zeros(Ranges.shape[0])
        dt = self._var.julianTime[1] - self._var.julianTime[0]
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
        #error=np.ones(Exceedance.shape) * np.std(Exceedance)
        #if debug: print "Error: ", str(np.std(Exceedance))
        self._plot.plot_xy(Exceedance, Ranges, #yerror=error,
                           yLabel='Amplitudes',
                           xLabel='Exceedance probability in %')

        return Exceedance, Ranges

    def vorticity(self, debug=False):
        """
        This method creates a new variable: 'depth averaged vorticity (1/s)'
        -> FVCOM.Variables.depth_av_vorticity
     
        Notes:
        -----
          - Can take time over the full domain
        """
        debug = (debug or self._debug)
        if debug:
            print 'Computing vorticity...'
            start = time.time()

        t = arange(self._grid.ntime)  

        #Surrounding elements
        n1 = self._grid.triele[:,0]
        n2 = self._grid.triele[:,1]
        n3 = self._grid.triele[:,2]
        #TR comment: not quiet sure what this step does
        n1[np.where(n1==0)[0]] = self._grid.trinodes.shape[1]
        n2[np.where(n2==0)[0]] = self._grid.trinodes.shape[1]
        n3[np.where(n3==0)[0]] = self._grid.trinodes.shape[1]
        #TR quick fix: due to error with pydap.proxy.ArrayProxy
        #              not able to cop with numpy.int
        n1 = int(n1)
        n2 = int(n2)
        n3 = int(n3)

        if debug:
            end = time.time()
            print "Check element=0, computation time in (s): ", (end - start)
            print "start np.multiply" 
        
        dvdx = np.zeros((self._grid.ntime,self._grid.nele))
        dudy = np.zeros((self._grid.ntime,self._grid.nele))

        j=0
        for i in t:
            dvdx[j,:] = np.multiply(self._grid.a1u[0,:], self._var.va[i,:]) \
                      + np.multiply(self._grid.a1u[1,:], self._var.va[i,n1]) \
                      + np.multiply(self._grid.a1u[2,:], self._var.va[i,n2]) \
                      + np.multiply(self._grid.a1u[3,:], self._var.va[i,n3])
            dudy[j,:] = np.multiply(self._grid.a2u[0,:], self._var.ua[i,:]) \
                      + np.multiply(self._grid.a2u[1,:], self._var.ua[i,n1]) \
                      + np.multiply(self._grid.a2u[2,:], self._var.ua[i,n2]) \
                      + np.multiply(self._grid.a2u[3,:], self._var.ua[i,n3])
            j+=1
        if debug:
            print "loop number ", i

        vort = dvdx - dudy

        # Add metadata entry
        self._var.depth_av_vorticity = vort
        self._History.append('depth averaged vorticity computed')
        print '-Depth averaged vorticity added to FVCOM.Variables.-'

        if debug:
            end = time.time()
            print "Computation time in (s): ", (end - start) 

    def vorticity_over_period(self, time_ind=[], t_start=[], t_end=[], debug=False):
        """
        This function computes the depth averaged vorticity for a time period.
     
        Outputs:
        -------
          - vort = horizontal vorticity (1/s), 2D array (time, nele)

        Keywords:
        -------
          - time_ind = time indices to work in, list of integers
          - t_start = start time, as a string ('yyyy-mm-ddThh:mm:ss'),
                     or time index as an integer
          - t_end = end time, as a string ('yyyy-mm-ddThh:mm:ss'),
                    or time index as an integer
        Notes:
        -----
          - Can take time over the full domain
        """
        debug = (debug or self._debug)
        if debug:
            print 'Computing vorticity...'
            start = time.time()

        # Find time interval to work in
        t = []
        if not time_ind==[]:
            t = time_ind
        elif not t_start==[]:
            if type(t_start)==str:
                t = time_to_index(t_start, t_end, self._var.matlabTime, debug=debug)
            else:
                t = arange(t_start, t_end)
        else:
            t = arange(self._grid.ntime)
            self.vorticity() 

        #Checking if vorticity already computed
        if not hasattr(self._var, 'depth_av_vorticity'): 
            #Surrounding elements
            n1 = self._grid.triele[:,0]
            n2 = self._grid.triele[:,1]
            n3 = self._grid.triele[:,2]
            #TR comment: not quiet sure what this step does
            n1[np.where(n1==0)[0]] = self._grid.trinodes.shape[1]
            n2[np.where(n2==0)[0]] = self._grid.trinodes.shape[1]
            n3[np.where(n3==0)[0]] = self._grid.trinodes.shape[1]
            #TR quick fix: due to error with pydap.proxy.ArrayProxy
            #              not able to cop with numpy.int
            n1 = int(n1)
            n2 = int(n2)
            n3 = int(n3)

            if debug:
                end = time.time()
                print "Check element=0, computation time in (s): ", (end - start)
                print "start np.multiply" 
        
            dvdx = np.zeros((t.shape[0],self._grid.nele))
            dudy = np.zeros((t.shape[0],self._grid.nele))

            j=0
            for i in t:
                dvdx[j,:] = np.multiply(self._grid.a1u[0,:], self._var.va[i,:]) \
                          + np.multiply(self._grid.a1u[1,:], self._var.va[i,n1]) \
                          + np.multiply(self._grid.a1u[2,:], self._var.va[i,n2]) \
                          + np.multiply(self._grid.a1u[3,:], self._var.va[i,n3])
                dudy[j,:] = np.multiply(self._grid.a2u[0,:], self._var.ua[i,:]) \
                          + np.multiply(self._grid.a2u[1,:], self._var.ua[i,n1]) \
                          + np.multiply(self._grid.a2u[2,:], self._var.ua[i,n2]) \
                          + np.multiply(self._grid.a2u[3,:], self._var.ua[i,n3])
                j+=1
            if debug:
                print "loop number ", i

            vort = dvdx - dudy
        else:
            vort = self._var.depth_av_vorticity[t[:], :]

        if debug:
            end = time.time()
            print "Computation time in (s): ", (end - start) 
        return vort

    def depth(self, debug=False):
        """
        This method creates a new grid variable: 'depth2D' (m)
        -> FVCOM.Grid.depth2D

        Notes:
        -----
          - depth convention: 0 = free surface
          - Can take time over the full domain
        """
        debug = debug or self._debug
        if debug:
            start = time.time()

        print "Computing depth..."
        #Compute depth      
        size = self._grid.nele
        size1 = self._grid.ntime
        size2 = self._grid.nlevel
        elc = np.zeros((size1, size))
        hc = np.zeros((size))

        try:
            for ind, value in enumerate(self._grid.trinodes):
                elc[:, ind] = np.mean(self._var.el[:, value], axis=1)
                hc[ind] = np.mean(self._grid.h[value])

            dep = self._var.el[:,:] + h[None,:]
        except MemoryError:
            print '---Data too large for machine memory---'
            print 'Tip: use ax or tx during class initialisation'
            print '---  to use partial data'
            raise

        if debug:
            end = time.time()
            print "Computation time in (s): ", (end - start)

        # Add metadata entry
        self._grid.depth2D = dep
        self._History.append('depth 2D computed')
        print '-Depth 2D added to FVCOM.Variables.-'

    def depth_at_point(self, pt_lon, pt_lat, index=[], debug=False):
        """
        This function computes the depth at any given point.

        Inputs:
        ------
          - pt_lon = longitude in decimal degrees East, float number
          - pt_lat = latitude in decimal degrees North, float number

        Outputs:
        -------
          - dep = depth, 2D array (ntime, nlevel)

        Keywords:
        --------
          - index = element index, interger

        Notes:
        -----
          - depth convention: 0 = free surface
          - index is used in case one knows already at which
            element depth is requested
        """
        debug = debug or self._debug
        if debug:
            print "Computing depth..."
            start = time.time()

        #Finding index
        if index==[]:      
            index = closest_point([pt_lon], [pt_lat],
                                  self._grid.lonc,
                                  self._grid.latc, debug=debug)[0]

        if not hasattr(self._grid, 'depth2D'):
            #Compute depth
            h = self.interpolation_at_point(self._grid.h, pt_lon, pt_lat,
                                            index=index, debug=debug)
            el = self.interpolation_at_point(self._var.el, pt_lon, pt_lat,
                                             index=index, debug=debug)

            dep = el + h
        else:
            dep = self.interpolation_at_point(self._grid.depth2D, pt_lon, pt_lat,
                                            index=index, debug=debug)
        if debug:
            end = time.time()
            print "Computation time in (s): ", (end - start)

        return dep

    def depth_averaged_power_density(self, debug=False):
        """
        This method creates a new variable: 'depth averaged power density' (W/m2)
        -> FVCOM.Variables.depth_av_power_density
    
        Description:
        -----------
        The power density (pd) is then calculated as follows:
            pd = 0.5*1025*(u**3)
    
        Notes:
        -----
          - This may take some time to compute depending on the size
            of the data set
        """
        debug = (debug or self._debug)
        if debug: print "Computing depth averaged power density..."
    
        if not hasattr(self._var, 'hori_velo_norm'):
            self.hori_velo_norm(debug=debug)
        if debug: print "Computing powers of hori velo norm..."
        #u = self._var.hori_velo_norm
        #pd = ne.evaluate('0.5*1025.0*(u**3)')
        pd = 0.5*1025.0*np.power(self._var.hori_velo_norm,3.0)
    
        # Add metadata entry
        self._var.depth_av_power_density = pd
        self._History.append('depth averaged power density computed')
        print '-Depth averaged power density to FVCOM.Variables.-' 

    def depth_averaged_power_assessment(self, power_mat,  
                                        cut_in=1.0, cut_out=4.5, debug=False):
        """
        This method creates a new variable: 'depth averaged power assessment' (W/m2)
        -> FVCOM.Variables.depth_av_power_assessment

        Description:
        -----------
        This function performs tidal turbine power assessment by accounting for
        cut-in and cut-out speed, power curve/function (pc):
            Cp = pc(u)
           (where u is the flow speed)

        The power density (pd) is then calculated as follows:
            pd = Cp*(1/2)*1025*(u**3)

        Inputs:
        ------
          - power_mat = power matrix (u,Ct(u)), 2D array (2,n),
                        u being power_mat[0,:] and Ct(u) being power_mat[1,:]

        Keywords:
        --------
          - cut_in = cut-in speed in m/s, float number
          - cut_out = cut-out speed in m/s, float number

        Notes:
        -----
          - This may take some time to compute depending on the size
            of the data set
        """
        debug = (debug or self._debug)
        if debug: print "Computing depth averaged power density..."

        if not hasattr(self._var, 'depth_av_power_density'):
            if debug: print "Computing power density..."
            self.depth_averaged_power_density(debug=debug)

        if debug: print "Initialising power curve..."
        Cp = interp1d(power_mat[0,:],power_mat[1,:])

        u = self._var.hori_velo_norm
        pd = self._var.depth_av_power_density

        pa = Cp(u)*pd

        if debug: print "finding cut-in and out..."
        #TR comment huge bottleneck here
        #ind = np.where(pd<pdin)[0]
        #if not ind.shape[0]==0:
        #    pd[ind] = 0.0
        for i in range(pa.shape[0]):
            for j in range(pa.shape[1]):
                if u[i,j] < cut_in:
                   pa[i,j] = 0.0 

        paout = Cp(cut_out)*0.5*1025.0*(cut_out**3.0)
        #TR comment huge bottleneck here
        #ind = np.where(pd>pdout)[0]
        #if not ind.shape[0]==0:
        #    pd[ind] = pdout
        for i in range(pa.shape[0]):
            for j in range(pa.shape[1]):
                if u[i,j] > cut_out:
                   pa[i,j] = paout     

        # Add metadata entry
        self._var.depth_av_power_assessment = pd
        self._History.append('depth averaged power assessment computed')
        print '-Depth averaged power assessment to FVCOM.Variables.-'   

    def Harmonic_analysis_at_point(self, pt_lon, pt_lat,
                                   time_ind=[], t_start=[], t_end=[],
                                   elevation=True, velocity=False,
                                   debug=False, **kwarg):
        '''
        Description:
        -----------
        This function performs a harmonic analysis on the sea surface elevation
        time series or the velocity components timeseries.

        Inputs:
        ------
          - pt_lon = longitude in decimal degrees East, float number
          - pt_lat = latitude in decimal degrees North, float number

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
        #TR_comments: Add debug flag in Utide: debug=self._debug
        index = closest_point([pt_lon], [pt_lat],
                              self._grid.lonc,
                              self._grid.latc, debug=debug)[0]
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
            u = self.interpolation_at_point(self._var.ua, pt_lon, pt_lat,
                                            index=index, debug=debug)  
            v = self.interpolation_at_point(self._var.va, pt_lon, pt_lat,
                                            index=index, debug=debug) 
            if not argtime==[]:
                time = time[argtime[:]]
                u = u[argtime[:]]
                v = v[argtime[:]]

            lat = self._grid.lat[index]
            harmo = solve(time, u, v, lat, **kwarg)

        if elevation:
            time = self._var.matlabTime[:]
            el = self.interpolation_at_point(self._var.el, pt_lon, pt_lat,
                                             index=index, debug=debug)

            if not argtime==[]:
                time = time[argtime[:]]
                el = el[argtime[:]]

            lat = self._grid.lat[index]
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
