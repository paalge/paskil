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
Module containing miscellaneous functions used internally by PASKIL

"""

import math
import os
import glob
from gi.repository import GExiv2 as pyexiv2

##########################################################################


def findFiles(directory, search_string):
    """
    Function performs a recursive search of the specified directory using the search string provided. It returns a list of filenames of 
    all files that matched the search string    
    """
    found_files = []
    found_files = found_files + glob.glob(directory + os.sep + search_string)

    for filename in glob.glob(directory + os.sep + "*"):
        if os.path.isdir(filename):
            found_files = found_files + findFiles(filename, search_string)

    # remove empty items
    while found_files.count([]) != 0:
        found_files.remove([])

    return found_files

##########################################################################


def pngsave(im, file_):
    """
    Function saves a PIL image as a PNG file, preserving the header data
    """

    # these can be automatically added to Image.info dict
    # they are not user-added metadata
    reserved = ('interlace', 'gamma', 'dpi', 'transparency', 'aspect')

    # undocumented class
    from PIL import PngImagePlugin
    meta = PngImagePlugin.PngInfo()

    # copy metadata into new object
    for k, v in im.info.iteritems():
        if k in reserved:
            continue
        meta.add_text(k, v, 0)

    # and save
    im.save(file_, "PNG", pnginfo=meta)

##########################################################################


def tupleCompare(first, second):
    """
    Compares the first elements of two tuples
    """

    return cmp(first[0], second[0])

##########################################################################


def stepFunction(min_, max_, step_position, length):
    """
    Returns a step function
    """
    step_function = []
    for i in range(0, step_position):
        step_function.append(min_)
    for i in range(step_position, length):
        step_function.append(max_)

    return step_function

##########################################################################


def readExifData(filename):
    """
    Returns a dict containing the exif data stored in a file.
    Exif tags that are not set are ignored (they will not appear
    in the returned dict). If filename does not contain any exif
    data, or it cannot be loaded, then an empty dict is returned.
    """
    exif_data = {}
    try:
        exif = pyexiv2.Metadata(filename)
        for tag in exif.get_exif_tags():
            try:
                exif_data[tag] = exif[tag]
            except:
                continue
    finally:
        return exif_data

##########################################################################
