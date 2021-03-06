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
PASKIL plugin for opening PNG files created by the UiO allsky camera in Longyearbyen
"""

#import required modules
from PASKIL import allskyImage, allskyImagePlugins
import Image
import sys

#start plugin class definition
class UiO_Allsky_LYR_PNG:

    def __init__(self):
        self.name = "UiO LYR allsky camera png image" #This is not used anywhere in the code yet, but is probably a good idea
    
    ###################################################################################
    
    def test(self,image_filename, info_filename):
        #look in the image header data to see if this image is from the UiO camera
        
        #this type of image requires a site info file
        if info_filename == None:
            return False
        
        #reject dark field images
        if image_filename.count("DARK") != 0:
            return False
        
        try:
            image = Image.open(image_filename)
        except:
            return False
        
        try:
            #if the image has not been opened by PASKIL before then the camera id will be found here
            if image.info['Source'] == "CAMERA_ID xxxxx.A95J5020.A00L9122.xxxxxx":
                return True
            else:
                return False
        except KeyError:
            return False
            
    ###################################################################################    
        
    def open(self,image_filename, info_filename):
        image = Image.open(image_filename)
        
        #read image header data
        info=image.info

        #Read site info file
        camera={}
        processing={}
        header=image.info.copy() #copy header data stored in image
        
        with open(info_filename,"r") as info_file:
            for line in info_file: #read file line by line
                if line.isspace(): 
                    continue #ignore blank lines
                words=line.split("=") #split the line at the = sign
                
                if len(words) != 2:
                    print("Error! allskyImagePlugins.UiO_Allsky_LYR.open(): Cannot read site info file, too many words per line")
                    sys.exit()
                    
                camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip() #store the values (minus white space) in a dictionary
        
        #create a dictionary containing all the metadata
        info={'header':header,'camera':camera,'processing':processing}
    
        #return new allskyImage object
        return allskyImage.allskyImage(image,image.filename,info)
        
    ###################################################################################
###################################################################################

#register the plugin with PASKIL
allskyImagePlugins.register(UiO_Allsky_LYR_PNG())
