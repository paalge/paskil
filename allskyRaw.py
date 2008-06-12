from extensions import cRaw
from PIL import Image
import allskyImage
import datetime,numpy,zlib


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
    red_data=numpy.array(raw_data[:,0],dtype='int32')
    green1_data=numpy.array(raw_data[:,1],dtype='int32')
    blue_data=numpy.array(raw_data[:,2],dtype='int32')
    green2_data=numpy.array(raw_data[:,3],dtype='int32')
    
    #convert the raw data array back into an image
    image1=Image.fromstring("I", (width, height), red_data.tostring())
    image2=Image.fromstring("I", (width, height), green1_data.tostring())
    image3=Image.fromstring("I", (width, height), blue_data.tostring())
    image4=Image.fromstring("I", (width, height), green2_data.tostring())

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

class rawImage:
    """
    Holds the separate channels of a raw image file.
    """
    
    def __init__(self,images, filename, info):
        #set private class attributes
        self.__channels = []
        
        for image in images:
            self.__channels.append(image.copy())
            
        for channel in self.__channels:    
            channel.__info = {}
            
        self.__size = self.__channels[0].size
        self.__filename = filename
        self.__info = {}
        
        #make hard copies of the info libraries 
        self.__info['camera'] = info['camera'].copy()
        self.__info['header'] = info['header'].copy()
        self.__info['processing'] = info['processing'].copy()
        
    ###################################################################################        
        
    def getChannel(self,channel):
        """
        Returns an allskyImage object containing the image data of the specified raw channel.
        """    
        
        if channel >= len(self.__channels) - 1:
            raise ValueError,"Selected channel does not exist."
        
        new_info={'header':self.__info['header'].copy(),'camera':self.__info['camera'].copy(),'processing':self.__info['processing'].copy()}
        
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
        
        
        return allskyImage.allskyImage(self.__channels[channel], self.__filename, new_info)
        
     ###################################################################################      
     
    def save(self,filename):
        """
        Compresses the raw data using the Canonical Huffman algorithm and saves the raw data as 
        a PASKIL '.sqd' file. Only pixel data within the field of view is saved, resulting in 
        considerably smaller files than is possible using other formats.       
        """
        
        #add image size to info dict
        size=self.__channels[0].size
        self.__info['header']['size']=size
        
        #convert the header data to a string and compress it using the zip library
        compressed_header = zlib.compress(str(self.__info), 9)
        
        #create a mask image for the field of view
        white_image = Image.new('L', size)
        
        mask = allskyImage.allskyImage(white_image,"None",self.__info)
        
        mask = mask.binaryMask(self.__info['camera']['fov_angle'])
        
        mask_array = numpy.fromstring(mask.getImage().tostring())
        
        #combine the channels of the raw image into an array
        raw_data = numpy.fromstring(self.__channels[0].tostring() + self.__channels[1].tostring() + self.__channels[2].tostring() + self.__channels[3].tostring())
        
        #compress the data using the huffman algorithm
        (compressed_data,compressed_size,decode_table) = cSquish.compress(raw_data,mask_array)
        
        
        
        
        
        
        
