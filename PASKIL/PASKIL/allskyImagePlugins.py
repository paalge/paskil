# Copyright (C) Nial Peters 2009
#
# This file is part of PASKIL.
#
# PASKIL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# PASKIL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PASKIL.  If not, see <http://www.gnu.org/licenses/>.
"""
Introduction:

    The allskyImagePlugins module provides the plugins that PASKIL needs to load its own allsky image
    format. Two formats are currently supported natively: PNG files with the metadata written into the
    image header and FITS files with the image data in the primary HDU and the metadata split between
    three extension HDUs.
    
    In addition to this, this module provides the documentation you will need to create your own plugins
    allowing you to load any image format into PASKIL.



Concepts:

    PASKIL considers each all-sky image to consist of two parts, the image and the image metadata. The 
    image could be in any format, png, jpg,ppm etc... and can be most easily loaded into PASKIL by using
    the python image library (PIL) to load the image and then passing the PIL image object to the 
    allskyImage constructor. If the image format is not natively supported by PIL, then you will need to
    write a PIL plugin to be able to load it - see the PIL handbook for details of how to do this.
    
    The image metadata (capture time, field of view etc..) could also be in any format. It could be 
    stored in the image header or in a separate file, or some combination of the two. The metadata can
    be anything you want, however, there are some fields that must be provided and are used by PASKIL
    to process the image. See 'Compulsary Fields' for details.
    
    PASKIL uses a plugin architecture to allow it to be able to support allsky images of any format 
    without the need for the core code to be modified. Once a user has written an appropriate plugin
    for the type of allsky image they are using, they have access to all of PASKIL's functionality.
    Essentially all the plugin has to do is convert the metadata into the same format as is used internally
    by PASKIL. This format is detailed below to aid plugin development.
    


Metadata Format:
    
    In order to create return an allskyImage instance, a plugin's open method must make a call to 
    allskyImage.allskyImage(), the constructor for allsky image objects. One of the arguments that this
    takes is 'info'. The info argument should be a dictionary containing four other dictionaries:
    
        info = {'header':{},'camera':{},'processing':{},'exif':{}}
        
    The metadata is split between these four dictionaries depending on the type of data. The header 
    dictionary contains general data about the image such as capture time, copyright information etc.
    The camera dictionary contains technical data about the camera setup such as the pixel coordinates
    of the center of the image and the orientation of the camera. The processing dictionary contains 
    a history of the processing that has been applied to the image. It is mainly intended to be used 
    internally by PASKIL, so it is best if it is initialised to an empty dictionary. The exif 
    dictionary is to hold the original exif data from the source image (if there was any).


    
Compulsary Fields:

    The following metadata must be specified for each image loaded into PASKIL. Both the 'header' and 
    the 'camera' dictionaries have compulsary entries. The keys are case sensitive and all values should
    be strings.
    
    header dictionary:
    
        'Creation Time'      - The time and date that the image was taken. This must be specified in the 
                               format "%d %b %Y %H:%M:%S %Z" (see http://docs.python.org/lib/module-time.html), 
                               for example "03 Jan 2003 14:00:00 GMT"
                          
        'Wavelength'         - The wavelength that the image was recorded at. This can be in any format 
                               that you wish, but you will have to remember what format you used when you 
                               want to create a dataset!
                
                            
    camera dictionary:
        
        'Magn. Bearing'      - The angle from Geographic North of Geomagnetic North. For example, for 
                               Longyearbyen Magn.Bearing=-33.
                            
        'cam_rot'            - The angle of the top of the image from Geographic North.
        
        'x_center'           - The x coordinate (in pixels) of the center of the field of view. This assumes 
                               that the origin is in the upper left corner of the image, with x values increasing 
                               from zero towards the right of the image.
        
        'y_center'           - The y coordinate (in pixels) of the center of the field of view. This assumes 
                               that the origin is in the upper left corner of the image, with y values increasing 
                               from zero towards the bottom of the image.
                        
        'Radius'             - The radius (in pixels) of the field of view.
        
        'fov_angle'          - The size of the field of view (from the center of the image to the edge of the 
                               field of view) in degrees.
        
        'lens_projection'    - The type of projection that you would like the lens to be modelled with. Currently
                               supported projections are "equidistant" and "equisolidangle".
                               
        'lat'                - The latitude of the camera (in degrees).
        
        'lon'                - The longitude of the camera (in degrees).    



Site Info File:

    The site information file is a plain text file used to hold image metadata. The format of the file is 
    entirely up to you, as long as you can write a plugin which can read it! The use of a site info file
    is optional. If all the required metadata can be acquired from else where, then you don't need to specify
    an external file. However, if you do need to be able to specify more metadata, then you have the option
    of loading it from a separate file. 

    

Writing Your Own Plugin:

    As mentioned above, all a plugin needs to be able to do is recognise a file as being of the type that it
    was written to open, and then convert the metadata into the format used by PASKIL. It is therefore relatively
    straightforwards to write plugins. A template plugin is provided in the PASKIL.plugins package to help point
    you in the right direction.
    
    A plugin consists of a single class with two methods. The test method should return true if the image filename passed
    to it is of the type that the plugin can open and false otherwise. The open method should return an allskyImage
    object or an allskyRaw object containing the image and its metadata. Simple! However, there are a few things to keep in mind. The image
    passed to the plugin may not be the type that the plugin is expecting. In which case it should return false rather
    than raising an exception. Also, the test method should be able to uniquely identify an image if possible. For 
    example, it is not recommended to claim that because an image is a PNG it is the type that the plugin can open. In
    the interests of efficiency, the test method should reject images of the wrong type as quickly as possible.
    
    In order to create the exif dictionary there is a readExifData function in the misc module. This returns a dictionary
    containing the exif data stored in an image.

    
        
"""

import allskyImage
import misc
import pyfits
from gi.repository import GExiv2 as pyexiv2
from PIL import Image, ImageOps

types = []  # list to hold all available plugins


##########################################################################

def list_plugins():
    """
    Returns a list of names of all the plugins that are registered.
    """
    return [x.name for x in types]

##########################################################################


def which_plugin(image_filename, info_filename=None, force=False):
    """
    Returns the name of the plugin that will be used to open the specified image.
    If no plugin is found to open the image, then None is returned.
    """
    try:
        plugin = load(image_filename, info_filename, force)
        return plugin.name
    except ValueError:
        return None

##########################################################################


def load(image_filename, info_filename, force):
    """    
    Returns the plugin object needed to open the image. Raises TypeError if no plugin is found. This should
    only be needed for debugging purposes.
    """

    if force:
        # skip the first three plugins in the list - these are the internal
        # ones
        i = 3
    else:
        i = 0

    while i < len(types):
        if types[i].test(image_filename, info_filename):
            return types[i]
        i += 1

    raise TypeError("allskyImagePlugins.load(): Unrecognised filetype for " +
                    image_filename + ". Make sure you have imported the required plugin for the image.")


##########################################################################

def register(plugin):
    """
    Registers a plugin. The plugin argument should be an instance of the plugin class to be registered. You
    must make a call to this function when you import an external plugin, otherwise it will be ignored.
    """
    # TODO - should check that the plugin has the correct methods/attributes

    types.append(plugin)

##########################################################################


class PASKIL_Allsky_Image_PNG:
    """
    Plugin class used to open PASKIL PNG files. These are png image files with the image metadata stored
    in the image header. The header data is stored as a string representation of a python dictionary and
    can be retrieved using the eval function. The primary dictionary contains 3 other dictionaries 'header',
    'camera' and 'processing'. These relate to information about the image, information about the camera
    setup and information about the processing that has been applied to the image (mainly used internally
    by PASKIL) respectively.

    This plugin is used to open images which have already been opened by PASKIL and then resaved. As a result, 
    all the metadata is now stored in the image header, and in order not to lose the processing history, it 
    should be read from the header rather than being re-loaded from a site info file.
    """

    def __init__(self):
        self.name = "PASKIL All-sky PNG Image Plugin"

    ##########################################################################

    def test(self, image_filename, info_filename):
        """
        Returns true if 'image_filename' is in the PASKIL PNG format, false otherwise.
        """

        # load image
        try:
            image = Image.open(image_filename)
        except:
            return False

        # look in the image header data to see if this image is from PASKIL
        keys = image.info.keys()
        if keys.count('header') == 1 and keys.count('camera') == 1 and keys.count('processing') == 1:
            return True
        else:
            return False

    ##########################################################################

    def open(self, image_filename, info_filename):
        """
        Returns an allskyImage object containing the image data and image metadata contained in 'image_filename'.
        """
        image = Image.open(image_filename)

        # read image header data
        info = image.info

        # load the metadata from the image header data
        camera = eval(info['camera'])
        processing = eval(info['processing'])
        header = eval(info['header'])
        try:
            exif = eval(info['exif'])
            del info['exif']
        except KeyError:
            exif = {}

        del info['camera']
        del info['processing']
        del info['header']

        # create a dictionary containing all the metadata
        info = {'header': header, 'camera': camera,
                'processing': processing, 'exif': exif}

        # return new allskyImage object
        return allskyImage.allskyImage(image, image.filename, info)

    ##########################################################################
##########################################################################


class PASKIL_Allsky_Image_JPEG:
    """
    Plugin class used to open PASKIL jpeg files. These are jpeg image files with the image metadata stored
    in the image exif (currently under the UserComment tag due to limitations of pyexiv2).

    This plugin is used to open images which have already been opened by PASKIL and then resaved. As a result, 
    all the metadata is now stored in the image exif, and in order not to lose the processing history, it 
    should be read from the exif rather than being re-loaded from a site info file.
    """

    def __init__(self):
        self.name = "PASKIL All-sky JPEG Image Plugin"

    ##########################################################################

    def test(self, image_filename, info_filename):
        """
        Returns true if 'image_filename' is in the PASKIL JPEG format, false otherwise.
        """
        # check exif
        exif = pyexiv2.Metadata(image_filename)
#         exif.read()

        try:
            if exif['Exif.Image.ProcessingSoftware'].value == "PASKIL":
                return True
            else:
                return False
        except:
            return False

    ##########################################################################

    def open(self, image_filename, info_filename):
        """
        Returns an allskyImage object containing the image data and image metadata contained in 'image_filename'.
        """
        image = Image.open(image_filename)
        exif_data = misc.readExifData(image_filename)

        info_str = exif_data.pop("Exif.Photo.UserComment")
        info = eval(info_str)
        info['exif'] = exif_data

        # return new allskyImage object
        return allskyImage.allskyImage(image, image.filename, info)

    ##########################################################################
##########################################################################


class PASKIL_Allsky_Image_FITS:
    """
    Plugin class used to open PASKIL FITS files. These are FITS files with the image data stored in the 
    primary HDU and the metadata stored in three extension HDUs, one for 'header' one for 'camera' and one
    for 'processing'. These relate to information about the image, information about the camera setup and 
    information about the processing that has been applied to the image (mainly used internally by PASKIL) 
    respectively.

    This plugin is used to open images which have already been opened by PASKIL and then resaved. As a result, 
    all the metadata is now stored in the image header, and in order not to lose the processing history, it 
    should be read from the header rather than being re-loaded from a site info file.
    """

    def __init__(self):
        self.name = "PASKIL All-sky FITS Image Plugin"

    ##########################################################################

    def test(self, image_filename, info_filename):
        """
        Returns true if image_filename is in the PASKIL FITS format, false otherwise.
        """
        try:
            image = Image.open(image_filename)
        except:
            return False

        # check image has fits format
        if image.format != 'FITS':
            return False

        # if it is a FITS image, then check if it is a PASKIL fits image

        # open fits file using pyfits
        hdulist = pyfits.open(image_filename)

        # look in the header of the primary hdu for the PASKIL tag
        try:
            mode = hdulist[0].header['PASKIL']

        except KeyError:
            return False

        if mode == 1:
            return True
        else:
            return False

    ##########################################################################

    def open(self, image_filename, info_filename):
        """
        Returns an allskyImage object containing the image data and image metadata contained in 'image'.
        """
        header = {}
        camera = {}
        processing = {}
        exif = {}

        # open fits file using pyfits
        hdulist = pyfits.open(image_filename)

        # read header data locations from header
        header_hdu = hdulist[hdulist[0].header['PSKHEAD']]
        camera_hdu = hdulist[hdulist[0].header['PSKCAM']]
        processing_hdu = hdulist[hdulist[0].header['PSKPRO']]
        exif_hdu = hdulist[hdulist[0].header['PSKEXIF']]

        # write image info dictionary
        for i in range(header_hdu.data.size):
            try:
                header[header_hdu.data[i][0]] = eval(header_hdu.data[i][1])
            except:
                header[header_hdu.data[i][0]] = header_hdu.data[i][1]

        for i in range(camera_hdu.data.size):
            try:
                camera[camera_hdu.data[i][0]] = eval(camera_hdu.data[i][1])
            except:
                camera[camera_hdu.data[i][0]] = camera_hdu.data[i][1]

        for i in range(processing_hdu.data.size):
            try:
                processing[processing_hdu.data[i][0]] = eval(
                    processing_hdu.data[i][1])
            except:
                processing[
                    processing_hdu.data[i][0]] = processing_hdu.data[i][1]

        for i in range(exif_hdu.data.size):
            try:
                exif[exif_hdu.data[i][0]] = eval(exif_hdu.data[i][1])
            except:
                exif[exif_hdu.data[i][0]] = exif_hdu.data[i][1]

        info = {'header': header, 'camera': camera,
                'processing': processing, 'exif': exif}

        mode = hdulist[0].header['PSKMODE']

        # load image data
        image_data = hdulist[0].data

        if mode != "RGB":
            # need to flip image as it is read in upside down
            new_image = ImageOps.flip(Image.fromarray(image_data))
        else:
            # read in separate RGB channels and then combine them into one
            # image
            red_image = Image.fromarray(image_data[0])
            green_image = Image.fromarray(image_data[1])
            blue_image = Image.fromarray(image_data[2])

            new_image = ImageOps.flip(
                Image.merge("RGB", [red_image, green_image, blue_image]))

        return allskyImage.allskyImage(new_image, image_filename, info)

    ##########################################################################
##########################################################################

# register plugins
register(PASKIL_Allsky_Image_PNG())
register(PASKIL_Allsky_Image_FITS())
register(PASKIL_Allsky_Image_JPEG())
