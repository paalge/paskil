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


Example:

    The following example creates a keogram of the 630nm wavelength between 18:30 and 19:30 on the 4/2/2003
    using the allsky images of type "png" stored in the directory "Allsky Images". The recursive option is 
    used to traverse the entire directory structure contained within "Allsky Images" looking for images. 
    The keogram is then plotted and viewed in an interactive plotting window.


        from PASKIL import allskyKeo, allskyData, allskyPlot
        import datetime
        from pylab import *
        
        #create datetime object defining start time for keogram
        start_time = datetime.datetime.strptime("04 Feb 2003 18:30:00 GMT","%d %b %Y %H:%M:%S %Z")
        
        #create datetime object defining end time for keogram 
        end_time = datetime.datetime.strptime("04 Feb 2003 19:30:00 GMT","%d %b %Y %H:%M:%S %Z") 
        
        #create a new dataset object
        dataset = allskyData.new("Allsky Images","630","png",site_info_file="site_info.txt",recursive=True) 
        
        #create a new keogram with a sweep angle of 33 degrees and using a strip width of 3 pixels and a data spacing of 60 seconds
        keo = allskyKeo.new(dataset,start_time,end_time,33,3,60) 
    
        plot = allskyPlot.plot([keo]) #plot the keogram

        show() #open the figure in an interactive plotting window       
""" 

################################################################################################################################################################

import datetime
import calendar
import math
import numpy
import matplotlib
import warnings
import Image
import ImageChops
import ImageFilter

from pylab import MinuteLocator, DateFormatter, date2num, num2date, FixedLocator, FixedFormatter

from PASKIL import allskyImage, allskyColour, allskyPlot, misc, stats

#Functions

###################################################################################    

def __imagePreProcess(image):
    """
    Checks that the image has had all the requisit preprocessing needed before it is put into a keogram. 
    Returns an allskyImage object which has been processed, if no processing was required then it returns 
    the original object.
    """   
        
    if not image.getInfo()['processing'].has_key('binaryMask'):
        image = image.binaryMask(float(image.getInfo()['camera']['fov_angle']))
        
    if not image.getInfo()['processing'].has_key('centerImage'):
        image = image.centerImage()
        
    if not image.getInfo()['processing'].has_key('alignNorth'):
        image = image.alignNorth()
    
    return image
        
###################################################################################            

def __checkImages(images, mode=None, wavelength=None, colour_table=None, calib_factor=None):
    """
    Checks that all allskyImages in the images list have the same mode, wavelength, absolute 
    calibration factor and colour table either as each other or as those specified by the 
    optional arguments. These are essentially the same checks that are done when a dataset is 
    created.
    """
    if len(images) == 0:
        raise ValueError, "Cannot perform checks on an empty list!"
    
    #if no optional arguments are specified, then take the values from the first image in the list
    if mode is None:
        mode = images[0].getMode()
    
    if wavelength is None:
        wavelength = images[0].getInfo()['header']['Wavelength']
    
    if colour_table is None:
        try:
            colour_table = images[0].getInfo()['processing']['applyColourTable']
        except KeyError:
            colour_table = None
    
    if calib_factor is None:
        try:
            calib_factor = images[0].getInfo()['processing']['absoluteCalibration']
        except KeyError:
            calib_factor = None
    
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
            if colour_table is None:
                pass
            else:
                raise ValueError, "Image has incorrect colour table"
        try:
            if im.getInfo()['processing']['absoluteCalibration'] != calib_factor:
                raise ValueError, "Image has incorrect absolute calibration factor"
        except KeyError:
            if calib_factor is None:
                pass
            else:
                raise ValueError, "Image has incorrect absolute calibration factor"
      
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
    fov_angle=float(image.info['fov_angle'])
    strip_width=int(image.info['strip_width'])
    keo_type = image.info['keo_type']
    data_points = eval(image.info['data_points'])
    data_spacing = int(image.info['data_spacing'])
    try:
        calib_factor = float(image.info['calib_factor'])
    except ValueError:
        calib_factor = None
    except KeyError:
        calib_factor = None
    
    #clear image header data
    image.info={}
    
    #create new keogram object
    new_keogram=keogram(image, None, start_time, end_time, angle, fov_angle, strip_width, None, keo_type, data_points, data_spacing, calib_factor)
    
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
        radii = []
        mode = data[0].getMode()
        try:
            colour_table = data[0].getInfo()['processing']['applyColourTable']
        except KeyError:
            colour_table = None
        
        try:
            calib_factor = data[0].getInfo['processing']['absoluteCalibration']
        except KeyError:
            calib_factor = None
        
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
        calib_factor = data.getCalib_factor()
    
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
        start_time = min(times)
    elif start_time > max(times):
        raise ValueError, "The image(s) are outside of the specified time range for the keogram"
    if end_time == None:
        end_time = max(times)
    elif end_time < min(times):
        raise ValueError, "The image(s) are outside of the specified time range for the keogram"

    
    #if the start and end times are the same (e.g. if the keogram has been created with a single image)
    #then add one hour to the end time
    if start_time == end_time:
        end_time = end_time + datetime.timedelta(hours=1)
    
    #crop the list of images/dataset to only include images in the specified range
    if type(data) == type(list()):
        i = 0
        while i < len(data):
            try:
                time=datetime.datetime.strptime(im.getInfo()['header']['Creation Time'], "%d %b %Y %H:%M:%S %Z")#read creation time from header
            except ValueError:
                time=datetime.datetime.strptime(im.getInfo()['header']['Creation Time']+"GMT", "%d %b %Y %H:%M:%S %Z")#read creation time from header
            if ((time < start_time) or (time > end_time)):
                data.pop(i)
                i -= 1
            i += 1
    else:
        data = data.crop(start_time, end_time)
    
        
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
    
    if keo_type == "Average":
        strip_width = 5
    #create keogram object
    keo_obj = keogram(keo_image, colour_table, start_time, end_time, angle, keo_fov_angle, strip_width, None, keo_type, data_points, mean_data_spacing_pix, calib_factor)
        
    return keo_obj
        
###################################################################################      

def _putData(image, keo_pix, width, height, strip_width, angle, keo_fov_angle, start_secs, end_secs, keo_type="CopyPaste"):
    
    current_image = __imagePreProcess(image)
    
    if keo_type == "Average":
        real_strip_width = strip_width
        strip_width = 5
    
    #if the image has a larger field of view than the keogram, then reduce it
    if int(current_image.getInfo()['camera']['fov_angle']) > keo_fov_angle:
        current_image = current_image.binaryMask(keo_fov_angle)
        current_image = current_image.centerImage()
    
    #if the image is larger than the keogram, then we have a problem! As a temporary fix
    #we just resize the whole image
    #TODO; change this to just resize the strip taken from the image (should be much faster)
    if int(current_image.getInfo()['camera']['Radius']) > height:
        current_image = current_image.resize((height, height))
    
    #read time data from image and convert to seconds
    try:
        try:
            capture_time = datetime.datetime.strptime(current_image.getInfo()['header'] ['Creation Time'], "%d %b %Y %H:%M:%S %Z")
        except ValueError:
            capture_time = datetime.datetime.strptime(current_image.getInfo()['header'] ['Creation Time'] + " GMT", "%d %b %Y %H:%M:%S %Z")
        capture_time_secs = calendar.timegm(capture_time.timetuple()) #convert to seconds since epoch
    except KeyError:
        raise IOError, "Cannot read creation time from image " + current_image.getFilename()
    
    #calculate x pixel coordinate in keogram of where strip from current image should go
    strip_width_secs = (float((end_secs-start_secs))/float(width+1-strip_width)) * strip_width
    x_coordinate = int(((float(width)/float(end_secs - start_secs + strip_width_secs)) * float((capture_time_secs-start_secs))) + strip_width/2)
    #x_coordinate=int(((float(width)-strip_width)/float((end_secs-start_secs)))*float((capture_time_secs-start_secs))+strip_width/2)
    
    #get strip from image
    if keo_type == "Average":
        strip = current_image.getStrip(angle, real_strip_width)
    else:
        strip = current_image.getStrip(angle, strip_width)
    
    #if the image has a different Radius or field of view angle, or both then life is more difficult
    im_fov_angle = float(current_image.getInfo()['camera']['fov_angle'])
    im_radius = float(current_image.getInfo()['camera']['Radius'])
    mode = current_image.getMode()
    if im_fov_angle != keo_fov_angle:
       
        #change image fov by appending black pixels to it (the image fov will always be <= keo fov)
        difference = ((2*im_radius)*float(float(keo_fov_angle)/float(im_fov_angle)))-(2*im_radius)
        
        if difference <= 0:
            raise RuntimeError, "Strip is longer than diameter of field of view - this shouldn't be possible, check the value you have used for 'Radius'"
        
        #define black for different image modes
        if mode in ("L", "I"):
            black = 0
        elif mode == "RGB":
            black = (0, 0, 0)
        else:
            raise ValueError, "Unknown image mode"
            
        for i in range(len(strip)):
            #create lists of black pixel values to prepend and append to the strip taken from the image
            prepend = [black]*int(difference/2)
            
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
                for j in range(real_strip_width):
                    pix_sum += strip[j][i]
                mean_value = int((pix_sum / float(real_strip_width)) + 0.5)
                keo_pix[x_coordinate, i] = mean_value
        else:
            for i in range(height):
                pix_sum = [0, 0, 0]
                for j in range(real_strip_width):
                    pix_sum[0] += strip[j][i][0] #Red value
                    pix_sum[1] += strip[j][i][1] #green value
                    pix_sum[2] += strip[j][i][2] #blue value
                    
                mean_value = (int((pix_sum[0] / float(real_strip_width)) + 0.5), int((pix_sum[1] / float(real_strip_width)) + 0.5), int((pix_sum[2] / float(real_strip_width)) + 0.5))
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


#class definitions

###################################################################################    

class keoIntensitiesBase:
    """
    Base class for holding the intensity profiles through a keogram. This class is 
    subclassed into keoTimeSlice and keoAngleSlice to deal with profiles in either
    the time or angle direction. 
    """
    
    def __init__(self, positions, intensities, calib_factor):
        
        self._intensities = intensities
        self._positions = positions
        self._calib_factor = calib_factor
        
        self.title = None
        self.x_label = None
        
        if calib_factor is None:
            self.y_label = "Intensity (CCD Counts)"
        else:
            self.y_label = "Intensity (kR)"
    
    def getRawIntensities(self):
        """
        Returns a list of intensities (pixel values) across the profile.
        """
        return self._intensities
    
    def _hasColourBar(self):
        """
        Required by the plotting interface (see allskyPlot)
        """
        return False
    
    def getCalibratedIntensities(self):
        """
        Returns a list of calibrated intensities (Rayleighs) across the profile.
        """
        calib_intensities = []
        
        for i in range(len(self._intensities)):
            calib_intensities.append(self._intensities[i]*self._calib_factor)
        
        return calib_intensities 
        
###################################################################################

class keoTimeSlice(keoIntensitiesBase):
    """
    Class to hold an intensity profile taken along the time axis (at constant 
    angle).
    """
    def __init__(self, positions, intensities, calib_factor):
        keoIntensitiesBase.__init__(self, positions, intensities, calib_factor)
        self.x_label = "Time (UT)"
        
    def getTimes(self):
        """
        Returns a list of datetime objects along the profile.
        """
        return self._positions
    
    def _plot(self, subplot):
        """
        Required by the plotting interface (see allskyPlot)
        """               
        #create tick marks for the x-axis
        time_span = self._positions[len(self._positions)-1] - self._positions[0]
        
        #decide on tick locations
        if time_span <= datetime.timedelta(hours=1):
            #if the keogram is less than an hour long - tick every 10 mins
            x_ticks = range(0, 70, 10)
        elif time_span < datetime.timedelta(hours=7):
            #if the keogram is less than 7 hours long - tick every 30 mins
            x_ticks = [0, 30]         
        else:
            #otherwise only tick every hour
            x_ticks = [0]
        
        #convert the datetime objects into floating point numbers for use with matplotlib
        time_data = []
        for date in self._positions:
            time_data.append(date2num(date))
        
        #plot the data in the subplot
        if self._calib_factor is not None:
            subplot.plot(self._positions, self.getCalibratedIntensities())
        else:
            subplot.plot(self._positions, self.getRawIntensities())
        subplot.xaxis.set_major_locator(MinuteLocator(x_ticks))
        subplot.xaxis.set_major_formatter(DateFormatter("%H:%M"))
        
        subplot.xaxis.axes.set_xlim(date2num(self._positions[0]), date2num(self._positions[len(self._positions)-1]))
        
        #set axis titles
        if self.y_label != None:
            subplot.axes.set_ylabel(self.y_label)
            subplot.yaxis.set_label_position("left")
            
        if self.x_label != None:
            subplot.axes.set_xlabel(self.x_label)
        
        #add title
        if self.title != None:
            subplot.set_title(self.title)
        
        #return a subplot object
        return subplot

###################################################################################        

class keoAngleSlice(keoIntensitiesBase):
    def __init__(self, positions, intensities, calib_factor):
        keoIntensitiesBase.__init__(self, positions, intensities, calib_factor)
        self.x_label = "Scan Angle (degrees)"
    
    def getAngles(self):
        """
        Returns a list of angles (floats) along the profile
        """
        return self._positions
    
    def _plot(self, subplot):
        """
        Required by the plotting interface (see allskyPlot)
        """
        #plot the data in the subplot
        if self._calib_factor is not None:
            subplot.plot(self._positions, self.getCalibratedIntensities())
        else:
            subplot.plot(self._positions, self.getRawIntensities())
        
        subplot.xaxis.axes.set_xlim(self._positions[0], self._positions[len(self._positions)-1])
        
        #set axis titles
        if self.y_label != None:
            subplot.axes.set_ylabel(self.y_label)
            subplot.yaxis.set_label_position("left")
            
        if self.x_label != None:
            subplot.axes.set_xlabel(self.x_label)
        
        #add title
        if self.title != None:
            subplot.set_title(self.title)
        
        #return a subplot object
        return subplot

###################################################################################
        
class keogram:
    """
    Class to hold keogram data. Unless otherwise stated, all methods return a new keogram object.
    """    
    def __init__(self, image, colour_table, start_time, end_time, angle, fov_angle, strip_width, intensities, keo_type, data_points, data_spacing, calib_factor):
        
        #set class attributes
        self.__image=image.copy()
        self.__mode=image.mode
        self.__keo_type = keo_type
        self.__data_points = data_points #pixel coordinates of where the image slices have been placed
        self.__data_spacing = data_spacing #median distance (in pixels) between data entries in keogram
        self.__calib_factor = calib_factor
        
        if colour_table != None:
            self.__colour_table=range(len(colour_table))
            for i in range(len(colour_table)):
                self.__colour_table[i]=colour_table[i]
        else:
            self.__colour_table=None   
            
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
    
    def absoluteCalibration(self, spectral_responsivity, exposure_time):
        """
        Returns a new keogram object which has been calibrated to kR
        """
        if ((self.__mode == "RGB") and (self.__intensities is None)):
            raise RuntimeError, "No intensity data available for this keogram"
        
        calib_factor = 1.0 / float(spectral_responsivity * exposure_time * 1000)
        
        new_keogram = keogram(self.__image, self.__colour_table, self.__start_time, self.__end_time, self.__angle, self.__fov_angle, self.__strip_width, self.__intensities, self.__keo_type, self.__data_points, self.__data_spacing, calib_factor)
        
        return new_keogram
    
     ###################################################################################                                
            
    def angle2pix(self, angle):
        """
        Converts an angle in degrees in the range (90-fov_angle)-(90+fov_angle) to a vertical pixel coordinate in the keogram. 
        Note that the angle IS NOT the angle from North unless the keogram has been created to run in the north-south direction. 
        If the angle is outside of the range of the keogram None is returned. This is the inverse operation of pix2angle()
        """
        if angle < (90-self.__fov_angle) or angle > (90+self.__fov_angle):
            return None
        
        return int((angle-(90-self.__fov_angle))*float(self.__image.size[1]/float(2.0*self.__fov_angle))+0.5)    
        
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
        
        #create new keogram object
        new_keogram=keogram(new_image, new_colour_table, self.__start_time, self.__end_time, self.__angle, self.__fov_angle, self.__strip_width, new_intensities, self.__keo_type, self.__data_points, self.__data_spacing, self.__calib_factor)

        return new_keogram
        
    ###################################################################################                             
    
    def getIntensitiesAt(self, position, strip_width=None, calibrated=False):
        """
        Returns a tuple of lists (angles, intensities) which correspond to a vertical slice through the keogram at the specified 
        time. The strip width argument controls the width in pixels of the strip that the intensities are averaged over. For example
        a strip width of 3 will mean that each intensity returned is the mean of the pixel intensity at time=time, and the 
        neighbouring pixels on each side. Intensities of zero are excluded from the mean calculation (since they correspond to times
        with no available data). For times within regions of missing data, getIntensities will return 0.
        """
        
        if (calibrated and (self.__calib_factor is None)):
            raise ValueError, "No calibration data available for this keogram"
        
        #find out if we are taking a horizontal or vertical slice from the keogram
        if isinstance(position, float):
            if strip_width is None:
                #set strip width to one degree
                strip_width = abs(self.angle2pix(position + 0.5) - self.angle2pix(position - 0.5))
                if strip_width == 0:
                    strip_width = 1
                
            positions, intensities = self._getHorizontalStrip(position, strip_width)
            return keoTimeSlice(positions, intensities, self.__calib_factor)
            
        elif isinstance(position, datetime.datetime):
            if strip_width is None:
                #set strip width to width used in creating keogram
                strip_width = self.__strip_width
                
            positions, intensities = self._getVerticalStrip(position, strip_width)
            return keoAngleSlice(positions, intensities, self.__calib_factor)
        else:
            raise TypeError, "Position must be either a float (angle) or a datetime object"

        
    ###################################################################################   
    
    def _getHorizontalStrip(self, angle, strip_width):
        #check that specified angle is within range of keogram
        if ((angle > (90 + self.__fov_angle)) or (angle < (90 - self.__fov_angle))):
            raise ValueError, "Angle is outside of range of keogram."
            
        times = [] #list to hold time values
        intensities = [] #list to hold intensity values
        
        if self.__intensities==None:
            keo_pix = self.__image.load()
        else:
            keo_pix = self.__intensities.load()
        
        #calculate pixel position of angle
        y_position = self.angle2pix(angle)
        
        for i in range(self.__width):
            times.append(self.pix2time(i))
            
            #calculate list of mean intensities (of a strip of width strip_width)
            sum_intensities=[]
            
            #work out max range for strip size (cannot exceed dimensions of keogram)
            if y_position + int(-strip_width/2)+1 < 0: 
                min_pix = -y_position
            else:
                min_pix=int(-strip_width/2)+1
            if y_position + int(strip_width/2)+1 > self.__height-1: 
                max_pix = self.__height-1-y_position
            else:
                max_pix=int(strip_width/2)+1    
                           
            for j in range(min_pix, max_pix):
                #if there is intensity data for the keogram
                if (self.__mode=="L") or (self.__intensities != None) or (self.__mode=="I"):
                    sum_intensities.append(keo_pix[i, y_position+j])
                
                #if there is no intensity data but there is a colour table    
                elif self.__mode == "RGB" and self.__colour_table != None:
                    if self.__colour_table.count(keo_pix[i, y_position+j]) > 1:
                        raise ValueError, "No unique intensity for RGB tuple"
                        
                    pix_intensity= self.__colour_table.index(keo_pix[i, y_position+j]) #for an RGB image, need to reverse the colour_table to get back to the original intensity
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
            
        return (times, intensities)
        
    ###################################################################################       
    
    def _getVerticalStrip(self, time, strip_width):                                 
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
            angles.append(180 - ((90.0+self.__fov_angle)-float(i)*angle_conversion_factor))
            
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
    
    def histogram(self):
        """
        Returns a histogram of the keogram image. For 'L' mode images this will be a list of 
        length 256, for 'I' mode images it will be a list of length 65536. The histogram
        method cannot be used for RGB images.
        """
        mode = self.getMode()
        
        if mode == "L":
            histogram = self.__image.histogram() #use PIL histogram method for 8bit images
        elif mode == "I":          
            im_pix = numpy.asarray(self.__image) #load pixel values
            histogram = numpy.histogram(im_pix, bins=range(65537), new=True)[0]
            
        else:
            raise ValueError, "Unsupported image mode"
        
        return histogram
    
    ###################################################################################                    
    
    def medianFilter(self, n):
        """
        This is a thin wrapper function for the median filter provided by PIL. It replaces each 
        pixel in the keogram image by the median value of the pixels in an nxn square around it 
        (where n is an integer).
        """
        #the filter size must be odd
        if n%2 == 0:
            warnings.warn("Filter size must be odd. Using n = "+str(n+1)+" instead")
            n = n + 1
        
        image = self.__image.filter(ImageFilter.MedianFilter(n))
        
        if self.__intensities != None:
            intensities = self.__intensities.filter(ImageFilter.MedianFilter(n))
        else:
            intensities=None
            
        #create new keogram object
        new_keogram=keogram(image, self.__colour_table, self.__start_time, self.__end_time, self.__angle, self.__fov_angle, self.__strip_width, intensities, self.__keo_type, self.__data_points, self.__data_spacing, self.__calib_factor)
        
        return new_keogram    
            
    ###################################################################################                
    
    def pix2angle(self, pixel):
        """
        Converts a vertical pixel coordinate into an angle in degrees. If the pixel coordinate is outside of the range of the 
        keogram None is returned. This is the inverse operation of angle2pix().
        """
        if pixel < 0 or pixel > self.__height:
            return None
        return float((90-self.__fov_angle)+((2*self.__fov_angle)/float(self.__height))*pixel)
    
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
    
    def _hasColourBar(self):
        if self.__colour_table is not None:
            return True
        else:
            return False
            
    ###################################################################################                            
    
    def _plot(self, subplot):
        """
        Plots the keogram data into the given subplot object. This method is required for
        compatibility with the allskyPlot module
        """
        #plot keogram image,matplotlib doesn't support 16bit images, so if the image is not RGB, then need to check that it is 8bit
        if self.__image.mode == 'RGB' or self.__image.mode == 'L':
            image = subplot.imshow(self.__image, origin="top", aspect="auto")
        else:
            image = subplot.imshow(self.__image.convert('L'), origin="top", aspect="auto", cmap=matplotlib.cm.gray)       
        
    
        if self.__colour_table is not None:
            allskyPlot.createColourbar(subplot, self.__colour_table, self.__calib_factor)
         
        #create tick marks for the y-axis every 20 degrees
        y_ticks = [] #tick positions (in pixels)
        y_labels = [] 
        for y in range(0, 180, 20):
            y_ticks.append(self.angle2pix(y))
            y_labels.append(str(int(math.fabs(y-180))))
        
        subplot.yaxis.set_major_locator(FixedLocator(y_ticks))
        subplot.yaxis.set_major_formatter(FixedFormatter(y_labels))
               
        #create tick marks for the x-axis
        time_span = self.__end_time - self.__start_time

        x_ticks = [] #tick positions (in pixels)
        x_labels = []
        current_time = self.__start_time.replace(minute=0, second=0, microsecond=0)
        while current_time <= self.__end_time:
            pix = self.time2pix(current_time)
            if pix is not None: #skip times outside the range of the keogram
                x_ticks.append(pix)
                x_labels.append(current_time.strftime("%H:%M"))
            
            if time_span <= datetime.timedelta(hours=1):
                #if the keogram is less than an hour long - tick every 10 mins
                current_time += datetime.timedelta(minutes=10)
        
            elif time_span < datetime.timedelta(hours=7):
                #if the keogram is less than 7 hours long - tick every 30 mins
                current_time += datetime.timedelta(minutes=30)  
                
            else:
                #otherwise only tick every hour
                current_time += datetime.timedelta(hours=1)
        
        subplot.xaxis.set_major_locator(FixedLocator(x_ticks))
        subplot.xaxis.set_major_formatter(FixedFormatter(x_labels))
        
        #set axis titles
        if self.y_label != None:
            subplot.axes.set_ylabel(self.y_label)
            subplot.yaxis.set_label_position("left")
            
        if self.x_label != None:
            subplot.axes.set_xlabel(self.x_label)
        
        if self.title == "DEFAULT":    
        #create title string for keogram
            start_time_string= self.__start_time.ctime()
            end_time_string=self.__end_time.ctime()
            keo_title=start_time_string+" - "+end_time_string
        else:
            keo_title = self.title
        
        #add title
        if keo_title != None:
            subplot.set_title(keo_title)
        
        #return a subplot object
        return subplot

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
        new_keogram=keogram(image, None, start_time, end_time, self.__angle, self.__fov_angle, [], self.__strip_width, self.__intensities, self.__keo_type, self.__data_points, self.__data_spacing, self.__calib_factor)
        
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
        header['strip_width']=str(self.__strip_width)
        header['colour_table']=str(self.__colour_table)
        header['fov_angle']=str(self.__fov_angle)
        header['keo_type'] = self.__keo_type
        header['data_points'] = str(self.__data_points)
        header['data_spacing'] = str(self.__data_spacing)
        header['calib_factor'] = str(self.__calib_factor)
        
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
        
        #return zoomed in keogram
        return keogram(image_sec, self.__colour_table, start_time, end_time, self.__angle, self.__fov_angle, self.__strip_width, intensities_sec, self.__keo_type, new_data_points, self.__data_spacing, self.__calib_factor)
                        
###################################################################################                                
                                                                
