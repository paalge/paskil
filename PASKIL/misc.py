"""
Module containing miscellaneous functions used internally by PASKIL

"""

import math, os, glob

###################################################################################

def findFiles(directory, search_string):
    """
    Function performs a recursive search of the specified directory using the search string provided. It returns a list of filenames of 
    all files that matched the search string    
    """
    found_files=[]
    found_files=found_files+glob.glob(directory+os.sep+search_string)
    
    for filename in glob.glob(directory+os.sep+"*"):
        if os.path.isdir(filename):
            found_files=found_files+findFiles(filename, search_string)
    
    #remove empty items
    while found_files.count([]) != 0:
        found_files.remove([])
    
    return found_files

###################################################################################

def pngsave(im, file_):
    """
    Function saves a PIL image as a PNG file, preserving the header data
    """

    # these can be automatically added to Image.info dict                                                                              
    # they are not user-added metadata
    reserved = ('interlace', 'gamma', 'dpi', 'transparency', 'aspect')

    #undocumented class
    from PIL import PngImagePlugin
    meta = PngImagePlugin.PngInfo()

    # copy metadata into new object
    for k, v in im.info.iteritems():
        if k in reserved: continue
        meta.add_text(k, v, 0)

    # and save
    im.save(file_, "PNG", pnginfo=meta)

###################################################################################

def xy2angle(x, y, x_0, y_0, fov_angle, radius):
    """
    Converts x and y coordinates into angle from the centre (from the Z axis).
    """
    dist_from_centre=math.sqrt(((x-x_0)*(x-x_0)) + ((y-y_0)*(y-y_0)))
    
    angle = float(float(dist_from_centre)*(float(fov_angle)/float(radius)))
    
    return angle
    
###################################################################################

def tupleCompare(first, second):
    """
    Compares the first elements of two tuples
    """
    
    return cmp(first[0], second[0])
    
###################################################################################

def stepFunction(min_, max_, step_position, length):
    """
    Returns a step function
    """
    step_function=[]
    for i in range(0, step_position):
        step_function.append(min_)
    for i in range(step_position, length):
        step_function.append(max_)
    
    return step_function
    
################################################################################### 
    
