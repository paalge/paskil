import Image,ImageChops
import allskyImage
import datetime,numpy,zlib
import warnings
from PASKIL.extensions import cRaw,cSquish

###################################################################################

def getHeaderData(filename):
    """
    Returns a dictionary containing the header data stored in an .sqd raw file.
    """
    
    #read compressed header from file using cSquish extension
    header = cSquish.getHeader(filename)
        
    return eval(header)
    
###################################################################################   

def isRaw(filename):
    """
    Returns True if the file is a raw image file that can be decoded by the allskyRaw module,
    False otherwise.
    """
    
    #check if the file is an sqd file first since this takes less time
    if cSquish.isSqd(filename):
        return True
    else:
        fp = open(filename,"rb")
        
        if cRaw.canDecode(fp):
            fp.close()
            return True
        else:
            fp.close()
            return False

###################################################################################
     
def getTimeStamp(filename):
    """
    Returns a datetime object containing the capture time (as recorded by the camera) of the raw image specified by
    the filename argument.
    """
    #open file for reading (binary)
    fp=open(filename,"rb")
    
    #get timestamp from raw image
    timestamp=cRaw.getTimestamp(fp)
    
    #close the file
    fp.close()
    
    #convert the timestamp to a datetime object
    time=datetime.datetime.fromtimestamp(timestamp)
    
    #return the answer
    return time

###################################################################################

def getRawData(filename):
    """
    Returns a tuple of length four, containing PIL image objects of the raw image data. Each image corresponds to 
    a single channel in the raw image, typically (R,G,B,G).
    """
    #open file for reading (binary)
    fp=open(filename,"rb")
    
    #get the raw pixel data from the image
    (raw_data,width,height)=cRaw.getRawData(fp)
    
    
    #close the file
    fp.close()

    #split the array into 4 arrays (one for each color) and convert the data into Int32
    red_data=numpy.array(raw_data[:,0],dtype="int32")
    red_data.shape = (height,width)

    green1_data=numpy.array(raw_data[:,1],dtype="int32")
    green1_data.shape = (height,width)
    
    blue_data=numpy.array(raw_data[:,2],dtype="int32")
    blue_data.shape = (height,width)
    
    green2_data=numpy.array(raw_data[:,3],dtype="int32")
    green2_data.shape = (height,width,)
    
    #convert the raw data array back into an image
    image1=Image.fromarray(red_data)
    #image2=Image.fromstring("I",(width,height),green1_data.tostring())
    image2=Image.fromarray(green1_data)
    image3=Image.fromarray(blue_data)
    image4=Image.fromarray(green2_data)

    return (image1,image2,image3,image4)

###################################################################################

def new(filename, site_info_file):
    
    #load image data
    (ch1,ch2,ch3,ch4) = getRawData(filename)
    
    #open site info file
    info_file=open(site_info_file,'r')
    
    #read in data from site info file and store in info dictionary
    for line in info_file: #read file line by line
            if line.isspace(): 
                continue #ignore blank lines
            words=line.split("=") #split the line at the = sign
            
            if len(words) != 2:
                raise ValueError, "Cannot read site info file, too many words per line"

            camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip() #store the values (minus white space) in a dictionary
     
    creation_time=getTimeStamp(filename)
        
    creation_time=creation_time.strftime("%d %b %Y %H:%M:%S %Z")
    header = {'Wavelength':"RGBG",'Creation Time': creation_time}   
    
    
    info={'header':header,'camera':camera,'processing':{}}
    
    return rawImage((ch1,ch2,ch3,ch4),filename,info)

###################################################################################

class rawImage(allskyImage.allskyImage):
    """
    Holds the separate channels of a raw image file.
    """
    
    def __init__(self, filename, info, channels=None):
        
        #set private class attributes
        self.__channels = []
        
        if channels is not None:
            for ch in channels:
                self.__channels.append(ch)
        
        if channels is None:
            self.__loaded = False
        else:
            self.__loaded = True

        #create dummy image object to pass to allskyImage.allskyImage.__init__()
        dummy_image = Image.new("1",(0,0))
        
        allskyImage.allskyImage.__init__(self,dummy_image,filename,info)
   
    ###################################################################################      
        
    def getImage(self):
        return self.convertToRGB().getImage()
    
    ###################################################################################          
    
    def getStrip(self, angle, strip_width,channel=None):
        
        if channel == None:
            rgb_image = self.convertToRGB()
            
            return rgb_image.getStrip(angle,strip_width)
        
        channel = self.getChannel(channel)
        return channel.getStrip(angle,strip_width)
        
    ###################################################################################      
    
    def applyColourTable(self,colour_table):
        raise TypeError, "Cannot apply a colour table to a raw image. Apply it to the separate channels"
    
    ###################################################################################          
    
    def convertToRGB(self):
        
        self.load()
        
        mean_green = ImageChops.add(self.__channels[1],self.__channels[3],0.5)
        
        #rescale values (currently have 16bit data stored in 32bit integers)
        scale = 4294967295.0 / 65535.0 

        #offset = - min_intensity * scale     .point(lambda i: i * scale + 0)
     
        
        
        #might need to convert each channel to mode "L" before trying to merge them to RGB
        rgb_image = Image.merge("RGB",(self.__channels[0].point(lambda i: i * scale + 0),mean_green.point(lambda i: i * scale + 0),self.__channels[2].point(lambda i: i * scale + 0)))
        
        new_info = self.getInfo()
        
        new_info['header']['Wavelength'] = "RGB"
        
        return allskyImage.allskyImage(rgb_image,self.getFilename,new_info)
            
    ###################################################################################
    
    def addTimestamp(self,format, colour="black", fontsize=20):
        
        return self.__runMethod(allskyImage.allskyImage.addTimestamp, format, colour=colour,fontsize=fontsize)
           
    ###################################################################################
    
    def __runMethod(self,method,*args,**kwargs):
        self.load()
        new_channels = []
        
        info_bkup = str(self.getInfo())
        
        for self._allskyImage__image in self.__channels:
            self._allskyImage__info = eval(info_bkup)
            new_channels.append(method(self,*args,**kwargs).getImage())
        
        return rawImage(self.getFilename(),self.getInfo(),channels = new_channels)
    
    ###################################################################################       
    def alignNorth(self,north="geographic"):
        
        return self.__runMethod(allskyImage.allskyImage.alignNorth, north=north)
           
    ###################################################################################
    
    def binaryMask(self, fov_angle, inverted=False):
        
        return self.__runMethod(allskyImage.allskyImage.binaryMask, fov_angle, inverted=inverted)
           
    ###################################################################################
    
    def centerImage(self):
        return self.__runMethod(allskyImage.allskyImage.centerImage)
    
    ###################################################################################    
    
    def convertTo8bit(self):
        return self.__runMethod(allskyImage.allskyImage.convertTo8bit)
    
    ###################################################################################        
    
    def createQuicklook(self, size=(480, 640), timestamp="%a %b %d %Y, %H:%M:%S %Z", fontsize=16):
        
        rgb_image = self.convertToRGB()
        
        return rgb_image.createQuicklook(size=size, timestamp=timestamp, fontsize=fontsize)
    
    ###################################################################################        
    
    def flatFieldCorrection(self, calibration):
        return self.__runMethod(allskyImage.allskyImage.flatFieldCorrection,calibration)
    
    ###################################################################################            
    
    def medianFilter(self, n,separate_channels=False):
        if not separate_channels:
            rgb_image = self.convertToRGB()
            return rgb_image.medianFilter(n)
        else:
            return self.__runMethod(allskyImage.allskyImage.medianFilter,n)
        
    ################################################################################### 
    
    def projectToHeight(self, height, grid_size=300,background='black',channel=None):
        
        if channel == None:
            rgb_image = self.convertToRGB()
            return rgb_image.projectToHeight(height, grid_size=grid_size, background=background)
        
        return self.getChannel(channel).projectToHeight(height, grid_size=grid_size, background=background)
               
    ###################################################################################    
    
    def resize(self,size):
        
        self.__runMethod(allskyImage.allskyImage.resize,size)
    
    ###################################################################################
                                       
    def load(self):
        if not self.__loaded:
            
            images = getRawData(self.getFilename())
            
            for image in images:
                self.__channels.append(image.copy())
            
            for channel in self.__channels:    
                channel.info = {}
            
            self.__loaded = True
        
    ###################################################################################        
        
    def getChannel(self,channel):
        """
        Returns an allskyImage object containing the image data of the specified raw channel.
        """    
        
        self.load()
        
        if channel >= len(self.__channels) - 1:
            raise ValueError,"Selected channel does not exist."
        
        new_info=self.getInfo()
        
        if channel == 0:
            new_info['header']['Wavelength']='Red'
        elif channel == 1:
            new_info['header']['Wavelength']='Green1'
        elif channel == 2:
            new_info['header']['Wavelength']='Blue'
        elif channel == 3:
            new_info['header']['Wavelength']='Green2'
        else:
            raise ValueError, "Unknown channel selection"
        
        
        return allskyImage.allskyImage(self.__channels[channel], self.getFilename, new_info)
  
    ###################################################################################
               
    
    ###################################################################################     
      
    def save(self,filename):
        """
        Compresses the raw data using the Canonical Huffman algorithm and saves the raw data as 
        a PASKIL '.sqd' file. Only pixel data within the field of view is saved, resulting in 
        considerably smaller files than is possible using other formats.       
        """
        
        self.load()
            
        #add image size to info dict
        size=self.__channels[0].size

        self.__info['header']['size']=size
        
        #convert the header data to a string and compress it using the zip library
        #compressed_header = zlib.compress(str(self.__info), 9)
        
        #create a mask image for the field of view
        white_image = Image.new('I', size,color=255)
        
        mask = allskyImage.allskyImage(white_image,"None",self.__info)
        
        mask = mask.binaryMask(float(self.__info['camera']['fov_angle']))

        mask_array = numpy.asarray(mask.getImage())
        mask_array = mask_array.flatten()

        mask_array = numpy.concatenate((mask_array,mask_array,mask_array,mask_array))
        print "mask array shape = ", mask_array.shape

        #combine the channels of the raw image into an array
        channel1_data = numpy.asarray(self.__channels[0]).flatten()
        channel2_data = numpy.asarray(self.__channels[1]).flatten()
        channel3_data = numpy.asarray(self.__channels[2]).flatten()
        channel4_data = numpy.asarray(self.__channels[3]).flatten()
        
        raw_data = numpy.concatenate((channel1_data,channel2_data,channel3_data,channel4_data))
    
    
        #sys.exit()
        #compress the data using the huffman algorithm
        cSquish.compress(raw_data,mask_array,str(self.__info),filename.rstrip(".sqd"))
  
     ###################################################################################
###################################################################################            
       
class sqdImage(rawImage):       
       
     def __init__(self,filename):
           
         #define class private attributes
         self.__info = getHeaderData(filename)
         self.__filename = filename
         self.__loaded = False
         self.__size = cSquish.getSize(filename)
         self.__channels = []
       
     ###################################################################################       
       
     def load(self):
         
         if not self.__loaded:
             #create a mask image for the field of view
             white_image = Image.new('L', self.__size)
        
             mask = allskyImage.allskyImage(white_image,"None",self.__info)
        
             mask = mask.binaryMask(float(self.__info['camera']['fov_angle']))
        
             mask_array = numpy.asarray(mask)
             
             decoded_data = cSquish.decompress(self.__filename)
             print "got here"
             im_array = numpy.zeros(shape=(4,self.__size[0],self.__size[1]),dtype='int')
             
             offset = self.__size[0]*self.__size[1]
             
             for k in range(4):
                 for i in range(self.__size[0]):
                     for j in range(self.__size[1]):
                         if mask_array[i][j]:
                             im_array[k][i][j] = decoded_data[i+j+k*offset]
             
             im = Image.fromarray(im_array[0])
             im.save("decodedsqd.png")
             
 
         
     ###################################################################################
###################################################################################                    
           