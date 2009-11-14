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

                    Python All-Sky Image Library
                        
                            Nial Peters
                            March  2008


Introduction:

    The Python All-Sky Image Library (PASKIL) is a collection of Python modules designed to manipulate 
    and process all-sky images.  Its plug-in architecture enables it to process images and image 
    meta-data of any format.

    PASKIL is largely built on top of the powerful Python Image Library (PIL) and it is advised that 
    users familirise themselves with the concepts behind PIL before trying to use PASKIL.

    If you have never used Python before, then don't despair! It is a very easy language to learn and use, and 
    there is lots of help available on the Internet. There is also lots of example code throughout this document 
    which shows how to use PASKIL in your own programs.



Installation:

    Prerequisites:
        Before installing and using PASKIL you will need to ensure that you have installed the following on 
        your computer:
    
            * Python: http://www.python.org/
            * A C compiler e.g. GCC: http://gcc.gnu.org/
            * The Python Image Library (PIL): http://www.pythonware.com/products/pil/
            * Matplotlib: http://matplotlib.sourceforge.net/
            * Matplotlib basemap toolbox: http://matplotlib.sourceforge.net/toolkits.html
            * NumPy: http://numpy.scipy.org/
            * PyFits: http://www.stsci.edu/resources/software_hardware/pyfits
            * Pyexiv2 (>=V.0.1.3): http://tilloy.net/dev/pyexiv2/download.htm
        
        Linux users will probably find all of this software in the software repository for their particular 
        distribution.    
    
    
    Step By Step Guide:
        
        1) Copy the PASKIL tar archive file into your home directory.
        2) Unpack the archive.
        3) Move to the unpacked directory.
        4) Run the command "python setup.py install". You will need root privileges to run this command.
           Windows users may need to use the command "setup.py install"



Using PASKIL:

    PASKIL is split into several modules, each of which deals with a specific aspect of all-sky image processing.
    The details of the functionality that each module provides can be found on its respective manual page. 
    However, as an overview:
        
        allskyCalib      -    Deals with producing flat field correction curves. These are needed to calibrate 
                              for the angular dependence of the CCD's sensitivity.

        allskyColour     -    Creates colour tables for mapping grey-scale images to RGB images. The colour 
                              tables are intelligently stretched to pick out the most detail in the image.

        allskyData       -    This module is designed to ease the use of large data sets. It provides an 
                              abstraction layer between the user and the directory structure of the data set.

        allskyImage      -    This is the main PASKIL module. It provides all the functionality needed for 
                              loading and manipulating all-sky images.

    allskyImagePlugins   -    Provides the plugin architecture that PASKIL requires to open different formats 
                              of all-sky image. See the documentation for this module for details on what image
                              metadata is required by PASKIL, how to input it and how to write your own plugins.

        allskyKeo        -    This module is used to create keograms from sets of all-sky images.
        
        allskyPlot       -    Provides plotting routines for all-sky images, keoagrams and other objects that
                              implement the plotting interface.

        allskyProj       -    Deals with projecting all-sky images onto maps.
        
        allskyRaw        -    Provides functions for reading raw image formats such as Nikon's NEF format.

        misc             -    Provides a few miscellaneous functions that are used internally by PASKIL.

        stats            -    Provides some statistical functions that are used internally by PASKIL.


    You may have noticed that PASKIL also contains a module called __init__. This contains a list of all the 
    other modules, and is used by Python on encountering a 'from PASKIL import *' command to ensure that all 
    the modules were imported. If you add a new module to PASKIL then it is important that you update this 
    list.


        
Useful Links:

    http://docs.python.org/tut/tut.html
        A good introductory Python tutorial.
        
    http://www.pythonware.com/library/pil/handbook/index.htm
        The Python Image Library (PIL) handbook. This is an excellent resource! It is very easy to understand and 
        I recommend that you read it before trying to use PASKIL as many of the concepts are the same.
        
    http://docs.python.org/lib/lib.html
        A Python library reference. This covers all the other library functions used in PASKIL.

    http://matplotlib.sourceforge.net/
        The webpage for the matplotlib package, which is used for all the plotting routines in PASKIL.
    
    
        
Bugs and comments:

    nonbiostudent@hotmail.com
"""
#Define a list of all modules in PASKIL package.
__all__ = ["allskyCalib", "allskyColour", "allskyData", "allskyImage", "allskyImagePlugins", "allskyPlot","allskyProj", "allskyKeo", "allskyRaw","misc", "stats", "plugins"]
__version__ = '3.2.1'
