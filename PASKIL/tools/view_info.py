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
from PASKIL import allskyImage

def __parse_cmd_line():
    """
    Function parses the command line input and returns a tuple
    of (options, args)
    """
    usage = "usage: %prog option(s) file"
    parser = OptionParser(usage)
    
    parser.add_option("-H", "--header", dest="view_header", action="store_true", default=False,
                      help="view the header data")
    
    parser.add_option("-C", "--camera", dest="view_camera", action="store_true", default=False,
                      help="view the camera data")
    
    parser.add_option("-P", "--processing", dest="view_processing", action="store_true", default=False,
                      help="view the processing data")
    
    parser.add_option("-E", "--exif", dest="view_exif", action="store_true", default=False,
                      help="view the exif data")
    
    parser.add_option("-A", "--all", dest="view_all", action="store_true", default=False,
                      help="view all data associated with the image (except processing data)")
    
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No input file")
    if not (options.view_all or options.view_camera or options.view_exif or 
            options.view_header or options.view_processing):
        parser.error("Must specify which information to display")
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
    
    info = im.getInfo()
    
    
    keys = []
    if options.view_header or options.view_all:
        keys.append('header')
    if options.view_camera or options.view_all:
        keys.append('camera')
    if options.view_exif or options.view_all:
        keys.append('exif')
    if options.view_processing:
        keys.append('processing')
    
    print ""
    for k in keys:
        print "****** "+k+" data ******"
        if len(info[k].keys()) == 0:
            print "None available"
        else:
            for name in info[k].keys():
                print name+" = "+str(info[k][name])
        print ""
        
        
        