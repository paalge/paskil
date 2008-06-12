"""
Plugin for loading images taken using the Nikon D80 DSLR allsky camera at KHO. This plugin is for opening
the PPM files produced by decoding the raw NEF files using dcraw.
"""

from PASKIL import allskyImage, allskyImagePlugins
import sys,datetime

class DSLR_LYR_JPG:

    def __init__(self):
        self.name = "Jeff and Nial's DSLR camera at KHO"
        
    ###################################################################################    
    
    def test(self,image,info_file):
    
        if image.format == "JPEG":
            try:
                filename = image.filename
                filename=filename.split("/")
                filename=filename[len(filename)-1]
                datetime.datetime.strptime(filename.rstrip(".JPG"), "LYR-SLR-%Y%m%d_%H%M%S")
            except ValueError:
                return False
            return True
        else:
            return False
            
    ###################################################################################
        
    def open(self,image,info_file):
        
        #Read site info file
        camera={}
        processing={}
        header=image.info
        for line in info_file: #read file line by line
            if line.isspace(): 
                continue #ignore blank lines
            words=line.split("=") #split the line at the = sign
            
            if len(words) != 2:
                print "Error! allskyImagePlugins.DSLR_LYR.open(): Cannot read site info file, too many words per line"
                sys.exit()
                
            camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip() #store the values (minus white space) in a dictionary
        
        #Read creation time from filename
        filename = image.filename
        filename=filename.split("/")
        filename=filename[len(filename)-1]
        creation_time=datetime.datetime.strptime(filename.rstrip(".JPG"), "LYR-SLR-%Y%m%d_%H%M%S")
        
        creation_time=creation_time.strftime("%d %b %Y %H:%M:%S %Z")
        header = {'Wavelength':"Visible",'Creation Time': creation_time}
        
        info={'header':header,'camera':camera,'processing':processing}
        
        #return new allskyImage object
        return allskyImage.allskyImage(image,image.filename,info)
        
    ###################################################################################
###################################################################################

allskyImagePlugins.register(DSLR_LYR_JPG())
