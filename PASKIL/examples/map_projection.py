# File: calibrated_image_from_raw.py
# Author: Nial Peters
# Date: 28th March 2009
#
# This script demonstrates how to create a map projection
# of an all-sky image. In this case we use a JPG image
# captured by a Nikon D80 camera situated at the Kjell 
# Henriksen Observatory on Svalbard.
#
# The meta-data used to load the image is stored in the file
# "JPG_site_info.txt". Details of the different fields in this
# file can be found on the documentation page for the 
# allskyImagePlugins module (or in the allskyImagePlugins.py 
# source file).


# Import the PASKIL modules that we will use for processing the 
# image.
from PASKIL import allskyImage, allskyProj


# Import the plugin needed to open this type of image.
from PASKIL.plugins import DSLR_LYR_JPG


# Import the pylab functions we need to save the map projection
from pylab import savefig


# Declare filenames as global variables for convenience.
jpg_file = "LYR-SLR-20081223_194416.JPG"
info_file = "jpg_site_info.txt"


# Open the image file
print("Opening image file")
image = allskyImage.new(jpg_file, info_file)


# The D80 has a 180 degree field of view. However, mountains
# obscure the view at high angles from zenith. To remove
# them we crop the image to only have a 150 degree field of 
# view. Note that with PASKIL you have to specify the angle from
# zenith that you want the image cropped at. Most methods return
# a new allskyImage object - here we simply overwrite the 
# original with the cropped version.
print("Cropping field of view")
image = image.binaryMask(75)


# Crop the image size to only include the field of view.
print("Cropping image to field of view size")
image = image.centerImage()


# Create a projection object which can then be used to create
# different map projections.
print("Projecting image")
proj_height = 150000 # meters (we assume that the green emissions dominate)
proj = image.projectToHeight(proj_height)


# The projection object can be used to create almost any map 
# projection desired. Here however, we use the default projection
# which is a azimuthal equidistant projection centred on the observatory.
print("Creating map")
_map = proj.default()


# Save the map projection
savefig("map_projection_example.png")
print("Done! Map projection is stored in map_projection_example.png")

