#!/usr/bin/python

# This script creates a keogram from a directory of all-sky
# images. The keogram is saved into the same directory as
# the images. The following variables can be edited to 
# control the keogram style.
#
# The script will create two files in the specified directory
# one called "keogram_object" and one called "keogram_plot"
# The "keogram_object" file can easily be loaded back into 
# PASKIL using the allskyKeo.load() function. This can then 
# be used to produce further plots, zoom in on a particular
# time series etc. The "keogram_plot" file is a plot of the 
# data.

###################################################
##            USER EDITABLE VARIABLES            ##
###################################################
# A list of file extensions of the image types you
# want included in the keogram.
IMAGE_FILE_TYPES = ['.png']

# The wavelength of the images you want included in
# the keogram.
IMAGE_WAVELENGTH = 'Green1'

# The angle from geographic north that you want the
# slice taken out of the image at.
ANGLE = 327

# The width (in pixels) of the slice you want taken
# from each image. 
STRIP_WIDTH = 5 

# The time in seconds between each image that is to 
# be included. If you set this to "AUTO" then it 
# will be estimated from the images themselves.
DATA_SPACING = "AUTO" 

# The type of keogram to be produced. Currently 
# supported options are:
#    CopyPaste - the strip of pixels from the image
#                is pasted directly into the keogram
#
#    Average - the strip of pixels is averaged in the
#              time direction and the mean values are
#              put into the keogram.
KEO_TYPE = "CopyPaste"

# The angle range of the keogram in degrees. This
# can either be None (in which case the full fields of
# view of the images used to create the keogram are used)
# or a tuple (min angle, max angle)
KEO_FOV_ANGLE = (10,170)


####################################################
####################################################



import sys,os.path
# Check that a directory was specified on the command line.
if len(sys.argv) !=2:
    print "Usage: keo_create [DIRECTORY]"
    sys.exit(0)

if not os.path.isdir(sys.argv[1]):
    print "keo_create: \""+sys.argv[1]+"\" is not a directory."
    print""
    print "Usage: keo_create [DIRECTORY]"
    sys.exit(0)
    
# Import the PASKIL modules needed to create keograms
from PASKIL import allskyData, allskyKeo, allskyPlot

# create a dataset object containing all the images of
# the correct type and wavelength in the specified folder
dataset = allskyData.new(sys.argv[1], IMAGE_WAVELENGTH, IMAGE_FILE_TYPES)

# create a keogram from the dataset
keogram = allskyKeo.new(dataset, ANGLE, strip_width=STRIP_WIDTH, 
                        data_spacing=DATA_SPACING, keo_type=KEO_TYPE,
                        keo_fov_angle=KEO_FOV_ANGLE)

# save the keogram object so that it can be opened/edited in future
keo_obj_filename = os.path.normpath(sys.argv[1]+"/keogram_object")
keogram.save(keo_obj_filename)

# plot the keogram and save the plot
keo_plot_filename = os.path.normpath(sys.argv[1]+"/keogram_plot.png")
plotted_keo = allskyPlot.plot([keogram])
plotted_keo.savefig(keo_plot_filename)


