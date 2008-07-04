"""
PIL plugin for opening the PMIS files that used to be produced by the UiO ASC. This plugin is largely
incomplete and needs a lot more work done to it to make it robust.
"""

import Image, ImageFile
import string,sys

class PmisImageFile(ImageFile.ImageFile):

    format = "PMIS"
    format_description = "Pmis raster image"

    def _open(self):
	
        # check header
        header = self.fp.read(100)
        if header[:4] != "PMIS":
            raise SyntaxError, "Not a PMIS file"
        
        #read header data
        header = header[60:]
        
        #find indicies of data fields
        indicies=[]
        try:
            indicies.append(header.index("D"))
            indicies.append(header.index("W"))
            indicies.append(header.index("F"))
            indicies.append(header.index("G"))
            indicies.append(header.index("E"))
            try:
                indicies.append(header.index("$"))
            except ValueError:
                indicies.append(header.index("S"))
        except ValueError:
            print "Cannot read pmis header data"
            sys.exit()
            
        #sort list
        indicies.sort()
  
        #create data fields dictionary
        data_fields={'D':'Creation Time','W':'Wavelength','F':'Filter Number','G':'Gain','E':'Exposure Time','$':'Site','S':'Site'}
 
        #loop through list of indices and read data
        for i in range(len(indicies)-1):             
            data=header[indicies[i]+1:indicies[i+1]]
            self.info[data_fields[header[indicies[i]]]]=data
        
        #read final data field in list
        data=header[indicies[len(indicies)-1]+1:]
        self.info[data_fields[header[indicies[len(indicies)-1]]]]=data
  
        # size in pixels (width, height)
        self.size = int(512), int(512)
 
        # Set image mode, in this case 32bit floating point pixel values
        self.mode="F"
     
        #image filetype setting
        self.filetype = "PMIS"
     
        # data descriptor (how the pixel data is arranged, and how to read it)
        self.tile = [("raw", (0, 0)+self.size, 180, ("F;16",0,1))]

#Image.register_open("PMIS", PmisImageFile)

Image.register_open("PMIS", PmisImageFile) 

#PMIS files have a whole range of extensions that they can have. Need to register them all
hex_range=['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']
filter_letter=["r","s","t","u","v","g","h","i","j","k","b","c","d","e","f"]

for i in hex_range:
    for j in hex_range:
        for k in filter_letter:
            Image.register_extension("PMIS","."+i+j+k) #register extension with PIL
   
