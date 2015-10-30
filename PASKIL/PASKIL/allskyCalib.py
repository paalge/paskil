# Copyright (C) Nial Peters 2009
#
# This file is part of PASKIL.
#
# PASKIL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# PASKIL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PASKIL.  If not, see <http://www.gnu.org/licenses/>.
"""
Introduction:

    The allskyCalib module provides functions and classes for applying flat field corrections to all-sky 
    images. The sensitivity of a camera CCD is dependant on the incident angle of the incoming photon. As a
    result, when using a wide field of view (such as a fish eye lens), the edges of the field of view will 
    tend to be darker than the center. Applying a flat field correction helps to negate this effect.
    
    
    
Concepts:

    There are two approaches to calibration. The first uses an absolute calibration, converting the intensity
    recorded by the CCD into Rayleighs and correcting for spatial/angular differences in sensitivity. This 
    requires data collected in a calibration lab. PASKIL allows such a calibration to be performed using the 
    fromFile() function to read in the calibration data. The second method does not require any calibration 
    data to be recoreded in a lab. It works by finding images recorded by the camera where the sky was 
    approximately evenly lit. By looking at the angular dependance of the intensity in such an image, an 
    estimate of the flat field calibration can be made. This method has two main stages; finding evenly lit 
    images and calculating the angluar dependance of the intensity.
    
    The first stage is achieved by looking for images which have a small variance in intensity. PASKIL provides
    the calculateVariances() function for this purpose. Having plotted the variances of your data set, you 
    should look for time periods of low variance and create a new data set containing only these images. This
    data set can then be analysed image by image and the angular dependance of CCD sensitivity estimated using 
    the fromImages() function.

Example:

    In the following example a set of images in a directory called "calibration images" are used to produce 
    the flat field calibration data. This is then applied to the image "test.png". The images in 
    "calibration images" would have been chosen by using variance.plot() and finding a time period with a 
    low variance.


        from PASKIL import allskyImage,allskyCalib,allskyData #import the modules
        
        #create dataset object containing the calibration images
        calibration_dataset = allskyData.new("calibration images","630",["png"],site_info_file="site_info.txt") 
        
        calibration = allskyCalib.fromImages(calibration_dataset) #create calibration object
        
        image = allskyImage.new("test.png",site_info_file="site_info.txt") #create allskyImage object
        image = image.flatFieldCorrection(calibration) #apply flat field correction
        image.save("test_out.png") #save corrected image
    
"""

##########################################################################

from PIL import Image  # imports from PIL
import stats
import misc  # imports from PASKIL
import datetime
import calendar  # imports from other python modules
from pylab import figure, title, xlabel, ylabel, plot
# Functions

##########################################################################


def calculateVariances(dataset):
    """
    Calculates the mean and variance of pixel values in all images in the specified dataset (where dataset 
    is a dataset object) and returns a variance object. 
    """
    data = []

    for infile, site_info_file in dataset.getAll():

        im = Image.open(infile)
        var, mean = stats.variance_mean(im.getdata())
        time = datetime.datetime.strptime(
            im.info['Creation Time'], "%d %b %Y %H:%M:%S %Z")
        data.append((time, var, mean))

    # sort list into chronological order
    data.sort(misc.tupleCompare)
    return variance(data)  # return variance object

##########################################################################


def fromFile(filename):
    """
    Returns a calibration object created from calibration data stored in a text file. The text file should 
    have two columns of numbers. The first should be the angle (integers running from 0-90 with a step size 
    of 1). The second should be the normalised flat field intensity at this angle (<=1). These angles are 
    degrees from vertical e.g. the first entry in the list is the correction factor for the centre of the 
    image, 0 degrees from vertical.These angles should not be confused with the angles from horizontal or 
    angles from North used elsewhere in the code.
    """
# loads the calibration data from a file and returns a calibration object
    raw_data = []
    calibration_data = []
    data_file = open(filename)

    for line in data_file:
        raw_data.append(
            (float(line.split()[0].strip()), float(line.split()[1].strip())))

    # sort raw data into angle order
    raw_data.sort(misc.tupleCompare)

    for i in range(len(raw_data)):
        if raw_data[i][0] != float(i):
            raise ValueError(
                "Calibration data in file must be specified at an angular resolution of 1 degree, starting from 0 degrees")

        calibration_data.append(raw_data[i][1])

    return calibration(calibration_data)

##########################################################################


def fromImages(dataset):
    """
    Returns a calibration object created by finding the median intensities at different angles from vertical
    of a set of "flat field images" stored in the specified dataset object. These are images in which the
    sky is approximately evenly lit. These images should be chosen by looking for time periods with a low 
    variance using the variance class. For each image in the dataset, this function takes slices through 
    the center of the image between 0-359 degrees from North at 1 degree resolution. It then records the 
    values of the intensities at angles 0-90 from the center. When this has been done for all images the 
    median values of intensity for each angle from the centre are calculated. These are then normalised.
    """

# Using the images in the time period found using the above functions, this function takes slices through the
# centre of the image at 1 degree resolution. It then records the values of the intensities at angles 0-fov_angle from
# the centre. When this has been done for all images the median values of intensity for each angle from the centre are
# calculated. These are then normalised.
    _sum = [0] * 91
    count = [0] * 91
    results = []

    for image in dataset:

        # Apply binary mask to all images at 90 degree field of view
        image = image.binaryMask(90)

        image = image.centerImage()

        x_center = image.getInfo()['camera']['x_center']

        for angle in range(180):
            # take a vertical slice of the image 1 pixel wide
            strip = image.getStrip(angle, 1)[0]

            for y in range(len(strip)):
                angle_from_zenith = int(image.xy2angle(x_center, y) + 0.5)
                _sum[angle_from_zenith] += strip[y]
                count[angle_from_zenith] += 1

    # find mean values of calibration factors at different angles
    for angle in range(91):
        ff_factor = (_sum[angle] / float(count[angle])) / \
            (_sum[0] / float(count[0]))
        results.append(ff_factor)

    return calibration(results)  # return calibration object

##########################################################################


def loadVariances(filename):
    """
    Loads variance data from a text file and returns a variance object. The text file should have three 
    columns: time, variance,mean. Where time is the number of days since the epoch (a float).
    """
# loads the variance data from a file and returns a variances object
    variances = []
    data_file = open(filename)

    for line in data_file:
        data_point = line.split()[0].strip(), float(
            line.split()[1].strip()), float(line.split()[2].strip())
        variances.append(data_point[1])

    return variance(variances)

##########################################################################

# Class definitions


class calibration:
    """
    Container class for flat field calibration data.
    """

    def __init__(self, calibration_data):
        self.calibration_data = calibration_data

    ##########################################################################

    def plot(self):
        """
        Returns a matplotlib figure object (see matplotlib webpage) containing a plot of the calibration
        data stored in the calibration object, angle from vertical against normalised flat field 
        intensity.
        """
        figure(1)
        title("Normalised flat field intensity against angle from zenith")
        plot(range(len(self.calibration_data)), self.calibration_data)
        xlabel("Angle (degrees)")
        ylabel("Normalised Flat Field Intensity")

        return figure(1)

    ##########################################################################

    def save(self, filename):
        """
        Saves the calibration data as a text file. This can be loaded using the fromFile function, 
        meaning that calibration data should only need to be calculated once.
        """
        # function writes calibration data to file for later processing.
        f = open(filename, "w")

        for i in range(len(self.calibration_data)):
            f.write(str(i) + "  " + str(self.calibration_data[i]) + "\n")

        f.close()

    ##########################################################################
##########################################################################


class variance:
    """
    Container class for variance data
    """

    def __init__(self, variances):
        self.variances = variances

    ##########################################################################

    def save(self, filename):
        """
        Saves the variance data as a text file. This can be loaded using the loadVariances() function, 
        meaning that variance data should only need to be calculated once.
        """
        f = open(filename, "w")

        for i in range(len(self.variances)):
            f.write(str(calendar.timegm(self.variances[i][0].timetuple())) + "  " + str(
                self.variances[i][1]) + "  " + str(self.variances[i][2]) + "\n")  # write: time,variance,mean

        f.close()

    ##########################################################################
##########################################################################
