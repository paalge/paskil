"""
Introduction:

    The allskyImage module provides a class of the same name which is used to represent an all-sky image. 
    The class contains methods for performing various manipulations of the image including aligning it 
    with North and applying a false colour scale. PASKIL supports both 16bit and 8bit images, however,
    the routines for 8bit images are considerably faster.


Concepts:

    An allskyImage object has two major constituents, a Python Image Library (PIL) image object which holds 
    the image data itself, and a hash table (or dictionary as it is known in Python) containing the image metadata.
    For details of what metadata is required, and how to load it into PASKIL see the allskyImagePlugins module.
    
    
    
Example:
    The following example code opens the image file "test.png" using the information in "site_info.txt".
    It then converts the image to 8bit, applies a binary mask giving a 70 degree field of view, centres 
    the image,aligns the top of the image with geographic north and saves it as "testout.png". Note that 
    you will also need to import the relevant plugin:
    

        from PASKIL import allskyImage #import the allskyImage module

        im=allskyImage.new("test.png",site_info_file="site_info.txt") #create a new allskyImage object
        im=im.convertTo8bit()
        im=im.binaryMask(70)
        im=im.centerImage()
        im=im.alignNorth()
        im.save("testout.png")    
"""
################################################################################################################################################################

import Image, ImageOps, ImageDraw, ImageFilter, ImageFont, ImageChops 
from PASKIL import misc, allskyImagePlugins, allskyProj
from PASKIL.extensions import cSquish
import pyfits, numpy
import sys, datetime, os, math
import warnings
import matplotlib
import matplotlib.pyplot
from pylab import AutoLocator,NullLocator,FuncFormatter

#attempt to import psyco to improve performance
try:
    import psyco
    use_psyco = True
except ImportError:
    use_psyco = False
    warnings.warn("Could not import psyco. This will reduce performance.")
 

##Functions

def new(image_filename, site_info_file="", force=False):
    """
    Creates a new allskyImage object. The image_filename argument specifies the image to be read. The site_info_file 
    option should be the filename of the site information file (if one is required). This is an optional file 
    containing image metadata. A filepointer to this file is passed to the allskyImagePlugin open method, see
    the allskyImagePlugins module for details. The default value is "", no site_info_file. The force option
    allows you to force PASKIL to use an external plugin for opening the file. This can be useful for overwriting
    incorrect image metadata. The default is False, which means that where possible the image metadata will be read
    from the image header, rather than an external source.
    """    

    if site_info_file != "":
        info_filename=site_info_file
    else:
        info_filename = None
    
    
    #Load correct image plugin to open image
    filetype=allskyImagePlugins.load(image_filename, info_filename, force)
    
    #Return allskyImage object
    allsky_image = filetype.open(image_filename, info_filename)

    return allsky_image

#allskyImage class definition

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
        self.__image=image.copy()
        self.__image.__info={}
        self.__filename=image_file
        self.__info={}
        
        #make hard copies of the info libraries 
        self.__info['camera']=info['camera'].copy()
        self.__info['header']=info['header'].copy()
        self.__info['processing']=info['processing'].copy()
    
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
        Returns a dictionary object containing three dictionaries ('header','camera' and 'processing')
        which contain a copy of the image metadata"""
        copy={'camera':self.__info['camera'].copy(), 'header':self.__info['header'].copy(), 'processing':self.__info['processing'].copy()}
        return copy
    
    def getMode(self):
        """
        Returns a string containing the mode of the image ("RGB","L" etc...). See PIL handbook for 
        details of different image modes"""
        return self.__image.mode
        
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
            time=datetime.datetime.strptime(self.__info['header']['Creation Time'], "%d %b %Y %H:%M:%S %Z")
        except KeyError:
            raise  IOError, "Cannot read time data from header for image "+self.__filename
        
        #create copy of image
        new_image = self.__image.copy()
            
        #create a datetime string with the desired format
        time_string = time.strftime(format)
            
        draw=ImageDraw.Draw(new_image)#create draw object of image
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", size=fontsize)#load font. This is likley to cause problems on systems where the fonts are stored under a different location. You'll just have to look for a suitable font, and change the path specified here - sorry!
            
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
        new_info['processing']['addTimeStamp']=""
        
        return allskyImage(new_image, self.__filename, new_info)
        
    ###################################################################################    
    
    def alignNorth(self, north="geographic", orientation='NESW'):
        """
        Aligns the top of the image with either geographic or geomagnetic north depending on the value of 
        the north argument. Default is "geographic", can also be set to "geomagnetic". The right hand edge 
        of the image will be aligned with East. The returned all-sky image will be in a NESW orientation. 
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
                raise(ValueError,"Unknown value for orientation. Expecting \"NESW\" or \"NWSE\"")
            
            new_info['camera']['cam_rot'] = new_info['camera']['Magn. Bearing']
            
        elif north != "geographic":
            raise(ValueError, "Unknown value for north. Expecting \"geomagnetic\" or \"geographic\"")
        
        #update processing history
        new_info['processing']['alignNorth'] = north+" ("+orientation+")"
        
        #return a new allskyImage instance
        return allskyImage(new_image, self.__filename, new_info)
        
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
        
        #create new allskyImage object
        new_image=allskyImage(self.__image, self.__filename, self.__info)
                
        #check if the image has had the flat field calibration applied
        if new_image.__info['processing'].keys().count('flatFieldCorrection') == 0:
            warnings.warn("Images should have flat field corrections applied before the colour table is applied")
            
        #check if the image has already had a colour table applied
        if new_image.__info['processing'].keys().count('applyColourTable') != 0:
            raise RuntimeError, "A colour table has already been applied to "+new_image.__filename
            
        #apply colour table
        if new_image.getMode() != "I": #PIL doesn't support 16bit images, so need to use own routine if "I" mode image
            new_image.__image.putpalette(colour_table.getColourTable())
        else:
            RGB_image=Image.new("RGB", new_image.getSize(), "Black")
            image_pix=new_image.__image.load()
            RGB_pix=RGB_image.load()
            
            for x in range(RGB_image.size[0]):
                for y in range(RGB_image.size[1]):
                    RGB_pix[x, y]=colour_table.colour_table[image_pix[x, y]]
                    
            new_image.__image=RGB_image
            
        new_image.__image=new_image.__image.convert("RGB")
        
        #update processing history
        new_image.__info['processing']['applyColourTable']=colour_table.colour_table
        
        return new_image

    ###################################################################################    
    
    def binaryMask(self, fov_angle, inverted=False):
        """
        Applies a binary mask to the image, setting pixels outside of the field of view to black. 
        The fov_angle argument should be the field of view in degrees from the centre. The inverted
        options controls whether the mask is black or white, default is False = black.
        """
        #create new allskyImage object
        new_image=allskyImage(self.__image, self.__filename, self.__info)
                
        if fov_angle > new_image.__info['camera']['fov_angle']:
            raise ValueError, "Field of view is too large for image."
        
        if self.__info['camera']['lens_projection'] == 'equidistant':
            #calculate focal length
            focal_length=float(new_image.__info['camera']['Radius'])/float(new_image.__info['camera']['fov_angle'])
            
            #calculate radius for masking circle
            radius=int((focal_length*fov_angle)+0.5)
        
        elif self.__info['camera']['lens_projection'] == 'equisolidangle':
            #calculate focal length
            focal_length=float(new_image.__info['camera']['Radius'])/(2.0*math.sin(math.radians(float(new_image.__info['camera']['fov_angle']))/2.0))
            
            #calculate radius for masking circle
            radius=int((2.0*focal_length*math.sin(math.radians(fov_angle)/2.0))+0.5)
        
        else:
            raise ValueError, "Unsupported lens projection type"
        
        mode = new_image.__image.mode
        
        if mode == "I":
            white=65535
        elif mode == "L":
            white=255
        elif mode == "RGB":
            white=(255, 255, 255)    
        else:
            raise ValueError, "Unsupported image mode"
            
        #calculate bounding box for the circle
        bb_left = int(new_image.__info['camera']['x_center'])-radius
        bb_top = int(new_image.__info['camera']['y_center'])-radius
        bb_right =int(new_image.__info['camera']['x_center'])+radius
        bb_bottom = int(new_image.__info['camera']['y_center'])+radius
        
        #create a black mask image
        mask=Image.new(mode, new_image.getSize(), "Black")
        
        #draw white circle
        draw=ImageDraw.Draw(mask)
        draw.ellipse((bb_left, bb_top, bb_right, bb_bottom), fill=white)
        
        #apply the mask to the image
        if mode == "L" or mode == "RGB":
            if inverted:
                mask = ImageChops.invert(mask)
                new_image.__image = ImageChops.lighter(new_image.__image, mask)
            else:
                new_image.__image = ImageChops.multiply(new_image.__image, mask)
        
        elif mode == "I":
            #if the image is 16bit then cannot use the ImageChops module, so use own multiplication routine
            if inverted:
                im_pix = numpy.asarray(self.__image)
                mask_pix = numpy.asarray(mask)
                
                new_image.__image = Image.fromarray(numpy.maximum(im_pix, 65535-mask_pix))
            
            else:
                im_pix = numpy.asarray(self.__image)
                mask_pix = numpy.asarray(mask)
                
                new_image.__image = Image.fromarray(numpy.minimum(im_pix, mask_pix))
        else:
            raise ValueError, "Unsupported image mode"
        
        #update radius value
        new_image.__info['camera']['Radius'] = radius
        
        #update fov_angle value
        new_image.__info['camera']['fov_angle'] = fov_angle
        
        #update the processing history
        new_image.__info['processing']['binaryMask'] = str(fov_angle)
        
        return new_image
    
    ###################################################################################        

    def centerImage(self):
        """
        Resizes and centres the image about the field of view, finding the best fit for the circular 
        field of view in a rectangular image. The image returned will be square, with dimensions of
        RadiusxRadius.
        """
        #create new allskyImage object
        #new_image=allskyImage(self.__image, self.__filename, self.__info)
            
        #check that binary mask has been applied
        if self.__info['processing'].keys().count('binaryMask') == 0:
            raise RuntimeError, "Image must have binary mask applied before it can be centred"
        
        #check if image has already been centered
        if self.__info['processing'].keys().count('centerImage') != 0:
            warnings.warn("Image "+self.__filename+" has already been centered")
        
        #first, the image field of view is centered in the image
        #get the bounding box of the image (box around non-zero parts of the image)
        bounding_box=self.__image.getbbox()
        
        if bounding_box == None:
            raise RuntimeError, "Cannot find bounding box"
        
        #crop the image to the size of the bounding box
        new_image=self.__image.crop(bounding_box)
        
        #the image is now pasted into a new image which encompasses the entire (theoretical) circular field of view. This is done to allow PASKIL to cope with images taken with non-circular fields of view.
        
        #create new square image with dimensions RadiusxRadius
        square_image=Image.new(self.__image.mode, (2*self.__info['camera']['Radius'], 2*self.__info['camera']['Radius']), color='black')
        
        #paste image into correct position in square image.
        width, height=new_image.size
        square_image.paste(new_image, (self.__info['camera']['Radius']-int(width/2), self.__info['camera']['Radius']-int(height/2), self.__info['camera']['Radius']-int(width/2)+width, self.__info['camera']['Radius']-int(height/2)+height))     
        
        #create a new info dictionary
        new_info=self.getInfo()
        
        #update image center data
        new_info['camera']['x_center']=int((square_image.size[0]/2) +0.5) #x coordinate of center
        new_info['camera']['y_center']=int((square_image.size[1]/2) +0.5) #y coordinate of center
        
        #update processing history
        new_info['processing']['centerImage']=""
        
        #create new allskyImage object
        new_asimage=allskyImage(square_image, self.__filename, new_info)
        
        return new_asimage
    
    ###################################################################################
    
    def convertTo8bit(self):
        """
        Converts an "I" mode image (16 bit) containing 12 bit data (such as those produced by the 
        UiO camera in LYR) into an "L" mode image (8bit). The apparent change in contrast levels 
        caused by this function is not a bug! It is due to the fact that 12bit image data (with a 
        maximum value of 4095) has been stored in a 16 bit image (with a possible maximum of 65535) 
        and therefore looked darker than it actually was."""
        
        #update processing history
        info = self.getInfo()
        info['processing']['convertTo8bit']=""
        
        #create new allskyImage object with an 8bit image
        new_image=allskyImage(self.__image.convert("L"), self.__filename, info)
     
        return new_image
        
    ###################################################################################    
    
    def createQuicklook(self, size=(480, 640), timestamp="%a %b %d %Y, %H:%M:%S %Z", fontsize=16):
        """
        Returns an allskyImage object which contains a thumbnail image with a timestamp appended to
        the bottom of it. The size option should be a tuple specifying the thumbnail size in 
        pixels. Note that the actual thumbnail produced will be 24 pixels higher due to the size of
        the timestamp. This method also preserves the aspect ratio of the image, so the thumbnail 
        may have a different ratio to the one specified. The timestamp option should be a string 
        specifying the format of the timestamp (see http://docs.python.org/lib/module-time.html).
        The fontsize option should be an integer specifying the font size. 
        """
    
        #create new allskyImage object
        new_image=allskyImage(self.__image, self.__filename, self.__info)
        
        #resize image
        quicklook=new_image.resize(size)
        
        if timestamp != None:
            #append 24 pixels to the bottom of the image
            if quicklook.__image.mode == "RGB":
                white=(255, 255, 255)
            elif quicklook.__image.mode == "L":
                white=255
            elif quicklook.__image.mode == "I":
                white=65536
            else:
                raise ValueError, "Image mode not supported yet"
            
            im=Image.new(quicklook.__image.mode, (quicklook.getSize()[0], quicklook.getSize()[1]+24), white) #create new image which is 24 pixels bigger
            im.paste(quicklook.__image, (0, 0, quicklook.getSize()[0], quicklook.getSize()[1]))
            
            quicklook=allskyImage(im, self.__filename, self.__info)
            
            quicklook=quicklook.addTimeStamp(timestamp, fontsize=fontsize)
        
        #update header data
        quicklook.__info['processing']['quicklook']=size
        
        return quicklook
                    
    ###################################################################################

    def flatFieldCorrection(self, calibration):
        """
        Applies a flat field correction to the image. This is needed due to the angular dependance
        of the sensitivity of the CCD (see allskyCalib). The calibration argument should be a 
        allskyCalib.calibration object.
        """

        #create new allskyImage object
        new_image=allskyImage(self.__image, self.__filename, self.__info)
    
        #check that image has been centered
        if new_image.__info['processing'].keys().count('centerImage') == 0:
            raise RuntimeError, "Image must be centered before it can be calibrated"
            
        #check if the image has already been calibrated
        if new_image.__info['processing'].keys().count('flatFieldCorrection') != 0:
            warnings.warn("Image has already been calibrated")
            
        #check that calibration data has the correct number of entries
        if len(calibration.calibration_data) != new_image.__info['camera']['fov_angle']+1:
            raise ValueError, "Incorrect number of entries in calibration data"

        image_pix=new_image.__image.load() #load pixel values
        
        for x in range(new_image.getSize()[0]):#for x in range image width
            for y in range(new_image.getSize()[1]):#for y in range image height
                #for each x,y find the angle from the center
                angle = self.xy2angle(x, y)
                
                #skip angles outside of the field of view
                if angle >= new_image.__info['camera']['fov_angle']:
                    continue
                    
                #apply correction to pixels inside the field of view
                gradient = calibration.calibration_data[int(angle)+1]-calibration.calibration_data[int(angle)]
                correction = 1.0/(calibration.calibration_data[int(angle)] + (angle-float(int(angle)))*gradient)
                image_pix[x, y] = int((image_pix[x, y]*correction)+0.5)
        
        #update processing history
        new_image.__info['processing']['flatFieldCorrection']=""
        
        return new_image
        
    ###################################################################################
    
    def getStrip(self, angle, strip_width):
        """
        Returns a list of lists (Python's equivalent of a 2D array, elements are accessed by 
        list[i][j]) containing pixel values in a strip through the centre of the image. The 
        angle argument controls the angle from geographic north that the strip is taken. The 
        strip_width argument controls the width of the strip in pixels. The image must be 
        aligned with North before this method can be used. The list returned will always have a
        length equal to the 'Radius' of the field of view of the image.
        """
        
        #check that image has been aligned with north (if so then it must have been centred)
        if self.__info['processing'].keys().count('alignNorth') == 0:
            raise RuntimeError, "Image must be aligned with North."
                
        #rotate image so that the slice runs from top to bottom
        #the rotation direction depends on the orientation of the image
        if self.__info['processing']['alignNorth'].count('NESW') != 0:
            im = self.__image.rotate(angle - float(self.__info['camera']['cam_rot']))
        elif self.__info['processing']['alignNorth'].count('NWSE') != 0:
            im = self.__image.rotate(float(self.__info['camera']['cam_rot']) - angle)
        else:
            raise(ValueError, "getStrip(): Cannot read orientation data from info dict. Try re-aligning the image with North")
        
        #load pixel values into an array 
        pixels = im.load()
        
        #find centre
        width, height = im.size
        centre = int((float(width)/2.0)+0.5)
        
        #record pixel vaules in centre slice
        strip = []
        for i in xrange(strip_width):
            strip.append([])
            for j in xrange(height):
                strip[i].append(i+j)
    
        #copy centre strip pixel values into strip list
        for j in range(int(-strip_width/2)+1, int(strip_width/2)+1):
            for i in range(height):
                
                x=int(strip_width/2+j)
                x2=int(centre+j)
                
                strip[x][i]= pixels[x2, i]
        
        #check that the length of the strip is equal to the radius - it might not be since we are dealing with a rectangular image, the radius could be the diagonal length and we could have taken a strip from the non-diagonal
        if len(strip[0]) != 2*self.__info['camera']['Radius']:
            #if the length is different, then append black pixels to either end of the strip to make the lengths the same
            difference=(2*self.__info['camera']['Radius'])-len(strip[0])
            
            if difference <=0:
                raise RuntimeError, "Strip is longer than diameter of field of view - this shouldn't be possible, check the value you have used for 'Radius'"
            
            #define black for different image modes
            if self.__image.mode in ("L", "I"):
                black=0
            elif self.__image.mode == "RGB":
                black =(0, 0, 0)
            else:
                raise ValueError, "Unknown image mode"
                
            for i in range(len(strip)):
                #create lists of black pixel values to prepend and append to the strip taken from the image
                prepend=[black]*int(difference/2)
                
                if difference%2 !=0: #diffence is odd
                    append=[black]*(int(difference/2)+1)
                else:
                    append=prepend
                
                strip[i].extend(append)
                prepend.extend(strip[i])
                    
                strip[i]=prepend    
                    
        return strip  
    
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
            histogram = numpy.histogram(im_pix, bins=range(65536), new=True)[0]
            
        else:
            raise ValueError, "Unsupported image mode"
        
        return histogram
    
    ###################################################################################    
    
    def load(self):
        if not self.__loaded:
            self.__image.load()
            self.__loaded = True
    
    ###################################################################################    
    
    def medianFilter(self, n):
        """
        This is a thin wrapper function for the median filter provided by PIL. It replaces each 
        pixel by the median value of the pixels in an nxn square around it (where n is an integer).
        """

        #create new allskyImage object
        new_image=allskyImage(self.__image, self.__filename, self.__info)
        
        new_image.__image = new_image.__image.filter(ImageFilter.MedianFilter(n))
        
        #update processing history
        new_image.__info['processing']['medianFilter'] = n
        
        return new_image
        
    ###################################################################################
    
    def _plot(self, subplot):
        """
        Returns a matplotlib subplot object containing the allsky image data.
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
        subplot.imshow(self.__image,origin="top", aspect="equal")
        
        if colour_table is not None:
            #find the thresholds on the colour table - then we can just display
            #the interesting parts of the colour table.
            
            #first we find the lower threshold
            colour_table.reverse()
            offset = colour_table.index(colour_table[-1])
            lower_threshold = len(colour_table)- 1 - offset
            
            #now the upper threshold
            colour_table.reverse()
            upper_threshold = colour_table.index(colour_table[-1])
            
            colour_bar_height = len(colour_table)
            
            colour_bar_width = 11

            #create a colour bar image
            colour_bar_image = Image.new("RGB",(colour_bar_width,colour_bar_height))
            colour_bar_pix = colour_bar_image.load()
            
            #colour in the colour bar based on the colour table of the image
            for y in xrange(colour_bar_height):
                current_ct_index = int((float(colour_bar_height - y)/float(colour_bar_height)) * (len(colour_table)-1))
                current_colour = colour_table[current_ct_index]
                
                for x in xrange(colour_bar_width):
                    colour_bar_pix[x,y] = current_colour
            
            #if the image could contain values outside of the threshold
            #region (there is now no way to determine this for certain, since the
            #intensity data was lost when the colour table was applied) then put
            #arrow heads on the colour bar to indicate this
            
            if lower_threshold != 0:
                d = ImageDraw.Draw(colour_bar_image)
                y0 = colour_bar_height - lower_threshold
                d.polygon([(0,y0),(0,y0-11),(5,y0-1),(10,y0-11),(10,y0)],fill='white')
            if upper_threshold != colour_bar_height-1:
                d = ImageDraw.Draw(colour_bar_image)
                y0 = colour_bar_height - upper_threshold
                d.polygon([(0,y0),(0,y0+11),(5,y0+1),(10,y0+11),(10,y0)],fill='white')
            
            #create a fake colour table - this is used to get matplotlib to create the colourbar axes
            #which we then use to plot out colour bar image into
            fake_data = numpy.random.rand(2,2)
            fake_colour_image = subplot.pcolor(fake_data)
            
            #create the matplotlib colour bar object and plot the colour table image in it
            colour_bar = matplotlib.pyplot.colorbar(fake_colour_image,ax=subplot,pad=0.15)
            colour_bar.ax.axes.clear()
            
            if not self.__info['processing'].has_key('absoluteCalibration'):
                colour_bar.ax.axes.set_ylabel("CCD Counts")
                colour_bar.ax.yaxis.set_label_position("left")
            
            colour_bar.ax.xaxis.set_major_locator(NullLocator())
            
            colour_bar.ax.imshow(colour_bar_image,origin="top")

            colour_bar.ax.axes.set_ylim((lower_threshold,upper_threshold))
            colour_bar.ax.axes.set_xlim((-1,11))
            #plot our colour bar image into the colour bar axes         
            colour_bar.ax.yaxis.set_major_locator(AutoLocator())
            colour_bar.ax.yaxis.set_major_formatter(FuncFormatter(self._formatCalibrated))
            colour_bar.ax.yaxis.tick_right()
            
            
        
        
        return subplot
        
    ###################################################################################        
    
    def _formatCalibrated(self,x, pos):
        if self.__info['processing'].has_key('absoluteCalibration'):
            return self.__info['processing']['absoluteCalibration'] * x
        else:
            return x

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
            size=(size[0], int((float(size[0])/float(self.__image.size[0]))*float(self.__image.size[1])+0.5))
            
        #resize the image
        resized_image=self.__image.resize(size)
        
        #calculate scaling factors for x and y
        scaling = float(size[0])/float(self.__image.size[0])
        
        #create new allskyImage
        new_image=allskyImage(resized_image, self.__filename, self.__info)
        
        #change the header data to reflect the change
        new_image.__info['camera']['x_center']=int(int(new_image.__info['camera']['x_center'])*scaling+0.5)
        new_image.__info['camera']['y_center']=int(int(new_image.__info['camera']['y_center'])*scaling+0.5)
        new_image.__info['camera']['Radius']=int(int(new_image.__info['camera']['Radius'])*scaling+0.5)
        
        #return resized image
        return new_image
        
    ###################################################################################
    
    def save(self, filename, format="png"):
        """
        Save the image and the meta-data as "filename". The format option should be a string which 
        matches the format attribute of a registered allskyImagePlugin object. This allows users to
        save in any format they wish, provided they write the plugin. See the allskyImagePlugins 
        module for details. Natively supported formats are:
        
            * "png":  a png image containing all the metadata in the image header
            
            * "fits": a flexible image transport system file with one hdu per image channel
                  (RGB images that are greyscale images which have been mapped through 
                  a colour table are stored as a single channel and are converted back
                  to RGB on loading) and three hdus containing metadata.
                  
        The default format is "png".
        """
        #saves the image data as 'filename'
        
        #detect format from filename
        if filename.endswith((".png", ".PNG")):
            format = "png"
        elif filename.endswith((".fits", ".FITS")):
            format = "fits"
        
        if format == "png": #save as png image
        
            if not filename.endswith((".png", ".PNG")):
                filename=filename+".png"
                
            
            #copy the header data back to the image
            self.__image.info={}
            self.__image.info['header']=str(self.__info['header']) 
            self.__image.info['camera']=str(self.__info['camera'])
            self.__image.info['processing']=str(self.__info['processing'])
            
            #save image
            misc.pngsave(self.__image, filename)
    
        
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
            
            
            #create a column definition
            header_cols_def=pyfits.ColDefs([header_keys_col, header_values_col])
            camera_cols_def=pyfits.ColDefs([camera_keys_col, camera_values_col])
            processing_cols_def=pyfits.ColDefs([processing_keys_col, processing_values_col])
            
            #create one extension hdu for each image header library ('header','camera','processing')
            header_hdu=pyfits.new_table(header_cols_def)
            camera_hdu=pyfits.new_table(camera_cols_def)
            processing_hdu=pyfits.new_table(processing_cols_def)
            
            #verify hdus
            header_hdu.verify('fix')
            camera_hdu.verify('fix')
            processing_hdu.verify('fix')
            
            #create a hdu list to contain the primary hdu and the extension hdus
            hdulist = pyfits.HDUList([primary_hdu, header_hdu, camera_hdu, processing_hdu])
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
    
    def xy2angle(self,x,y):
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

#use psyco to pre-compile computationally intensive functions
if use_psyco:
    psyco.bind(allskyImage.applyColourTable)
    psyco.bind(allskyImage.flatFieldCorrection)
    psyco.bind(allskyImage.getStrip)
    psyco.bind(allskyImage.medianFilter)
    psyco.bind(allskyImage.projectToHeight)        


