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

    The allskyImage module provides a class of the same name which is used to 
    represent an all-sky image. The class contains methods for performing 
    various manipulations of the image including aligning it with North and 
    applying a false colour scale. PASKIL supports both 16bit and 8bit images,
    however, the routines for 8bit images are considerably faster.


Concepts:

    An allskyImage object has two major constituents, a Python Image Library 
    (PIL) image object which holds the image data itself, and a hash table (or
    dictionary as it is known in Python) containing the image metadata. For 
    details of what metadata is required, and how to load it into PASKIL see 
    the allskyImagePlugins module.
    
    
Example:
    The following example code opens the image file "test.png" using the 
    information in "site_info.txt". It then converts the image to 8bit, applies
    a binary mask giving a 70 degree field of view, centres the image, aligns 
    the top of the image with geomagnetic north and saves it as "testout.png". 
    Note that you will also need to import the relevant plugin:
    

        from PASKIL import allskyImage #import the allskyImage module
        
        #create a new allskyImage object
        im=allskyImage.new("test.png", site_info_file="site_info.txt")
        
        im=im.convertTo8bit()
        im=im.binaryMask(70)
        im=im.centerImage()
        im=im.alignNorth(north='geomagnetic', orientation='NWSE')
        im.save("testout.png")    
"""
################################################################################################################################################################

import sys
import datetime
import os
import math
import warnings

import numpy
import pyexiv2
import pyfits 
import matplotlib
import matplotlib.font_manager
import matplotlib.pyplot
import Image, ImageOps, ImageDraw, ImageFilter, ImageFont, ImageChops 

from PASKIL import misc, allskyImagePlugins, allskyProj, allskyPlot, allskyColour

 
def new(image_filename, site_info_file=None, force=False):
    """
    Creates a new allskyImage object. The image_filename argument specifies the image to be read. The site_info_file 
    option should be the filename of the site information file (if one is required). This is an optional file 
    containing image metadata. The filename of this file is passed to the allskyImagePlugin open method, see
    the allskyImagePlugins module for details. The default value is None, no site_info_file. The force option
    allows you to force PASKIL to use an external plugin for opening the file. This can be useful for overwriting
    incorrect image metadata. The default is False, which means that where possible the image metadata will be read
    from the image header, rather than an external source.
    """    
    #Load correct image plugin to open image
    filetype = allskyImagePlugins.load(image_filename, site_info_file, force)
    
    #Return allskyImage object
    allsky_image = filetype.open(image_filename, site_info_file)

    return allsky_image

###################################################################################

class allskyImage:
    """
    Holds both the image data and the image metadata associated with an all-sky image. Provides methods
    for manipulating both. Unless stated otherwise, all methods return a new allskyImage object.
    """

    def __init__(self, image, image_file, info):
    #This function in run when the class is instanciated. It sets up the class attributes.
    
        #set private class attributes
        self.__loaded = False #shows if the image data has been loaded yet.
        self.__image = image#.copy()
        self.__image.__info = {}
        self.__filename = image_file
        self.__info = {}
        
        self.title = "DEFAULT"
        
        #make hard copies of the info dictionaries 
        self.__info['camera'] = info['camera'].copy()
        self.__info['header'] = info['header'].copy()
        self.__info['processing'] = info['processing'].copy()
        try:
            self.__info['exif'] = info['exif'].copy()
        except KeyError:
            self.__info['exif'] = {}
    
    ###################################################################################
    
    #define getters 
    def getSize(self): 
        """
        Returns a tuple (width,height) containing the size in pixels of the image (equivalent to 
        self.getImage().size)"""
        return self.__image.size
    
    def getFilename(self):
        """
        Returns a string containg the filename of the image. This will be the same as the image_file
        argument passed to the constructor
        """
        return self.__filename
        
    def getImage(self):
        """
        Returns a PIL image object which is a copy of the all-sky image"""
        return self.__image.copy()
        
    def getInfo(self):
        """
        Returns a dictionary object containing four dictionaries ('header','camera', 'processing', 'exif')
        which contain a copy of the image metadata"""
        copy={'camera':self.__info['camera'].copy(), 'header':self.__info['header'].copy(), 'processing':self.__info['processing'].copy(), 'exif':self.__info['exif'].copy()}
        return copy
    
    def getExif(self):
        """
        Returns a dictionary object containing the exif data associated with the image.
        Note that this data is copied from the original image used to create the all-sky
        image and is NOT kept up to date by PASKIL. It is therefore likely that exif 
        tags such as size/orientation etc. will be incorrect with respect to the current
        image data.
        """
        return self.__info['exif'].copy()
    
    def getMode(self):
        """
        Returns a string containing the mode of the image ("RGB","L" etc...). See PIL handbook for 
        details of different image modes"""
        return self.__image.mode
    
    def getColourTable(self):
        try:
            return allskyColour.basicColourTable(self.__info['processing']['applyColourTable'])
        except KeyError:
            return None
        
    ###################################################################################

    def absoluteCalibration(self, spectral_responsivity, exposure_time, const_factor=1.0):
        """
        Returns a new allskyImage object which has been calibrated to kR. This is a lazy
        operation in that the actual pixel values are not changed. Instead, the scaling 
        on the colour bar will be changed when the image is plotted. The spectral 
        responsivity should be in Counts per second per pixel per Rayleigh. Exposure
        time should be in seconds. The constant factor option allows a fixed scaling 
        factor to be applied, for example if transmission through the instrument dome
        is 96%, then const_factor=1.04 will account for this.
        """
        new_info = self.getInfo()
        
        new_info['processing']['absoluteCalibration'] = const_factor / float(spectral_responsivity * exposure_time * 1000)
        
        return allskyImage(self.getImage(), self.__filename, new_info)
        
    ###################################################################################

    def addTimeStamp(self, format, colour="black", fontsize=20):
        """
        Prints the creation time (as specified in info[`header'][`Creation Time']) on the image in 
        a format specified by the format argument. The format string is the same as for time.strftime() 
        see http://docs.python.org/lib/module-time.html. Applying a time stamp before a colour table 
        has been applied will mean that the colour table will be applied to the time stamp as well. 
        A time stamp will also affect any statistical operations performed on the image (for example 
        producing a histogram). It is therefore recommended to apply the time stamp as a final step in 
        processing.
        """
        
        #check that colour table has already been applied
        if ((self.__info['processing'].keys().count('applyColourTable') == 0) and (self.getMode() != "RGB")):
            warnings.warn("Adding a time stamp before applying a colour table will result in the colour table being applied to the time stamp as well!")
            sys.stdout.flush()
            
        #check if a time stamp has already been applied
        if self.__info['processing'].keys().count('addTimeStamp') != 0:
            warnings.warn("A timestamp has already been applied to "+self.__filename)
            return self
        
        #attempt to read time data from header
        try:
            time = datetime.datetime.strptime(self.__info['header']['Creation Time'], "%d %b %Y %H:%M:%S %Z")
        except ValueError:
            time = datetime.datetime.strptime(self.__info['header'] ['Creation Time'] + " GMT", "%d %b %Y %H:%M:%S %Z")
        except KeyError:
            raise  IOError, "Cannot read time data from header for image " + self.__filename
        
        #create copy of image
        new_image = self.__image.copy()
            
        #create a datetime string with the desired format
        time_string = time.strftime(format)
            
        draw = ImageDraw.Draw(new_image)#create draw object of image
        
        #find the font to use
        font_file = matplotlib.font_manager.findfont("FreeSans")
        font = ImageFont.truetype(font_file, size=fontsize)#load font. 
            
        #find size of timestamp
        text_width, text_height=draw.textsize(time_string, font=font)
        
        #if text is too big for image then complain and quit
        if text_width > new_image.size[0] | text_height > new_image.size[1]:
            raise ValueError, "Timestamp is too big for image!"
        
        #insert timestamp
        x_position=int((new_image.size[0]-text_width)/2)
        draw.text((x_position, new_image.size[1]-text_height-4), time_string, font=font, fill=colour)
        
        #create copy of info
        new_info = self.getInfo()
        
        #update processing history
        new_info['processing']['addTimeStamp'] = ""
        
        return allskyImage(new_image, self.__filename, new_info)
        
    ###################################################################################    
    
    def alignNorth(self, north="geographic", orientation='NESW'):
        """
        Aligns the top of the image with either geographic or geomagnetic north depending on the value of 
        the north argument. Default is "geographic", can also be set to "geomagnetic". The right hand edge 
        of the image will be aligned with East. The returned all-sky image will be in a NESW orientation by 
        default but this can be changed to 'NWSE' using the orientation argument. 
        The image must be centered before it can be aligned with North. It is expected that the images are
        in a NWSE orientation before they are processed by PASKIL (i.e. looking upwards).
        """               
        #check that image has already been centered
        if self.__info['processing'].keys().count('centerImage') == 0:
            raise RuntimeError, "Image " + self.__filename + " must be centred before it can be aligned with north."
        
        #copy the info dict, ready to create a new allskyImage
        new_info = self.getInfo()    
        
        #align the image with geographic north
        try:
            if new_info['processing']['alignNorth'].count('NESW') != 0:
                #rotate clockwise since the Image is in a NESW orientation
                new_image = self.__image.rotate(-float(new_info['camera']['cam_rot']))
            elif new_info['processing']['alignNorth'].count('NWSE') != 0:
                #rotate anti-clockwise since the Image is in a NWSE orientation
                new_image = self.__image.rotate(float(new_info['camera']['cam_rot']))
            else:
                #this image was alignedNorth using an old version of PASKIL and
                #is therefore in a NESW orientation
                #rotate clockwise since the Image is in a NESW orientation
                new_image = self.__image.rotate(-float(new_info['camera']['cam_rot']))
                new_info['processing']['alignNorth'] = new_info['processing']['alignNorth'] + "(NESW)"
            
        except KeyError:
            #the image hasn't been aligned North before, we assume it is in NWSE orientation and change the info to reflect this
            new_info['processing']['alignNorth'] = "(NWSE)"
            new_image = self.__image.rotate(float(new_info['camera']['cam_rot']))
        new_info['camera']['cam_rot'] = "0.0"
        
        #if the image does not already have the correct orientation then
        #flip it east west 
        if new_info['processing']['alignNorth'].count(orientation) == 0:
            new_image = ImageOps.mirror(new_image)
                        
        if north=="geomagnetic":
            if orientation == 'NESW':
                new_image = new_image.rotate(float(new_info['camera']['Magn. Bearing']))
            elif orientation == 'NWSE':
                new_image = new_image.rotate(-float(new_info['camera']['Magn. Bearing']))
            else:
                raise(ValueError, "Unknown value for orientation. Expecting \"NESW\" or \"NWSE\"")
            
            new_info['camera']['cam_rot'] = new_info['camera']['Magn. Bearing']
            
        elif north != "geographic":
            raise(ValueError, "Unknown value for north. Expecting \"geomagnetic\" or \"geographic\"")
        
        #update processing history
        new_info['processing']['alignNorth'] = north+" ("+orientation+")"
        
        #return a new allskyImage instance
        return allskyImage(new_image, self.__filename, new_info)
        
    ###################################################################################    
    
    def angle2dist(self, angle):
        """
        Converts an angle (in degrees) from zenith into a radial distance in pixels
        from the image centre.
        """
        if self.__info['camera']['lens_projection'] == 'equidistant':
            #calculate focal length
            focal_length = float(self.__info['camera']['Radius'])/float(self.__info['camera']['fov_angle'])
            
            #calculate radius for masking circle
            radius = int(round(focal_length*angle))
        
        elif self.__info['camera']['lens_projection'] == 'equisolidangle':
            #calculate focal length
            focal_length = float(self.__info['camera']['Radius'])/(2.0*math.sin(math.radians(float(self.__info['camera']['fov_angle']))/2.0))
            
            #calculate radius for masking circle
            radius = int(round(2.0*focal_length*math.sin(math.radians(angle)/2.0)))
        
        else:
            raise ValueError, "Unsupported lens projection type"
        
        return radius
        

    ###################################################################################
        
    def applyColourTable(self, colour_table):
        """
        Applies a colour table to the image, converting the image mode from ``L'' to ``RGB''. 
        The colour_table argument should be a colourTable object as defined in the allskyColour 
        module.
        """
        #cannot apply a colour table to an RGB image
        if self.__image.mode == "RGB":
            raise TypeError, "Cannot apply a colour table to an RGB image"
                
        #check if the image has had the flat field calibration applied
        if self.__info['processing'].keys().count('flatFieldCorrection') == 0:
            warnings.warn("Images should have flat field corrections applied before the colour table is applied")
            
        #check if the image has already had a colour table applied
        if self.__info['processing'].keys().count('applyColourTable') != 0:
            raise RuntimeError, "A colour table has already been applied to " + self.__filename
        
        #get a copy of the image
        new_image = self.getImage()
            
        #apply colour table
        if self.__image.mode != "I": #PIL doesn't support 16bit images, so need to use own routine if "I" mode image
            new_image.putpalette(colour_table.getColourTable())
        else:
            RGB_image = Image.new("RGB", new_image.size, "Black")
            image_pix = new_image.load()
            RGB_pix = RGB_image.load()
            
            for x in range(RGB_image.size[0]):
                for y in range(RGB_image.size[1]):
                    RGB_pix[x, y] = colour_table.colour_table[image_pix[x, y]]
                    
            new_image = RGB_image
            
        new_image = new_image.convert("RGB")
        
        #copy the info
        new_info = self.getInfo()
        
        #update processing history
        new_info['processing']['applyColourTable'] = colour_table.colour_table
        
        return allskyImage(new_image, self.__filename, new_info)

    ###################################################################################    
    
    def binaryMask(self, fov_angle, inverted=False):
        """
        Applies a binary mask to the image, setting pixels outside of the field of view to black. 
        The fov_angle argument should be the field of view in degrees from the centre. The inverted
        options controls whether the mask is black or white, default is False = black.
        """
                
        if fov_angle > self.__info['camera']['fov_angle']:
            raise ValueError, "Field of view is too large for image."
        
        radius = self.angle2dist(fov_angle)
        
        mode = self.__image.mode
        
        if mode == "I":
            white = 65535
        elif mode == "L":
            white = 255
        elif mode == "RGB":
            white = (255, 255, 255)    
        else:
            raise ValueError, "Unsupported image mode"
            
        #calculate bounding box for the circle
        bb_left = int(self.__info['camera']['x_center']) - radius
        bb_top = int(self.__info['camera']['y_center']) - radius
        bb_right = int(self.__info['camera']['x_center']) + radius
        bb_bottom = int(self.__info['camera']['y_center']) + radius
        
        #create a black mask image
        mask = Image.new(mode, self.__image.size, "Black")
        
        #draw white circle
        draw = ImageDraw.Draw(mask)
        draw.ellipse((bb_left, bb_top, bb_right, bb_bottom), fill=white)
        
        #apply the mask to the image
        if mode == "L" or mode == "RGB":
            if inverted:
                mask = ImageChops.invert(mask)
                new_image = ImageChops.lighter(self.__image, mask)
            else:
                new_image = ImageChops.multiply(self.__image, mask)
        
        elif mode == "I":
            #if the image is 16bit then cannot use the ImageChops module, so use own multiplication routine
            if inverted:
                im_pix = numpy.asarray(self.__image)
                mask_pix = numpy.asarray(mask)
                
                new_image = Image.fromarray(numpy.maximum(im_pix, 65535-mask_pix))
            
            else:
                im_pix = numpy.asarray(self.__image)
                mask_pix = numpy.asarray(mask)
                
                new_image = Image.fromarray(numpy.minimum(im_pix, mask_pix))
        else:
            raise ValueError, "Unsupported image mode"
        
        new_info = self.getInfo()
        
        #update radius value
        new_info['camera']['Radius'] = radius
        
        #update fov_angle value
        new_info['camera']['fov_angle'] = fov_angle
        
        #update the processing history
        new_info['processing']['binaryMask'] = str(fov_angle)
        
        return allskyImage(new_image, self.__filename, new_info)
    
    ###################################################################################        

    def centerImage(self):
        """
        Resizes and centres the image about the field of view, finding the best fit for the circular 
        field of view in a rectangular image. The image returned will be square, with dimensions of
        2*Radiusx2*Radius.
        """

        #check if image has already been centered
        if self.__info['processing'].keys().count('centerImage') != 0:
            warnings.warn("Image "+self.__filename+" has already been centered")
        
        #first, the image field of view is centered in the image
        #get the bounding box of the image (box around non-zero parts of the image)
        r = int(self.__info['camera']['Radius'])
        x_0 = int(self.__info['camera']['x_center'])
        y_0 = int(self.__info['camera']['y_center'])
        width, height = self.__image.size
        
        left = x_0 - r
        if left < 0:
            left = 0
        right = x_0 + r
        if right > (width -1):
            right = width - 1
        upper = y_0 - r
        if upper < 0:
            upper = 0
        lower = y_0 + r
        if lower > height -1:
            lower = height

        bounding_box = (left, upper, right, lower)
        
        #crop the image to the size of the bounding box
        new_image = self.__image.crop(bounding_box)
        
        #the image is now pasted into a new image which encompasses the entire (theoretical) circular field of view. This is done to allow PASKIL to cope with images taken with non-circular fields of view.
        
        #create new square image with dimensions RadiusxRadius
        square_image = Image.new(self.__image.mode, (2*r, 2*r), color='black')
        
        #paste image into correct position in square image.
        width, height = new_image.size
        square_image.paste(new_image, (r-int(width/2), r-int(height/2), r-int(width/2)+width, r-int(height/2)+height))     
        
        #create a new info dictionary
        new_info = self.getInfo()
        
        #update image center data
        new_info['camera']['x_center'] = int((square_image.size[0]/2) +0.5) #x coordinate of center
        new_info['camera']['y_center'] = int((square_image.size[1]/2) +0.5) #y coordinate of center
        
        #update processing history
        new_info['processing']['centerImage']=""
        
        #create new allskyImage object
        new_asimage = allskyImage(square_image, self.__filename, new_info)
        
        return new_asimage
    
    ###################################################################################
    
    def convertTo8bit(self):
        """
        Converts an "I" mode image into an "L" mode image.
        """
        
        #update processing history
        info = self.getInfo()
        info['processing']['convertTo8bit'] = ""
        
        #create new allskyImage object with an 8bit image
        new_image = allskyImage(self.__image.convert("L"), self.__filename, info)
     
        return new_image
        
    ###################################################################################    
    
    def createQuicklook(self, size=(480, 640), timestamp="%a %b %d %Y, %H:%M:%S %Z", fontsize=16):
        """
        Returns an PIL Image object which contains a thumbnail image with a timestamp appended to
        the bottom of it. The size option should be a tuple specifying the thumbnail size in 
        pixels. Note that the actual thumbnail produced will be 24 pixels higher due to the size of
        the timestamp. This method also preserves the aspect ratio of the image, so the thumbnail 
        may have a different ratio to the one specified. The timestamp option should be a string 
        specifying the format of the timestamp (see http://docs.python.org/lib/module-time.html).
        The fontsize option should be an integer specifying the font size. 
        """
    
        #create new allskyImage object
        new_image = allskyImage(self.__image, self.__filename, self.__info)
        
        #resize image
        quicklook = new_image.resize(size)
        
        if timestamp != None:
            #append 24 pixels to the bottom of the image
            if self.__image.mode == "RGB":
                white=(255, 255, 255)
            elif self.__image.mode == "L":
                white=255
            elif self.__image.mode == "I":
                white=65536
            else:
                raise ValueError, "Image mode not supported yet"
            
            im=Image.new(self.__image.mode, (quicklook.getSize()[0], quicklook.getSize()[1]+24), white) #create new image which is 24 pixels bigger
            im.paste(quicklook.getImage(), (0, 0, quicklook.getSize()[0], quicklook.getSize()[1]))
            
            quicklook=allskyImage(im, self.__filename, self.__info)
            
            quicklook=quicklook.addTimeStamp(timestamp, fontsize=fontsize)
        
        return quicklook.getImage()
                    
    ###################################################################################

    def flatFieldCorrection(self, calibration):
        """
        Applies a flat field correction to the image. This is needed due to the angular 
        dependance of the transmission through the lens. The calibration argument should 
        be an allskyCalib.calibration object.
        """
    
        #check that image has been centered
        if self.__info['processing'].keys().count('centerImage') == 0:
            raise RuntimeError, "Image must be centered before it can be calibrated"
            
        #check if the image has already been calibrated
        if self.__info['processing'].keys().count('flatFieldCorrection') != 0:
            warnings.warn("Image has already been calibrated")
        
        new_image = self.getImage() #copy image
        image_pix = new_image.load() #load pixel values
        
        for x in range(new_image.size[0]):#for x in range image width
            for y in range(new_image.size[1]):#for y in range image height
                #for each x,y find the angle from the center
                angle = self.xy2angle(x, y)
                
                #skip angles outside of the field of view
                if angle >= self.__info['camera']['fov_angle']:
                    continue
                    
                #apply correction to pixels inside the field of view
                gradient = calibration.calibration_data[int(angle)+1]-calibration.calibration_data[int(angle)]
                correction = 1.0/(calibration.calibration_data[int(angle)] + (angle-float(int(angle)))*gradient)
                image_pix[x, y] = int((image_pix[x, y]*correction)+0.5)
        
        #update processing history
        new_info = self.getInfo()
        new_info['processing']['flatFieldCorrection']=""
        
        return allskyImage(new_image, self.__filename, new_info)
        
    ###################################################################################
    def getStrip(self, angle, strip_width):
        
        #check that image has been aligned with north (if so then it must have been centred)
        if self.__info['processing'].keys().count('alignNorth') == 0:
            raise RuntimeError, "Image must be aligned with North."
                
        #rotate image so that the slice runs from top to bottom
        #the rotation direction depends on the orientation of the image
        if (angle - float(self.__info['camera']['cam_rot'])) != 0.0:          
            if self.__info['processing']['alignNorth'].count('NESW') != 0:
                im = self.__image.rotate(angle - float(self.__info['camera']['cam_rot']))
            elif self.__info['processing']['alignNorth'].count('NWSE') != 0:
                im = self.__image.rotate(float(self.__info['camera']['cam_rot']) - angle)
            else:
                raise ValueError, "getStrip(): Cannot read orientation data from info dict. Try re-aligning the image with North"
    
        #convert the rotated image to a numpy array (im is a PIL Image object)
        im_arr = numpy.asarray(im)
        
        #ensure the array is 3d even if we are not dealing with an RGB image
        if len(im_arr.shape) == 2:
            im_arr = im_arr.reshape((im_arr.shape[0],im_arr.shape[1],1))
        
        radius = int(self.__info['camera']['Radius'])
        #calculate bounding indices of slice
        width = im.size[0]
        centre = int((float(width)/2.0)+0.5) - 1
        
        lower_x = centre - int(strip_width/2)
        upper_x = centre + int(strip_width/2.0 +0.5)
        
        #create an array of zeros to hold the strip data
        strip = numpy.zeros((2*radius,upper_x-lower_x,im_arr.shape[2]),im_arr.dtype)
        
        #the radius of the image may be larger than the image dimensions, in which 
        #case we ensure that the strip is padded with zeros to the size of the radius
        lower_y = int(((2*radius)-im_arr.shape[0])/2)
        upper_y = im_arr.shape[0] + lower_y
        strip[lower_y:upper_y,:,:] = im_arr[:, lower_x:upper_x,:]   
        return strip.swapaxes(0, 1)
    
    ###################################################################################
    
    def histogram(self):
        """
        Returns a histogram of the image. For 'L' mode images this will be a list of 
        length 256, for 'I' mode images it will be a list of length 65536. The histogram
        method cannot be used for RGB images.
        """
        mode = self.getMode()
        
        if mode == "L":
            histogram = self.__image.histogram() #use PIL histogram method for 8bit images
        elif mode == "I":          
            im_pix = numpy.asarray(self.__image) #load pixel values
            histogram = numpy.histogram(im_pix, bins=range(65537))[0]
            
        else:
            raise ValueError, "Unsupported image mode"
        
        return histogram
    
    ###################################################################################    
    
    def keoSanityCheck(self, angle, fov, strip_width=5, colour=(255,0,0), fill=True):
        """
        Returns a PIL image object which is a copy of the allsky image but with the 
        pixels that would be put into a keogram with the specified parameters 
        highlighted. The colour argument controls the highlighting colour.
        """
        
        #make a copy of self to draw onto         
        im = self.getImage()       
        im = im.convert("RGB")
        
        #rotate image so that the slice runs from top to bottom
        #check that image has been aligned with north (if so then it must have been centred)
        if self.__info['processing'].keys().count('alignNorth') == 0:
            raise RuntimeError, "Image must be aligned with North."
                
        #rotate image so that the slice runs from top to bottom
        #the rotation direction depends on the orientation of the image
        if (angle - float(self.__info['camera']['cam_rot'])) != 0.0:          
            if self.__info['processing']['alignNorth'].count('NESW') != 0:
                rot_angle = angle - float(self.__info['camera']['cam_rot'])
                im = im.rotate(rot_angle)
            elif self.__info['processing']['alignNorth'].count('NWSE') != 0:
                rot_angle = float(self.__info['camera']['cam_rot']) - angle
                im = im.rotate(rot_angle)
            else:
                raise ValueError, "keoSanityCheck(): Cannot read orientation data from info dict. Try re-aligning the image with North"
    
        #work out the length of the slice
        if fov[1] >= 90:
            upper_length = self.angle2dist(fov[1]-90)
        else:
            upper_length = self.angle2dist(fov[1])
        if fov[0] >= 90:
            lower_length = self.angle2dist(fov[0]-90)
        else:
            lower_length = self.angle2dist(fov[0])        
        
        #work out the coordinates for the slice
        width, height = self.getSize()
        
        centre = (int((float(width)/2.0)+0.5) - 1,int((float(height)/2.0)+0.5) - 1)

        lower_x = centre[0] - int(strip_width/2)
        upper_x = centre[0] + int(strip_width/2.0 +0.5)
        lower_y = centre[1] - lower_length
        upper_y = centre[1] + upper_length
        
        #draw a rectangle around the slice
        draw = ImageDraw.Draw(im)
        if fill:
            draw.rectangle([lower_x,lower_y,upper_x+1,upper_y+1], outline=colour, fill=colour)
        else:
            draw.rectangle([lower_x,lower_y,upper_x+1,upper_y+1], outline=colour)
        
        #rotate back to orginal image orientation
        im = im.rotate(-rot_angle)
        
        return im
    
    ###################################################################################
    
    def medianFilter(self, n):
        """
        This is a thin wrapper function for the median filter provided by PIL. It replaces each 
        pixel by the median value of the pixels in an nxn square around it (where n is an odd integer).
        """       
        new_image = self.__image.filter(ImageFilter.MedianFilter(n))
        
        #update processing history
        new_info = self.getInfo()
        new_info['processing']['medianFilter'] = n
        
        return allskyImage(new_image, self.__filename, new_info)
        
    ###################################################################################
    
    def _hasColourBar(self):
        """
        Part of the plotting interface. Returns True if the image will be plotted with a
        colour bar, False otherwise.
        """
        try:
            colour_table = self.__info['processing']['applyColourTable']
        except KeyError:
            colour_table = None
        
        if colour_table is not None:
            return True
        else:
            return False
    
    ###################################################################################   
    
    def _plot(self, subplot):
        """
        Part of the plotting interface. Plots the image data into the supplied subplot
        object. 
        """
        
        #turn off the axes
        subplot.yaxis.set_visible(False)
        subplot.xaxis.set_visible(False)
        
        #if the image has a colour table applied, then create a colour bar
        try:
            colour_table = self.__info['processing']['applyColourTable']
        except KeyError:
            colour_table = None
        
        #plot the image data into the axes
        subplot.imshow(self.__image, origin="top", aspect="equal")
        
        if colour_table is not None:
            try:
                calib_factor = float(self.__info['processing']['absoluteCalibration'])
            except KeyError:
                calib_factor = None    
            
            allskyPlot.createColourbar(subplot, colour_table, calib_factor)
            
        if self.title == "DEFAULT":    
        #create title string for image
            image_title = self.__info['header']['Creation Time']
        else:
            image_title = self.title
        
        #add title
        if image_title != None:
            subplot.set_title(image_title)    
          
        return subplot

    ###################################################################################        
        
    def projectToHeight(self, height, grid_size=300, background='black'):
        """
        Returns a projection object which can be used to create map projections of the allsky image.
        See the allskyProj module for details. The height argument should be the altitude in meters
        of the contents of the image. The grid_size option determines the dimensions of the lat,lon
        grid that the image is split into. A larger grid size will result in a less grainy image but 
        longer computation times and higher memory usage. Projections are done using a curved 
        atmosphere model assuming a spherical Earth with a radius of 6.37E6 meters. It should be 
        noted that projected images have 1 degree less field of view than their corresponding all-
        sky images. The background option controls the background colour of the map projection,
        default is black.
        """        
        return allskyProj.projection(self, height, grid_size, background=background)
        
    ###################################################################################
    
    def resize(self, size):
        """
        Resizes the image. The size argument should be a tuple (width,height) where the dimensions
        are in pixels. This method preserves the aspect ratio of the image, so while the returned
        image will always have the specified width, the height may be adjusted.
        """
        
        #check that the new size maintains the aspect ratio of the image
        if float(size[0])/float(self.__image.size[0]) != float(size[1])/float(self.__image.size[1]):
            #if not then change it so it does
            size = (size[0], int((float(size[0])/float(self.__image.size[0]))*float(self.__image.size[1])+0.5))
            
        #resize the image
        resized_image = self.__image.resize(size)
        
        #calculate scaling factors for x and y
        scaling = float(size[0])/float(self.__image.size[0])
        
        #change the header data to reflect the change
        new_info = self.getInfo()
        new_info['camera']['x_center']=int(int(new_info['camera']['x_center'])*scaling+0.5)
        new_info['camera']['y_center']=int(int(new_info['camera']['y_center'])*scaling+0.5)
        new_info['camera']['Radius']=int(int(new_info['camera']['Radius'])*scaling+0.5)
        
        #return resized image
        return allskyImage(resized_image, self.__filename, new_info)
        
    ###################################################################################
    
    def save(self, filename, format="png"):
        """
        Save the image and the meta-data as "filename". The format argument can be:
        
            * "png":  a png image containing all the metadata in the image header
            
            * "jpg": a jpeg image containing all the metadata in the UserComment tag
                     of the exif data.
            
            * "fits": a flexible image transport system file with one hdu per image channel
                  (RGB images that are greyscale images which have been mapped through 
                  a colour table are stored as a single channel and are converted back
                  to RGB on loading) and three hdus containing metadata.
                  
        The default format is "png". Although the format can also be read from the filename,
        "myimage.fits" will be saved as a fits image, not a png.
        """       
        #detect format from filename
        if filename.endswith((".png", ".PNG")):
            format = "png"
        elif filename.endswith((".fits", ".FITS")):
            format = "fits"
        elif filename.endswith((".jpg", ".JPG", ".JPEG", ".jpeg")):
            format = "jpg"
        
        if format == "png": #save as png image
        
            if not filename.endswith((".png", ".PNG")):
                filename=filename+".png"
                
            
            #copy the header data back to the image
            self.__image.info={}
            self.__image.info['header']=str(self.__info['header']) 
            self.__image.info['camera']=str(self.__info['camera'])
            self.__image.info['processing']=str(self.__info['processing'])
            self.__image.info['exif']=str(self.__info['exif'])
            
            #save image
            misc.pngsave(self.__image, filename)
        
        elif format == "jpg": #save as jpeg format
            #save the image data into a jpeg file
            self.__image.save(filename)
            
            #prepare to copy exif data in
            exif_im = pyexiv2.ImageMetadata(filename)
            exif_im.read()
            
            #copy the existing exif data into the saved exif
            existing_exif = self.getExif()
            for tag,value in existing_exif.items():
                try:
                    exif_im[tag].value = value
                except:
                    continue
            
            #now write the PASKIL specific exif tags
            exif_im['Exif.Image.ProcessingSoftware'].value = "PASKIL"
            
            info_no_exif = self.getInfo()
            info_no_exif.pop('exif')
            
            #this should really be stored in the MakerNote tag,
            #but pyexiv2 can't read it back if you put it there - so
            #for now we'll just have to abuse the usercomment tag
            exif_im['Exif.Photo.UserComment'].value = str(info_no_exif)
            
            #write the exif back to the file
            exif_im.write()
        
        elif format == "fits": #save as FITS format
    
            if self.getMode() != "RGB":
                #convert the image object to an array
                data_array=numpy.asarray(self.__image).copy()
                data_array=numpy.rot90(data_array.swapaxes(1, 0)) #images are indexed (x,y) whereas arrays are indexed (y,x)
                
                #create a primary hdu to store the image
                primary_hdu = pyfits.PrimaryHDU(data_array)
                primary_hdu.verify('fix')
                
                #create primary hdu header, this is where all the data used by PASKIL to re-load the file is stored
                primary_hdu_header=primary_hdu.header
                primary_hdu_header.update('PASKIL', 1, "File created using PASKIL")
                primary_hdu_header.update('PSKMODE', 'Intensities', "Image is greyscale")
                primary_hdu_header.update('PSKHEAD', 1, "HDU containing the header dictionary")
                primary_hdu_header.update('PSKCAM', 2, "HDU containing the camera dictionary")
                primary_hdu_header.update('PSKPRO', 3, "HDU containing the processing dictionary")
                primary_hdu_header.update('PSKEXIF', 4, "HDU containing the exif dictionary")
                
            else: #image is RGB
                #convert the image object to an array
                r, g, b=self.__image.split()
                
                data_array= numpy.array([numpy.rot90(numpy.asarray(r).copy().swapaxes(1, 0)), numpy.rot90(numpy.asarray(g).copy().swapaxes(1, 0)), numpy.rot90(numpy.asarray(b).copy().swapaxes(1, 0))])

                #create a primary hdu to store the image
                primary_hdu = pyfits.PrimaryHDU(data_array)
                primary_hdu.verify('fix')
            
                #create primary hdu header, this is where all the data used by PASKIL to re-load the file is stored
                primary_hdu_header=primary_hdu.header
                primary_hdu_header.update('PASKIL', 1, "File created using PASKIL")
                primary_hdu_header.update('PSKMODE', 'RGB', "Image is RGB")
                primary_hdu_header.update('PSKHEAD', 1, "HDU containing the header dictionary")
                primary_hdu_header.update('PSKCAM', 2, "HDU containing the camera dictionary")
                primary_hdu_header.update('PSKPRO', 3, "HDU containing the processing dictionary")
                primary_hdu_header.update('PSKEXIF', 4, "HDU containing the exif dictionary")
                primary_hdu_header.add_comment('Sequence for NAXIS3   : RED, GREEN, BLUE')
            
            
            #create the columns for storing the image header data - this is stored in a separate hdu rather than in the primary hdu's
            #header so that there is no limit on the length of the image header data. Entries such as the color table can be quite big.
            #Each header entry is stored in two variable length columns one for the 'keys' and one for the 'values'.
            
            #find max length of keys and values and convert both to strings for storage in FITS table
            key_length=1
            value_length=1
            data=self.getInfo()['header']
            for key, value in data.iteritems():
                value=str(value)
                data[key]=value #convert values to strings
                if len(key) > key_length:
                    key_length=len(key)
                if len(value) > value_length:
                    value_length=len(value)
            
            header_keys_col=pyfits.Column(name="key", format="A"+str(key_length), array=data.keys())
            header_values_col=pyfits.Column(name="value", format="A"+str(value_length), array=data.values())
            
            
            #find max length of keys and values and convert both to strings for storage in FITS table
            key_length=1
            value_length=1
            data=self.getInfo()['camera']
            for key, value in data.iteritems():
                value=str(value)
                data[key]=value #convert values to strings
                if len(key) > key_length:
                    key_length=len(key)
                if len(value) > value_length:
                    value_length=len(value)
            
            camera_keys_col=pyfits.Column(name="key", format="A"+str(key_length), array=data.keys())
            camera_values_col=pyfits.Column(name="value", format="A"+str(value_length), array=data.values())
            
            
            #find max length of keys and values and convert both to strings for storage in FITS table
            key_length=1
            value_length=1
            data=self.getInfo()['processing']
            for key, value in data.iteritems():
                value=str(value)
                data[key]=value #convert values to strings
                if len(key) > key_length:
                    key_length=len(key)
                if len(value) > value_length:
                    value_length=len(value)

            processing_keys_col=pyfits.Column(name="key", format="A"+str(key_length), array=data.keys())
            processing_values_col=pyfits.Column(name="value", format="A"+str(value_length), array=data.values())
            
            key_length=1
            value_length=1
            data=self.getInfo()['exif']
            for key, value in data.iteritems():
                value=str(value)
                data[key]=value #convert values to strings
                if len(key) > key_length:
                    key_length=len(key)
                if len(value) > value_length:
                    value_length=len(value)
            
            exif_keys_col=pyfits.Column(name="key", format="A"+str(key_length), array=data.keys())
            exif_values_col=pyfits.Column(name="value", format="A"+str(value_length), array=data.values())
            
            
            #create a column definition
            header_cols_def=pyfits.ColDefs([header_keys_col, header_values_col])
            camera_cols_def=pyfits.ColDefs([camera_keys_col, camera_values_col])
            processing_cols_def=pyfits.ColDefs([processing_keys_col, processing_values_col])
            exif_cols_def=pyfits.ColDefs([exif_keys_col, exif_values_col])
            
            #create one extension hdu for each image header library ('header','camera','processing')
            header_hdu=pyfits.new_table(header_cols_def)
            camera_hdu=pyfits.new_table(camera_cols_def)
            processing_hdu=pyfits.new_table(processing_cols_def)
            exif_hdu=pyfits.new_table(exif_cols_def)
            
            #verify hdus
            header_hdu.verify('fix')
            camera_hdu.verify('fix')
            processing_hdu.verify('fix')
            exif_hdu.verify('fix')
            
            #create a hdu list to contain the primary hdu and the extension hdus
            hdulist = pyfits.HDUList([primary_hdu, header_hdu, camera_hdu, processing_hdu, exif_hdu])
            hdulist.verify('fix')
            
            #save to file
            if not filename.endswith((".fits", ".FITS")):
                filename=filename+".fits"
            
            #check if file already exists, if it does, then overwrite it
            if os.path.exists(filename):
                os.remove(filename)
                
            hdulist.writeto(filename)
        
        else:
            raise ValueError, "Illegal value for format argument, expecting \'png\' or \'fits\'."
        
    ###################################################################################        
    
    def subtractBackgroundImage(self, background):
        """
        Returns a new allskyImage object with the specified background image subtracted.
        The background argument should be an allskyImage object containing the 
        background image data.
        
        If the image which the background is being subtracted from has had some processing
        already applied to it (e.g. binaryMask, alignNorth etc.) then it is important that 
        the background image is loaded with the correct parameters in the site info file. 
        Otherwise it may be subtracted from the image at an incorrect angle/position.
        """
        
        if self.__image.mode == "RGB":
            raise TypeError, "Cannot subtract RGB images"
        if self.__info['processing'].has_key('flatFieldCorrection'):
            raise RuntimeError, "Background subtraction must be done before flat field calibration"
        if self.__info['processing'].has_key('convertTo8bit'):
            #conversion to 8bit scales intensities relative to max and min pixel values
            #therefore it does not make sense to allow background subtraction (the background
            #image will be scaled differently)
            raise TypeError, "Cannot subtract images which have been converted to 8bit (due to intensity scaling)"
        if background.getMode() != self.__image.mode:
            raise ValueError, "Background image has a different mode to image"
        #apply the same processing to the background image as is applied to this image
        if self.__info['processing'].has_key('binaryMask'):
            background = background.binaryMask(self.__info['camera']['fov_angle'])
        if self.__info['processing'].has_key('centerImage'):
            background = background.centerImage()
        if self.__info['processing'].has_key('alignNorth'):
            #work out what orientation we are in
            if self.__info['processing']['alignNorth'].count('NESW') != 0:
                orientation = 'NESW'
            elif self.__info['processing']['alignNorth'].count('NWSE') != 0:
                orientation = 'NWSE'
            else:
                #this image was alignedNorth using an old version of PASKIL and
                #is therefore in a NESW orientation
                orientation = 'NESW'
                
            #now decide if we are aligned geographic or geomagnetic
            if float(self.__info['camera']['cam_rot']) == 0.0:    
                north = 'geographic'
            else:
                north = 'geomagnetic'
            
            background = background.alignNorth(north=north, orientation=orientation)
        
        #hopefully the background image is still the same size as this one, otherwise
        #we have problem!
        if background.getSize() != self.__image.size:
            raise ValueError, "Background image is not the same size as the image it is to be subtracted from"
        
        #if the image is 8bit then use PIL's subtraction method
        if self.__image.mode == 'L':
            new_image = ImageChops.subtract(self.__image, background.getImage())
        else:
            #convert to numpy arrays, subtract and convert back
            im_arr = numpy.asarray(self.__image)
            bkgd_arr = numpy.asarray(background.getImage())
            
            result = im_arr - bkgd_arr
            
            result = result * (result > 0) #replace negative numbers with zero
            
            new_image = Image.fromarray(result)
        
        new_info = self.getInfo()
        
        new_info['processing']['subtractBackground'] = background.getFilename()
        
        return allskyImage(new_image, self.__filename, new_info)
        
    ###################################################################################
        
    def xy2angle(self, x, y):
        """
        Converts x and y pixel coordinates into an angle from the zenith (from the Z axis).
        The angle returned is in degrees. Note that (x,y)=(0,0) is the top left corner of
        the image.
        """
        x_0 = self.__info['camera']['x_center']
        y_0 = self.__info['camera']['y_center']
        
        dist_from_center=math.sqrt(((x-x_0)*(x-x_0)) + ((y-y_0)*(y-y_0)))
        
        if self.__info['camera']['lens_projection'] == 'equidistant':
            #calculate focal length
            focal_length=float(self.__info['camera']['Radius'])/float(self.__info['camera']['fov_angle'])
            
            #calculate the angle
            angle = dist_from_center/focal_length
        
        elif self.__info['camera']['lens_projection'] == 'equisolidangle':

            #calculate focal length
            focal_length=float(self.__info['camera']['Radius'])/(2.0*math.sin(math.radians(float(self.__info['camera']['fov_angle']))/2.0))
            
            #calculate angle
            angle_radians = 2.0 * math.asin(dist_from_center/(2.0 * focal_length))
            angle = math.degrees(angle_radians)
        
        else:
            raise ValueError, "Unsupported lens projection type"
    
        return angle

###################################################################################                
    
