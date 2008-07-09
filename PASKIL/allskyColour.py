"""
Introduction:
    
    The allskyColour module provides functions and classes for producing false colour tables to map 
    greyscale images to RGB images. The colour mappings are done using histogram data from the images. 
    Intensity ranges with a high pixel count are given the largest sections of the palette, whereas 
    intensity ranges with a very low pixel count may be mapped to a single colour.


    
Concepts:

    Mappings between greyscale images and RGB images are done using a colour table. This is literally a 
    table of RGB tuples, one for each possible pixel value in the greyscale image. For example a colour 
    table for an 8 bit greyscale image will have 256 entries, whereas one for a 12 bit image will have 
    4096 entries. A greyscale pixel with a value of 234 will be mapped to the colour stored in the 234th 
    element of the colour table.
    
    The palette controls which colours are available for use in the colour table. For example, you might 
    want to map a greyscale image to a red-scale image, in which case you only want shades of red in your 
    colour table. In this case, the palette will contain a linear range of red values e.g. (0,0,0) to 
    (255,0,0). It is unlikely that you want to apply a linear colour scale to your all-sky image, so PASKIL
    produces the colour table from the palette using a histogram. Intensity ranges with a high pixel count 
    are given the largest sections of the palette, whereas intensity ranges with a very low pixel count may
    be mapped to a single colour. This helps to pick out the most detail in the image.
    
    A specific intensity range can be picked out using upper and lower thresholds. Intensities below the 
    lower threshold are set to the first colour in the palette and intensities above the upper threshold are 
    set to the last colour in the palette. This leaves more colours available for the intensity range that 
    you are interested in.
    
    
    
Example:
    
    The following example creates an allskyImage object from the image "test.png". It then finds the mean 
    histogram of all the images in the "test_images" directory. Using this histogram and the default palette
    it applies a colour table to the image and saves it as "test_out.png". The thresholds are set so as to 
    apply the colour table to the full range of intensities in the image.


        from PASKIL import allskyImage,allskyData, allskyColour #import modules
    
        image = allskyImage.new("test.png",site_info_file="site_info.txt") #create allskyImage object
        
        #create dataset object
        dataset = allskyData.new("test_images","630",["png","jpg"],site_info_file="site_info.txt") 
    
        histogram=allskyColour.histogram(dataset) #create histogram using dataset
    
        colour_table=allskyColour.default(histogram,(0,255)) #create colourTable object using the histogram
        image=image.applyColourTable(colour_table.getColourTable()) #apply the colour table to the image
    
        image.save("test_out.png") #save the image

"""

################################################################################################################################################################



from PIL import Image #imports from PIL
import warnings


#Functions

###################################################################################

def createSegment(length,start_RGB,end_RGB):
    """
    Creates a new segment object. The length argument should be an integer defining the range of the segment 
    (the number of colours it contains). The start_RGB and end_RGB are RGB tuples (R,G,B) defining the colour 
    range of the segment. The colours are found by a linear interpolation of the colour range between the start 
    and end nodes. For example createSegment(256,(0,0,0),(0,0,255)) will produce a segment with 256 colours 
    which range linearly from black to blue. It may be useful to look at the source code for the default() 
    function to see how segments can be used to build up palettes spanning a large range of colours.
    """
    
    return segment(length,start_RGB,end_RGB)

###################################################################################

def default(histogram,thresholds):
    """
    Returns a colourTable object which uses a default palette (black to blue to red) consisting of five 
    segments. The histogram argument should be a list of integers representing the pixel count of their
    respective pixel value. For example item 0 in the list should be the number of black pixels. It is 
    recommended to use mean histograms for directories of images such as those produced by the histogram() 
    function. The thresholds argument should be a tuple (min_threshold,max_threshold). It controls what range
    of intensities the colour table is applied to. Intensities above the max_threshold are set to the 
    highest value in the colour table (red for the default), and intensities below the min_threshold are set 
    to the lowest (black for the default)
    """
    segments=range(5)        
    segments[0]=segment(256,(0,0,0),(0,0,255))
    segments[1]=segment(256,(0,0,255),(0,255,255))
    segments[2]=segment(256,(0,255,255),(0,255,0))
    segments[3]=segment(256,(0,255,0),(255,255,0))
    segments[4]=segment(256,(255,255,0),(255,0,0))
    
    return fromList(segments,histogram,thresholds)
    
###################################################################################

def histogram(dataset):
    """
    Function returns a mean histogram for all the images in the dataset specified (this should be an 
    allskyData.dataset object).
    """
    if dataset.getMode() == "L":
        size=256
    elif dataset.getMode() == "I":
        size=65536
    else:
        raise ValueError, "Unsupported image mode"
    
    number_of_images=0 #number of images read
    total_histogram=range(size)
    mean_histogram=range(size)
    current_histogram=range(size)
    
    for infile in dataset.getAll():
        current_image=Image.open(infile[0])
            
        number_of_images+=1
        
        if dataset.getMode() == "L":
            current_histogram=current_image.histogram() #use PIL histogram method for 8bit images
        else:
            current_histogram=[0]*size #create list of zeros
            
            im_pix=current_image.load() #load pixel values
            
            width,height=current_image.size
            
            for x in range(width):
                for y in range(height):
                    current_histogram[im_pix[x,y]]+=1
            
        for i in range(size):
            total_histogram[i]+=current_histogram[i]
                    
    for i in range(size):    
        mean_histogram[i]=int((float(total_histogram[i])/float(number_of_images))+0.5)    
    
    return mean_histogram

###################################################################################

def fromImage(filename,histogram,thresholds):
    """
    Function returns a colourTable object which uses the palette contained in the image specified by the 
    filename argument. Such palette files can be produced using the colourTable.savePalette() method. Other 
    arguments are the same as for default().
    """
    #open palette image and store the first line of pixel values as the colour_table
    im=Image.open(filename)
    width,height=im.size
    
    palette=list(im.getdata())[0:width]
    
    #create a colourTable object to hold the data
    colour_table = colourTable(palette,histogram,thresholds)
    
    return colour_table
    
###################################################################################    

def fromList(segments,histogram,thresholds):
    """
    Function returns a colourTable object which uses a palette defined by a list of segment objects passed 
    as the segments argument. The list must contain at least one entry. See the segments class for details. 
    Other arguments are the same as for default().
    """
    if len(segments)<1:
        raise ValueError, "List of segments must contain at least one entry"
    
    #create palette from list of segments
    palette=[]
    for i in range(len(segments)):
        palette=palette+segments[i].tolist()
        
    #create a colourTable object to hold the data
    colour_table = colourTable(palette,histogram,thresholds)
    
    return colour_table
    
###################################################################################    

def loadHistogram(filename):
    """
    Function returns a histogram object based on the data in the text file specified by the filename 
    argument. This function reads files produced by the histogram.save() method.
    """
    #open histogram file for reading
    fp=open(filename,"r")
    histogram=[]
    index=[]
    for line in fp:
        words = line.split()
        if len(words) !=2:
            raise ValueError, "Incorrect number of data entries in file: "+filename
            
        histogram.append(int(words[1]))
        index.append(int(words[0]))
        
    if index != range(256) and index != range(65536):
        raise ValueError, "Incorrect number of data entries in file: "+filename

    fp.close()
    
    return histogram        

###################################################################################    



#class definitions

###################################################################################

class basicColourTable:
    """
    Reduced version of the colourTable class, which only holds the colour table data and not the palette and
    histogram data. This class is mostly used internally by PASKIL for storing colour table data in saved
    images.
    """
    def __init__(self,colour_table):
        self.colour_table=colour_table
    
    def getColourTable(self):
        """
        Returns the colour table data in a format compatible with PIL's Image class putpalette() method.
        """
        #convert colour_table to a list format for use with putpalette()
        list_colour_table=range(3*len(self.colour_table))
        j=0    
        for i in range(len(self.colour_table)):
            list_colour_table[j],list_colour_table[j+1],list_colour_table[j+2]=self.colour_table[i]
            j+=3
        
        return list_colour_table 

###################################################################################

class colourTable:
    """
    Container class for histogram, palette and colour table data.
    """
    def __init__(self,palette,histogram,thresholds):
        
        #check that thresholds are within range of image
        if thresholds[1]>=len(histogram):
            raise ValueError, "Max threshold is outside of image pixel value range"
        
        #set class attributes
        self.__palette=palette
        self.__histogram=histogram
        
        #create colour table from palette and histogram
        self.colour_table=[] 
    
        #find total number of counts in histogram between thresholds
        total_counts=0
        for i in range(thresholds[0],thresholds[1]):
            total_counts+=histogram[i]
        
        #set values below min_threshold to first value in colour table
        for i in range(thresholds[0]):
            self.colour_table.append(palette[0])
        
        #set values between threshold to colours, with a step size based on the histogram.
        #This gives widest colour variation at intensities with high pixel counts
        place_holder=0
        float_place_holder=0.0
        count=0
        for i in range(thresholds[0],thresholds[1]):
            self.colour_table.append(palette[place_holder])
            
            #calculate current count
            count=count+histogram[i]
            float_place_holder=(float(len(palette))*float(count))/float(total_counts)
            place_holder=int(float_place_holder+0.5)
            
            if place_holder >= len(palette):
                warnings.warn("Placeholder exceeds palette length. If this message appears more than once, consider ajusting thresholds")
                place_holder=len(palette)-1
            
        #set values above max_threshold to last value in colour table
        for i in range(thresholds[1],len(histogram)):
            self.colour_table.append(palette[len(palette)-1])

    ###################################################################################
    
    def getColourTable(self):
        """
        Returns the colour table data in a format compatible with PIL's Image class putpalette() method.
        """
        #convert colour_table to a list format for use with putpalette()
        list_colour_table=range(3*len(self.__histogram))
        j=0    
        for i in range(len(self.__histogram)):
            list_colour_table[j],list_colour_table[j+1],list_colour_table[j+2]=self.colour_table[i]
            j+=3
        
        return list_colour_table
    
    ###################################################################################

    def saveColourTable(self,filename):
        """
        Saves a quicklook image of the colour_table. The file type should be specified in the filename 
        argument e.g. saveColourTable(``my_colours.png'').
        """
        image_string=[]
        for i in range(50):
            image_string=image_string+self.colour_table #give the image a larger height than one pixel


        im=Image.new(mode="RGB",size=(len(self.colour_table),50))
        im.putdata(image_string)
        im.save(filename)

    ###################################################################################
    
    def saveHistogram(self,filename):
        """
        Saves the histogram data as a text file. This can be useful for plotting the histogram if desired.
        """
        output_file=open(filename,"w")        
        for i in range(len(self.__histogram)-1):    
            output_file.write(str(i)+" "+str(self.__histogram[i])+"\n")
        output_file.close()    
        
    ###################################################################################
            
    def savePalette(self,filename):
        """
        Saves a quicklook image of the palette. The file type should be specified in the filename 
        argument e.g. savePalette(``my_palette.png'').
        """
        image_string=[]
        for i in range(50):
            image_string=image_string+self.__palette #give the image a larger height than one pixel


        im=Image.new(mode="RGB",size=(len(self.__palette),50))
        im.putdata(image_string)
        im.save(filename)

    ###################################################################################
###################################################################################

class segment:
    """
    Class to contain a linear colour range. Lists of segment objects can be used to create complex palettes
    spanning large colour ranges using the fromList() function.
    """
    def __init__(self,length,start_RGB,end_RGB):
        self.__length=length
        self.__start_Red,self.__start_Green,self.__start_Blue=start_RGB
        self.__end_Red,self.__end_Green,self.__end_Blue=end_RGB
        
    ###################################################################################    
        
    def tolist(self):
        """
        Returns a list of (R,G,B) tuples containing all the colours in the segment.
        """
        colour_table=[]
        
        grad_R=float((self.__end_Red-self.__start_Red))/float(self.__length)
        grad_B=float((self.__end_Blue-self.__start_Blue))/float(self.__length)
        grad_G=float((self.__end_Green-self.__start_Green))/float(self.__length)
        
        
        for i in range(self.__length):
            R=self.__start_Red+(float(i)*grad_R)
            G=self.__start_Green+(float(i)*grad_G)
            B=self.__start_Blue+(float(i)*grad_B)
            RGB=tuple((int(R+0.5),int(G+0.5),int(B+0.5)))
            colour_table.append(RGB)
                        
        return colour_table
        
    ###################################################################################    
###################################################################################
    
