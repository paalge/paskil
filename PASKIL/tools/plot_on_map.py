#!/usr/bin/python

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
import os
import sys
from optparse import OptionParser

from pylab import show
from PASKIL import allskyImage

def __parse_cmd_line():
    """
    Function parses the command line input and returns a tuple
    of (options, args)
    """
    usage = "usage: %prog [options] file"
    parser = OptionParser(usage)
    
    parser.add_option("-a", "--altitude", dest="proj_height", action="store", default=150000,
                      help="altitude (in meters) to project the image to (default = 150000)")
    
    parser.add_option("-c", "--colour", dest="background", action="store", default='black',
                      help="background colour for map projection, can be 'black' (default) or 'white'")
    
    parser.add_option("-f", "--field_of_view", dest="angle", action="store", default=None,
                      help="crop the image at a set angle (in degrees) from the zenith")
    
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No input file")

    return (options, args)


if __name__ == "__main__":
    options, args = __parse_cmd_line()
    
    
    if not os.path.exists(args[0]):
        print "Cannot open file \'"+args[0]+"\'. No such file."
        sys.exit()
    
    try:
        im = allskyImage.new(args[0])
    except:
        print "\'"+args[0]+"\' is not a recognised PASKIL image file."
        sys.exit()
    
    if options.angle is not None:
        im = im.binaryMask(float(options.angle))
    
    proj = im.projectToHeight(options.proj_height,background=options.background)
    proj.default()
    show()