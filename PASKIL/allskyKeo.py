"""
Introduction:

    The allskyKeo module provides a keogram class used to represent a keogram. Keograms are an effective
    means to summarise all-sky data from a long time period. They are basically thin strips taken from all
    the images and stacked together in the time axis.
    
    

Concepts:
    
    Keograms are created by taking strips of pixel values out of all-sky images and stacking them together.
    The width of the strip of pixels can be set using the strip_width argument. A value of about 5 gives 
    reasonable results. Gaps in the data are interpolated using a linear interpolation. However, large gaps
    due to lack of data are not interpolated across and will result in blank spaces in the keogram. The 
    angle (from geographic North) that the strips are taken from the images at, can be set using the angle 
    argument.
    
    Note: The Open Closed Boundary (OCB) methods in this module are 'experimental' to say the least, and have
    little scientific backing. Probably best not to use them!



Example:

    The following example creates a keogram of the 630nm wavelength between 18:30 and 19:30 on the 4/2/2003
    using the allsky images of type "png" stored in the directory "Allsky Images". The recursive option is 
    used to traverse the entire directory structure contained within "Allsky Images" looking for images. 
    The keogram then has the OCB drawn on it and is plotted and viewed in an interactive plotting window.


        from PASKIL import allskyKeo,allskyData
        import datetime
        from pylab import *
        
        #create datetime object defining start time for keogram
        start_time=datetime.datetime.strptime("04 Feb 2003 18:30:00 GMT","%d %b %Y %H:%M:%S %Z")
        
        #create datetime object defining end time for keogram 
        end_time=datetime.datetime.strptime("04 Feb 2003 19:30:00 GMT","%d %b %Y %H:%M:%S %Z") 
        
        #create a new dataset object
        dataset=allskyData.new("Allsky Images","630","png",site_info_file="site_info.txt",recursive="r") 
        
        #create a new keogram with a sweep angle of 33 degrees and using a strip width of 3 pixels and a data spacing of 60 seconds
        keo=allskyKeo.new(dataset,start_time,end_time,33,3,60) 
    
        keo2=keo.plotOCB() #draw the OCB onto the keogram image
        plot=keo2.plot() #plot the keogram

        plot #identify which figure we want to show
        show() #open the figure in an interactive plotting window    
    
""" 

################################################################################################################################################################

import datetime
import calendar
import time
import math
import matplotlib
import warnings
import Image
import ImageChops
import ImageFilter
import ImageOps

from pylab import figure, imshow, title, MinuteLocator, NullLocator, DateFormatter, twinx, twiny, date2num, num2date, savefig, clf, FixedLocator, FuncFormatter

from PASKIL import allskyImage, allskyColour, misc, stats

#Functions

###################################################################################    

def rev(x, pos):
    """
    This function is used in formatting the axes of a keogram plot.
    """
    return str(int(math.fabs(x-180)))

def __imagePreProcess(image):
    """
    Checks that the image has had all the requisit preprocessing needed before it is put into a keogram. 
    Returns an allskyImage object which has been processed, if no processing was required then it returns 
    the original object.
    """   
        
    if image.getInfo()['processing'].keys().count('binaryMask') == 0:
        image=image.binaryMask(float(image.getInfo()['camera']['fov_angle']))
        
    if image.getInfo()['processing'].keys().count('centerImage') == 0:
        image=image.centerImage()
        
    if image.getInfo()['processing'].keys().count('alignNorth') == 0:
        image=image.alignNorth()
    
    return image
        
###################################################################################            

def __checkImages(images, mode=None, wavelength=None, colour_table=None):
    """
    Checks that all allskyImages in the images list have the same mode, wavelength and 
    colour table either as each other or as those specified by the optional arguments.
    These are essentially the same checks that are done when a dataset is created.
    """
    if len(images) == 0:
        raise ValueError, "Cannot perform checks on an empty list!"
    
    #if no optional arguments are specified, then take the values from the first image in the list
    if mode == None:
        mode = images[0].getMode()
    
    if wavelength == None:
        wavelength = images[0].getInfo()['header']['Wavelength']
    
    if colour_table == None:
        try:
            colour_table = images[0].getInfo()['processing']['applyColourTable']
        except KeyError:
            colour_table = None
    
    #compare these values to all the other images in the list
    for im in images:
        if im.getMode() != mode:
            raise ValueError, "Image has incorrect mode, expecting mode: "+str(mode)
        if im.getInfo()['header']['Wavelength'] != wavelength:
            raise ValueError, "Image has incorrect wavelength, expecting: "+str(wavelength)
        try:
            if im.getInfo()['processing']['applyColourTable'] != colour_table:
                raise ValueError, "Image has incorrect colour table"
        except KeyError:
            if colour_table == None:
                pass
            else:
                raise ValueError, "Image has incorrect colour table"
      
###################################################################################
 
def load(filename):
    """
    Loads a keogram object from the specified file. Keogram files can be created using the save() method.
    """
    image=Image.open(filename)
    
    #read header data
    angle=float(image.info['angle'])
    if image.info['colour_table'] != str(None):
        colour_table=list(eval(image.info['colour_table']))
    else:
        colour_table=None

    start_time=datetime.datetime.strptime(image.info['start_time'].lstrip().rstrip(), "%d %b %Y %H:%M:%S")
    end_time=datetime.datetime.strptime(image.info['end_time'].lstrip().rstrip(), "%d %b %Y %H:%M:%S")
    OCB=list(eval(image.info['OCB']))
    fov_angle=float(image.info['fov_angle'])
    strip_width=int(image.info['strip_width'])
    keo_type = image.info['keo_type']
    data_points = eval(image.info['data_points'])
    data_spacing = int(image.info['data_spacing'])
    
    #clear image header data
    image.info={}
    
    #create new keogram object
    new_keogram=keogram(image, None, start_time, end_time, angle, fov_angle, OCB, strip_width, None, keo_type, data_points, data_spacing)
    
    #if it should have a colour table then apply it
    if colour_table != None:
        ct = allskyColour.basicColourTable(colour_table)
        new_keogram=new_keogram.applyColourTable(ct)
    
    return new_keogram
    
###################################################################################                
            
def new(data, angle, start_time=None, end_time=None, strip_width=5, data_spacing="AUTO", keo_type="CopyPaste"):
    """
    Returns a keogram object. The dataset argument should be an allskyData.dataset object which contains 
    the images from which the keogram will be produced.  The angle argument is the angle from geographic 
    North that the slices from the images will be taken. The strip width option controls the width (in pixels) 
    of the slice taken from the image. The start and end time options should be datetime objects specifying 
    the time range of the keogram (the keogram will be inclusive of these times). The default value is None, 
    in which case all images in the dataset will be included.The data_spacing option should be the amount of 
    time (in seconds) between the source images for the keogram. The default value is"AUTO", in which case the 
    minimum gap between consecutive images in the dataset is used. However, under some circumstances, this may 
    lead to a stripy, uninterpolated keogram, in which case you should increase the data_spacing value. The keo_type
    argument controls how the keogram is produced. If it is set to "Average" then the keogram will be made up of a 
    series of strips one pixel wide, which are the averaged pixel values of the slice taken from the image. These one
    pixel wide strips will then be interpolated between. Effective use of this type, requires a much larger strip width
    and is computationally more expensive. It is also not particularly sucessful for RGB keograms. "CopyPaste" type keograms
    are made up of finite width slices of the image (specified by strip_width), which are then interpolated between.
    This is not a keogram in the strictest sense of the word, since the finite width of the slices is plotted in the 
    time domain, which doesn't really make sense. However, for RGB keograms it often produces a more attractive plot
    with less interpolation effects. 
    """    
    #the strip width has to be odd otherwise life is too difficult
    if strip_width%2 == 0:
        strip_width += 1
        warnings.warn("strip_width must be an odd number. Changing to "+str(strip_width))
            
    #read the keogram parameters either from the dataset or the list of images
    if type(data) == type(list()):
        #data is list of allskyImage objects
        __checkImages(data) #check for consistancy of image properties
        
        times = []
        fov_angles = []
        radii =[]
        mode = data[0].getMode()
        try:
            colour_table = data[0].getInfo()['processing']['applyColourTable']
        except KeyError:
            colour_table = None
        
        for im in data:
            try:
                time=datetime.datetime.strptime(im.getInfo()['header']['Creation Time'], "%d %b %Y %H:%M:%S %Z")#read creation time from header
            except ValueError:
                time=datetime.datetime.strptime(im.getInfo()['header']['Creation Time']+"GMT", "%d %b %Y %H:%M:%S %Z")#read creation time from header
            times.append(time)
            fov_angles.append(im.getInfo()['camera']['fov_angle'])
            radii.append(int(im.getInfo()['camera']['Radius']))
        times = list(set(times)) #remove duplicate entries from times list
        keo_fov_angle = float(max(fov_angles))
        
    else:
        #the data argument is a dataset object
        times=list(set(data.getTimes())) #need to convert this list to a set just incase there are two images from the same time (would result in zero as separation)
        mode = data.getMode()
        keo_fov_angle = float(max(data.getFov_angles()))
        colour_table = data.getColourTable()
        radii = data.getRadii()
    
    times.sort()
        
    #if data_spacing is set to auto, then determine the data spacing in the data set
    if data_spacing=="AUTO":
        #if there is only one image in the dataset, then the spacing cannot be found!
        if len(times)< 2:
            raise RuntimeError, "Not enough images in dataset to allow automatic data spacing calculation"
        spacings=[]
        i=1
        while i < len(times):
            spacing = times[i]-times[i-1]
            if spacing != 0:
                spacings.append((times[i]-times[i-1]).seconds)
            i+=1
          
        #use smallest time spacing - otherwise some of the strips will overlap
        data_spacing=min(spacings)
    
        #find mean data_spacing. This is used to determine the maximum extent of interpolation (large gaps in the data are not filled in)
        mean_data_spacing_secs = stats.median(spacings) #changed to median for V3.2 since it gives better results
    else:
        mean_data_spacing_secs = data_spacing 
    
    #if start and end times are set to None, then get them from the list of times
    if start_time == None:
        start_time=min(times)
    if end_time == None:
        end_time=max(times)
    
    #if the start and end times are the same (e.g. if the keogram has been created with a single image)
    #then add one hour to the end time
    if start_time == end_time:
        end_time = end_time + datetime.timedelta(hours=1)
        
    #convert start and end times into seconds since the epoch
    start_secs=calendar.timegm(start_time.timetuple())
    end_secs=calendar.timegm(end_time.timetuple())
    
    #work out a good width for the keogram - this is a bit arbitrary but gives reasonable results
    if keo_type == "CopyPaste":
        keo_width=int(float(((end_secs-start_secs)*strip_width))/(data_spacing/2.0))
    else:
        keo_width=int(float(((end_secs-start_secs)*5))/(data_spacing/2.0))
    
    
    keo_height=int(2*max(radii)) #height (in pixels) of the keogram to be created. This is set to 2* the max Radius in the dataset. Note that this radius might relate to a smaller fov than the max fov, in which case all the images will have to be resized before being put into the keogram -too bad
    
    #work out the mean data spacing in pixels
    mean_data_spacing_pix=int((float(keo_width)/float(end_secs-start_secs))*mean_data_spacing_secs)
    
    #create new image to hold keogram
    keo_image=Image.new(mode, (keo_width, keo_height), "Black")
    keo_pix = keo_image.load() #get pixel access object for keogram image
    
    #put data into keogram
    data_points = []
    for image in data:
        data_points.append(_putData(image, keo_pix, keo_width, keo_height, strip_width, angle, keo_fov_angle, start_secs, end_secs, keo_type=keo_type))
    
    #interpolate the data
    if keo_type == "CopyPaste":
        _interpolateData(data_points, keo_image, mode, colour_table, strip_width, 1.5*mean_data_spacing_pix) #1.5 factor allows some flexibility in data spacing without interpolating across large gaps
    elif keo_type == "Average":
        _interpolateData(data_points, keo_image, mode, colour_table, 1, 1.5*(mean_data_spacing_pix+5)) #+5 is effective strip width - used in calculating the width of the keogram
    
    #create keogram object
    OCB=[]
    keo_obj = keogram(keo_image, colour_table, start_time, end_time, angle, keo_fov_angle, OCB, strip_width, None, keo_type, data_points, mean_data_spacing_pix)
        
    return keo_obj
        
###################################################################################    

def plotKeograms(keograms, columns=1, size=None, title=None):
    """
    Returns a matplotlib figure object containing plots of all the specified keograms. The keograms 
    argument should be a sequence of keogram objects. Keograms will be plotted in the order they 
    appear in the keograms list, left to right, top to bottom. By default, the keograms will be 
    plotted below each other in a single column. This behaivior can be modified using the 
    columns option. The titles of the individual keograms can be set using their title attribute.
    The title of the whole figure can be set using the title option.
    """
      
    #create a new matplotlib figure object.
    figure = matplotlib.pyplot.figure()
    
    if size != None:
        figure.set_size_inches(size[0], size[1])
    
    number_of_subplots = len(keograms)
    rows = math.ceil(float(number_of_subplots)/float(columns))
    
    #Create the title for the figure
    if title != None:
        figure.text(.5, .95, title, horizontalalignment='center') 
    
    #if there are more than one keograms to plot then extend the vertical space for each subplot
    #this is to prevent axis titles and axis labels from overlapping
    if number_of_subplots > 1:
        figure.subplotpars.hspace = 0.4
    
    subplots = []
    
    current_row = 1
    current_column = 1
    
    #create subplots for figure
    for keo in keograms:
        
        subplots.append(keo.plot(figure, number_of_subplots, current_column, current_row))
        
        #update row and column numbers - left to right, top to bottom
        if current_column < columns:
            current_column += 1
        elif current_column == columns:
            current_column = 1
            current_row += 1
    
    #add subplots to figure
    for s in subplots:
        figure.add_subplot(s)
    
    return figure  
        
###################################################################################    

def _putData(image, keo_pix, width, height, strip_width, angle, keo_fov_angle, start_secs, end_secs, keo_type="CopyPaste"):
    
    current_image=__imagePreProcess(image)
    
    #if the image has a larger field of view than the keogram, then reduce it
    if int(current_image.getInfo()['processing']['binaryMask']) > keo_fov_angle:
        current_image = current_image.binaryMask(keo_fov_angle)
        current_image = current_image.centerImage()
    
    #if the image is larger than the keogram, then we have a problem! As a temporary fix
    #we just resize the whole image
    #TODO; change this to just resize the strip taken from the image (should be much faster)
    if int(current_image.getInfo()['camera']['Radius']) > height:
        current_image = current_image.resize((height,height))
    
    #read time data from image and convert to seconds
    try:
        capture_time=datetime.datetime.strptime(current_image.getInfo()['header'] ['Creation Time'], "%d %b %Y %H:%M:%S %Z")
        capture_time_secs=calendar.timegm(capture_time.timetuple()) #convert to seconds since epoch
    except KeyError:
        raise IOError, "Cannot read creation time from image "+filename
    
    #calculate x pixel coordinate in keogram of where strip from current image should go
    strip_width_secs = (float((end_secs-start_secs))/float(width+1-strip_width)) * strip_width
    x_coordinate = int(((float(width)/float(end_secs - start_secs + strip_width_secs)) * float((capture_time_secs-start_secs))) + strip_width/2)
    #x_coordinate=int(((float(width)-strip_width)/float((end_secs-start_secs)))*float((capture_time_secs-start_secs))+strip_width/2)
    
    #get strip from image
    strip=current_image.getStrip(angle, strip_width)
    
    #if the image has a different Radius or field of view angle, or both then life is more difficult
    im_fov_angle=float(current_image.getInfo()['camera']['fov_angle'])
    im_radius=float(current_image.getInfo()['camera']['Radius'])
    mode=current_image.getMode()
    if im_fov_angle != keo_fov_angle:
       
        #change image fov by appending black pixels to it (the image fov will always be <= keo fov)
        difference=((2*im_radius)*float(float(keo_fov_angle)/float(im_fov_angle)))-(2*im_radius)
        
        if difference <=0:
            raise RuntimeError, "Strip is longer than diameter of field of view - this shouldn't be possible, check the value you have used for 'Radius'"
        
        #define black for different image modes
        if mode in ("L", "I"):
            black=0
        elif mode == "RGB":
            black =(0, 0, 0)
        else:
            raise ValueError, "Unknown image mode"
            
        for i in range(len(strip)):
            #create lists of black pixel values to prepend and append to the strip taken from the image
            prepend=[black]*int(difference/2)
            
            if difference%2 !=0: #diffence is odd
                append=[black]*(int(difference/2)+1)
            else:
                append=prepend
            
            strip[i].extend(append)
            prepend.extend(strip[i])
                
            strip[i]=prepend
        
    if len(strip[0]) != height:
        #if strip taken from image is a different size to the keogram, then resize it. This is done by creating an image of the strip and then resizing the image - a slightly odd way of doing it, but saves me having to worry about the interpolation problems
        strip_image=Image.new(mode, (len(strip), len(strip[0])))
        strip_pix=strip_image.load()
        for i in range(len(strip)):
            for j in range(len(strip[0])):
                strip_pix[i, j]=strip[i][j]
        strip_image=strip_image.resize((len(strip), height))
        strip_pix=strip_image.load()
        strip=([[]]*strip_image.size[0])
        for i in range(strip_image.size[0]):
            for j in range(height):
                strip[i].append(strip_pix[i, j])
    
    #store data in keogram
    if keo_type == "CopyPaste":
        #just copy the pixel data from the image into the keogram
        for i in range(height):
            for j in range(-strip_width/2+1, strip_width/2+1):
                try:
                    keo_pix[x_coordinate+j, i]=strip[strip_width/2+j][i]
                except Exception, ex:
                    raise ex
    elif keo_type == "Average":
        #average the strip in the x direction and copy the mean values into the keogram
        if mode != "RGB":
            for i in range(height):
                pix_sum = 0
                for j in range(strip_width):
                    pix_sum += strip[j][i]
                mean_value = int((pix_sum / float(strip_width)) + 0.5)
                keo_pix[x_coordinate, i] = mean_value
        else:
            for i in range(height):
                pix_sum = [0, 0, 0]
                for j in range(strip_width):
                    pix_sum[0] += strip[j][i][0] #Red value
                    pix_sum[1] += strip[j][i][1] #green value
                    pix_sum[2] += strip[j][i][2] #blue value
                    
                mean_value = (int((pix_sum[0] / float(strip_width)) + 0.5), int((pix_sum[1] / float(strip_width)) + 0.5), int((pix_sum[2] / float(strip_width)) + 0.5))
                keo_pix[x_coordinate, i] = mean_value
    else:
        raise ValueError, "Unknown keogram type. Expecting \"CopyPaste\" or \"Average\", got "+type

    #return the x-coordinate of where we just put the data
    return x_coordinate
        
###################################################################################
        
def _interpolateData(data_list, image, mode, colour_table, strip_width, max_gap):
    """
    Interpolates between the strips in the keogram image. Large gaps (probably due to missing data) are not
    interpolated across and will be left as black strips in the final keogram.
    """
    #ensure there are no duplicate entries in the data_list
    data_list=list(set(data_list))

    #if there is only one data_list entry then return (no interpolation possible)
    if data_list==None or len(data_list) <= 1:
        return
    
    #sort data list into numerical order
    data_list.sort()
    
    #load pixels
    keo_pix=image.load()
        
    #fill in rest of keogram using linear interpolation
    for i in range(len(data_list)-1):
        start_pix=int(data_list[i]+int(strip_width/2))
        end_pix=int(data_list[i+1]-int(strip_width/2))
        
        #check that any interpolation is actually needed
        if start_pix == end_pix:
            continue
        
        #check for missing data entries
        if end_pix-start_pix > max_gap:
            continue #don't interpolate over large gaps in the data.
        
        #For "L" and "I" mode images - simple linear interpolation between values
        if mode == "L" or mode == "I":
            for y in range(image.size[1]):
                gradient=(keo_pix[end_pix, y]-keo_pix[start_pix, y])/(end_pix-start_pix)
                
                for x in range(start_pix+1, data_list[i+1]-int(strip_width/2)):
                
                    keo_pix[x, y]=keo_pix[start_pix, y] + (x-start_pix)*gradient
                           
        # For RGB images with no colour table - simple linear interpolation between values of R,G and B            
        elif mode == "RGB" and colour_table==None:
            for y in range(image.size[1]):
                R_gradient=(keo_pix[end_pix, y][0]-keo_pix[start_pix, y][0])/(end_pix-start_pix)
                G_gradient=(keo_pix[end_pix, y][1]-keo_pix[start_pix, y][1])/(end_pix-start_pix)
                B_gradient=(keo_pix[end_pix, y][2]-keo_pix[start_pix, y][2])/(end_pix-start_pix)
                    
                for x in range(start_pix+1, data_list[i+1]-int(strip_width/2)):
                
                    keo_pix[x, y]=(keo_pix[start_pix, y][0] + (x-start_pix)*R_gradient, keo_pix[start_pix, y][1] + (x-start_pix)*G_gradient, keo_pix[start_pix, y][2] + (x-start_pix)*B_gradient)
                    if keo_pix[x, y][0] > 255 or keo_pix[x, y][1] > 255 or keo_pix[x, y][2] > 255:
                        raise ValueError, "Pixel value out of range."
                        
        # For RGB images with a colour table - linear interpolation along the colour table. Final keogram will only have colours in it that appear in the colour table. This allows the colour table to be undone, returning the image to greyscale.        
        elif mode == "RGB" and colour_table != None:

            for y in range(image.size[1]):
                gradient=(colour_table.index(keo_pix[end_pix, y])-colour_table.index(keo_pix[start_pix, y]))/(end_pix-start_pix)
                for x in range(start_pix+1, data_list[i+1]-int(strip_width/2)):
                    index_in_colour_table=int(colour_table.index(keo_pix[start_pix, y]) + ((x-start_pix)*gradient)+0.5)
                    keo_pix[x, y]=colour_table[index_in_colour_table]
                    
        else:
            raise ValueError, "Unknown image mode"
            
###################################################################################    


#class definition

###################################################################################    

class keogram:
    """
    Class to hold keogram data. Unless otherwise stated, all methods return a new keogram object.
    """    
    def __init__(self, image, colour_table, start_time, end_time, angle, fov_angle, OCB, strip_width, intensities, keo_type, data_points, data_spacing):
        
        #set class attributes
        self.__image=image.copy()
        self.__mode=image.mode
        self.__keo_type = keo_type
        self.__data_points = data_points #pixel coordinates of where the image slices have been placed
        self.__data_spacing = data_spacing #median distance (in pixels) between data entries in keogram
        
        if colour_table != None:
            self.__colour_table=range(len(colour_table))
            for i in range(len(colour_table)):
                self.__colour_table[i]=colour_table[i]
        else:
            self.__colour_table=None
        
        if OCB !=[]:
            self.__OCB=range(len(OCB))
            for i in range(len(OCB)):
                self.__OCB[i]=OCB[i]
        else:
            self.__OCB=[]    
            
        self.__width, self.__height = image.size
        self.__start_time=start_time
        self.__end_time=end_time
        self.__angle=angle
        self.__fov_angle=fov_angle
        self.__strip_width = strip_width
        self.__intensities = intensities
        
        #set attributes which control plotting
        self.title = "DEFAULT"
        self.x_label = "Time (UT)"
        self.y_label = "Scan Angle (degrees)"
        
    ###################################################################################                            
    #define getters
    
    def getImage(self):
        """
        Returns a PIL image object containing a copy of the keogram image data
        """
        return self.__image.copy()
    
    def getMode(self):
        """
        Returns a string containing the mode of the keogram image, e.g. "RGB". See the PIL handbook for details of image modes.
        """
        return self.__mode
    
    def getColour_table(self):
        """
        Returns a list of RGB tuples containing the colour table which has been applied to the keogram. The keogram will inherit its
        colour table from its source images (or a colour table can be applied using the applyColourTable() method). If the keogram has
        no colour table then None is returned.
        """
        if self.__colour_table != None:
            copy = []
            for element in self.__colour_table:
                copy.append(element)
            return copy
            
        else:
            return None
    def getDataPoints(self):
        """
        Returns a list of x-coordinates of the centers of the images slices in the keogram
        image.
        """
        return self.__data_points
    
    def getWidth(self):
        """
        Returns an integer containing the width of the keogram image in pixels.
        """
        return self.__width
        
    def getHeight(self):
        """
        Returns an integer containing the height of the keogram image in pixels.        
        """
        return self.__height
    
    def getStart_time(self):
        """
        Returns a datetime object containing the earliest time shown in the keogram.
        """
        return self.__start_time
        
    def getEnd_time(self):
        """
        Returns a datetime object containing the latest time shown in the keogram.
        """
        return self.__end_time
        
    def getAngle(self):
        """
        Returns the angle from geographic North at which the keogram was made. This is the angle from geographic North that the strips
        were taken out of the images.
        """
        return self.__angle
    
    def getFov_angle(self):
        """
        Returns the field of view angle of the keogram. This is inherited from the source images.
        """
        return self.__fov_angle
    
    def getStrip_width(self):
        """
        Returns the width of the strips (in pixels) that were taken from the source images to create the keogram.
        """
        return self.__strip_width
    
    def getType(self):
        """
        Returns a string describing the type of the keogram. Either "CopyPaste" or "Average"
        """
        return self.__keo_type
    
    ###################################################################################                                
        
    def angle2pix(self, angle):
        """
        Converts an angle in degrees in the range (90-fov_angle)-(90+fov_angle) to a vertical pixel coordinate in the keogram. 
        Note that the angle IS NOT the angle from North unless the keogram has been created to run in the north-south direction. 
        If the angle is outside of the range of the keogram None is returned. This is the inverse operation of pix2angle()
        """
        if angle < (90-self.__fov_angle) or angle >= (90+self.__fov_angle):
            return None
        
        return int((angle-(90-self.__fov_angle))*float(self.__image.size[1]/float(2*self.__fov_angle))+0.5)    
        
    ###################################################################################                                
    
    def applyColourTable(self, colour_table):
        """
        Returns a new keogram object with a colour table applied. The new keogram image will be "RGB". The colour table argument 
        should be a colourTable object as defined in allskyColour.
        """
        #can't apply a colour table to an RGB image
        if self.getMode() == 'RGB':
            raise ValueError, "Cannot apply a colour table to an RGB keogram"
        
        #copy the "L" image into the intensities attribute
        new_intensities=self.getImage()
        
        #apply the colour table
        if self.getMode() != "I": #PIL doesn't support 16bit images, so need to use own routine if "I" mode image
            new_image=self.getImage()
            new_image.putpalette(colour_table.getColourTable())
        else:
            new_image=Image.new("RGB", new_intensities.size, "Black")
            new_image_pix=new_image.load()
            intensity_pix=new_intensities.load()
            
            for x in range(new_image.size[0]):
                for y in range(new_image.size[1]):
                    new_image_pix[x, y]=colour_table.colour_table[intensity_pix[x, y]]
        
        new_colour_table=colour_table.colour_table
        new_image=new_image.convert("RGB")
        new_mode="RGB"
        
        #create new keogram object
        new_keogram=keogram(new_image, new_colour_table, self.__start_time, self.__end_time, self.__angle, self.__fov_angle, self.__OCB, self.__strip_width, new_intensities, self.__keo_type, self.__data_points, self.__data_spacing)

        return new_keogram
        
    ###################################################################################    
    
    def calculateOCB(self):
        """
        Returns a list of length len(width) containing the vertical position (in pixels) of the Open Closed Boundary for the 
        corresponding horizontal pixel coordinate. It also saves this data in the OCB attribute, so further calls to calculateOCB(),
        findOCB() and plotOCB() will not require the OCB to be located again. The OCB is calculated at a resolution equal to the 
        strip width used to create the keogram.
        """
        #if the OCB has already been calculated, then return the already calculated results
        if len(self.__OCB) == self.__width:
            return self.__OCB    
            
        #otherwise calculate the OCB
        OCB=[]
        for i in range(self.__strip_width):
            OCB.append(None)
        for pixel in range(self.__strip_width/2, self.__width-self.__strip_width/2, self.__strip_width):
            time = self.pix2time(pixel)
            step_function=self.findOCB(time, OCB[pixel])
        
            if step_function !=None:
                for i in range(self.__strip_width):
                    OCB.append(step_function.index(max(step_function)))
            else:
                for i in range(self.__strip_width):
                    OCB.append(self.__height-1)
                    
        for i in range(self.__strip_width):            
            OCB.remove(None)
        
        #median filter OCB values
        OCB_copy=[]
        for i in range(len(OCB)):
            OCB_copy.append(OCB[i])    
            
        for i in range(self.__strip_width, len(OCB)-self.__strip_width, 2*self.__strip_width):
            values=[]
            for j in range(-self.__strip_width, self.__strip_width+1):
                values.append(OCB_copy[i+j])
            OCB[i]=stats.median(values)
        
        for i in range(len(OCB)):
            self.__OCB.append(OCB[i])    
        return OCB    
        
    ###################################################################################                            
    
    def findOCB(self, time, previous_position):
        """
        Returns the vertical position (in pixels) of the Open Closed Boundary at the specified time. If the time is outside the 
        range of the keogram then ValueError will be raised.
        """
        #function returns latitude of OCB. 
        #check that specified time is within range of keogram
        if time > self.__end_time or time < self.__start_time:
            raise ValueError, "Time is outside of range of keogram."
        
        #if the OCB has already been calculated then take it's value from the OCB list.
        if len(self.__OCB) == self.__width:
            return self.__OCB[self.time2pix(time)]
        
        auroral_intensity = 200 #min value counted as being "auroral"
        
        #read intensity values from array of keogram pixel values
        angles, intensities=self.getIntensities(time, self.__strip_width)
        
        #return None if there is no data for this time
        if intensities.count(0)==self.__height:
            return None
        
        #if there are no high intensities in the strip, return
        if max(intensities) < auroral_intensity:
            median_intensity=stats.median(intensities) #median intensity before step
            return misc.stepFunction(median_intensity, auroral_intensity, self.__height-1, self.__height)
        
        #set lower limit for search for step_position.
        #This is done for efficiency, there is no need to look at all angles each time
        if previous_position == None:
            lower_limit = 1
        else:
            lower_limit = previous_position - self.__height/2
            if lower_limit < 1:
                lower_limit=1
        
        #create empty array for storing fit values
        fit = []
        
        #for each possible position of the step (lower_limit-height), calculate median intensity before step, and create a step function ranging from his value to 255.                
        for step_position in range(lower_limit, self.__height):
            median_intensity=stats.median(intensities[0:step_position]) #median intensity before step
        
            #create step function
            step_function = misc.stepFunction(median_intensity, auroral_intensity, step_position, self.__height)
        
            #calculate fit to data
            fit.append(0.0)
            for j in range(self.__height):
                fit[step_position-lower_limit] = fit[step_position-lower_limit] + (step_function[j]-intensities[j])*(step_function[j]-intensities[j])
    
        #find optimum step function (one with minimum fit)
        step_position=lower_limit+fit.index(min(fit)) #pixel position of step with lowest fit
                #create optimum step function
        median_intensity=stats.median(intensities[0:step_position])
        step_function = misc.stepFunction(median_intensity, auroral_intensity, step_position, self.__height)
                #if the OCB was not located, return 
        if step_position==self.__height-1:
            return step_function
            
        return step_function    
        #Apply Blanchard et al criteria to check if we have really found the OCB

        #check if polar cap intensity < auroral intensity
        mean_polar_cap_intensity=stats.mean(intensities[0:step_position])
        mean_auroral_intensity=stats.mean(intensities[step_position:])
        
        if mean_polar_cap_intensity > mean_auroral_intensity:
            #print self.time2pix(time),": mean_polar_cap_intensity > mean_auroral_intensity",mean_polar_cap_intensity,mean_auroral_intensity
            return None #Cannot find OCB for this time
    

        #check if step increase is more than 65% of polar cap intensity (should be 75% according to Blanchard, but the patches increase the polar cap intensity)
        step_increase=255-mean_polar_cap_intensity
        if step_increase<=(0.65*mean_polar_cap_intensity):
            #print self.time2pix(time),": step_increase<=(0.65*mean_polar_cap_intensity)",step_increase,mean_polar_cap_intensity
            return None #Cannot find OCB for this time
            
        #check if correlation is >80%

        #multiply intensities by step function
        step_times_data=[]
        for i in range(self.__height):
            step_times_data.append(step_function[i]*intensities[i])

        correlation= (stats.mean(step_times_data)-(stats.mean(step_function)*stats.mean(intensities)))/(math.sqrt(stats.variance(step_function))*math.sqrt(stats.variance(intensities)))
    
        if correlation < 0.7:
            #print self.time2pix(time),": correlation < 0.8 = ",correlation
            return None
        return step_function
        
    ###################################################################################                            
    
    def getIntensities(self, time, strip_width):
        """
        Returns a tuple of lists (angles, intensities) which correspond to a vertical slice through the keogram at the specified 
        time. The strip width argument controls the width in pixels of the strip that the intensities are averaged over. For example
        a strip width of 3 will mean that each intensity returned is the mean of the pixel intensity at time=time, and the 
        neighbouring pixels on each side. Intensities of zero are excluded from the mean calculation (since they correspond to times
        with no available data). For times within regions of missing data, getIntensities will return 0.
        """
        #check that specified time is within range of keogram
        if time > self.__end_time or time < self.__start_time:
            raise ValueError, "Time is outside of range of keogram."
            
        angles = [] #list to hold angle values
        intensities = [] #list to hold intensity values
        
        if self.__intensities==None:
            keo_pix=self.__image.load()
        else:
            keo_pix=self.__intensities.load()
        
        #calculate pixel position of time
        x_position=self.time2pix(time)
        
        #calculate list of angles (corresponding to pixels in vertical strip of keogram)
        angle_conversion_factor = float(2.0*self.__fov_angle)/float(self.__height)
        
        for i in range(self.__height):
            angles.append((90.0+self.__fov_angle)-float(i)*angle_conversion_factor)
            
            #calculate list of mean intensities (of a strip of width strip_width)
            sum_intensities=[]
            
            #work out max range for strip size (cannot exceed dimensions of keogram)
            if x_position + int(-strip_width/2)+1 < 0: 
                min_pix = -x_position
            else:
                min_pix=int(-strip_width/2)+1
            if x_position + int(strip_width/2)+1 > self.__width-1: 
                max_pix = self.__width-1-x_position
            else:
                max_pix=int(strip_width/2)+1    
                
                
            for j in range(min_pix, max_pix):
                #if there is intensity data for the keogram
                if self.__mode=="L" or self.__intensities != None:
                    sum_intensities.append(keo_pix[x_position+j, i])
                
                #if there is no intensity data but there is a colour table    
                elif self.__mode == "RGB" and self.__colour_table != None:
                    if self.__colour_table.count(keo_pix[x_position+j, i]) > 1:
                        raise ValueError, "No unique intensity for RGB tuple"
                        
                    pix_intensity= self.__colour_table.index(keo_pix[x_position+j, i]) #for an RGB image, need to reverse the colour_table to get back to the original intensity
                    sum_intensities.append(pix_intensity)
                    
                #no hope of finding intensities
                else:
                    raise RuntimeError, "There is no intensity data for this keogram."

            #remove zeros from intensities list
            while sum_intensities.count(0) != 0:
                sum_intensities.remove(0)
            
            #calculate mean
            if sum_intensities.count(0) >= int(len(sum_intensities)/2):
                mean_intensity=0 #pixel is inside a region of no data
            else:    
                #remove zeros from intensities list
                while sum_intensities.count(0) != 0:
                    sum_intensities.remove(0)
                
                mean_intensity=float(sum(sum_intensities))/float(len(sum_intensities))
            
    
            #store mean intensities in a list
            intensities.append(mean_intensity)
            
        return (angles, intensities)
        
    ###################################################################################                    
    
    def medianFilter(self, n):
        """
        This is a thin wrapper function for the median filter provided by PIL. It replaces each 
        pixel in the keogram image by the median value of the pixels in an nxn square around it 
        (where n is an integer).
        """
        image = self.__image.filter(ImageFilter.MedianFilter(n))
        
        if self.__intensities != None:
            intensities = self.__intensities.filter(ImageFilter.MedianFilter(n))
        else:
            intensities=None
            
        #create new keogram object
        new_keogram=keogram(image, self.__colour_table, self.__start_time, self.__end_time, self.__angle, self.__fov_angle, self.__OCB, self.__strip_width, intensities, self.__keo_type, self.__data_points, self.__data_spacing)
        
        return new_keogram    
            
    ###################################################################################                
    
    def pix2angle(self, pixel):
        """
        Converts a vertical pixel coordinate into an angle in degrees. If the pixel coordinate is outside of the range of the 
        keogram None is returned. This is the inverse operation of angle2pix().
        """
        if pixel < 0 or pixel >= self.__height:
            return None
        return float((90-self.__fov_angle)+((2*self.__fov_angle)/self.__height)*pixel)
    
    ###################################################################################                        
        
    def pix2time(self, pixel):
        """
        Converts a horizontal pixel coordinate into a datetime object. If the pixel coordinate is outside of the range of the keogram
        None is returned. This is the inverse operation of time2pix().
        """
        if pixel <0 or pixel>=self.__width:
            return None
        time = num2date(date2num(self.__start_time)+(((date2num(self.__end_time)-date2num(self.__start_time))/self.__width)*pixel))
        time=time.replace(tzinfo=None)
        return time
        
    ###################################################################################                            
    
    def plot(self, figure, num, col, row):
        """
        Returns a matplotlib figure object containing a plot of the keogram. The keo_title option should be a string that you want to
        appear as the title for the plot. The default is the time range of the keogram. Setting keo_title to None will result in no title
        on the plot. The x_label and y_label options should be strings that you want to appear as axis titles on the plot. The defaults are
        "Time (UT)" and "Scan angle (degrees)" respectively. Setting them to None will result in no axis titles. The size option should be
        a tuple (width,height) in inches. The default value is None. In this case the size for the plot is determined automatically based on
        the size of the keogram image. 
        
        Use show() to view the plot in an interactive viewing window. E.g.:
            from pylab import show
            plot=keo.plot()
            plot
            show()
        """
        
        #calculate number of minutes between tick marks
        time_range_days=date2num(self.__end_time)-date2num(self.__start_time)
        time_range_mins=time_range_days*24.0*60.0
        if int(time_range_mins/10) == 0:
            minutes=[]
        elif int(time_range_mins/60) <= 1:#if the time range is less than 1 hour
            minutes=range(0, 60, int(time_range_mins/10)) #list containing the number of minutes at which we want tick marks
        
        elif int(time_range_mins/60) >= 7: #if time range is greater than 7 hours just have hour marks
            minutes=[0]
        else:
            minutes=[0, 30] #else have hour and half hour marks
        
        
        if self.title == "DEFAULT":    
        #create title string for keogram
            start_time_string= self.__start_time.ctime()
            end_time_string=self.__end_time.ctime()
            keo_title=start_time_string+" - "+end_time_string
        else:
            keo_title = self.title
        
        #create a new subplot object to hold this keogram
        subplot = matplotlib.axes.Subplot(figure, num, col, row)
        
        #add title
        if keo_title != None:
            subplot.set_title(keo_title)
    
        
        #plot keogram image in figure,matplotlib doesn't support 16bit images, so if the image is not RGB, then need to check that it is 8bit
        if self.__image.mode == 'RGB' or self.__image.mode == 'L':
            image=subplot.imshow(self.__image, origin="top", aspect="auto")
        else:
            image=subplot.imshow(self.__image.convert('L'), origin="top", aspect="auto", cmap=matplotlib.cm.gray)
            
        #define formatting for axes
        x_tick_positions=MinuteLocator(minutes) #find the positions of the x tick marks
        time_format= DateFormatter("%H:%M") #define the format of the times displayed on the x_axis
        
        #y axis
        subplot.yaxis=subplot.axes.twinx() #create another set of axes (which will become the y axis)
        subplot.yaxis.set_xbound(0, self.__width)
        subplot.yaxis.set_ybound(90+self.__fov_angle, 90-self.__fov_angle)
        subplot.yaxis.yaxis.tick_left() #set the position of the tick marks for the y axis of the new set
        #set axis titles
        if self.y_label != None:
            subplot.yaxis.set_ylabel(self.y_label)
            subplot.yaxis.yaxis.set_label_position("left")
        
        
        subplot.yaxis.xaxis.set_major_locator(NullLocator()) #turn off the x axis of the new set
      
        subplot.yaxis = subplot.yaxis.yaxis
        
        
        #x axis
        subplot.xaxis=subplot.axes.twiny() #create another set of axes (which will become the x axis)
        subplot.xaxis.set_xbound(date2num(self.__start_time), date2num(self.__end_time))
        subplot.xaxis.set_ybound(0, self.__height)
        subplot.xaxis.xaxis.tick_bottom() #set the position of the tick marks for the x axis of the new set
        if self.x_label != None:
            subplot.xaxis.set_xlabel(self.x_label)
            subplot.xaxis.xaxis.set_label_position("bottom")
        subplot.xaxis.yaxis.tick_right()
        subplot.xaxis.yaxis.set_visible(False)
        subplot.xaxis.xaxis.set_major_locator(x_tick_positions) #set the tick mark positions for the x axis of the new set
        subplot.xaxis.xaxis.set_major_formatter(time_format) #set the tick mark format for the x axis of the new set
       

        subplot.set_ybound(90+self.__fov_angle, 90-self.__fov_angle)

        subplot.yaxis.set_major_formatter(FuncFormatter(rev))
        subplot.xaxis = subplot.xaxis.xaxis
       
        image.axes.axis('off') #remove pixel count axes from plotted image
            
#        #set axis titles
#        if self.y_label != None:
#            subplot.yaxis.set_label(self.y_label)
#            subplot.yaxis.set_label_position("left")
#            
#        if self.x_label != None:
#            subplot.xaxis.set_label(self.x_label)
#            subplot.xaxis.set_label_position("bottom")
        
        #return a subplot object
        return subplot
    
    ###################################################################################
    
    def plotOCB(self):
        """
        Returns a new keogram object with the position of the OCB drawn onto the keogram image. If the OCB has not been calculated 
        already, then it will be calculated first and stored in both the original keogram object and the new one.
        """
        #check that the OCB has been calculated
        if len(self.__OCB) != self.__width:
            self.calculateOCB() #if it hasn't, then calculate it
        
        
        image=self.getImage()
        
        #load the pixel values
        keo_pix = image.load()
        
        #check that keogram image is compatible with OCB array
        if self.__width != len(self.__OCB):
            raise ValueError, "Size mismatch between keogram and OCB data"
    
        #set the colour of the OCB line depending on the image mode of the keogram
        if self.__mode == "RGB":
            black = (0, 0, 0)
        elif self.__mode == "L":
            black = 0
        else:
            raise TypeError, "Unsupported image mode for keogram: "+str(self.__mode)
    
        #plot the OCB data 
        for pixel in range(len(self.__OCB)):
            
            #make each point 5 pixels high (if possible)
            top=-self.__OCB[pixel]
            bottom = self.__height - self.__OCB[pixel]
            
            if top < -2:
                top = -2
            if bottom > 3:
                bottom = 3
            
            #plot a 5 pixel high line for each OCB boundary position
            for i in range(top, bottom):
                keo_pix[pixel, self.__OCB[pixel]+i]=black
        
        #create new keogram object
        new_keogram=keogram(image, self.__colour_table, self.__start_time, self.__end_time, self.__angle, self.__fov_angle, self.__OCB, self.__strip_width, self.__intensities, self.__keo_type, self.__data_points, self.__data_spacing)
        
                
        return new_keogram
        
    ###################################################################################            
    
    def roll(self, file_list):
        """
        This method is designed to be used for producing real-time keograms. The file_list argument should be either a list of tuples 
        (filename,site_info_file) of images and their corresponding site_info_files, or a list of allskyImage objects, which you want to be included in the 
        current keogram. The total time span of the keogram will remain unchanged, but the keogram will be shifted to include the 
        new images. For example, if you have created a keogram which spans from 11:00 to 12:00 and you then use roll() with the 
        filename of an image that was captured at 12:01, then the keogram that is returned will span from 11:01 to 12:01 and will 
        include the data from the new image.
        """
        
        #if file_list is empty or is none then return
        if file_list==None or len(file_list) == 0 :
            return self
        
        latest_time = datetime.datetime.fromordinal(1)
        earliest_time = datetime.datetime.utcnow()
        
        capture_times = []
        
        #if the list is of file names then load the allskyImages
        images = []
        for item in file_list:
            if isinstance(item, allskyImage.allskyImage):
                images.append(item)
            else:
                images.append(allskyImage.new(item[0], item[1]))
               
        #find latest and earliest creation times in file list
        for im in images:
            
            #read time data from image
            try:
                capture_time=datetime.datetime.strptime(im.getInfo()['header'] ['Creation Time'], "%d %b %Y %H:%M:%S %Z")
            except KeyError:
                raise IOError, "Cannot read creation time from image "+im.getFilename()
            
            #if it is later than the latest time then update latest time
            if capture_time > latest_time:
                latest_time=capture_time
                
            #if it is earlier than the earliest time then update earliest time
            if capture_time < earliest_time:
                earliest_time=capture_time
            
        #if earliest_time<start_time and latest_time>end_time then give up, which direction should the keogram be moved in?
        if latest_time > self.__end_time and earliest_time < self.__start_time:
            raise ValueError, "File list time range exceeds keogram time range, which way should the keogram be rolled?"
        
        #if all the capture times are within the existing range of the keogram, then no roll is needed
        if latest_time <= self.__end_time and earliest_time >= self.__start_time:
            time_roll = datetime.timedelta(seconds=0)
            pix_roll = 0
        
        if latest_time > self.__end_time: #keogram needs to be rolled forwards in time            
            #work out time roll
            time_roll=latest_time-self.__end_time
            
            #find out how many pixels to roll keogram by
            time_part = self.time2pix(self.__start_time + time_roll)
            
            if time_part == None:
                #if pix_roll is bigger than the keogram itself, then just blank the whole keogram
                pix_roll = self.getWidth()
            else:  
                pix_roll = time_part 
        
        if earliest_time < self.__start_time: #keogram needs to be rolled backwards in time    
        
            #work out time roll
            time_roll=self.__start_time-earliest_time

            #find out how many pixels to roll keogram by
            time_part = self.time2pix(self.__start_time + time_roll)
            if time_part == None:
                #if pix_roll is bigger than the keogram itself, then just blank the whole keogram
                pix_roll = self.getWidth()
            else:  
                pix_roll = -time_part 
        
        #modify start and end times
        end_time=time_roll+self.__end_time
        start_time=time_roll+self.__start_time
        
        #update entries in data_points. Remove any points which are no longer in the keogram
        new_data_points = []
        for point in self.__data_points:
            if ((point - pix_roll < 0) or (point - pix_roll > self.getWidth())):
                continue
            else:
                new_data_points.append(point - pix_roll)           
            
        #if the keogram has a colour table applied then use the intensity data, otherwise use the image
        if self.__intensities == None:
            image=self.__image
        else:
            image=self.__intensities
        
        #move keogram image across
        image=ImageChops.offset(image, -pix_roll, 0)
        
        
        #blank end section of keogram. The offset function wraps the image, so we need to blank the end section to prevent data from the start of the keogram ending up at the end of it.
        
        #define black for RGB and L images
        if self.__mode=="RGB":
            black=(0, 0, 0)
        elif self.__mode=="L":
            black=0
        else:
            raise TypeError, "Unsupported keogram mode."
        
        #load pixel access object
        keo_pix=image.load()
        
        #apply black values to keogram
        for y in range(self.__height):
            for i in range(pix_roll):
                keo_pix[self.__width-1-i, y]=black
        
        #convert start and end times into seconds
        start_secs=calendar.timegm(start_time.timetuple())
        end_secs=calendar.timegm(end_time.timetuple())
        
        #put data into keogram
        for im in images:
            new_data_points.append(_putData(im, keo_pix, self.getWidth(), self.getHeight(), self.__strip_width, self.__angle, self.__fov_angle, start_secs, end_secs, keo_type=self.__keo_type))
        
        #update the data_points attribute
        self.__data_points = new_data_points
               
        #interpolate the data
        if self.__keo_type == "CopyPaste":
            _interpolateData(new_data_points, image, self.__mode, self.__colour_table, self.__strip_width, 1.5*(self.__data_spacing))
        elif self.__keo_type == "Average":
            _interpolateData(new_data_points, image, self.__mode, self.__colour_table, 1, 1.5*(self.__data_spacing+5)) #+5 is effective strip width used when calculating keogram width
        
        #create new keogram object
        new_keogram=keogram(image, None, start_time, end_time, self.__angle, self.__fov_angle, [], self.__strip_width, self.__intensities, self.__keo_type, self.__data_points, self.__data_spacing)
        
        #if the original keogram had a colour table applied, then re-apply it now
        if self.__colour_table != None:
            ct=allskyColour.basicColourTable(self.getColour_table())
            new_keogram=new_keogram.applyColourTable(ct)
        
        return new_keogram
            
    ###################################################################################    
    
    def save(self, filename):
        """
        Saves keogram object in specified file. It can be retrieved later using the load() function.
        """
        #create dictionary to store keogram attributes
        header={}
        
        #populate dictionary
        header['angle']=str(self.__angle)
        header['start_time']=str(self.__start_time.strftime("%d %b %Y %H:%M:%S"))
        header['end_time']=str(self.__end_time.strftime("%d %b %Y %H:%M:%S"))
        header['OCB']=str(self.__OCB)
        header['strip_width']=str(self.__strip_width)
        header['colour_table']=str(self.__colour_table)
        header['fov_angle']=str(self.__fov_angle)
        header['keo_type'] = self.__keo_type
        header['data_points'] = str(self.__data_points)
        header['data_spacing'] = str(self.__data_spacing)
        
        #if no colour table has been applied then save the image, otherwise save the intensities
        if self.__colour_table==None:
        
            #save header data in image header
            self.__image.info=header
            
            #save image as png file
            misc.pngsave(self.__image, filename)
            
        else:
            #save header data in image header
            self.__intensities.info=header
            
            #save image as png file
            misc.pngsave(self.__intensities, filename)
    
    ###################################################################################                        
    
    def savePlot(self, filename, remove_space=True, keo_title="DEFAULT", x_label="Time (UT)", y_label="Scan angle (degrees)", size=None):
        """
        Saves a plot of the keogram data as a png file specified by the filename argument. This is a convenience 
        function which essentially does keo.plot() and then pylab.savefig(). However, it also removes the white 
        borders in the matplotlib plots (this can be disabled by setting remove_space to False). The other 
        arguments are the same as for plot().
        """    
        #ensure the current figure is clear
        clf()
        
        #plot the keogram
        plot=self.plot(keo_title=keo_title, x_label=x_label, y_label=y_label, size=size)
        
        #save the figure as a png
        savefig(filename)
        
        if remove_space:
            #reopen the image as a PIL image
            im=Image.open(filename)
            
            #remove the white space from the image
            im2=im.crop(ImageOps.invert(im.copy().convert('L')).getbbox())
        
            if not filename.endswith((".png", ".PNG")):
                filename=filename+".png"
        
            im2.save(filename)
        
    ###################################################################################                    
            
    def time2pix(self, time):
        """
        Converts a datetime object into a horizontal pixel coordinate. If the time is outside of the range of the keogram None is 
        returned. This is the inverse operation of pix2time().
        """
        pixel= int((float(self.__width-(self.__strip_width/2))/float((date2num(self.__end_time)-date2num(self.__start_time))))*float((date2num(time)-date2num(self.__start_time)))+(self.__strip_width/2))
    
        if pixel>self.__width or pixel < 0:
            return None
        return pixel
        
    ###################################################################################
    
    def zoom(self, start_time, end_time):
        """
        Returns a keogram object spanning the time between start_time and end_time. Both arguments should be datetime objects. If both
        start_time and end_time are outside the range of the current keogram then ValueError is raised. If just one is outside of the
        time range then this part of the new keogram will be blank.
        """
        #check that zoom range includes some of the keogram
        if start_time > self.__end_time or end_time < self.__start_time:
            raise ValueError, "Zoom range is outside of keogram range."
        
        #convert times to pixel coordinates
        start_pix = self.time2pix(start_time)
        end_pix = self.time2pix(end_time)
        
        #if part of the zoom range is outside of the current keogram, then change the zoom range to fit
        if end_pix== None:
            end_pix=self.__width
            end_time=self.__end_time
        if start_pix==None:
            start_pix=0
            start_time=self.__start_time
        
        #update entries in data_points. Remove any points which are no longer in the keogram
        new_data_points = []
        for point in self.__data_points:
            if ((point < start_pix) or (point > end_pix)):
                continue
            else:
                new_data_points.append(point)
             
        #get section of keogram image
        image_sec=self.__image.crop((start_pix, 0, end_pix, self.__height))
        
        #get section of keogram intensities
        if self.__intensities ==None:
            intensities_sec=None
        else:
            intensities_sec=self.__intensities.crop((start_pix, 0, end_pix, self.__height))
        
        #get section of OCB data
        OCB_sec=self.__OCB[start_pix:end_pix]
        
        #return zoomed in keogram
        return keogram(image_sec, self.__colour_table, start_time, end_time, self.__angle, self.__fov_angle, OCB_sec, self.__strip_width, intensities_sec, self.__keo_type, new_data_points, self.__data_spacing)
                        
###################################################################################                                
                                
