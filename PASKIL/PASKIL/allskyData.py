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

    The allskyData module provides a set of tools to simplify the use of large 
    data sets which may span across a complicated directory structure. It 
    provides an abstraction layer between the user and the locations of the 
    images to be used, allowing image access by time rather than filename.
    
    
Concepts:
    
    The allskyData module contains a dataset class. This is essentially five 
    ordered lists. One of filenames, one of times, one of filenames for site
    information files, one of radii and one of fields of view. A dataset object
    is created by indexing the images in a directory structure. A dataset can 
    only contain images of the same Wavelength and mode (see PIL handbook for 
    description of mode). However, datasets containing different image file 
    formats are possible. Once created, a dataset object allows images to 
    be retrieved by their creation time rather than their filename.
    
    The dataset class can also be used to simplify loading images with
    different site info files. A separate dataset object can be constructed
    for each set of images with a particular site info file. These can then
    be joined together into a single dataset using the combine() function. The
    result is a dataset that can be used to access any of the images, without
    the user having to worry about which info file belongs to which image.

    For very large datasets, the indexing process can take some time. There is
    therefore the option to save the dataset object once it is created. This 
    allows the same dataset to be loaded rapidly in the future. However, no 
    checks are made to ensure that the dataset object still matches the actual 
    data (although if image files contained in the dataset are deleted or 
    renamed, then an exception will be raised when the dataset is reloaded).
    
    The images in a dataset can be iterated over using standard Python syntax
    (see example below).
    

Example:
    
    The following example creates a dataset of all the png and jpg files in the
    directory "Allsky Images". The recursive option is not used, so subfolders 
    will not be included. Only images corresponding to a wavelength of 630nm 
    are included. A list of all the files between 18:30 and 19:30 on the 
    4/2/2003 is then printed to the screen. The iterator protocol is then used
    to apply a binary mask to all the images in the dataset.

        from PASKIL import allskyData
        import datetime

        #create dataset object
        dataset = allskyData.new("Allsky Images","630",["png","jpg"],
                                 site_info_file="site_info.txt") 
        
        #create datetime object defining start time for list
        start_time = datetime.datetime.strptime("04 Feb 2003 18:30:00 GMT",
                                                "%d %b %Y %H:%M:%S %Z")
        
        #create datetime object defining end time for list 
        end_time = datetime.datetime.strptime("04 Feb 2003 19:30:00 GMT",
                                              "%d %b %Y %H:%M:%S %Z") 
    
        #get names of files between start and end times (inclusive).
        filenames = dataset.getFilenamesInRange(start_time,end_time) 

        print filenames
        
        #alternatively we can use the iterator to process the images
        for im in dataset:
            im.binaryMask(75)
            im.save("masked-"+im.getFilename())
        
"""

###############################################################################
from __future__ import with_statement
import glob
import datetime
import cPickle
import os
import os.path

from PASKIL import allskyImage, allskyColour, misc

# Functions:

###############################################################################


def combine(datasets):
    """
    Returns a dataset object which is the combination of all the datasets in 
    the specified list. The datasets argument should be a list of dataset 
    objects. It is not possible to combine datasets with different wavelengths,
    image modes or colour tables. It is however, possible to combine datasets 
    with different filetypes and different site information files. Files which 
    appear in more than one of the datasets to be combined, will only appear 
    once in the new dataset.
    """
    colour_table = datasets[0].getColourTable()
    wavelength = datasets[0].getWavelength()
    mode = datasets[0].getMode()
    calib_factor = datasets[0].getCalib_factor()
    lens_proj = datasets[0].getLensProjection()

    for i in range(1, len(datasets)):
        # check if datasets can be combined
        if ((wavelength != datasets[i].getWavelength()) or
                (mode != datasets[i].getMode()) or
                (colour_table != datasets[i].getColourTable()) or
                (calib_factor != datasets[i].getCalib_factor()) or
                (lens_proj != datasets[i].getLensProjection())):

            raise ValueError("Incompatible datasets")

    # create tuple list from dataset data
    tuple_list = []
    filetypes = []

    for d in datasets:
        filetypes += d.getFiletypes()

        tuple_list += zip(d.getTimes(), d.getFilenames(),
                          d.getSite_info_files(), d._getRadiiList(),
                          d._getFov_anglesList())

    # sort the list into chronological order and remove duplicate entries
    tuple_list = list(set(tuple_list))
    tuple_list.sort(misc.tupleCompare)

    # remove duplicate entries from filetypes list
    filetypes = list(set(filetypes))

    return dataset(tuple_list, wavelength, filetypes, mode, colour_table,
                   calib_factor, lens_proj)

###############################################################################


def fromList(file_names, wavelength, filetype, site_info_file=None):
    """
    Creates a dataset from a list of filenames. The file_names argument should 
    be a list of strings specifying the filenames of the files to be included. 
    The wavelength argument should be a string that matches the value of the 
    'Wavelength' field in the image metadata see allskyImagePlugins module for 
    details. The site_info_file option should be the filename of the site 
    information file (if one is required). The filetype argument is a list of 
    filetypes (e.g. ["png","jpg"]), so a dataset spanning many filetypes can be 
    prodcued using this function (if only a single filetype is desired then it 
    must be specified as ["filetype"]). A dataset spanning images with 
    different site info files can only be produced by combining several 
    datasets with different site info files. Note that images in the list 
    supplied which do not conform to the dataset's parameters will be ignored. 
    If no images are found that can be added to the dataset then ValueError is
    raised.
    """
    data = []
    mode = None
    found_wavelengths = set([])  # set of wavelengths found during the search

    # check that filetypes argument is a list - this is a common user error!
    if type(filetype) is not list:
        raise TypeError("Filetype argument should be a list.")

    for filename in file_names:
        # check if file is of correct type
        if not filename.endswith(tuple(filetype)):
            continue  # if not then skip it

        # attempt to create an allskyImage object, if there is no plugin for it,
        # then skip this file
        try:
            current_image = allskyImage.new(filename, site_info_file)

        except TypeError:
            continue  # skip file if PASKIL cannot open it
        except IOError:
            continue  # skip file if PIL cannot decode the image

        # get the image info
        info = current_image.getInfo()

        # check if the image has the correct wavelength
        current_image_wavelength = info['header']['Wavelength']
        if current_image_wavelength.find(wavelength) == -1:
            found_wavelengths.add(current_image_wavelength)
            continue  # if image has wrong wavelength then skip it

        # check the image has the correct mode, calib factor and colour table
        try:
            current_colour_table = info['processing']['applyColourTable']
        except KeyError:
            current_colour_table = None

        try:
            current_calib_factor = info['processing']['absoluteCalibration']
        except KeyError:
            current_calib_factor = None

        current_lens_projection = info['camera']['lens_projection']

        if mode == None:
            mode = current_image.getMode()
            colour_table = current_colour_table
            calib_factor = current_calib_factor
            lens_projection = current_lens_projection

        if current_image.getMode() != mode:
            print("Warning! allskyData.fromList(): Skipping file " + filename +
                  ". Incorrect image mode.")
            continue

        if current_colour_table != colour_table:
            print("Warning! allskyData.fromList(): Skipping file " + filename +
                  ". Incorrect colour table.")
            continue

        if current_calib_factor != calib_factor:
            print("Warning! allskyData.fromList(): Skipping file " + filename +
                  ". Incorrect absolute calibration factor.")
            continue

        if current_lens_projection != lens_projection:
            print("Warning! allskyData.fromList(): Skipping file " + filename +
                  ". Incorrect lens projection.")
            continue
        # read creation time from header
        time_str = info['header']['Creation Time']

        # convert to datetime object
        try:
            time = datetime.datetime.strptime(time_str,
                                              "%d %b %Y %H:%M:%S %Z")
        except ValueError:
            time = datetime.datetime.strptime(time_str.rstrip() + " GMT",
                                              "%d %b %Y %H:%M:%S %Z")

        # store data associated with this image in the data list as a tuple
        data.append((time, filename, site_info_file,
                     float(info['camera']['Radius']),
                     float(info['camera']['fov_angle'])))

    # check to make sure the dataset is not empty
    if len(data) == 0:
        raise ValueError("No images were compatible with the dataset format,"
                         " ensure you have imported the required plugins,that the wavelength "
                         "string matches that in the image header, and that you have specified "
                         "any relevant site info files. Images with the following wavelengths "
                         "were found " + str(found_wavelengths))

    # sort the list into chronological order
    data.sort(misc.tupleCompare)

    # return a dataset object
    return dataset(data, wavelength, filetype, mode, colour_table,
                   calib_factor, lens_projection)


###############################################################################

def load(filename):
    """
    Loads a dataset object from a file. Dataset files can be produced using the
    save() method. Note that no checks are made to ensure that the images in 
    the loaded dataset still have the same properties that they had when 
    the dataset was first created. If the images have been modified in some way
    then this might lead to unexpected behavior.
    """
    with open(filename, "rb") as f:
        dataset = cPickle.load(f)

    # check that the all the files stored in the dataset still exist.
    for image_filename in dataset.getFilenames():
        if not os.path.exists(image_filename):
            raise IOError("allskyData.load(): The file \"" + image_filename +
                          "\" no longer exists. The dataset \"" +
                          filename + "\" is therefore"
                          " not valid!")

    return dataset

###############################################################################


def new(directory, wavelength, filetype, site_info_file=None, recursive=False):
    """
    Returns a dataset object containing images of type filetype, taken at a 
    wavelength of wavelength (needs to be the same value as in the image header
    under 'Wavelength' see allskyImagePlugins module for details), contained in 
    the specified directory. If recursive is set to True then all 
    subdirectories of "directory" will be searched, the default value is False 
    no recursive search. The site_info_file option should be the filename of 
    the site information file (if one is required). The filetype argument is a 
    list of filetypes (e.g. ["png","jpg"]), so a dataset spanning many 
    filetypes can be prodcued using this function (if only a single filetype is
    desired then it must be specified as ["filetype"]). A dataset spanning 
    images with different site info files can only be produced by combining 
    several datasets with different site info files. All arguments to this 
    function should be strings, including wavelength. All images in a dataset 
    must have the same mode, the same lens projection and the same colour 
    table. Note that images in the directory supplied which do not conform to 
    the dataset's parameters will be ignored.
    """

    search_list = []

    # check that filetypes argument is a list - this is a common user error!
    if type(filetype) != type(list()):
        raise TypeError("Incorrect type for filetype argument. "
                        "Expecting list.")

    # expand the paths of the directory and site info file
    directory = os.path.normpath(directory)

    # check that the site info file exists
    if site_info_file is not None:
        site_info_file = os.path.normpath(site_info_file)
        if not os.path.exists(site_info_file):
            raise IOError("Cannot find site information file " +
                          site_info_file)

    # check that the search directory exists
    if not os.path.isdir(directory):
        raise IOError("No directory called " + directory)

    for i in range(len(filetype)):
        if recursive:
            # sweep the directory structure recursively
            search_list = search_list + misc.findFiles(directory, "*." +
                                                       filetype[i].lstrip("."))

        else:
            # only look in current directory
            search_list = search_list + glob.glob(directory + os.sep + "*." +
                                                  filetype[i].lstrip("."))

    # check that some files with the specified extensions were found
    if len(search_list) == 0:
        raise ValueError("Unable to locate any files with extensions: " +
                         str(filetype))

    return fromList(search_list, wavelength, filetype, site_info_file)

###############################################################################

# class definition


class dataset:
    """
    The dataset class provides a layer of abstraction between the user and a
    set of all-sky images stored across (a possibly complex) directory 
    structure. It provides a convenient way to manipulate large numbers of 
    images, allowing access to images by capture time rather than filename.
    """

    def __init__(self, data, wavelength, filetypes, mode, colour_table,
                 calib_factor, lens_projection):

        # check that the filetype argument is of the correct type -
        # this is a common error to make
        if type(filetypes) != list:
            raise TypeError("Incorrect type, " + str(type(filetype)) +
                            " for filetype argument, expecting list")

        # constants for any given dataset
        self.__wavelength = wavelength
        self.__mode = mode
        self.__colour_table = colour_table
        self.__calib_factor = calib_factor
        self.__lens_projection = lens_projection

        # multiple values allowed for any given dataset
        self.__filetypes = list(set(filetypes))

        n = range(len(data))
        self.__times = [data[i][0] for i in n]
        self.__filenames = [data[i][1] for i in n]
        self.__site_info_files = [data[i][2] for i in n]
        self.__radii_list = [data[i][3] for i in n]
        self.__fov_angles_list = [data[i][4] for i in n]

        # the dataset methods assume that there are only unique filenames
        # in the list it is unlikely that there ever wouldn't be - but it
        # is possible (maybe?!)
        assert len(self.__filenames) == len(list(set(self.__filenames)))

        # it is also possible that multiple images with the same capture time
        # have been put in the dataset - this will lead to unpredictable
        # behavior so we don't allow it
        if len(self.__times) != len(list(set(self.__times))):
            raise ValueError("Datasets cannot contain different images with "
                             "the same capture time")

    ###########################################################################
    # define iterator method to allow datasets to support the iterator protocol

    def __iter__(self):

        return datasetIterator(self.getAll())

    ###########################################################################
    # define dataset comparison methods
    def __eq__(self, x):
        if not isinstance(x, dataset):
            return NotImplemented

        for k in self.__dict__.keys():
            if self.__dict__[k] != getattr(x, k):
                return False
        return True

    def __ne__(self, x):
        if not isinstance(x, dataset):
            return NotImplemented
        for k in self.__dict__.keys():
            if self.__dict__[k] != getattr(x, k):
                return True
        return False

    ###########################################################################

    def __t_range2indices(self, start_time, end_time):
        """
        Returns a (start_index, end_index) tuple referring to the indices
        in self.__times which span (inclusive of start and end indices) 
        the supplied time range. Note that if you use this to slice a list
        to include only times in the supplied range (inclusive), then you 
        need to use [start_index:end_index+1] to ensure you include the 
        end time.
        """
        l = len(self.__times)
        start_index = l
        end_index = 0
        index = 0
        while index < l:
            if self.__times[index] >= start_time:
                start_index = index
                break
            index += 1
        while index < l:
            if self.__times[index] == end_time:
                end_index = index
                break
            elif self.__times[index] > end_time:
                if index == 0:
                    index = 1
                end_index = index - 1
                break
            index += 1
        return (start_index, end_index)

    ###########################################################################
    # define getters
    def getCalib_factor(self):
        """
        Returns a float containing the absolute calibration factor (conversion 
        factor between pixel value and kR) for the images in the dataset. If no
        calibration has been applied to the images then None is returned.
        """
        return self.__calib_factor

    def getWavelength(self):
        """
        Returns a string containing the wavelength of the dataset. This will 
        have the same format as the 'Wavelength' field in the image metadata, 
        see the allskyImagePlugins module for details.
        """
        return self.__wavelength

    def getLensProjection(self):
        """
        Returns a string describing the lens projection of the images in the 
        dataset. Currently supported projections are "equidistant" and
        "equisolidangle"
        """
        return self.__lens_projection

    def getColourTable(self):
        """
        Returns an allskyColour.basicColourTable object of the colour table 
        that has been applied to the images in the dataset, or None.
        """
        if self.__colour_table is not None:
            ct = allskyColour.basicColourTable(self.__colour_table)
        else:
            ct = None

        return ct

    def getRadii(self):
        """
        Returns a set (only unique values) of the radii of the images in the 
        dataset in pixels.
        """
        return set(self.__radii_list)

    def getFov_angles(self):
        """
        Returns a set (only unique values) of field of view angles contained in
        the dataset.
        """
        return set(self.__fov_angles_list)

    def _getRadiiList(self):
        """
        Returns a list of the  radii corresponding to each image in the dataset
        in pixels.
        """
        return [x for x in self.__radii_list]

    def _getFov_anglesList(self):
        """
        Returns a list of field of view angles  corresponding to each image 
        contained in the dataset.
        """
        return [x for x in self.__fov_angles_list]

    def getMode(self):
        """
        Returns a string containing the mode of the images in the dataset, e.g.
        "RGB" see the PIL handbook for details about different image modes.
        """
        return self.__mode

    def getFiletypes(self):
        """
        Returns a list of strings of the filetypes allowed to be contained in 
        the dataset e.g. ["png","jpg"]. Note that this does not mean that the 
        dataset does contain files of all the types returned, just that it
        could.
        """
        return [x for x in self.__filetypes]

    def getFilenames(self):
        """
        Returns a list of strings containing the filenames of all the images 
        contained in the dataset. The list will be ordered chronologically with
        respect to the capture times of the images.
        """
        return [x for x in self.__filenames]

    def getNumImages(self):
        """
        Returns the number of images in the dataset.
        """
        return len(self.__filenames)

    def getTimes(self):
        """
        Returns a list of datetime objects corresponding to the capture times 
        of all the images in the dataset. The list will be ordered chronologically.
        """
        return [x for x in self.__times]

    def getSite_info_files(self):
        """
        Returns a list of strings containing the filenames of the 
        site_info_files corresponding to the images in the dataset. The list 
        will have one entry for each image in the dataset and will be ordered 
        chronologically with respect to the capture times of the images. If the
        images don't have site_info_files then a list of empty strings will be 
        returned.
        """
        return [x for x in self.__site_info_files]

    ###########################################################################

    def crop(self, start_time, end_time):
        """
        Returns a new dataset object which only spans the time range between 
        start_time and end_time (inclusive). Both arguments should be datetime 
        objects.
        """
        s, e = self.__t_range2indices(start_time, end_time)

        if s > e:
            raise ValueError("No image files in specified range")

        e += 1  # so that list slices include the image at index e

        # build list of tuples
        cropped_data = zip(self.__times[s:e], self.__filenames[s:e],
                           self.__site_info_files[s:e], self.__radii_list[s:e],
                           self.__fov_angles_list[s:e])

        return dataset(cropped_data, self.__wavelength, self.__filetypes,
                       self.__mode, self.__colour_table, self.__calib_factor,
                       self.__lens_projection)

    ###########################################################################

    def getAll(self):
        """
        Returns a list of tuples of strings containing the names of all the 
        files in the dataset and their corresponding site info files, 
        e.g. [(image1, site_info1), (image2, site_info2)...]
        """
        return zip(self.__filenames, self.__site_info_files)

    ###########################################################################

    def getFilenamesInRange(self, time1, time2):
        """
        Returns a list of tuples of strings containing the names of all the 
        files in the dataset that correspond to times between time1 and time2
        (inclusive) and their corresponding site info files, 
        e.g. [(image1, site_info1), (image2, site_info2)...]

        The list will be ordered in chronological order. The time arguments 
        should be datetime objects.
        """
        s, e = self.__t_range2indices(time1, time2)
        e += 1  # so that list slices include the image at index e

        return zip(self.__filenames[s:e], self.__site_info_files[s:e])

    ###########################################################################

    def getImage(self, time):
        """
        Returns an allskyImage object containing the image data for the 
        specified time. If no image exists for the specified time then None is
        returned. The time argument should be a datetime object.
        """
        try:
            index = self.__times.index(time)
        except ValueError:
            return None

        return allskyImage.new(self.__filenames[index],
                               self.__site_info_files[index])

    ###########################################################################

    def getImagesInRange(self, time1, time2):
        """
        Returns a list of allskyImage objects containing all the images that 
        correspond to times between time1 and time2 (inclusive). The list will 
        be ordered in chronological order. The time arguments should be 
        datetime objects. This function creates a new instance of the 
        allskyImage class for each image in the range. 
        """
        filenames = self.getFilenamesInRange(time1, time2)

        return [allskyImage.new(*x) for x in filenames]

    ###########################################################################

    def getNearest(self, time):
        """
        Returns an allskyImage object corresponding to the image in the dataset 
        which has a creation time closest to the specified time. The time 
        argument should be a datetime object. 
        """
        filename, site_info_filename = self.getNearestFilename(time)

        return allskyImage.new(filename, site_info_filename)

    ###########################################################################

    def getNearestFilename(self, time):
        """
        Returns a (filename, site_info_file) tuple corresponding to the image 
        in the dataset which has a creation time closest to the specified time.
        The time argument should be a datetime object. 
        """
        diff = [abs(t - time) for t in self.__times]
        index = diff.index(min(diff))

        return (self.__filenames[index], self.__site_info_files[index])

    ###########################################################################

    def save(self, filename):
        """
        Saves the dataset object in specified file. It can be retrieved at a 
        later date using the load() function. However, be aware that changing 
        the image files, the site information files or the directory structure
        of the images stored in a dataset after it has been created may cause 
        unpredictable results. If you need to change the files somehow, then it
        is better to create a new dataset object using the new files.
        """
        # open file for writing
        with open(filename, "wb") as f:
            # pickle the dataset object and save it to the file
            cPickle.dump(self, f, cPickle.HIGHEST_PROTOCOL)

    ###########################################################################

    def split(self, n):
        """
        Split the dataset into n datasets. Returns a tuple of dataset objects.
        Each dataset in the tuple will have approximately equal numbers of 
        images in it and they will be ordered chronologiaclly. For example if
        d contains a series of 10 images spanning one hour, then d.split(2) 
        will return a tuple whose first element is a dataset containing the 
        first 5 images from d.
        """
        length = self.getNumImages()

        # can't split into more pieces than there are images!
        if n > length:
            raise ValueError("Dataset only contains " + str(length) +
                             " images. Can't split into " + str(n) +
                             "new datasets.")
        if int(n) <= 0:
            raise ValueError("n must be a positive integer")

        inc = int(float(length) / float(n) + 0.5)
        split_list = []
        data = zip(self.__times, self.__filenames, self.__site_info_files,
                   self.__radii_list, self.__fov_angles_list)

        for i in range(0, n - 1):
            data_slice = data[i * inc:i * inc + inc]
            split_list.append(dataset(data_slice, self.__wavelength,
                                      self.__filetypes, self.__mode,
                                      self.__colour_table,
                                      self.__calib_factor,
                                      self.__lens_projection))

        data_slice = data[n * inc - inc:]
        split_list.append(dataset(data_slice, self.__wavelength,
                                  self.__filetypes, self.__mode,
                                  self.__colour_table, self.__calib_factor,
                                  self.__lens_projection))

        return tuple(split_list)

    ###########################################################################
########################################################################


class datasetIterator:
    """
    Iterator class for the dataset class. Allows you to use "for image in 
    dataset:" constructs for iterating over all images in a dataset.
    """

    def __init__(self, filenames):
        self.__filenames = filenames
        self.__current_index = 0
        self.__largest_index = len(filenames)

    ###########################################################################

    def __iter__(self):
        """
        Method required by iterator protocol. Allows iterator to be used in 
        for loops.
        """
        return self

    ###########################################################################

    def next(self):
        """
        Required for the iterator protocol. Returns the next allskyImage in the
        dataset. 
        """

        if self.__current_index < self.__largest_index:

            im = allskyImage.new(self.__filenames[self.__current_index][0],
                                 site_info_file=self.__filenames[self.__current_index][1])
            self.__current_index += 1

            # return image
            return im

        else:
            # all images have been returned, raise an exception from now on.
            raise StopIteration

    ###########################################################################
#########################################################################
