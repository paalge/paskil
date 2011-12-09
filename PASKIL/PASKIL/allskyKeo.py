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
Introduction:

    The allskyKeo module provides a keogram class used to represent a keogram.
    Keograms are an effective means to summarise all-sky data from a long time
    period. They are basically thin strips taken from all the images and 
    stacked together in the time axis.
    
    
Concepts:
    
    Keograms are created by taking strips of pixel values out of all-sky images
    and stacking them together. The width of the strip of pixels can be set 
    using the strip_width argument. A value of about 5 gives reasonable 
    results. Gaps in the data are interpolated using linear interpolation. 
    However, large gaps due to lack of data are not interpolated across and 
    will result in blank spaces in the keogram. The angle (from geographic 
    North) that the strips are taken from the images at, can be set using the
    angle argument.
    

Example:

    The following example creates a keogram of the 630nm wavelength between 
    18:30 and 19:30 on the 4/2/2003 using the allsky images of type "png" 
    stored in the directory "Allsky Images". The recursive option is used to 
    traverse the entire directory structure contained within "Allsky Images" 
    looking for images. The keogram is then plotted and viewed in an 
    interactive plotting window.


        from PASKIL import allskyKeo, allskyData, allskyPlot
        import datetime
        from pylab import show
        
        #create datetime object defining start time for keogram
        start_time = datetime.datetime.strptime("04 Feb 2003 18:30:00 GMT",
                                                "%d %b %Y %H:%M:%S %Z")
        
        #create datetime object defining end time for keogram 
        end_time = datetime.datetime.strptime("04 Feb 2003 19:30:00 GMT",
                                              "%d %b %Y %H:%M:%S %Z") 
        
        #create a new dataset object
        dataset = allskyData.new("Allsky Images","630","png",
                                 site_info_file="site_info.txt",recursive=True) 
        
        #create a new keogram with a sweep angle of 327 degrees from geographic
        #north and using a strip width of 3 pixels and a data spacing of 60 
        #seconds
        keo = allskyKeo.new(dataset, 327, start_time=start_time,
                            end_time=end_time, strip_width=3, data_spacing=60)
        
        #set a title for the keogram plot
        keo.title = "An Example Keogram"
        
        #set the x axis to show a label every 10 mins
        keo.time_label_spacing = 10 
    
        #plot the keogram
        plot = allskyPlot.plot([keo]) 

        show() #open the figure in an interactive plotting window       
""" 

###############################################################################
import datetime
import calendar
import math
import numpy
import matplotlib.cm
import warnings
import Image
import ImageFilter
import multiprocessing
import copy

from pylab import MinuteLocator, DateFormatter, date2num, num2date
from pylab import FixedLocator, FixedFormatter

from PASKIL import allskyImage, allskyColour, allskyPlot, misc, stats
from PASKIL.extensions import cKeo

###############################################################################    
# "public" function definitions
###############################################################################

def combine(keograms, data_spacing="AUTO"):
    """
    Combines all the keograms in the list into a single keogram. Keograms in 
    the list must have the same mode, calib_factor and colour_table.
    
    If data_spacing is set to \'AUTO\' then the data spacing will be 
    re-evaluated using the data points from all of the keograms to be combined.    
    """
    #check func arg is a list
    if type(keograms) != type(list()):
        raise ValueError, ("combine(keograms) expecting a list, got " + 
                           str(type(keograms)))
    
    #check that the keograms all have the same properties
    modes = set()
    calib_factors = set()
    colour_tables = set()
    strip_widths = set()
    keo_types = set()
    heights = set()
    angles = set()
    keo_fovs = set()
    keo_lens_projs = set()
    for keo in keograms:
        modes.add(keo.getMode())
        calib_factors.add(keo.getCalib_factor())
        colour_tables.add(keo.getColour_table())
        strip_widths.add(keo.getStrip_width())
        heights.add(keo.getHeight())
        keo_types.add(keo.getType())
        angles.add(keo.getAngle())
        keo_lens_projs.add(keo.getLens_projection())
        keo_fovs.add(keo.getFov_angle())
        
    if len(modes) > 1:
        raise ValueError, "Cannot combine keograms with different modes"
    if len(keo_fovs) > 1:
        raise ValueError, ("Cannot combine keograms with different fields of "
                           "view")
    if len(calib_factors) > 1:
        raise ValueError, ("Cannot combine keograms with different calibration"
                           " factors")
    if len(colour_tables) > 1:
        raise ValueError, ("Cannot combine keograms with different colour "
                           "tables")
    if len(strip_widths) > 1:
        raise ValueError, "Cannot combine keograms with different strip widths"
    if len(keo_types) > 1:
        raise ValueError, "Cannot combine keograms of different keo_types"
    if len(heights) > 1:
        raise ValueError, "Cannot combine keograms of different heights"
    if len(angles) > 1:
        raise ValueError, "Cannot combine keograms of different angles"
    if len(keo_lens_projs) > 1:
        raise ValueError, ("Cannot combine keograms with different "
                           "lens projections")

    mode = modes.pop()
    calib_factor = calib_factors.pop()
    colour_table = colour_tables.pop()
    strip_width = strip_widths.pop()
    keo_type = keo_types.pop()
    height = heights.pop()
    angle = angles.pop()
    keo_fov_angle = keo_fovs.pop()
    lens_proj = keo_lens_projs.pop()
        
    #get the times of each data entry in each keogram
    times = []
    for keo in keograms:
        times += keo.getDataTimes()
    
    #work out the size for the combined keogram
    combined_width, combined_mean_data_spacing = _calc_keo_width(times, 
                                                                 None, None, 
                                                                 strip_width, 
                                                                 keo_type, 
                                                                 data_spacing)
    
    #create an array for the new keogram
    keo_arr = _generate_keo_arr(mode, combined_width, height)
    
    #work out the data points in the new keogram (this essentially uses the 
    #time2pix method)
    converter = _generate_time2pix_converter(min(times), max(times), 
                                             combined_width, strip_width)
    combined_data_pts = [converter(t) for t in times]
    extra_bit = (strip_width / 2)
    
    #convert data points to integer pixel coordinates
    int_combined_data_pts = [int(round(x)) for x in combined_data_pts]
    
    i = 0
    for keo in keograms:
        s_data_pts = keo.getDataPoints()
        s_data = keo.getData()
        for s_x in s_data_pts:
            t_x = int_combined_data_pts[i]            
            keo_arr[t_x + (-extra_bit):t_x + (extra_bit + 1),
                     :, :] = s_data[s_x + (-extra_bit):s_x + (extra_bit + 1), 
                                    :, :]
            i += 1
        
    if keo_type == "CopyPaste":
        #1.5 factor allows some flexibility in data spacing without 
        #interpolating across large gaps
        keo_arr = _interpolateData(int_combined_data_pts, keo_arr, mode, 
                                   colour_table, strip_width, 
                                   int(1.5 * combined_mean_data_spacing)) 
    elif keo_type == "Average":
        #+5 is effective strip width - used in calculating the width 
        #of the keogram
        keo_arr = _interpolateData(int_combined_data_pts, keo_arr, 
                                   mode, colour_table, 1, 
                                   int(1.5 * (combined_mean_data_spacing + 5))) 
        
    return keogram(keo_arr, colour_table, min(times), max(times), angle, 
                      keo_fov_angle, strip_width, keo_type, combined_data_pts, 
                      data_spacing, calib_factor, lens_proj)


###############################################################################    
    
def new(data, angle, start_time=None, end_time=None, strip_width=5, 
        data_spacing="AUTO", keo_type="CopyPaste", keo_fov_angle=None):   
    """
    Returns a keogram object. The data argument can be either an 
    allskyData.dataset object or a list of allskyImage.allskyImage objects - 
    the images from which the keogram will be produced.  The angle argument is 
    the angle from geographic North that the slices from the images will be 
    taken at. The strip width option controls the width (in pixels) of the 
    slice taken from the image. The start and end time options should be 
    datetime objects specifying the time range of the keogram (the keogram will
    be inclusive of these times). The default value is None, in which case all 
    images in the dataset/list will be included. The data_spacing option should
    be the amount of time (in seconds) between the source images for the 
    keogram. The default value is "AUTO", in which case the minimum gap between 
    consecutive images in the dataset is used. However, under some 
    circumstances, this may lead to a stripy, uninterpolated keogram, in which 
    case you should increase the data_spacing value. The keo_type argument 
    controls how the keogram is produced. If it is set to "Average" then the 
    keogram will be made up of a series of strips one pixel wide, which are the
    averaged pixel values of the slice taken from the image. These one pixel 
    wide strips will then be interpolated between. Effective use of this type, 
    requires a much larger strip width than 'CopyPaste' keograms. It is also 
    not particularly successful for RGB keograms. "CopyPaste" type keograms
    are made up of finite width slices of the image (specified by strip_width),
    which are then interpolated between. This is not a keogram in the strictest
    sense of the word, since the finite width of the slices is plotted in the 
    time domain, which doesn't really make sense. However, for RGB keograms it 
    often produces a more attractive plot with less interpolation effects.
    
    For keograms produced from dataset objects, this function uses the 
    multiprocessing module to split keogram creation over multiple CPUs
    (where available). This can significantly speed up creating keograms - 
    however, this is not possible to do when creating keograms from a list
    of allskyImage objects.
    
    Keogram objects (as returned by this function) can be visualised using
    the allskyPlot module. See allskyPlot.plot and allskyKeo.keogram for
    details.
    """
    #the strip width has to be odd otherwise life is too difficult
    if strip_width % 2 == 0:
        strip_width += 1
        warnings.warn("strip_width must be an odd number. Changing to " + 
                      str(strip_width))
    
    #check fov arg is tuple
    if type(keo_fov_angle) not in [type(None), tuple]:
        raise TypeError, ("keo_fov_angle must be either None or a tuple "
                          "(min fov, max fov)")
    
    #check that the range is sensible
    if type(keo_fov_angle) is tuple:
        if keo_fov_angle[0] >= keo_fov_angle[1]:
            raise ValueError, ("Lower field of view angle bound must be "
                               "smaller than upper bound.")
        for bound in keo_fov_angle:
            if bound < 0.0 or bound > 180.0:
                raise ValueError, ("Field of view bounds must be in the "
                                   "range 0.0 - 180.0 degrees")
    
    #record key word arguments passed to this function
    kwargs = {'start_time':start_time, 'end_time':end_time, 
              'strip_width':strip_width, 'data_spacing':data_spacing, 
              'keo_type':keo_type, 'keo_fov_angle':keo_fov_angle}
    
    #if data is a list of allskyImages, then we can't process it asyncronously 
    #(can't pickle a PIL Image object)
    if type(data) is list:
        return __fromList(data, angle, **kwargs)
    
    #otherwise we assume that it is a dataset object and we can process it 
    #asyncronously
    #work out a good number of processes to split between
    num_chunks = 1
    num_images = data.getNumImages()
    num_cpus = multiprocessing.cpu_count()
    
    #need at least 2 images per chunk, and no point in creating more processes 
    #than cpus
    if num_images >= 2 * num_cpus:
        num_chunks = num_cpus
    elif int(num_images / 2) >= 2:
        num_chunks = int(num_images / 2)
    #else num_chunks remains as 1
       
    #create argument tuples
    args = map(None, data.split(num_chunks), [angle] * num_chunks)
    kwargs['interpolate'] = False #don't want to interpolate the sections
    arg_tuples = map(None, args, [kwargs] * num_chunks)

    #create processing pool 
    try:
        processing_pool = multiprocessing.Pool(processes=num_chunks)
        
        #create the keogram segments
        results = processing_pool.map(__fromDatasetWrapper, arg_tuples, 
                                      chunksize=1)
    except Exception, ex:
        #if anything goes wrong, kill the child processes
        processing_pool.terminate()
        raise ex

    processing_pool.close()
    
    #put the pieces of keogram together in a new keogram
    return combine(results, data_spacing=data_spacing)        

      
###############################################################################
 
def load(filename):
    """
    Loads a keogram object from the specified file. Keogram files can be 
    created using the save() method.
    """
    image = Image.open(filename)
    
    #read header data
    angle = float(image.info['angle'])
    ct = image.info['colour_table']
    if ct != str(None):
        colour_table = allskyColour.basicColourTable(eval(ct))
    else:
        colour_table = None
    
    #get time strings
    st_str = image.info['start_time'].lstrip().rstrip()
    et_str = image.info['end_time'].lstrip().rstrip()
    
    start_time = datetime.datetime.strptime(st_str, "%d %b %Y %H:%M:%S")
    end_time = datetime.datetime.strptime(et_str, "%d %b %Y %H:%M:%S")
    fov_angle = eval(image.info['fov_angle'])
    strip_width = int(image.info['strip_width'])
    keo_type = image.info['keo_type']
    data_points = eval(image.info['data_points'])
    lens_projection = image.info['lens_projection']
    try:
        data_spacing = int(image.info['data_spacing'])
    except ValueError:
        #data spacing might be "Auto"
        data_spacing = image.info['data_spacing']
    try:
        calib_factor = float(image.info['calib_factor'])
    except ValueError:
        calib_factor = None
    except KeyError:
        calib_factor = None
    
    #convert image to array
    keo_arr = numpy.asarray(image).swapaxes(0, 1)
    
    #ensure the array is 3d even if we are not dealing with an RGB image
    if len(keo_arr.shape) == 2:
        keo_arr = keo_arr.reshape((keo_arr.shape[0], keo_arr.shape[1], 1))
    

    return keogram(keo_arr, colour_table, start_time, end_time, angle, 
                   fov_angle, strip_width, keo_type, data_points, 
                   data_spacing, calib_factor, lens_projection)
    
###############################################################################



###############################################################################
# "protected" function definitions - not for public consumption
###############################################################################

def _generate_pix2angle_converter(keo_height, keo_fov_angle, lens_projection):
    """
    Returns a function for converting from pixel coordinates to angles in a 
    keogram with the specified properties. Note that the pixel at coordinate 0 
    corresponds to the top of the keogram image, and the lower field of view 
    angle bound.
    """
    
    angle_range = math.radians(keo_fov_angle[1] - keo_fov_angle[0])
    
    if lens_projection == "equidistant":
        focal_length = (keo_height - 1) / float(angle_range)
        
        return lambda pix: (math.degrees(float(pix) / focal_length) + 
                            keo_fov_angle[0])
    
    elif lens_projection == "equisolidangle":
        angle_from_zenith = lambda angle: math.fabs(angle - 90.0)
        
        theta_1 = math.radians(angle_from_zenith(keo_fov_angle[0]))
        theta_2 = math.radians(angle_from_zenith(keo_fov_angle[1]))
    
        focal_length = float(keo_height-1) / (2.0 * (math.sin(theta_1/2.0) + math.sin(theta_2/2.0)))
        
        zenith_pixel = _generate_angle2pix_converter(keo_height, keo_fov_angle, lens_projection)(90.0)
        
        angle_from_zenith = lambda pix: 2.0*math.asin(math.fabs(zenith_pixel-pix)/(2.0*focal_length))
        
        
        return lambda pix: math.degrees(((-1 if pix<zenith_pixel else 1)*angle_from_zenith(pix)) + math.radians(90.0))



###############################################################################

def _generate_angle2pix_converter(keo_height, keo_fov_angle, lens_projection):
    """
    Returns a function for converting from angles to pixel coordinates in a 
    keogram with the specified properties. Note that the pixel at coordinate 0 
    corresponds to the top of the keogram image, and the lower field of view 
    angle bound.
    """
    angle_range = math.radians(keo_fov_angle[1] - keo_fov_angle[0])
    
    if lens_projection == "equidistant":
        focal_length = (keo_height - 1) / float(angle_range)
        
        return lambda angle: focal_length * math.radians(angle - 
                                                          keo_fov_angle[0])
    elif lens_projection == "equisolidangle":
        angle_from_zenith = lambda angle: math.fabs(angle - 90.0)
        
        theta_1 = math.radians(angle_from_zenith(keo_fov_angle[0]))
        theta_2 = math.radians(angle_from_zenith(keo_fov_angle[1]))
    
        focal_length = float(keo_height-1) / (2.0 * (math.sin(theta_1/2.0) + math.sin(theta_2/2.0)))

        return lambda angle: ((-1 if angle<90 else 1)*(2.0 * focal_length * math.sin(math.radians(angle_from_zenith(angle)) / 2.0)))+(2.0 * focal_length * math.sin(theta_1 / 2.0))
    
    else:
        raise ValueError, ("Unknown lens projection \"" + str(lens_projection)+ 
                           "\"Expecting \"equidistant\" or \"equisolidangle\"")


###############################################################################

def _generate_pix2time_converter(start_time, end_time, width, strip_width):
    """
    Returns a function for converting from pixel coordinates to times in a 
    keogram with the specified properties. The return value of the converter 
    function is a datetime object.
    """
    #half_strip has to be an int since the start and end buffers are an 
    #integer number of pixels
    half_strip = int(strip_width // 2) 
    time_pix_ratio = (date2num(end_time) - 
                      date2num(start_time)) / float((width - strip_width))
    start_secs = date2num(start_time)
    
    return lambda pix: num2date(start_secs + (time_pix_ratio * 
                                 (pix - half_strip))).replace(tzinfo=None)


###############################################################################

def _generate_time2pix_converter(start_time, end_time, width, strip_width):
    """
    Returns a function for converting from time to pixel coordinates in a 
    keogram with the specified properties. Note that the converter function 
    returns floating point pixel values (since each pixel in the keogram 
    represents a range of time values).
    """
    #half_strip has to be an int since the start and end buffers are an integer 
    #number of pixels
    half_strip = int(strip_width // 2) 
    pix_time_ratio = (width - strip_width) / float((date2num(end_time) - 
                                                    date2num(start_time)))
    start_secs = date2num(start_time)
    
    return lambda time: ((date2num(time) - start_secs) * 
                         (pix_time_ratio)) + half_strip


###############################################################################

def _generate_keo_arr(mode, keo_width, keo_height):   
    """
    Returns a numpy array with the correct size and data type (dtype) for 
    the specified mode, width and height. The returned array is ALWAYS 3D.
    """
    
    if mode == "RGB":
        keo_arr = numpy.zeros(shape=(keo_width, keo_height, 3), dtype='uint8')
    elif mode == "L":
        keo_arr = numpy.zeros(shape=(keo_width, keo_height, 1), dtype='uint8')
    elif mode == "I":
        keo_arr = numpy.zeros(shape=(keo_width, keo_height, 1), dtype='int32')
    else:
        raise ValueError, "Unsupported mode for keogram"
    return keo_arr


###############################################################################

def _estimate_data_spacing(times):
    """
    For a list of datetime objects, returns the minimum and median gaps
    between elements in the list as a tuple.
    """
    
    #if there is only one image in the dataset, then the spacing cannot be 
    #found!
    if len(times) < 2:
        raise RuntimeError, ("Not enough images to allow automatic data "
                             "spacing calculation")
    spacings = []
    i = 1
    while i < len(times):
        spacing = times[i] - times[i - 1]

        if spacing != 0:
            spacings.append((times[i] - times[i - 1]).seconds)
        i += 1
    min_data_spacing = min(spacings)
    med_data_spacing_secs = stats.median(spacings)
    
    return min_data_spacing, med_data_spacing_secs


###############################################################################
    
def _calc_keo_width(times, start_time, end_time, strip_width, keo_type, 
                    data_spacing):
    """
    Returns a tuple of keogram_width and the mean spacing between data points
    in the keogram in pixels (well, actually the median spacing - but never
    mind).
    
    The width is calculated in an unscientific way using the strip width, 
    time range and data spacing of the keogram to be created. It is a slightly
    random formula for keogram width, but it is designed to ensure that there
    is at least some space between consecutive strips to allow for 
    interpolation. The hope is that this reduces the stripyness of the keogram.
    """
    #remove duplicate times (otherwise get zero division error)
    times = list(set(times))
    
    times.sort()
    
    #find the data spacing (in seconds)
    #if data_spacing is set to auto, then determine the data spacing in the 
    #data set
    if data_spacing == "AUTO":
        min_data_spacing, mean_data_spacing_secs = _estimate_data_spacing(times)
    else:
        mean_data_spacing_secs = data_spacing
        min_data_spacing = data_spacing
    
    if start_time is None:
        start_time = min(times)
    if end_time is None:
        end_time = max(times)
    
    #convert start and end times into seconds since the epoch
    start_secs = calendar.timegm(start_time.timetuple())
    end_secs = calendar.timegm(end_time.timetuple())
    
    #work out a good width for the keogram - this is a bit arbitrary but 
    #gives reasonable results
    if keo_type == "CopyPaste":
        keo_width = int(float(((end_secs - start_secs) * strip_width)) / 
                        (min_data_spacing / 2.0))
    else:
        keo_width = int(float(((end_secs - start_secs) * 5)) / 
                        (min_data_spacing / 2.0))
    
    #convert the mean data spacing to pixels    
    mean_data_spacing_pix = int((float(keo_width) / 
                                 float(end_secs - start_secs)) * 
                                 mean_data_spacing_secs)
    
    return keo_width, mean_data_spacing_pix


###############################################################################

def __fromDatasetWrapper(args_tuple): 
    """
    Simple wrapper function to allow the __fromDataset function to be called
    using an argument tuple (args, kwargs).
    """
    return __fromDataset(*args_tuple[0], **args_tuple[1])


###############################################################################

def __fromList(data, angle, start_time=None, end_time=None, strip_width=5, 
               data_spacing="AUTO", keo_type="CopyPaste", interpolate=True, 
               keo_fov_angle=None):
    """
    Creates a keogram object from a list of allskyImage objects.
    """
    #TODO - there is no need for this function to have kwargs - they
    #all have to specified when it is called anyway. The kwargs should
    #only be available for new(), here they should be ordinary args
    
    _checkImages(data) #check for consistancy of image properties
    
    times = []
    fov_angles = []
    radii = []
    mode = data[0].getMode()

    colour_table = data[0].getColourTable()
    lens_proj = data[0].getInfo()['camera']['lens_projection']
    
    
    try:
        calib_factor = data[0].getInfo()['processing']['absoluteCalibration']
    except KeyError:
        calib_factor = None
    
    for im in data:
        info = im.getInfo()
        
        #read creation time from header
        try:
            time = datetime.datetime.strptime(info['header']['Creation Time'],
                                               "%d %b %Y %H:%M:%S %Z")
        except ValueError:
            time = datetime.datetime.strptime(info['header']['Creation Time'] +
                                               "GMT", "%d %b %Y %H:%M:%S %Z")
        times.append(time)
        fov_angles.append(info['camera']['fov_angle'])
        radii.append(int(info['camera']['Radius']))
    times = list(set(times)) #remove duplicate entries from times list
    
    max_im_fov = float(max(fov_angles))
    if keo_fov_angle is None:
        keo_fov_angle = (90 - max_im_fov, 90 + max_im_fov)
    
    #if start and end times are set to None, then get them from the list of 
    #times
    if start_time == None:
        start_time = min(times)
    elif start_time > max(times):
        raise ValueError, ("The image(s) are outside of the specified time "
                           "range for the keogram")
    if end_time == None:
        end_time = max(times)
    elif end_time < min(times):
        raise ValueError, ("The image(s) are outside of the specified time "
                           "range for the keogram")
    
    if start_time > end_time:
        raise ValueError, ("The start time for the keogram is after the end "
                           "time!")
    
    #if the start and end times are the same (e.g. if the keogram has been 
    #created with a single image) then add one hour to the end time
    if start_time == end_time:
        end_time = end_time + datetime.timedelta(hours=1)

    #crop the list of images to only include images in the specified range and
    #record the times
    i = 0
    times = []
    while i < len(data):
        im = data[i]
        info = im.getInfo()
        #read creation time from header
        try:
            time = datetime.datetime.strptime(info['header']['Creation Time'], 
                                              "%d %b %Y %H:%M:%S %Z")
        except ValueError:
            time = datetime.datetime.strptime(info['header']['Creation Time'] +
                                               "GMT", "%d %b %Y %H:%M:%S %Z")
        if time < start_time or time > end_time:
            data.pop(i)
            i -= 1
        else:
            times.append(time)
        i += 1
    
    #calculate the width of the keogram in pixels
    keo_width, mean_data_spacing_pix = _calc_keo_width(times, start_time, 
                                                       end_time, strip_width, 
                                                       keo_type, data_spacing)
    
    
    #calculate the height for the keogram. This could be set to any value 
    #(since the strips taken from the images are just resized to fit). However,
    #to minimise the amount of resizing to be done we guess that the max radius 
    #corresponds to the image with the max fov angle, and calculate the height 
    #for the keogram based on this 
    im_angle2pix = _generate_angle2pix_converter(2 * max(radii), 
                                                 (90 - max_im_fov, 
                                                  90 + max_im_fov), lens_proj)
    min_pix = im_angle2pix(keo_fov_angle[0])
    max_pix = im_angle2pix(keo_fov_angle[1])
    keo_height = max_pix - min_pix + 2
    
    #create new array to hold keogram data
    keo_arr = _generate_keo_arr(mode, keo_width, keo_height)
        
    #put data into keogram
    data_points = []
    for image in data:
        data_points.append(_putData(image, keo_arr, strip_width, angle,
                                     keo_fov_angle, start_time, end_time, 
                                     keo_type=keo_type))
    
    #convert data points to integer pixel coordinates
    int_data_points = [int(round(x)) for x in data_points]
        
    #interpolate the data
    if interpolate:
        if keo_type == "CopyPaste":
            #1.5 factor allows some flexibility in data spacing without 
            #interpolating across large gaps
            keo_arr = _interpolateData(int_data_points, keo_arr, mode, 
                                       colour_table, strip_width, 
                                       int(1.5 * mean_data_spacing_pix)) 
        elif keo_type == "Average":
            #+5 is effective strip width - used in calculating the 
            #width of the keogram
            keo_arr = _interpolateData(int_data_points, keo_arr, mode, 
                                       colour_table, 1, 
                                       int(1.5 * (mean_data_spacing_pix + 5)))
        
    if keo_type == "Average":
        strip_width = 5
    
    #create keogram object
    return keogram(keo_arr, colour_table, start_time, end_time, angle, 
                   keo_fov_angle, strip_width, keo_type, data_points, 
                   data_spacing, calib_factor, lens_proj)


###############################################################################      

def __fromDataset(data, angle, start_time=None, end_time=None, strip_width=5, 
                  data_spacing="AUTO", keo_type="CopyPaste", interpolate=True, 
                  keo_fov_angle=None):
    """
    Creates a keogram object from a dataset.
    """
    #TODO - there is no need for this function to have kwargs - they
    #all have to specified when it is called anyway. The kwargs should
    #only be available for new(), here they should be ordinary args
    
    #the strip width has to be odd otherwise life is too difficult
    if strip_width % 2 == 0:
        strip_width += 1
        warnings.warn("strip_width must be an odd number. Changing to " + 
                      str(strip_width))
    
    #check that the dataset isn't empty
    if data.getNumImages() == 0:
        raise ValueError, "Cannot create a keogram from an empty dataset"
            
    #read the keogram parameters from the dataset
    
    #need to convert the times list to a set just incase there are two images
    #from the same time (would result in zero as separation)
    times = list(set(data.getTimes())) 
    mode = data.getMode()
    max_im_fov = float(max(data.getFov_angles()))
    if keo_fov_angle is None:
        keo_fov_angle = (90 - max_im_fov, 90 + max_im_fov)
    colour_table = data.getColourTable()
    radii = data.getRadii()
    calib_factor = data.getCalib_factor()
    lens_proj = data.getLensProjection()
    times.sort()
    
    #if start and end times are set to None, then get them from the list of 
    #times
    if start_time == None:
        start_time = min(times)
    elif start_time > max(times):
        raise ValueError, ("The image(s) are outside of the specified time "
                           "range for the keogram")
    if end_time == None:
        end_time = max(times)
    elif end_time < min(times):
        raise ValueError, ("The image(s) are outside of the specified time "
                           "range for the keogram")
    
    if start_time > end_time:
        raise ValueError, ("The start time for the keogram is after the end "
                           "time!")
    
    #if the start and end times are the same (e.g. if the keogram has been 
    #created with a single image) then add one hour to the end time
    if start_time == end_time:
        end_time = end_time + datetime.timedelta(hours=1)
    
    #crop the dataset to only include images in the specified range
    data = data.crop(start_time, end_time)

    #calculate the width of the keogram in pixels
    keo_width, mean_data_spacing_pix = _calc_keo_width(data.getTimes(), 
                                                       start_time, end_time, 
                                                       strip_width, keo_type, 
                                                       data_spacing)
    
    #calculate the height for the keogram. This could be set to any value 
    #(since the strips taken fromthe images are just resized to fit). However, 
    #to minimise the amount of resizing to be donewe guess that the max radius 
    #corresponds to the image with the max fov angle, and calculate theheight 
    #for the keogram based on this 
    im_angle2pix = _generate_angle2pix_converter(2 * max(radii), 
                                                 (90 - max_im_fov, 
                                                  90 + max_im_fov), lens_proj)
    min_pix = im_angle2pix(keo_fov_angle[0])
    max_pix = im_angle2pix(keo_fov_angle[1])
    keo_height = max_pix - min_pix + 2 
    
    #create new array to hold keogram data
    keo_arr = _generate_keo_arr(mode, keo_width, keo_height)
        
    #put data into keogram
    data_points = []
    for image in data:
        data_points.append(_putData(image, keo_arr, strip_width, angle, 
                                    keo_fov_angle, start_time, end_time, 
                                    keo_type=keo_type))
        
    #interpolate the data
    if interpolate:
        #convert data points to integer pixel coordinates
        int_data_points = [int(round(x)) for x in data_points]
        
        if keo_type == "CopyPaste":
            #1.5 factor allows some flexibility in data spacing without 
            #interpolating across large gaps
            keo_arr = _interpolateData(int_data_points, keo_arr, mode, 
                                       colour_table, strip_width, 
                                       int(1.5 * mean_data_spacing_pix)) 
        elif keo_type == "Average":
            #+5 is effective strip width - used in calculating the width 
            #of the keogram
            keo_arr = _interpolateData(int_data_points, keo_arr, mode, 
                                       colour_table, 1, 
                                       int(1.5 * (mean_data_spacing_pix + 5))) 
        
    if keo_type == "Average":
        strip_width = 5
    
    #create keogram object
    return keogram(keo_arr, colour_table, start_time, end_time, angle, 
                   keo_fov_angle, strip_width, keo_type, data_points, 
                   mean_data_spacing_pix, calib_factor, lens_proj)
    

###############################################################################

def _interpolateData(data_list, array, mode, colour_table, strip_width, 
                     max_gap):
    """
    Interpolates between the strips in the keogram image. Large gaps (probably 
    due to missing data) are not interpolated across and will be left as black 
    strips in the final keogram.
    
    The actual interpolation code is in the cKeo extension module 
    (in PASKIL/extensions).
    
    There are two ways in which the interpolation can be done, one is a simple
    linear interpolation, the other is for keograms with a colour table 
    applied. For the latter case, the interpolation is done in such a way, that
    only values which appear in the colour table will be put into the final 
    keogram. It is important to realise however, that because applying a 
    colour table can map multiple intensity values to the same colour - 
    applying a colour table and then interpolating is not the same as 
    interpolating and then applying a colour table.
    """
    
    #ensure there are no duplicate entries in the data_list
    data_list = list(set(data_list))

    #if there is only one data_list entry then return (no interpolation possible)
    if data_list == None or len(data_list) <= 1:
        return array
    
    #sort data list into numerical order
    data_list.sort()
    
    #convert to numpy array
    data_list = numpy.array(data_list, dtype="intc")
    
    #convert array to C type integers
    array = array.astype("intc")
    
    #note that the cKeo module does the interpolations in-place - there is
    #no return value
    if mode == "L":
        #interpolate using C extension module    
        cKeo.linear_interpolate(array[:, :, 0], data_list, strip_width, max_gap)
        array = array.astype("uint8")
    elif mode == "I":
        #interpolate using C extension module    
        cKeo.linear_interpolate(array[:, :, 0], data_list, strip_width, max_gap)
        array = array.astype("int32")
    elif mode == "RGB":
        if colour_table is None:
            cKeo.linear_interpolate(array[:, :, 0], data_list, strip_width, 
                                    max_gap)
            cKeo.linear_interpolate(array[:, :, 1], data_list, strip_width, 
                                    max_gap)
            cKeo.linear_interpolate(array[:, :, 2], data_list, strip_width, 
                                    max_gap)
            array = array.astype("uint8")
        else:
            numpy_ct = numpy.array(colour_table.colour_table, dtype="intc")
            cKeo.ct_lin_interp(array[:, :, 0], data_list, numpy_ct[:, 0], 
                               strip_width, max_gap)
            cKeo.ct_lin_interp(array[:, :, 1], data_list, numpy_ct[:, 1], 
                               strip_width, max_gap)
            cKeo.ct_lin_interp(array[:, :, 2], data_list, numpy_ct[:, 2], 
                               strip_width, max_gap)
            array = array.astype("uint8")
    else:
            raise ValueError, "Unknown image mode"
    
    return array
        

###############################################################################      

def _putData(image, keo_arr, strip_width, angle, keo_fov_angle, start_time, 
             end_time, keo_type="CopyPaste"):
    """
    Takes a strip from the image and puts it into the keogram array.
    """
    #TODO - there is no need for this function to have kwargs - they
    #all have to specified when it is called anyway. The kwargs should
    #only be available for new(), here they should be ordinary args
    
    current_image = _imagePreProcess(image)
    
    width = keo_arr.shape[0]
    height = keo_arr.shape[1]
    
    if keo_type == "Average":
        real_strip_width = strip_width
        strip_width = 5
    
    #get image properties
    current_image_info = current_image.getInfo()
    im_fov_angle = float(current_image_info['camera']['fov_angle'])
    im_lens_proj = current_image_info['camera']['lens_projection']
    mode = current_image.getMode()
    
    #get strip from image
    if keo_type == "Average":
        strip = current_image.getStrip(angle, real_strip_width)
    else:
        strip = current_image.getStrip(angle, strip_width)

    #slice out field of view section of strip that we are interested in, 
    #filling missing data i.e. data outside of the image's fov with black 
    #pixels
    strip_a2p = _generate_angle2pix_converter(strip.shape[1], 
                                              (90 - im_fov_angle, 
                                               90 + im_fov_angle), 
                                               im_lens_proj)
    
    min_fov_pix = strip_a2p(keo_fov_angle[0])
    max_fov_pix = strip_a2p(keo_fov_angle[1])
    

    fov_corrected_strip = numpy.zeros((strip.shape[0], 
                                       (max_fov_pix - min_fov_pix +
                                        2), #+2 because it includes end points
                                       strip.shape[2]), dtype=strip.dtype) 
    
    corr_strip_a2p = _generate_angle2pix_converter(fov_corrected_strip.shape[1], 
                                                   keo_fov_angle, im_lens_proj)
    
    if keo_fov_angle[0] <= 90 - im_fov_angle:
        strip_lower_pix = 0
        corr_lower_pix = int(round(corr_strip_a2p(90 - im_fov_angle)))
    else:
        strip_lower_pix = int(round(strip_a2p(keo_fov_angle[0])))
        corr_lower_pix = 0
    
    if keo_fov_angle[1] >= 90 + im_fov_angle:
        strip_upper_pix = strip.shape[1] - 1
        corr_upper_pix = corr_lower_pix + (strip_upper_pix - strip_lower_pix)
    else:
        corr_upper_pix = fov_corrected_strip.shape[1] - 1
        strip_upper_pix = strip_lower_pix + (corr_upper_pix - corr_lower_pix)
        
    
    fov_corrected_strip[:, corr_lower_pix:corr_upper_pix + 1,
                         :] = strip[:, strip_lower_pix:strip_upper_pix + 1, :]
        
     
    #read time data from image and convert to seconds
    try:
        try:
            capture_time = datetime.datetime.strptime(current_image_info['header'] ['Creation Time'], 
                                                      "%d %b %Y %H:%M:%S %Z")
        except ValueError:
            capture_time = datetime.datetime.strptime(current_image_info['header'] ['Creation Time'] + 
                                                      " GMT", "%d %b %Y %H:%M:%S %Z")
    except KeyError:
        raise IOError, ("Cannot read creation time from image " + 
                        current_image.getFilename())
    
    #calculate x pixel coordinate in keogram of where strip from current image 
    #should go
    time2pix = _generate_time2pix_converter(start_time, end_time, width, 
                                            strip_width)
    x_coordinate = time2pix(capture_time)
          
    if fov_corrected_strip.shape[1] != height:
        #if strip taken from image is a different size to the keogram, then 
        #resize it. This is done by creating an image of the strip and then 
        #resizing the image - a slightly odd way of doing it, but saves me 
        #having to worry about the interpolation problems
        if mode != "RGB":
            #if it's not rgb then only want a 2d array.
            fov_corrected_strip = fov_corrected_strip[:, :, 0]
        
        strip_image = Image.fromarray(fov_corrected_strip)
        strip_image = strip_image.resize((height, fov_corrected_strip.shape[0]))
        size_corrected_strip = numpy.asarray(strip_image).copy()
        
        #convert back to a 3d array
        if len(size_corrected_strip.shape) == 2:
            size_corrected_strip = size_corrected_strip.reshape(size_corrected_strip.shape[0], 
                                                                size_corrected_strip.shape[1], 1)
    else:
        size_corrected_strip = fov_corrected_strip
    #convert x_coordinate into integer pixel coordinate
    int_x_coordinate = int(round(x_coordinate))
    
    #store data in keogram
    if keo_type == "CopyPaste":
        #just copy the pixel data from the image into the keogram
        keo_arr[int_x_coordinate + (-strip_width / 2 + 1):int_x_coordinate + 
                (strip_width / 2 + 1), :, :] = size_corrected_strip[:, :, :]

    elif keo_type == "Average":
        keo_arr[int_x_coordinate, :, :] = size_corrected_strip.mean(axis=0)[:, :]

    else:
        raise ValueError, ("Unknown keogram type. Expecting \"CopyPaste\" or"
                           " \"Average\", got " + type)

    #return the x-coordinate of where we just put the data
    return x_coordinate
        
    
###############################################################################    

def _imagePreProcess(image):
    """
    Checks that the image has had all the requisit preprocessing needed before 
    it is put into a keogram. Returns an allskyImage object which has been 
    processed, if no processing was required then it returns the original 
    object.
    """   
    info = image.getInfo()
        
    if not info['processing'].has_key('binaryMask'):
        image = image.binaryMask(float(info['camera']['fov_angle']))
        
    if not info['processing'].has_key('centerImage'):
        image = image.centerImage()
        
    if not info['processing'].has_key('alignNorth'):
        image = image.alignNorth()
    
    return image
  
        
###############################################################################            

def _checkImages(images, mode=None, wavelength=None, colour_table=None, 
                 calib_factor=None, lens_proj=None):
    """
    Checks that all allskyImages in the images list have the same mode, 
    wavelength, absolute calibration factor, lens projection and colour 
    table either as each other or as those specified by the optional 
    arguments. These are essentially the same checks that are done when 
    a dataset is created.
    """
    if len(images) == 0:
        raise ValueError, "Cannot perform checks on an empty list!"
    
    #if no optional arguments are specified, then take the values from the first image in the list
    if mode is None:
        mode = images[0].getMode()
    
    if wavelength is None:
        wavelength = images[0].getInfo()['header']['Wavelength']
    
    if colour_table is None:
        colour_table = images[0].getColourTable()
    
    if calib_factor is None:
        try:
            calib_factor = images[0].getInfo()['processing']['absoluteCalibration']
        except KeyError:
            calib_factor = None
    
    if lens_proj is None:
        lens_proj = images[0].getInfo()['camera']['lens_projection']
    
    #compare these values to all the other images in the list
    for im in images:
        if im.getMode() != mode:
            raise ValueError, ("Image has incorrect mode, expecting mode: " + 
                               str(mode))
        if im.getInfo()['header']['Wavelength'].find(wavelength) == -1:
            raise ValueError, ("Image has incorrect wavelength, expecting: " + 
                               str(wavelength))

        if im.getColourTable() != colour_table:
            raise ValueError, "Image has incorrect colour table"
        
        if im.getInfo()['camera']['lens_projection'] != lens_proj:
            raise ValueError, ("Image has incorrect lens projection, "
                               "expecting: " + lens_proj)
        
        try:
            if im.getInfo()['processing']['absoluteCalibration'] != calib_factor:
                raise ValueError, ("Image has incorrect absolute calibration "
                                   "factor")
        except KeyError:
            if calib_factor is None:
                pass
            else:
                raise ValueError, ("Image has incorrect absolute calibration "
                                   "factor")


###############################################################################


###############################################################################
#class definitions
###############################################################################    

class keoIntensitiesBase:
    """
    Base class for holding the intensity profiles through a keogram. This class
    is subclassed into keoTimeSlice and keoAngleSlice to deal with profiles in 
    either the time or angle direction. 
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
    
    
    ###########################################################################
    
    def getRawIntensities(self):
        """
        Returns a list of intensities (pixel values) across the profile.
        """
        return self._intensities


    ###########################################################################
    
    def _hasColourBar(self):
        """
        Required by the plotting interface (see allskyPlot)
        """
        return False


    ###########################################################################
        
    def getCalibratedIntensities(self):
        """
        Returns a list of calibrated intensities (Rayleighs) across the 
        profile.
        """
        calib_intensities = []
        
        for i in range(len(self._intensities)):
            calib_intensities.append(self._intensities[i] * self._calib_factor)
        
        return calib_intensities 


    ###########################################################################        
###############################################################################

class keoTimeSlice(keoIntensitiesBase):
    """
    Class to hold an intensity profile taken along the time axis (at constant 
    angle).
    
    The profile can be plotted using the allskyPlot module:
    >>> profile = keo.getIntensitiesAt(angle)
    >>> profile.title = "My intensity plot"
    >>> profile.x_label = "The x axis (time)"
    >>> profile.y_label = "The y axis (intensity)"
    >>> allskyPlot.plot([profile])
    
    Setting the labels/title to None, will result in them not being labelled
    in the plot.    
    """
    def __init__(self, positions, intensities, calib_factor):
        keoIntensitiesBase.__init__(self, positions, intensities, calib_factor)
        self.x_label = "Time (UT)"


    ###########################################################################
        
    def getTimes(self):
        """
        Returns a list of datetime objects along the profile.
        """
        return self._positions


    ###########################################################################
    
    def _plot(self, subplot):
        """
        Required by the plotting interface (see allskyPlot)
        """               
        #create tick marks for the x-axis
        time_span = (self._positions[len(self._positions) - 1] - 
                     self._positions[0])
        
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
        
        subplot.xaxis.axes.set_xlim(date2num(self._positions[0]), 
                                    date2num(self._positions[len(self._positions) - 1]))
        
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


    ###########################################################################
###############################################################################        

class keoAngleSlice(keoIntensitiesBase):
    """
    Class to hold an intensity profile taken along the angle axis (at constant 
    time). See keoTimeSlice for example of plotting.
    """
    def __init__(self, positions, intensities, calib_factor):
        keoIntensitiesBase.__init__(self, positions, intensities, calib_factor)
        self.x_label = "Scan Angle (degrees)"


    ###########################################################################
        
    def getAngles(self):
        """
        Returns a list of angles (floats) along the profile
        """
        return self._positions


    ###########################################################################
        
    def _plot(self, subplot):
        """
        Required by the plotting interface (see allskyPlot)
        """
        #plot the data in the subplot
        if self._calib_factor is not None:
            subplot.plot(self._positions, self.getCalibratedIntensities())
        else:
            subplot.plot(self._positions, self.getRawIntensities())
        
        subplot.xaxis.axes.set_xlim(self._positions[0], 
                                    self._positions[len(self._positions) - 1])
        
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


    ###########################################################################                      
###############################################################################                                

class keogram:
    """
    Class to hold keogram data. Unless otherwise stated, all methods return a 
    new keogram object.
    
    Keograms can be plotted using the allskyPlot module. The labels/title on 
    the plotted keogram are controlled by the following attributes:
    
        title: The title for the plot. May be set to None (no title) or 
               "DEFAULT" in which case the time range for the keogram is
               used for the title.
        
        x_label: The label on the x_axis. This defaults to "Time (UT)", but
                 may be set to None (no label) or any other string.
        
        y_label: The label on the y_axis. This defaults to "Scan Angle 
                 (degrees)", but may be set to None (no label) or any 
                 other string.
        
        time_label_spacing: The interval (in minutes) between tick marks
                            on the x_axis.
    
    Example:
    >>> keo = allskyKeo.new(data, 327)
    >>> keo.title = "My Keogram"
    >>> keo.time_label_spacing = 30
    >>> p = allskyPlot.plot([keo])
    >>> p.savefig("my_keogram.png")
    
    """    
    def __init__(self, data_array, colour_table, start_time, end_time,
                 angle, fov_angle, strip_width, keo_type,
                 data_points, data_spacing, calib_factor, lens_proj):
        
        #check that fov is a tuple (min fov,max fov)
        if type(fov_angle) is not tuple:
            raise TypeError, ("fov_angle argument must be a tuple (min fov, "
                              "max fov)")
        
        #set class attributes
        self.__data = data_array.copy()
        self.__keo_type = keo_type
        
        #pixel coordinates of where the image slices have been placed
        self.__data_points = list(set(data_points)) 
        self.__data_points.sort()
        
        #median distance (in pixels) between data entries in keogram
        self.__data_spacing = data_spacing 
        
        self.__calib_factor = calib_factor
        self.__lens_projection = lens_proj
        
        #read mode from dtype of array
        if self.__data.dtype == 'int32':
            self.__mode = 'I'
        elif self.__data.dtype == 'uint8':
            if self.__data.shape[2] == 3:
                self.__mode = 'RGB'
            else:
                self.__mode = 'L'
        else:
            raise ValueError, "Unknown mode for keogram"
 
        self.__colour_table = colour_table
           
            
        self.__width = self.__data.shape[0]
        self.__height = self.__data.shape[1]
        self.__start_time = start_time
        self.__end_time = end_time
        self.__angle = angle
        self.__fov_angle = fov_angle
        self.__strip_width = strip_width

        #set attributes which control plotting
        self.title = "DEFAULT"
        self.x_label = "Time (UT)"
        self.y_label = "Scan Angle (degrees)"
        self.time_label_spacing = None #in minutes (or None)
  
        
    ###########################################################################                            
    
    def __eq__(self, x):
        """
        Allows comparison of keogram objects using ==.
        """
        #can only compare a keogram object to another keogram object
        if not isinstance(x, keogram):
            return NotImplemented
        
        #check attributes are the same
        for k in self.__dict__.keys():
            if k == "_keogram__data":
                continue
            if self.__dict__[k] != getattr(x, k):
                return False
                    
        #check data array is the same
        try:
            if (self.__data == x._keogram__data).all():
                return True
            else:
                return False
        except AttributeError:
            return False


    ########################################################################### 
        
    def __ne__(self, x):
        """
        Allows comparison of keogram objects using !=.
        """
        #can only compare a keogram object to another keogram object    
        if not isinstance(x, keogram):
            return NotImplemented
        
        #check attributes are not the same
        for k in self.__dict__.keys():
            if k == "_keogram__data":
                continue
            if self.__dict__[k] != getattr(x, k):
                return True
                   
        #check data array is not the same
        try:
            if (self.__data == x._keogram__data).all():
                return False
            else:
                return True
        except AttributeError:
            return True

    
    ########################################################################### 
    #define getters
    
    def getImage(self):
        """
        Returns a PIL image object containing a copy of the keogram data 
        displayed as an image. This method will take account of any colour 
        table that has been applied.
        """
  
        #if there is a colour table which has not yet been applied, then 
        #apply it!
        if self.__colour_table is not None and self.__mode != "RGB":
            #PIL doesn't support 16bit images, so need to use own routine 
            #if "I" mode image
            if self.__mode != "I": 
                im_arr = self.__data.flatten() #remove 3rd dimension
                im_arr = im_arr.reshape((self.__width, 
                                         self.__height)).swapaxes(0, 1)
                keo_image = Image.fromarray(im_arr)
                keo_image.putpalette(self.__colour_table.getColourTable())
                
            else:
                keo_image = Image.new("RGB", (self.__width, self.__height), 
                                      "Black")
                keo_image_pix = keo_image.load()
                
                data = self.__data
                ct = self.__colour_table.getColourTable()
                for x in range(keo_image.size[0]):
                    for y in range(keo_image.size[1]):
                        keo_image_pix[x, y] = ct[data[x, y]]
                        
            keo_image = keo_image.convert("RGB")
        
        elif self.__mode == "RGB":
            keo_image = Image.fromarray(self.__data.swapaxes(0, 1))
        
        else:
            im_arr = self.__data.flatten()  #remove 3rd dimension
            im_arr = im_arr.reshape((self.__width, 
                                    self.__height)).swapaxes(0, 1)
            keo_image = Image.fromarray(im_arr)
        return keo_image


    ########################################################################### 
        
    def getMode(self):
        """
        Returns a string containing the mode of the keogram image, 
        e.g. "RGB". See the PIL handbook for details of image modes.
        """
        return self.__mode


    ########################################################################### 
        
    def getCalib_factor(self):
        """
        Returns the absolute calibration factor for the keogram, or None.
        """
        return self.__calib_factor
 
 
    ########################################################################### 
            
    def getColour_table(self):
        """
        Returns an allskyColour.basicColourTable object containing the
        colour mappings used in the keogram. The colour table can either
        be inherited from the source images used to create the keogram
        or it can be added using the addColourTable method.
        """
        return self.__colour_table
 
 
    ########################################################################### 
        
    def getData(self):
        """
        Returns a numpy array object containing the keogram data. Edits to this
        data will be reflected in the keogram itself. Do keo.getData().copy() 
        to avoid overwriting your keogram data!
        """
        return self.__data
  
  
    ########################################################################### 
        
    def getDataPoints(self):
        """
        Returns a list of x-coordinates of the centers of the image slices in 
        the keogram image. Note that the coordinates will be integers (the 
        pixel coordinate of the image slice in the keogram image). However, 
        due to the finte time which one pixel represents, doing time2pix() on 
        one of these coordinates will not return the exact capture time of the
        image that the slice was taken from.
        """
        return [int(round(x)) for x in self.__data_points]

    ###########################################################################     
    
    def getDataSpacing(self):
        """
        Returns the data spacing of the keogram.
        """
        return self.__data_spacing
    
    ########################################################################### 
        
    def getDataTimes(self):
        """
        Returns a list of datetime objects corresponding to the capture times 
        of the images used to create the keogram.
        """
        pix2time = _generate_pix2time_converter(self.__start_time, 
                                                self.__end_time, self.__width, 
                                                self.__strip_width)
        return [pix2time(x) for x in self.__data_points]
        
        
    ########################################################################### 
            
    def getWidth(self):
        """
        Returns an integer containing the width of the keogram image in pixels.
        """
        return self.__width


    ########################################################################### 
            
    def getHeight(self):
        """
        Returns an integer containing the height of the keogram image in 
        pixels.        
        """
        return self.__height


    ########################################################################### 
        
    def getStart_time(self):
        """
        Returns a datetime object containing the earliest time shown in the 
        keogram.
        """
        return self.__start_time


    ########################################################################### 
            
    def getEnd_time(self):
        """
        Returns a datetime object containing the latest time shown in the 
        keogram.
        """
        return self.__end_time


    ########################################################################### 
            
    def getAngle(self):
        """
        Returns the angle from geographic North at which the keogram was made. 
        This is the angle from geographic North that the strips were taken out 
        of the images.
        """
        return self.__angle


    ########################################################################### 
        
    def getFov_angle(self):
        """
        Returns the field of view angle of the keogram as a tuple (min, max). 
        The angles are in degrees. The field of view of the keogram can be
        set either when it is created (using the keo_fov_angle argument) or
        using the zoomFov() method.
        """
        return self.__fov_angle


    ########################################################################### 
        
    def getStrip_width(self):
        """
        Returns the width of the strips (in pixels) that were taken from the 
        source images to create the keogram.
        """
        return self.__strip_width


    ########################################################################### 
        
    def getType(self):
        """
        Returns a string describing the type of the keogram. Either "CopyPaste"
        or "Average"
        """
        return self.__keo_type


    ########################################################################### 
        
    def getLens_projection(self):
        """
        Returns a string describing the lens projection of the images in the 
        keogram. Currently supported projections are "equidistant" and
        "equisolidangle"
        """
        return self.__lens_projection
   
        
    ########################################################################### 
        
    def absoluteCalibration(self, spectral_responsivity, exposure_time):
        """
        Returns a new keogram object which has been calibrated to kR
        """
        if (self.__mode == "RGB"):
            raise RuntimeError, "No intensity data available for this keogram"
        
        calib_factor = 1.0 / float(spectral_responsivity * exposure_time * 
                                   1000)
        
        return keogram(self.__data, self.__colour_table, 
                              self.__start_time, self.__end_time, self.__angle, 
                              self.__fov_angle, self.__strip_width, 
                              self.__keo_type, self.__data_points, 
                              self.__data_spacing, calib_factor, 
                              self.__lens_projection)
    
    
    ########################################################################### 
                
    def angle2pix(self, angle):
        """
        Converts an angle in degrees to a vertical pixel coordinate in the 
        keogram. Note that the angle IS NOT the angle from North unless the 
        keogram has been created to run in the north-south direction. If the 
        angle is outside of the range of the keogram None is returned. This is 
        the inverse operation of pix2angle()
        """
        if angle < self.__fov_angle[0] or angle > self.__fov_angle[1]:
            return None
        
        converter = _generate_angle2pix_converter(self.__height, 
                                                  self.__fov_angle, 
                                                  self.__lens_projection)
        return converter(angle)
        
        
    ########################################################################### 
        
    def applyColourTable(self, colour_table):
        """
        Returns a new keogram object with a colour table applied. The colour 
        table argument should be a colourTable or basicColourTable object as 
        defined in the allskyColour module.
        """
        #can't apply a colour table to an RGB image
        if self.getMode() == 'RGB':
            raise ValueError, "Cannot apply a colour table to an RGB keogram"
        
        #create new keogram object
        return keogram(self.__data, colour_table, self.__start_time, 
                              self.__end_time, self.__angle, self.__fov_angle, 
                              self.__strip_width, self.__keo_type, 
                              self.__data_points, self.__data_spacing, 
                              self.__calib_factor, self.__lens_projection)
        

    ########################################################################### 
        
    def getIntensitiesAt(self, position, strip_width=None):
        """
        If the position argument is a datetime object, then this method returns
        a keoAngleSlice object containing the intensities across the whole 
        field of view at the time specified. If the position argument is a 
        number (angle in degrees), then this method returns a keoTimeSlice 
        object containing the intensities across the whole time range of the 
        keogram at the specified angle. If the position argument is outside the
        range of the keogram then None is returned.
        
        The strip width argument controls the width in pixels of the strip that
        the intensities are averaged over. For example a strip width of 3 will 
        mean that each intensity returned is the mean of the pixel intensity at
        time=time, and the neighbouring pixels on each side. If strip width is 
        set to None, then intensities will be averaged over 1 degree for time 
        slices and over the strip width used for creating the keogram for angle
        slices. Intensities of zero are excluded from the mean calculation 
        (since they correspond to times with no available data). For times 
        within regions of missing data, the intensity will be 0.
        
        keoAngleSlice and keoTimeSlice objects can be plotted using the 
        allskyPlot module. For example:
        
        create the keogram    
            >>> keo = allskyKeo.new(data,327)
        get intensities at a scan angle of 30 degrees 
            >>> i_at_30 = keo.getIntensitiesAt(30.0)
        plot the keogram and the intensities in a figure 
            >>> p = allskyPlot.plot([keo,i_at_30]) 
        save the figure
            >>> p.savefig("keo_and_intensities.png") 
        
        Note that if the keogram has been calibrated then the plotted 
        intensities will be in Rayleighs, otherwise they will be in CCD counts.
        
        """
        #can't get intensities for RGB keogram
        if self.__mode == "RGB":
            raise RuntimeError, "Cannot resolve intensities for an RGB keogram"
        
        #find out if we are taking a horizontal or vertical slice from the keogram
        if type(position) in (int, float):
            #if position is outside range of keo, then return None
            if position > self.__fov_angle[1] or position < self.__fov_angle[0]:
                return None
            
            if strip_width is None:
                #set strip width to one degree
                strip_width = abs(self.angle2pix(position + 0.5) - 
                                  self.angle2pix(position - 0.5))
                if strip_width == 0:
                    strip_width = 1
                
            positions, intensities = self._getHorizontalStrip(position, 
                                                              strip_width)
            return keoTimeSlice(positions, intensities, self.__calib_factor)
            
        elif isinstance(position, datetime.datetime):
            #if position is outside range of keo, then return None
            if (position > self.pix2time(self.__width -1) or 
                position < self.pix2time(0)):
                return None
            
            if strip_width is None:
                #set strip width to width used in creating keogram
                strip_width = self.__strip_width
                
            positions, intensities = self._getVerticalStrip(position, 
                                                            strip_width)
            return keoAngleSlice(positions, intensities, self.__calib_factor)
        else:
            raise TypeError, ("Position must be either a number (angle) or a "
                              "datetime object")

        
    ########################################################################### 
        
    def _getHorizontalStrip(self, angle, strip_width):
        #check that specified angle is within range of keogram
        if angle > self.__fov_angle[1] or angle < self.__fov_angle[0]:
            raise ValueError, "Angle is outside of range of keogram."
        
        if self.__mode == 'RGB':
            raise RuntimeError, "Operation not permitted for RGB keograms"
        
        #calculate pixel position of angle
        y_position = int(round(self.angle2pix(angle)))
        
        #work out max strip width we can use (cannot exceed dimensions of 
        #keogram)
        if y_position + int(-strip_width / 2) + 1 < 0: 
            min_pix = 0
        else:
            min_pix = y_position + int(-strip_width / 2) + 1
            
        if y_position + int(strip_width / 2) + 1 > self.__height - 1: 
            max_pix = self.__height - 1
        else:
            max_pix = y_position + int(strip_width / 2) + 1    
        
        #not RGB, only want a 2D array
        intensities = self.__data[:, min_pix:max_pix, 0] 
        
        #mask out zero intensities
        masked_intensities = numpy.ma.array(intensities, 
                                            mask=(intensities == 0)) 
        
        #compute mean and fill in zeros for missing intensities 
        mean_intensities = masked_intensities.mean(axis=1).filled(0)                
        
        #calculate times associated with intensities
        p2t = _generate_pix2time_converter(self.__start_time, self.__end_time, 
                                           self.__width, self.__strip_width)
        times = [p2t(x) for x in range(self.__width)]
                    
        return (times, mean_intensities.tolist())
        
        
    ########################################################################### 
        
    def _getVerticalStrip(self, time, strip_width):                                 
        #check that specified time is within range of keogram
        if time > self.pix2time(self.__width -1) or time < self.pix2time(0):
            raise ValueError, "Time is outside of range of keogram."
        
        if self.__mode == 'RGB':
            raise RuntimeError, "Operation not permitted for RGB keograms"
                    
        #calculate pixel position of time
        x_position = int(round(self.time2pix(time)))
        
        #work out max strip width we can use (cannot exceed dimensions of 
        #keogram)
        if x_position + int(-strip_width / 2) + 1 < 0: 
            min_pix = 0
        else:
            min_pix = x_position + int(-strip_width / 2) + 1
            
        if x_position + int(strip_width / 2) + 1 > self.__width: 
            max_pix = self.__width
        else:
            max_pix = x_position + int(strip_width / 2) + 1    
        
        # not RGB, so only want a 2D array
        intensities = self.__data[min_pix:max_pix, :, 0] 
        
        #mask out zero intensities
        masked_intensities = numpy.ma.array(intensities, mask=(intensities == 0))
        
        #compute mean and fill in zeros for missing intensities                
        mean_intensities = masked_intensities.mean(axis=0).filled(0) 
                
        #calculate list of angles (corresponding to pixels in vertical 
        #strip of keogram)
        p2a = _generate_pix2angle_converter(self.__height, self.__fov_angle, 
                                            self.__lens_projection)
        
        angles = [p2a(x) for x in range(self.__height)]
        
        return (angles, mean_intensities.tolist())
        

    ########################################################################### 
        
    def histogram(self):
        """
        Returns a histogram of the keogram image. For 'L' mode images this will
        be a list of length 256, for 'I' mode images it will be a list of 
        length 65536. The histogram method cannot be used for RGB images.
        """        
        if self.__mode == "L":
            histogram = numpy.histogram(self.__data, bins=range(257))[0]
        elif self.__mode == "I":          
            histogram = numpy.histogram(self.__data, bins=range(65537))[0]
            
        else:
            raise ValueError, "Unsupported image mode"
        
        return histogram
    

    ########################################################################### 
        
    def medianFilter(self, n):
        """
        This is a thin wrapper function for the median filter provided by PIL. 
        It replaces each pixel in the keogram image by the median value of the 
        pixels in an nxn square around it (where n is an integer).
        """
        #the filter size must be odd
        if n % 2 == 0:
            warnings.warn("Filter size must be odd. Using n = " + str(n + 1) +
                           " instead")
            n = n + 1
        
        #convert array data to image object
        image = Image.fromarray(self.__data)
        
        #apply the filter
        image = image.filter(ImageFilter.MedianFilter(n))
        
        #convert back to an array
        filtered_arr = numpy.asarray(image)
        
            
        #create new keogram object
        return keogram(filtered_arr, self.__colour_table, 
                              self.__start_time, self.__end_time, 
                              self.__angle, self.__fov_angle, 
                              self.__strip_width, self.__keo_type, 
                              self.__data_points, self.__data_spacing, 
                              self.__calib_factor, self.__lens_projection)    
            

    ########################################################################### 
        
    def pix2angle(self, pixel):
        """
        Converts a vertical pixel coordinate into an angle in degrees. If the 
        pixel coordinate is outside of the range of the keogram None is 
        returned. This is the inverse operation of angle2pix().
        """        
        if pixel < 0 or pixel > self.__height - 1:
            return None
        
        converter = _generate_pix2angle_converter(self.__height, 
                                                  self.__fov_angle, 
                                                  self.__lens_projection)        
        return converter(pixel)
    

    ########################################################################### 
            
    def pix2time(self, pixel):
        """
        Converts a horizontal pixel coordinate into a datetime object. If the 
        pixel coordinate is outside of the range of the keogram
        None is returned. This is the inverse operation of time2pix().
        """
        if pixel < 0 or pixel > self.__width - 1:
            return None
        
        converter = _generate_pix2time_converter(self.__start_time, 
                                                 self.__end_time, self.__width,
                                                 self.__strip_width)
        return converter(pixel)
        

    ########################################################################### 
        
    def _hasColourBar(self):
        """
        Returns true if the keogram has a colour table applied, false 
        otherwise. This method is required for compatibility with the 
        allskyPlot module.
        """
        if self.__colour_table is not None:
            return True
        else:
            return False
            

    ########################################################################### 
        
    def _plot(self, subplot):
        """
        Plots the keogram data into the given subplot object. This method is 
        required for compatibility with the allskyPlot module.
        """
        image = self.getImage()
        
        #plot keogram image,matplotlib doesn't support 16bit images, so if the 
        #image is not RGB, then need to check that it is 8bit
        if image.mode == 'RGB' or image.mode == 'L':
            image = subplot.imshow(image, origin="top", aspect="auto")
        else:
            image = subplot.imshow(image.convert('L'), origin="top", 
                                   aspect="auto", cmap=matplotlib.cm.gray)       
        
    
        if self.__colour_table is not None:
            allskyPlot.createColourbar(subplot, 
                                       self.__colour_table.colour_table, 
                                       self.__calib_factor)
         
        #create tick marks for the y-axis every 20 degrees
        y_ticks = [] #tick positions (in pixels)
        y_labels = [] 
        for y in range(0, 180, 20):
            y_ticks.append(self.angle2pix(y))
            y_labels.append(str(int(math.fabs(y - 180))))
        
        subplot.yaxis.set_major_locator(FixedLocator(y_ticks))
        subplot.yaxis.set_major_formatter(FixedFormatter(y_labels))
               
        #create tick marks for the x-axis
        x_ticks = [] #tick positions (in pixels)
        x_labels = []
        current_time = self.__start_time.replace(minute=0, second=0, 
                                                 microsecond=0)
        while current_time <= self.__end_time:
            pix = self.time2pix(current_time)
            if pix is not None: #skip times outside the range of the keogram
                x_ticks.append(pix)
                x_labels.append(current_time.strftime("%H:%M"))
            
            if self.time_label_spacing is not None:
                current_time += datetime.timedelta(minutes=self.time_label_spacing) 
                
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
            start_time_string = self.__start_time.ctime()
            end_time_string = self.__end_time.ctime()
            keo_title = start_time_string + " - " + end_time_string
        else:
            keo_title = self.title
        
        #add title
        if keo_title != None:
            subplot.set_title(keo_title)
        
        #return a subplot object
        return subplot


    ########################################################################### 
            
    def roll(self, file_list):
        """
        This method is designed to be used for producing real-time keograms. 
        The file_list argument should be either a list of tuples 
        (filename,site_info_file) of images and their corresponding 
        site_info_files (can be None), or a list of allskyImage objects, which
        you want to be included in the current keogram. The total time span of 
        the keogram will remain unchanged, but the keogram will be shifted to 
        include the new images. For example, if you have created a keogram 
        which spans from 11:00 to 12:00 and you then use roll() with the 
        filename of an image that was captured at 12:01, then the keogram that
        is returned will span from 11:01 to 12:01 and will include the data 
        from the new image.
        """
        
        #if file_list is empty or is none then return copy of self
        if file_list is None or len(file_list) == 0 :
            return copy.deepcopy(self)
        
        #initialise time limits to greatest extremes they could have
        latest_time = datetime.datetime.fromordinal(1)
        earliest_time = datetime.datetime.utcnow()
        
        #if the list is of file names then load the allskyImages
        images = []
        for item in file_list:
            if isinstance(item, allskyImage.allskyImage):                
                images.append(item)
            else:
                images.append(allskyImage.new(item[0], item[1]))
        
        #make sure the images are compatable with this keogram
        _checkImages(images, mode=self.__mode, 
                     colour_table=self.__colour_table, 
                     calib_factor=self.__calib_factor, 
                     lens_proj=self.__lens_projection)
               
        #find latest and earliest creation times in file list
        for im in images:            
            #read time data from image
            time_str = im.getInfo()['header']['Creation Time'].lstrip().rstrip()
            try:
                capture_time = datetime.datetime.strptime(time_str,
                                                          "%d %b %Y %H:%M:%S %Z")
            
            except ValueError:
                capture_time = datetime.datetime.strptime(time_str, 
                                                          "%d %b %Y %H:%M:%S")
            
            except KeyError:
                raise IOError, ("Cannot read creation time from image " + 
                                im.getFilename())
            
            #if it is later than the latest time then update latest time
            if capture_time > latest_time:
                latest_time = capture_time
                
            #if it is earlier than the earliest time then update earliest time
            if capture_time < earliest_time:
                earliest_time = capture_time
            
        #if earliest_time<start_time and latest_time>end_time then give up, 
        #which direction should the keogram be moved in?
        if latest_time > self.__end_time and earliest_time < self.__start_time:
            raise ValueError, ("File list time range exceeds keogram time "
                               "range, which way should the keogram be rolled?")
        
        #if all the capture times are within the existing range of the keogram,
        #then no roll is needed
        if (latest_time <= self.__end_time and 
            earliest_time >= self.__start_time):
            time_roll = datetime.timedelta(seconds=0)
            int_pix_roll = 0
            pix_roll = 0.0
        
        buffer = (self.__strip_width // 2)
        
        if latest_time > self.__end_time:
            #keogram needs to be rolled forwards in time             
            #work out time roll
            time_roll = latest_time - self.__end_time
            
            #find out how many pixels to roll keogram by
            pix_roll = self.time2pix(self.__start_time + time_roll)
            
            if pix_roll is None:
                #if pix_roll is bigger than the keogram itself, 
                #then just blank the whole keogram
                int_pix_roll = self.__width
            else:  
                int_pix_roll = int(round(pix_roll - buffer)) 
        
        elif earliest_time < self.__start_time: 
            #keogram needs to be rolled backwards in time    
            #work out time roll
            time_roll = earliest_time - self.__start_time

            #find out how many pixels to roll keogram by
            pix_roll = -self.time2pix(self.__start_time - time_roll)
            if pix_roll is None:
                #if pix_roll is bigger than the keogram itself, then just blank
                # the whole keogram
                int_pix_roll = -self.__width
            else:  
                int_pix_roll = int(round(pix_roll + buffer)) 

        #modify start and end times
        end_time = time_roll + self.__end_time
        start_time = time_roll + self.__start_time
        
        #update entries in data_points. Remove any points which are no longer 
        #in the keogram
        new_data_points = []
        to_rolled_pix = _generate_time2pix_converter(start_time, end_time, 
                                                     self.__width, 
                                                     self.__strip_width)
        for t in self.getDataTimes():
            if (t < start_time) or (t > end_time):
                continue
            else:
                new_data_points.append(to_rolled_pix(t))        
            
        #create an array to hold the rolled keogram data
        rolled_array = numpy.zeros(self.__data.shape, dtype=self.__data.dtype)
        
        #copy the relevant data from the old keogram into the rolled keogram
        if int_pix_roll >= 0:
            rolled_array[0:self.__width - int_pix_roll,
                          :, :] = self.__data[int_pix_roll:, :, :]
        else:
            rolled_array[-int_pix_roll:,
                          :, :] = self.__data[:self.__width + int_pix_roll, :, :]
        
        #put data into keogram
        for im in images:
            new_data_points.append(_putData(im, rolled_array, 
                                            self.__strip_width, 
                                            self.__angle, self.__fov_angle, 
                                            start_time, end_time, 
                                            keo_type=self.__keo_type))
        
        if self.__data_spacing == "AUTO":
            p2t = _generate_pix2time_converter(start_time, end_time, 
                                               self.__width, self.__strip_width)
            data_spacing_secs = _estimate_data_spacing([p2t(x) for x in new_data_points])[1]
            data_spacing = (to_rolled_pix(start_time + 
                                         datetime.timedelta(seconds=data_spacing_secs)) - 
                                         to_rolled_pix(start_time))
        else:
            data_spacing = (to_rolled_pix(start_time + 
                                         datetime.timedelta(seconds=self.__data_spacing)) - 
                                         to_rolled_pix(start_time))
        
        #interpolate the data
        int_new_data_points = [int(round(x)) for x in new_data_points]
        if self.__keo_type == "CopyPaste":
            rolled_array = _interpolateData(int_new_data_points, rolled_array, 
                                            self.__mode, self.__colour_table, 
                                            self.__strip_width, 
                                            int(1.5 * (data_spacing)))
        elif self.__keo_type == "Average":
            rolled_array = _interpolateData(int_new_data_points, rolled_array,
                                             self.__mode, self.__colour_table, 
                                             1, int(1.5 * (data_spacing + 5))) #+5 is effective strip width used when calculating keogram width
        
        #create new keogram object                           
        return keogram(rolled_array, self.__colour_table, start_time, 
                              end_time, self.__angle, self.__fov_angle, 
                              self.__strip_width, self.__keo_type, 
                              new_data_points, self.__data_spacing, 
                              self.__calib_factor, self.__lens_projection)
            

    ########################################################################### 
        
    def save(self, filename):
        """
        Saves keogram object in specified file. It can be retrieved later 
        using the load() function.
        """
        
        #create dictionary to store keogram attributes
        header = {}
        
        #populate dictionary
        header['angle'] = str(self.__angle)
        header['start_time'] = str(self.__start_time.strftime("%d %b %Y %H:%M:%S"))
        header['end_time'] = str(self.__end_time.strftime("%d %b %Y %H:%M:%S"))
        header['strip_width'] = str(self.__strip_width)
        header['fov_angle'] = str(self.__fov_angle)
        header['keo_type'] = self.__keo_type
        header['data_points'] = str(self.__data_points)
        header['data_spacing'] = str(self.__data_spacing)
        header['calib_factor'] = str(self.__calib_factor)
        header['lens_projection'] = self.__lens_projection
        
        if self.__colour_table is not None:
            header['colour_table'] = str(self.__colour_table.colour_table)
        else:
            header['colour_table'] = str(None)
        
        
        #convert array to image
        image = self.getImage()
        
        #save header data in image header
        image.info = header
            
        #save image as png file
        misc.pngsave(image, filename)

       

    ########################################################################### 
                
    def time2pix(self, time):
        """
        Converts a datetime object into a horizontal pixel coordinate. If 
        the time is outside of the range of the keogram None is returned. This 
        is the inverse operation of pix2time().
        """
        if time < self.pix2time(0) or time > self.pix2time(self.__width - 1):
            return None
        
        converter = _generate_time2pix_converter(self.__start_time, 
                                                 self.__end_time, self.__width,
                                                 self.__strip_width)
        return converter(time)
        

    ########################################################################### 
        
    def zoomFov(self, fov):
        """
        Returns a keogram object spanning the field of view range specified.
        The fov argument should be a tuple (min angle, max angle). The angle
        range must be within the range of the current keogram or ValueError is
        raised. All angles are in degrees.
        """
        #check fov arg is tuple
        if type(fov) is not tuple:
            raise TypeError, ("field of view argument must be a tuple (min fov"
                              ", max fov)")
        
        #check that the range is sensible
        if fov[0] >= fov[1]:
            raise ValueError, ("Lower field of view angle bound must be smaller"
                               " than upper bound.")
        
        #check the range is within the range of the keogram
        if fov[0] < self.__fov_angle[0] or fov[1] > self.__fov_angle[1]:
            raise ValueError, ("Field of view specified is larger than the "
                               "field of view of the keogram.")
        
        #work out slice indicies
        a2p = _generate_angle2pix_converter(self.__height, self.__fov_angle, 
                                            self.__lens_projection)
        lower = int(round(a2p(fov[0])))
        upper = int(round(a2p(fov[1])))
        cropped_arr = self.__data[:, lower:upper + 1, :]
        
        return keogram(cropped_arr, self.__colour_table, self.__start_time, 
                       self.__end_time, self.__angle, fov, self.__strip_width, 
                       self.__keo_type, self.__data_points, 
                       self.__data_spacing, self.__calib_factor, 
                       self.__lens_projection)
        

    ########################################################################### 
        
    def zoomTime(self, start_time, end_time):
        """
        Returns a keogram object spanning the time between start_time and 
        end_time. Both arguments should be datetime objects. If both
        start_time and end_time are outside the range of the current keogram 
        then ValueError is raised. If just one is outside of the
        time range then this part of the new keogram will be blank.
        """
        #check that zoom range includes some of the keogram
        if start_time > self.__end_time or end_time < self.__start_time:
            raise ValueError, "Zoom range is outside of keogram range."
        
        #convert times to pixel coordinates
        start_pix = self.time2pix(start_time)
        end_pix = self.time2pix(end_time)
        
        buffer = self.__strip_width // 2
        
        #if part of the zoom range is outside of the current keogram, then 
        #change the zoom range to fit
        if end_pix == None:
            end_pix = self.__width - buffer
            end_time = self.__end_time
        if start_pix == None:
            start_pix = 0 + buffer
            start_time = self.__start_time
        
        #update entries in data_points. Remove any points which are no longer 
        #in the keogram
        new_data_points = []
        to_zoomed_pix = _generate_time2pix_converter(start_time, end_time, 
                                                     int(round(end_pix)) - 
                                                     int(round(start_pix)) + 
                                                     self.__strip_width, 
                                                     self.__strip_width)
        times = self.getDataTimes()
        for t in times:
            if (t < start_time) or (t > end_time):
                continue
            else:
                new_data_points.append(to_zoomed_pix(t))
        
        #round pixel coordinates to exact pixels
        start_pix = int(round(start_pix))
        end_pix = int(round(end_pix))
             
        #get section of keogram data array
        data_sec = self.__data[start_pix - buffer:end_pix + buffer + 1,
                                :, :] #+1 to include data at end pix coordinate
                
        #return zoomed in keogram
        return keogram(data_sec, self.__colour_table, start_time, 
                       end_time, self.__angle, self.__fov_angle, 
                       self.__strip_width, self.__keo_type, 
                       new_data_points, self.__data_spacing, 
                       self.__calib_factor, self.__lens_projection)
       
       
    ###########################################################################       
###############################################################################                                
                                                                
