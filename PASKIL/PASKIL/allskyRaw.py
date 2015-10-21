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
The allskyRaw module is designed to allow decoding and manipulation of raw image files.
It is largely incomplete and still needs a lot of work before it is fully functional.
However, it can be used to load raw images and extract single colour channels from them.
"""

import datetime

import numpy
from PIL import Image, ImageChops

import allskyImage
from PASKIL.extensions import cRaw

##########################################################################


def isRaw(filename):
    """
    Returns True if the file is a raw image file that can be decoded by the allskyRaw module,
    False otherwise.
    """
    fp = open(filename, "rb")

    if cRaw.canDecode(fp):
        fp.close()
        return True
    else:
        fp.close()
        return False

##########################################################################


def getTimeStamp(filename):
    """
    Returns a datetime object containing the capture time (as recorded by the camera) of the raw image specified by
    the filename argument.
    """
    # open file for reading (binary)
    fp = open(filename, "rb")

    # get timestamp from raw image
    timestamp = cRaw.getTimestamp(fp)

    # close the file
    fp.close()

    # convert the timestamp to a datetime object
    time = datetime.datetime.fromtimestamp(timestamp)

    # return the answer
    return time

##########################################################################


def getRawData(filename):
    """
    Returns a tuple of length four, containing PIL image objects of the raw image data. Each image corresponds to 
    a single channel in the raw image, typically (R,G,B,G).
    """
    # open file for reading (binary)
    fp = open(filename, "rb")

    # get the raw pixel data from the image
    (raw_data, width, height) = cRaw.getRawData(fp)

    # close the file
    fp.close()

    # split the array into 4 arrays (one for each color) and convert the data
    # into Int32
    red_data = numpy.array(raw_data[:, 0], dtype="int32")
    red_data.shape = (height, width)

    green1_data = numpy.array(raw_data[:, 1], dtype="int32")
    green1_data.shape = (height, width)

    blue_data = numpy.array(raw_data[:, 2], dtype="int32")
    blue_data.shape = (height, width)

    green2_data = numpy.array(raw_data[:, 3], dtype="int32")
    green2_data.shape = (height, width,)

    # convert the raw data array back into an image
    image1 = Image.fromarray(red_data)
    image2 = Image.fromarray(green1_data)
    image3 = Image.fromarray(blue_data)
    image4 = Image.fromarray(green2_data)

    return (image1, image2, image3, image4)

##########################################################################


def new(filename, site_info_file):

    # load image data
    (ch1, ch2, ch3, ch4) = getRawData(filename)

    # open site info file
    info_file = open(site_info_file, 'r')
    camera = {}

    # read in data from site info file and store in info dictionary
    for line in info_file:  # read file line by line
        if line.isspace():
            continue  # ignore blank lines
        words = line.split("=")  # split the line at the = sign

        if len(words) != 2:
            raise ValueError, "Cannot read site info file, too many words per line"

        # store the values (minus white space) in a dictionary
        camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip()

    creation_time = getTimeStamp(filename)

    creation_time = creation_time.strftime("%d %b %Y %H:%M:%S %Z")
    header = {'Wavelength': "RGBG", 'Creation Time': creation_time}

    info = {'header': header, 'camera': camera, 'processing': {}}

    return rawImage((ch1, ch2, ch3, ch4), filename, info)

##########################################################################


class rawImage(allskyImage.allskyImage):
    """
    Holds the separate channels of a raw image file. This class is less than half written! You
    should only use the getChannel method for now.
    """

    def __init__(self, filename, info, channels=None):

        # set private class attributes
        self.__channels = []

        if channels is not None:
            for ch in channels:
                self.__channels.append(ch)

        if channels is None:
            self.__loaded = False
        else:
            self.__loaded = True

        # create dummy image object to pass to
        # allskyImage.allskyImage.__init__()
        dummy_image = Image.new("1", (0, 0))

        allskyImage.allskyImage.__init__(self, dummy_image, filename, info)

    ##########################################################################

    def getImage(self):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        return self.convertToRGB().getImage()

    ##########################################################################

    def getStrip(self, angle, strip_width, channel=None):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        if channel == None:
            rgb_image = self.convertToRGB()

            return rgb_image.getStrip(angle, strip_width)

        channel = self.getChannel(channel)
        return channel.getStrip(angle, strip_width)

    ##########################################################################

    def applyColourTable(self, colour_table):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        raise TypeError, "Cannot apply a colour table to a raw image. Apply it to the separate channels"

    ##########################################################################

    def convertToRGB(self):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        self.load()

        mean_green = ImageChops.add(
            self.__channels[1], self.__channels[3], 0.5)

        # rescale values (currently have 16bit data stored in 32bit integers)
        scale = 4294967295.0 / 65535.0

        #offset = - min_intensity * scale     .point(lambda i: i * scale + 0)

        # might need to convert each channel to mode "L" before trying to merge
        # them to RGB
        rgb_image = Image.merge("RGB", (self.__channels[0].point(
            lambda i: i * scale + 0), mean_green.point(lambda i: i * scale + 0), self.__channels[2].point(lambda i: i * scale + 0)))

        new_info = self.getInfo()

        new_info['header']['Wavelength'] = "RGB"

        return allskyImage.allskyImage(rgb_image, self.getFilename, new_info)

    ##########################################################################

    def addTimeStamp(self, format, colour="black", fontsize=20):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        return self.__runMethod(allskyImage.allskyImage.addTimeStamp, format, colour=colour, fontsize=fontsize)

    ##########################################################################

    def __runMethod(self, method, *args, **kwargs):
        self.load()
        new_channels = []

        info_bkup = str(self.getInfo())

        for self._allskyImage__image in self.__channels:
            self._allskyImage__info = eval(info_bkup)
            new_ASI = method(self, *args, **kwargs)

            new_channels.append(new_ASI.getImage())

        return rawImage(self.getFilename(), new_ASI.getInfo(), channels=new_channels)

    ##########################################################################
    def alignNorth(self, north="geographic"):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        return self.__runMethod(allskyImage.allskyImage.alignNorth, north=north)

    ##########################################################################

    def binaryMask(self, fov_angle, inverted=False):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        return self.__runMethod(allskyImage.allskyImage.binaryMask, fov_angle, inverted=inverted)

    ##########################################################################

    def centerImage(self):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        return self.__runMethod(allskyImage.allskyImage.centerImage)

    ##########################################################################

    def convertTo8bit(self):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        return self.__runMethod(allskyImage.allskyImage.convertTo8bit)

    ##########################################################################

    def createQuicklook(self, size=(480, 640), timestamp="%a %b %d %Y, %H:%M:%S %Z", fontsize=16):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        rgb_image = self.convertToRGB()

        return rgb_image.createQuicklook(size=size, timestamp=timestamp, fontsize=fontsize)

    ##########################################################################

    def flatFieldCorrection(self, calibration):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        return self.__runMethod(allskyImage.allskyImage.flatFieldCorrection, calibration)

    ##########################################################################

    def medianFilter(self, n, separate_channels=False):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"
        if not separate_channels:
            rgb_image = self.convertToRGB()
            return rgb_image.medianFilter(n)
        else:
            return self.__runMethod(allskyImage.allskyImage.medianFilter, n)

    ##########################################################################

    def projectToHeight(self, height, grid_size=300, background='black', channel=None):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        if channel == None:
            rgb_image = self.convertToRGB()
            return rgb_image.projectToHeight(height, grid_size=grid_size, background=background)

        return self.getChannel(channel).projectToHeight(height, grid_size=grid_size, background=background)

    ##########################################################################

    def resize(self, size):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

        self.__runMethod(allskyImage.allskyImage.resize, size)

    ##########################################################################

    def load(self):
        if not self.__loaded:

            images = getRawData(self.getFilename())

            for image in images:
                self.__channels.append(image.copy())

            for channel in self.__channels:
                channel.info = {}

            self.__loaded = True

    ##########################################################################

    def getChannel(self, channel):
        """
        Returns an allskyImage object containing the image data of the specified raw channel.
        """

        self.load()

        if channel > len(self.__channels) - 1:
            raise ValueError, "Selected channel does not exist."

        new_info = self.getInfo()

        if channel == 0:
            new_info['header']['Wavelength'] = 'Red'
        elif channel == 1:
            new_info['header']['Wavelength'] = 'Green1'
        elif channel == 2:
            new_info['header']['Wavelength'] = 'Blue'
        elif channel == 3:
            new_info['header']['Wavelength'] = 'Green2'
        else:
            raise ValueError, "Unknown channel selection"

        return allskyImage.allskyImage(self.__channels[channel], self.getFilename(), new_info)

    ##########################################################################

    ##########################################################################

    def save(self, filename):
        raise NotImplementedError, "The allskyRaw module is still under construction, and this method is not finished/debugged yet!"

     ##########################################################################
##########################################################################
