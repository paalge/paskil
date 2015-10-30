# File: calibrated_image_from_raw.py
# Author: Nial Peters
# Date: 28th March 2009

# This script demonstrates how to create an absolutely calibrated
# image at 630.0 nm from a raw image file (in this case a .NEF
# file) using PASKIL. The NEF file was captured using a Nikon D80
# camera situated at the Kjell Henriksen Observatory on Svalbard.
# The calibration factors used were calculated using laboratory
# facilities at the University Centre on Svalbard.

# The meta-data used to load the image is stored in the file
# "NEF_site_info.txt". Details of the different fields in this
# file can be found on the documentation page for the
# allskyImagePlugins module (or in the allskyImagePlugins.py
# source file).


# Import the PASKIL modules that we will use for processing the
# image.
from PASKIL import allskyImage, allskyPlot, allskyCalib, allskyColour


# Import the plugin needed to open this type of image.
from PASKIL.plugins import DSLR_NEF


# Declare filenames as global variables for convenience.
nef_file = "LYR-SLR-20080201_184252.NEF"
info_file = "NEF_site_info.txt"
background_image = "LYR-SLR-20010101_000000.NEF"
ffcalib_file = "D80_flat_field.txt"


# Open the raw image files.
print "Decoding NEF files"
raw_image = allskyImage.new(nef_file, site_info_file=info_file)
bkgd_image = allskyImage.new(background_image, site_info_file=info_file)


# The raw image object contains pixel data from all four colour
# channels of the camera. We are only interested in one of the
# green channels, so we extract that now. For the D80, the
# different colour channels are as follows: 0=red, 1=1st green,
# 2=blue, 3=2nd green. The green channels are essentially
# identical.
print "Extracting green channel"
green_image = raw_image.getChannel(1)
green_bkgd = bkgd_image.getChannel(1)


# Subtract the background image. Most methods return
# a new allskyImage object - here we simply overwrite the
# original with the background subtracted version.
print "Subtracting background image"
green_image = green_image.subtractBackgroundImage(green_bkgd)


# The D80 has a 180 degree field of view. However, mountains
# obscure the view at high angles from zenith. To remove
# them we crop the image to only have a 150 degree field of
# view. Note that with PASKIL you have to specify the angle from
# zenith that you want the image cropped at.
print "Cropping field of view"
green_image = green_image.binaryMask(75)


# Crop the image size to only include the field of view.
print "Cropping image to field of view size"
green_image = green_image.centerImage()


# Next we align the top of the image with geomagnetic north.
# Since most all-sky images have a NWSE orientation, we stick
# with this convention.
print "Aligning image with geomagnetic north"
green_image = green_image.alignNorth(north='geomagnetic', orientation='NWSE')


# Create a calibration object for applying a flat field
# correction to the image. In this case, the calibration factors
# are simply read from a text file. The file contains two
# columns of numbers: <angle> <normalised intensity>
# The angles must start from 0 (0 degrees from zenith) and
# increment by one degree for each row. The normalised intensity
# should be a fraction of the intensity recorded at zenith.
ffcalib = allskyCalib.fromFile(ffcalib_file)


# Apply the flat field calibration to the image.
print "Applying flat field correction"
green_image = green_image.flatFieldCorrection(ffcalib)


# Greyscale images are difficult to interpret, so we create
# a false colour scale for the image. Here we use PASKIL's
# default colour palette, but it is easy to define your own.
# Intensities below the lower threshold are all set to the
# lowest value colour. Intensities above the upper threshold
# are all set to the highest value colour. Careful choice of
# thresholds allows the greatest variation of colour within
# the desired intensity range.
print "Creating false colour scale"
image_histogram = green_image.histogram()
thresholds = (40, 300)
colour_table = allskyColour.default(image_histogram, thresholds)


# Apply the colour mappings we have just created
false_colour_image = green_image.applyColourTable(colour_table)


# Apply the absolute calibration to the image. This converts
# the pixel values into Rayleighs. However, it is a lazy
# operation so don't expect the values in the file to be in
# Rayleighs! The calibration is only done when the image is
# plotted. The const_factor argument is used to account for
# transmission through the instrument dome.
print "Calibrating intensities to Rayleighs"
factor = 1.4E-3  # counts per second per Rayleigh
exptime = 20.0  # exposure time in seconds
dome_tansmission = 0.96  # transmission through instrument dome
calibrated_image = false_colour_image.absoluteCalibration(
    factor, exptime, const_factor=1.0 / dome_tansmission)


# Plot the image using the allskyPlot module. The returned
# object is a matplotlib figure object - see the matplotlib
# documentation for details of all the things you can do with
# this!
print "Plotting image"
calibrated_image.title = "Example Calibrated Image"
figure = allskyPlot.plot([calibrated_image])
figure.savefig("calibrated_example.png")
print "Done! Calibrated image is stored in calibrated_example.png"
