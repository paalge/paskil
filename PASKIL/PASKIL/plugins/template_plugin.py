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
This file contains a template for producing PASKIL plugins. These are not the same as PIL plugins.
PIL plugins enable python to load the image data i.e. the actual pixel values. PASKIL plugins are
used to load the image metadata and store it in a standard PASKIL internal format (the allskyImage
object).

"""

#import required modules
from PASKIL import allskyImage, allskyImagePlugins
import Image
#start plugin class definition
class Example_AllskyImage_Format:
    """
    A template plugin class.
    """
    def __init__(self):
        """
        This method is run when the class is instanciated and is used to set up class attributes
        """
        self.name = "Imaginary image format used for example" #This is not used anywhere in the code yet, but is probably a good idea
    
    ###################################################################################
    
    def test(self, image_filename, info_filename):
        """
        This method should test to see whether the filename that is passed to it is of the type that this
        plugin was designed to read. The image_filename argument is a string, and the info_file is either the
        name of a metadata file or None. Remeber that this method may be passed images that are not of 
        the correct type and in this case should return False rather than raising an exception - expect to
        use lots of try except blocks! The method should return True if the image is of the correct type and
        False otherwise. It is your own responsibility to make sure that plugins can uniquely identify their
        image types and do not overlap with other plugins.
        """
        try:
            image = Image.open(image_filename)
        except:
            return False
        
        try:
            #look in the image header to see if it is the type of image we are after
            if image.info['Is an example image'] == True:
                return True
            else:
                return False
            
        #if the image header doesn't have an 'Is an example image' field then return False
        except KeyError:
            return False
            
    ###################################################################################    
        
    def open(self, image_filename, info_filename):
        """
        This method should return an instance of the allskyImage.allskyImage class. The method needs to 
        read the metadata for the image, either from the image itself or from the optional info file. The
        data should be stored in dictionaries in the format specified in the allskyImagePlugins documentation.
        The info_filename argument can be either the filename of the site information file or None.
        """
        image = Image.open(image_filename)
        #read image header data, here we assume that the image header already contains all the metadata in the correct format
        info = image.info
    
        #return new allskyImage object
        return allskyImage.allskyImage(image, image.filename, info)
        
    ###################################################################################
###################################################################################

#register the plugin with PASKIL, without this step the plugin will just be ignored! The argument to the register function should be an instance of your plugin class
allskyImagePlugins.register(Example_AllskyImage_Format())