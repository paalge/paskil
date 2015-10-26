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
Plugin for loading images taken using the Nikon D80 DSLR allsky camera at KHO. 
"""
from __future__ import with_statement
from PASKIL import allskyImage, allskyImagePlugins
import sys
import datetime
import Image


class DSLR_LYR_JPG:

    def __init__(self):
        self.name = "Jeff and Nial's DSLR camera at KHO"

    ##########################################################################

    def test(self, image_filename, info_filename):

        try:
            image = Image.open(image_filename)
        except:
            return False

        if image.format == "JPEG":
            try:
                filename = image.filename
                filename = filename.split("/")
                filename = filename[len(filename) - 1]
                datetime.datetime.strptime(
                    filename.rstrip(".JPG"), "LYR-SLR-%Y%m%d_%H%M%S")
            except ValueError:
                return False
            return True
        else:
            return False

    ##########################################################################

    def open(self, image_filename, info_filename):

        image = Image.open(image_filename)

        # Read site info file
        camera = {}
        processing = {}
        header = image.info

        with open(info_filename, "r") as info_file:
            for line in info_file:  # read file line by line
                if line.isspace():
                    continue  # ignore blank lines
                words = line.split("=")  # split the line at the = sign

                if len(words) != 2:
                    print "Error! allskyImagePlugins.DSLR_LYR.open(): Cannot read site info file, too many words per line"
                    sys.exit()

                # store the values (minus white space) in a dictionary
                camera[words[0].lstrip().rstrip()] = words[1].lstrip().rstrip()

        # Read creation time from filename
        filename = image.filename
        filename = filename.split("/")
        filename = filename[len(filename) - 1]
        creation_time = datetime.datetime.strptime(
            filename.rstrip(".JPG"), "LYR-SLR-%Y%m%d_%H%M%S")

        creation_time = creation_time.strftime("%d %b %Y %H:%M:%S %Z")
        header = {'Wavelength': "Visible", 'Creation Time': creation_time}

        info = {'header': header, 'camera': camera, 'processing': processing}

        # return new allskyImage object
        return allskyImage.allskyImage(image, image.filename, info)

    ##########################################################################
##########################################################################

allskyImagePlugins.register(DSLR_LYR_JPG())
