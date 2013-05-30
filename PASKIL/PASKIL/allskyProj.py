#Copyright (C) Nial Peters 2009
#
#This file is part of PASKIL.
#
#PASKIL is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#PASKIL is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with PASKIL.  If not, see <http://www.gnu.org/licenses/>.
"""
Introduction:
    
    The allskyProj module provides a projection class which can be used to produce map projections of
    allsky images.



Concepts:
    
    The projections are done using a curved atmosphere model to calculate the field of view distance
    on the surface of the Earth. The image is then projected onto a map using the relevent projection
    for the type of lens used. This map projection is then used to grid the image data in a regular 
    lat/lon grid. The gridded data can then be transformed to whatever map projection is desired (this
    is done by the createMapProjection method). This method returns a matplotlib.toolboxes.basemap
    object, allowing users the use of any of the basemap methods, for example drawing coastlines.



Example:
    
    In the following example the allskyImage object 'im' is projected to an altitude of 300km, and 
    then projected onto an equidistant projection map of the Svalbard area. The coastlines and lines
    of equal latitude and longitude are drawn in and then the figure is saved as a png file.
    
        import allskyProj
        from pylab import savefig
    
        proj=im.projectToHeight(300000) #create a projection object of the data at 300km
        
        #create an azimuthal equidistant map projection 2000x2000km in size centered on 78N 10E
        map_projection=proj.createMapProjection(projection='aeqd',lat_0=78, lon_0=10, width=2000000, height=2000000, resolution='l')
        
        map_projection.drawcoastlines() #draw in the coastlines
        map_projection.drawmeridians(range(-180,180,10)) #draw in lines of constant longitude at a resolution of 10 degrees
        map_projection.drawparallels(range(-90,90,10)) #draw in lines of constant latitude at a resolution of 10 degrees
        
        savefig("fig1.png") #save figure as a png file
        
"""

import math, numpy
import Image, ImageOps
from mpl_toolkits.basemap import Basemap
from matplotlib import cm
from matplotlib.pyplot import gca

from PASKIL import allskyPlot

#define private dictionary for converting between lens projection descriptions and matplotlib.basemap projection descriptions
__proj_codes={'equidistant':'aeqd', 'equisolidangle':'laea', 'gnomonic':'gnom'}

#define private dictionary for converting between image modes and numpy data types
__data_types={'L':'uint8', 'I':'int16', 'RGB':'uint8'}

class projection:
    """
    Holds image data in a format suitable for use in producing map projections.
    """
    
    def __init__(self, im, proj_height, grid_size, background='black'):
        
        #check arguments
        if background not in ['black', 'white']:
            raise ValueError, "Illegal value for background, expecting 'black' or 'white'"
        
        self.__background=background
        self.__allsky_image = im
        
        #define radius of Earth
        Re=6.37E6
         
        #get image info
        image_info=im.getInfo()
        
        #get image mode
        self.__mode=im.getMode()
        
        #Temporary fix! Due to problems with PIL and Matplotlib not really supporting 16bit images properly
        #here we just convert the image to 8bit - hopefully this won't be necessary in the future
        if self.__mode == "I":
            im = im.convertTo8bit()
            self.__mode = 'L'
          
        #ensure that the image is aligned with geographic north
        if image_info['processing'].has_key('alignNorth'):
            if image_info['processing']['alignNorth'] != 'geographic (NESW)':
                im = im.alignNorth(north='geographic', orientation='NESW')
            
        else:
            if not image_info['processing'].has_key('binaryMask'):
                im = im.binaryMask(float(image_info['camera']['fov_angle']))
        
            if not image_info['processing'].has_key('centerImage'):
                im = im.centerImage()
            
            im = im.alignNorth(north = 'geographic')
        
        #center the image (regardless of whether this has been done before)
        im = im.centerImage()
        
        #if the background is white, then apply an inverted binary mask, this reduces the field of view by 1 degree
        if self.__background == 'white':
            im=im.binaryMask(float(image_info['camera']['fov_angle'])-1, inverted=True)
        
        #record fov in radians
        fov_angle=math.radians(float(image_info['camera']['fov_angle']))
        
        self.site_lat=float(image_info['camera']['lat'])
        self.site_lon=float(image_info['camera']['lon'])
        lens_projection=image_info['camera']['lens_projection']
        
        try:
            self.__colour_table=image_info['processing']['applyColourTable']
        except KeyError:
            self.__colour_table=None
        
        #calculate distance shown in image using curved atmosphere model
        self.fov_distance=Re*(fov_angle-math.asin((Re*math.sin(fov_angle))/(Re + proj_height)))
        
        #create map object the same size as the image, with same projection as used by lens
        image_map=Basemap(projection=globals()['__proj_codes'][lens_projection], lat_0=self.site_lat, lon_0=self.site_lon, width=2*self.fov_distance, height=2*self.fov_distance, resolution='l', area_thresh=100)
        
        image = im.getImage()
            
        #convert the image to a numpy array
        im_array=numpy.asarray(image).copy()
        im_array=im_array.swapaxes(1, 0)
        im_array=numpy.array(im_array, dtype=globals()['__data_types'][self.__mode])
        
        #if the original image was not RGB then need to add a dimension to the array (even though it only has length 1), later code requires a 3D array
        if im.getMode()!='RGB':
            im_array.shape=(im_array.shape[0], im_array.shape[1], 1)
        
        #create an array of x,y pixel coordinates corresponding to a lat long grid
        
        #find lats and longs to start and end at
        start_lat=image_map.latmin-3
        end_lat=image_map.latmax+3
        
        #max and min longitudes by looking at the lons of the corners of the map. This might go wrong for some maps - but should just result in parts of the image missing rather than anything more serious
        lllon=image_map.llcrnrlon
        ullon=image_map(image_map.xmin, image_map.ymax, inverse=True)[0]
        lrlon=image_map(image_map.xmax, image_map.ymin, inverse=True)[0]
        urlon=image_map.urcrnrlon
        
        start_lon=min([lllon, ullon, lrlon, urlon])
        end_lon=max([lllon, ullon, lrlon, urlon])
        
        #define increments
        lat_increment=(end_lat-start_lat)/grid_size
        lon_increment=(end_lon-start_lon)/grid_size
        
        #create lats and longs arrays
        lats=[]
        lons=[]
        for i in range(grid_size):
            lats.append(start_lat+(i*lat_increment))
            lons.append(start_lon+(i*lon_increment))
        
        #create array of x,y tuples for each lat and lon which is going to be sampled
        map_coords=numpy.empty((grid_size, grid_size, 2))
        
        for x in range(grid_size):
            for y in range(grid_size):
                map_coords[x, y]=image_map(lons[x], lats[y])
        
        #create array of pixel values in a regular lat lon grid
        if self.__mode=='RGB':
            self.__image_data=numpy.empty((grid_size, grid_size, 3), dtype=globals()['__data_types'][self.__mode])
        else:
            self.__image_data=numpy.empty((grid_size, grid_size, 1), dtype=globals()['__data_types'][self.__mode])
        
        for x in range(grid_size):
            for y in range(grid_size):
                #i and j are the array indices in the original image that correspond to the lats and lons contained in the map coords array at indices x and y.
                i=int(((map_coords[x, y, 0]-image_map.xmin)/(image_map.xmax-image_map.xmin))*im.getSize()[0])
        
                j=im.getSize()[1]-int(((map_coords[x, y, 1]-image_map.ymin)/(image_map.ymax-image_map.ymin))*im.getSize()[1])
                
                #if the lat/lon coordinate is outside of the original image then fill it in with either black or white
                if i >= im_array.shape[0] or j >= im_array.shape[1] or j<0 or i<0:
                    if self.__background == 'white':
                        if im.getMode()=="I":
                            self.__image_data[y, x, :]=65535 #white in 16bit image 
                        else:
                            self.__image_data[y, x, :]=255 #white in RGB and 8bit images
                    else:
                        self.__image_data[y, x, :]=0

                else:
                    self.__image_data[y, x, :]=im_array[i, j, :]

        self.__image_lons=numpy.array(lons)
        self.__image_lats=numpy.array(lats)     

    ###################################################################################
    
    def createMapProjection(self, grid_size=500, colour_bar=True, **kwargs):
        """
        Returns a matplotlib basemap object containing a plot of the map projection described by kwargs.
        The grid_size option sets the number of grid squares that the map plot will be split into to 
        interpolate the image data. A higher number will result in longer processing times but a less
        grainy image.
        
        For a list of possible kwargs, see the matplotlib.toolkits.basemap documentation. This also details 
        the basemap methods which can be used for drawing in the coastlines,meridians etc on the map projection:
        http://matplotlib.sourceforge.net/matplotlib.toolkits.basemap.basemap.html
         
        """
        #create desired map of observatory area
        observatory_map=Basemap(**kwargs)
        
        #define grid sizes for transforming image data
        nx=grid_size
        ny=grid_size
        
        if self.__mode=='RGB':
            #transform image data to fit to map
            red_transformed_data=numpy.array(observatory_map.transform_scalar(self.__image_data[:, :, 0], self.__image_lons, self.__image_lats, ny, nx), dtype=globals()['__data_types'][self.__mode])
            green_transformed_data=numpy.array(observatory_map.transform_scalar(self.__image_data[:, :, 1], self.__image_lons, self.__image_lats, ny, nx), dtype=globals()['__data_types'][self.__mode])
            blue_transformed_data=numpy.array(observatory_map.transform_scalar(self.__image_data[:, :, 2], self.__image_lons, self.__image_lats, ny, nx), dtype=globals()['__data_types'][self.__mode])
            
            #convert the array back into an image
            red_image=Image.fromarray(red_transformed_data)
            green_image=Image.fromarray(green_transformed_data)
            blue_image=Image.fromarray(blue_transformed_data)
        
            #combine RGB channels into a single image
            image=Image.merge('RGB', [red_image, green_image, blue_image])
            
        else:
            #transform image data to fit to map
            transformed_data=numpy.array(observatory_map.transform_scalar(self.__image_data[:, :, 0], self.__image_lons, self.__image_lats, ny, nx), dtype=globals()['__data_types'][self.__mode])
        
            #convert the array back into an image
            image=Image.fromarray(transformed_data)
        
        #need to flip image when converting back from an array
        image=ImageOps.flip(image)
        
        #plot the image. Matplotlib doesn't support 16bit images, so need to convert to 8bit before plotting
        if self.__mode == 'I':
            image=image.convert('L')
        
        if self.__mode == 'RGB':
            observatory_map.imshow(image)
            try:
                ct = self.__allsky_image.getInfo()['processing']['applyColourTable']
            except KeyError:
                ct = None
            try:
                calib_factor = float(self.__allsky_image.getInfo()['processing']['absoluteCalibration'])
            except KeyError:
                calib_factor = None
            if ct is not None:
                allskyPlot.createColourbar(gca(), ct, None)
            
        else:
            observatory_map.imshow(image, cmap=cm.gray) #plot the image, setting cmap to gray to prevent matplotlib applying its own colour table

        return observatory_map
    
    ###################################################################################
    
    def default(self, colour_bar=True):
        """
        Creates a 'standard' map projection of the image and returns it as a matplotlib basemap
        object. The 'standard' is an azimuthal equidistant projection centred on the observation
        site with a width and height equal to three times the field of view distance. The coastlines,
        meridians and parallels are drawn in automatically.
        """
        if self.__background=='white':
            line_colour='black'
        else:
            line_colour='white'
        
        _map=self.createMapProjection(projection='aeqd', colour_bar=colour_bar, lat_0=self.site_lat, lon_0=self.site_lon, resolution='h', width=3*self.fov_distance, height=3*self.fov_distance)
        _map.drawcoastlines(color=line_colour, linewidth=0.5)
        _map.drawmeridians(range(-180, 180, 10), color=line_colour)
        _map.drawparallels(range(-90, 90, 10), color=line_colour)
        _map.drawmapboundary(fill_color=self.__background)
        
        return _map
    
    ###################################################################################          
###################################################################################
