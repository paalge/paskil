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


#import required modules
from PASKIL import allskyImage, allskyImagePlugins,allskyRaw
import datetime,os
#start plugin class definition
class NEF_Format:
    """
    An plugin for NEF files - this is still under construction and is only being used for testing 
    at the moment.
    """
    def __init__(self):
        """
        This method is run when the class is instanciated and is used to set up class attributes
        """
        self.name = "Imaginary image format used for example" #This is not used anywhere in the code yet, but is probably a good idea
    
    ###################################################################################
    
    def test(self, image_filename, info_filename):
        """
        This method should test to see whether the PIL image that is passed to it is of the type that this
        plugin was designed to read. The image argument is a PIL image, and the info_file is either a file
        pointer to a metadata file or None. Remeber that this method may be passed images that are not of 
        the correct type and in this case should return False rather than raising an exception - expect to
        use lots of try except blocks! The method should return True if the image is of the correct type and
        False otherwise. It is your own responsibility to make sure that plugins can uniquely identify their
        image types and do not overlap with other plugins.
        """
        if image_filename.endswith(".NEF"):
            return allskyRaw.isRaw(image_filename)
        else:
            return False
            
    ###################################################################################    
        
    def open(self, image_filename, info_filename):
        """
        This method should return an instance of the allskyImage.allskyImage class. The method needs to 
        read the metadata for the image, either from the image itself or from the optional info file. The
        data should be stored in dictionaries in the format specified in the allskyImagePlugins documentation.
        The image argument is a PIL image, and the info_file is either a file pointer to a metadata file or 
        None.
        """
        #Read site info file
        camera={}
        processing={}
        header={}
        
        with open(info_filename,"r") as info_file:
            for line in info_file: #read file line by line
                if line.isspace(): 
                    continue #ignore blank lines
                words=line.split("=") #split the line at the = sign
                
                if len(words) != 2:
                    print("Error! allskyImagePlugins.DSLR_LYR.open(): Cannot read site info file, too many words per line")
                    sys.exit()
                    
                camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip() #store the values (minus white space) in a dictionary
        
        #Read creation time from filename
        filename = os.path.basename(image_filename)
        creation_time=datetime.datetime.strptime(filename.rstrip(".NEF"), "LYR-SLR-%Y%m%d_%H%M%S")
        
        creation_time=creation_time.strftime("%d %b %Y %H:%M:%S %Z")
        header = {'Wavelength':"RGGB",'Creation Time': creation_time}
        
        info={'header':header,'camera':camera,'processing':processing}
        
        #return new allskyImage object
        return allskyRaw.rawImage(image_filename,info)
        
    ###################################################################################
###################################################################################

#register the plugin with PASKIL, without this step the plugin will just be ignored! The argument to the register function should be an instance of your plugin class
allskyImagePlugins.register(NEF_Format())