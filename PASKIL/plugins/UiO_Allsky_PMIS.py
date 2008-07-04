"""
PASKIL plugin for opening PMIS files created by the UiO allsky cameras in Longyearbyen and Ny Alesund.
"""
from __future__ import with_statement
from PASKIL.allskyImage import allskyImage
from PASKIL.allskyImagePlugins import register
import PmisImagePlugin
import sys,datetime
import Image

class UiO_Allsky_PMIS:
    
    def __init__(self):
        self.name = "UiO allsky camera PMIS image"
       
    ###################################################################################    
    
    def test(self, image_filename, info_filename):

        #load image
        try:
            image = Image.open(image_filename)
  
        except:
            return False
        
        if image.format == "PMIS":
            return True
        else:
            return False
            
    ###################################################################################                
    
    def open(self, image_filename, info_filename):    
        image = Image.open(image_filename)
        
        with open(info_filename,"r") as info_file:
        
            camera={}
            processing={}
            header=image.info.copy()
            
            #check that a site info file was specified
            if info_file == None:
                raise ValueError, "You must specify a site information file for this type of image"
            
            #check that the wavelength in the header matches the wavelength in the file extension
            if image.filename.endswith(("r","s","t","u","v")) and header['Wavelength'] != "630.0nm":
                raise ValueError, "Wavelength in header does not match wavelength denoted by file extension"
            
            if image.filename.endswith(("g","h","i","j","k")) and header['Wavelength'] != "557.7nm":
                raise ValueError, "Wavelength in header does not match wavelength denoted by file extension"
            
            if image.filename.endswith(("b","c","d","e","f")) and header['Wavelength'] != "427.8nm":
                raise ValueError, "Wavelength in header does not match wavelength denoted by file extension"
            
            #Read site info file
            with open(info_filename,"r") as info_file:
                for line in info_file: #read file line by line
                    if line.isspace(): 
                        continue #ignore blank lines
                    words=line.split("=") #split the line at the = sign
                    
                    if len(words) != 2:
                        print "Error! allskyImagePlugins.DSLR_LYR.open(): Cannot read site info file, too many words per line"
                        sys.exit()
                        
                    camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip() #store the values (minus white space) in a dictionary
                
            #convert the creation time data stored in the PMIS header into the PASKIL format
            try:
                creation_time=datetime.datetime.strptime(header['Creation Time'], "%Y-%m-%d_%H:%M:%S")
            except:
                #different date format for 1997
                creation_time=datetime.datetime.strptime(header['Creation Time'], "%Y-%m-%d_%H.%M.%S")
                
            header['Creation Time']=creation_time.strftime("%d %b %Y %H:%M:%S %Z")
            
            info={'header':header,'camera':camera,'processing':processing}
            
            #return new allskyImage object
            return allskyImage(image.convert("I"),image.filename,info)
        
    ###################################################################################
###################################################################################

register(UiO_Allsky_PMIS())



   

