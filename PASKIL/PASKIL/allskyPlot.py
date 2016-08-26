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

    The allskyPlot module provides functionality for visualising many of the objects
    used by PASKIL (for example allskyImage objects, allskyKeo objects). It is designed
    to allow plotting of multiple objects (of different types) in a single figure. This
    module is largely incomplete, untested and in need of some improvement. However,
    the basic functionality is there and now it should just be a case of polishing it!
    
    
Concepts:
    
    The main function is the plot function. This takes a list of objects and plots them
    as subfigures in a matplotlib figure object. It is designed to work with any objects
    that implement a plotting interface consisting of the following methods:
    
        _hasColourBar() - Returns True or False depending on whether the plot of the 
                          object will have a colour bar next to it or not.
                          
        _plot(subplot)  - Returns the supplied subplot with the object plotted into it.

"""
import matplotlib.pyplot
import math
import numpy
from PIL import Image, ImageDraw

from pylab import NullLocator, FixedLocator, FuncFormatter


def plot(objects, columns=1, size=None):
    """
    Plots a list of objects implementing the plotting interface. Objects is a
    list of objects to be plotted. Columns specifies how many columns of
    subplots to include in the final plot, default is one in which case all
    objects will be plotted below each other. Size is a tuple (width,height)
    of the size in inches of the final figure, default is None in which case
    the default value for matplotlib is used.
    """

    fig = matplotlib.pyplot.figure()

    if size is not None:
        fig.set_size_inches(size[0], size[1])

    rows = int(math.ceil(len(objects) / float(columns)))

    # for some reason matplotlib messes up the colourbars if there are more columns than
    # rows. So as a quick fix we make sure that there aren't!
    if columns > rows:
        rows = columns

    # if some of the objects to be plotted have colour bars, but some don't, then the
    # alignments will get messed up. Here we check if any of the objects at all have
    # colour bars, so that we can correct for it as we plot them
    cb_correct = False
    for _object in objects:
        if _object._hasColourBar():
            cb_correct = True
            break

    i = 1
    # if len(objects) > 1:
    #    fig.subplotpars.hspace = 0.4

    for _object in objects:
        # create a new subplot object
        s = fig.add_subplot(rows, columns, i)

        if (cb_correct and (not _object._hasColourBar())):
            # create an invisible colour bar so that the sizes of the objects
            # will be the same
            fake_data = numpy.random.rand(2, 2)
            fake_colour_image = s.pcolor(fake_data)
            if s.numCols > 1:
                colour_bar = matplotlib.pyplot.colorbar(
                    fake_colour_image, ax=s, pad=0.15)
            else:
                colour_bar = matplotlib.pyplot.colorbar(
                    fake_colour_image, ax=s)
            colour_bar.ax.axes.set_visible(False)

        # add the object to the figure
        s = _object._plot(s)

        i += 1

    return fig

##########################################################################


def createColourbar(subplot, colour_table, calib_factor):
    """
    Function draws a colour bar in the specified subplot. The colour_table argument should
    be a list of RGB values (i.e. use the colourTable.getColourTable() method). The calib_factor
    is the multiplier that converts between pixel values and kR. In general this function should
    only be called by an object's _plot() method.
    """
    # find the thresholds on the colour table - then we can just display
    # the interesting parts of the colour table.

    # first we find the lower threshold
    colour_table.reverse()
    offset = colour_table.index(colour_table[-1])
    lower_threshold = len(colour_table) - 1 - offset

    # now the upper threshold
    colour_table.reverse()
    upper_threshold = colour_table.index(colour_table[-1])

    # if the image could contain values outside of the threshold
    # region (there is now no way to determine this for certain, since the
    # intensity data was lost when the colour table was applied) then put
    # arrow heads on the colour bar to indicate this
    lower_arrow = 0
    upper_arrow = 0

    # decide on the size of the colour bar image - what is important here is
    # the aspect ratio
    if (upper_threshold - lower_threshold) >= 230:
        # colour bar is very long - extend width to get correct aspect ratio
        # 33 is just an arbitrary number that works
        colour_bar_width = (upper_threshold - lower_threshold) // 33
        # the colour bar should be an odd number of pixels wide (to make
        # drawing arrowheads easy)
        if colour_bar_width % 2 != 0:
            colour_bar_width += 1

        if lower_threshold != 0:
            lower_arrow = colour_bar_width  # size of the arrow head in pixels
        if upper_threshold != len(colour_table) - 1:
            upper_arrow = colour_bar_width  # size of the arrow head in pixels

        # +1 = counting from zero!
        colour_bar_height = (
            upper_threshold - lower_threshold) + 1 + upper_arrow + lower_arrow
        cb_height_scaling = 1.0
    else:
        # colour bar is very short - extend height to get correct aspect ratio
        colour_bar_width = 7
        if lower_threshold != 0:
            lower_arrow = 7  # size of the arrow head in pixels
        if upper_threshold != len(colour_table) - 1:
            upper_arrow = 7  # size of the arrow head in pixels

        cb_height_scaling = 230.0 / float(upper_threshold - lower_threshold)
        colour_bar_height = 231 + upper_arrow + lower_arrow

    # create a colour bar image
    colour_bar_image = Image.new(
        "RGB", (colour_bar_width, colour_bar_height), (255, 255, 255))
    colour_bar_pix = colour_bar_image.load()

    # colour in the arrows (if there are any)
    # remember that image indexing starts at top left
    for y in range(0, upper_arrow):
        for x in range(colour_bar_width):
            colour_bar_pix[x, y] = colour_table[upper_threshold]
    for y in range(0, lower_arrow):
        for x in range(colour_bar_width):
            colour_bar_pix[
                x, colour_bar_height - y - 1] = colour_table[lower_threshold]

    # colour in the rest of the colour bar based on the colour table of the
    # image
    for y in range(colour_bar_height - upper_arrow - lower_arrow):
        current_ct_index = upper_threshold - \
            (int((y / float(colour_bar_height - upper_arrow - lower_arrow)
                  * (upper_threshold - lower_threshold)) + 0.5))
        current_colour = colour_table[current_ct_index]
        for x in range(colour_bar_width):
            colour_bar_pix[x, y + upper_arrow] = current_colour

    # if the image could contain values outside of the threshold
    # region (there is now no way to determine this for certain, since the
    # intensity data was lost when the colour table was applied) then put
    # arrow heads on the colour bar to indicate this
    if lower_threshold != 0:
        d = ImageDraw.Draw(colour_bar_image)
        y0 = colour_bar_height
        d.polygon([(0, y0), (0, y0 - colour_bar_width), ((colour_bar_width - 1) / 2, y0 - 1),
                   ((colour_bar_width - 1), y0 - colour_bar_width), ((colour_bar_width - 1), y0)], fill='white')
    if upper_threshold != colour_bar_height - 1:
        d = ImageDraw.Draw(colour_bar_image)
        y0 = 0  # colour_bar_height - upper_threshold - colour_bar_width
        d.polygon([(0, y0), (0, y0 + colour_bar_width), ((colour_bar_width - 1) / 2, y0 + 1),
                   ((colour_bar_width - 1), y0 + colour_bar_width), ((colour_bar_width - 1), y0)], fill='white')

    # create a fake colour table - this is used to get matplotlib to create the colourbar axes
    # which we then use to plot out colour bar image into
    fake_data = numpy.random.rand(2, 2)
    fake_colour_image = subplot.pcolor(fake_data)

    # create the matplotlib colour bar object
    if subplot.numCols > 1:
        colour_bar = matplotlib.pyplot.colorbar(
            fake_colour_image, ax=subplot, pad=0.15)
    else:
        colour_bar = matplotlib.pyplot.colorbar(fake_colour_image, ax=subplot)
    colour_bar.ax.axes.clear()  # get rid of our fake colourbar data

    # calculate where the ticks on the y axis of the colour bar should go.
    # this is slightly tricky since we have three scales to consider:
    # the absolute pixel coordinates of the image, the CCD counts of the
    # camera and the absolute calibrated intensities. The following code
    # attempts to put approx 7 ticks at whole numbers of either CCD counts or
    # kR. It is not very elegant!
    if calib_factor is None:
        colour_bar.ax.axes.set_ylabel("CCD Counts")
        y_ticks = []
        # we want ~7 labels on the colour bar
        ccd_step_size = ((upper_threshold - lower_threshold) / 7.0)
        if ccd_step_size > 1:
            # try to make the tick spacing an integer number
            ccd_step_size = int(ccd_step_size + 0.5)

        # take account of the colourbar height scaling (if any)
        pix_step_size = ccd_step_size * cb_height_scaling

        for i in range(8):
            y_ticks.append(lower_arrow + 1 + i * pix_step_size)

        colour_bar.ax.yaxis.set_major_locator(FixedLocator(y_ticks))
    else:
        colour_bar.ax.axes.set_ylabel("kR")
        y_ticks = []
        # we want ~7 labels on the colour bar
        cal_step_size = (
            (upper_threshold - lower_threshold) * calib_factor / 7.0)
        if cal_step_size < 1:
            # but will make do with 6 if it is easier
            cal_step_size = (
                (upper_threshold - lower_threshold) * calib_factor / 6.0)
        if cal_step_size < 1:
            # or even 5 if it is easier
            cal_step_size = (
                (upper_threshold - lower_threshold) * calib_factor / 5.0)

        if cal_step_size > 1:
            # try to make the tick spacing an integer number
            cal_step_size = int(cal_step_size + 0.5)

        # take account of the colourbar height scaling (if any)
        pix_step_size = (
            cal_step_size / float(calib_factor)) * cb_height_scaling

        for i in range(8):
            y_ticks.append(lower_arrow + 1 + i * pix_step_size)

        colour_bar.ax.yaxis.set_major_locator(FixedLocator(y_ticks))

    # plot the colourbar image into the axes
    colour_bar.ax.yaxis.set_label_position("left")
    colour_bar.ax.xaxis.set_major_locator(NullLocator())
    colour_bar.ax.imshow(colour_bar_image, origin="top")
    colour_bar.ax.axes.set_ylim((0, colour_bar_height))
    colour_bar.ax.axes.set_xlim((-1, colour_bar_width - 1))

    # create a formatter function for the y-axis based on the various scaling factors
    # that have been used. The lambda functions take a pixel coordinate in the colourbar
    # image and return its value in either kR or CCD counts
    if calib_factor is not None:
        y_formatter = lambda x, pos: round(
            (calib_factor * (((x - lower_arrow - 1) / cb_height_scaling) + lower_threshold)), 2)
    else:
        y_formatter = lambda x, pos: (
            (x - lower_arrow - 1) / cb_height_scaling) + lower_threshold
    colour_bar.ax.yaxis.set_major_formatter(FuncFormatter(y_formatter))
    colour_bar.ax.yaxis.tick_right()
