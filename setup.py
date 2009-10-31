from distutils.core import setup,Extension
import sys

try:
    import numpy
    import numpy.numarray
except ImportError:
    raise ImportError, "Could not import numpy. Please ensure that it is correctly installed. See http://numpy.scipy.org/"
 
#get the lists of directories containing the numpy header files
numpyincludedirs = numpy.get_include()
numarrayincludedirs = numpy.numarray.get_numarray_include_dirs()

#if we are installing PASKIL, then do a few checks
if sys.argv.count('install') != 0:
    #try to import all the modules required by PASKIL to make sure
    #they are all installed properly
       
    try:
        import matplotlib
    except ImportError:
        raise ImportError, "Could not import matplotlib. Please ensure that it is correctly installed. See http://matplotlib.sourceforge.net/"
        
    try:
        from mpl_toolkits.basemap import Basemap
    except ImportError:
        raise ImportError, "Could not import basemap toolbox. Please ensure that it is correctly installed. See http://matplotlib.sourceforge.net/toolkits.html"
        
    try:
        import pyfits
    except ImportError:
        raise ImportError, "Could not import pyfits. Please ensure that it is correctly installed. See http://www.stsci.edu/resources/software_hardware/pyfits"
        
    try:
        import Image
    except ImportError:
        raise ImportError, "Could not import the Python Image Library. Please ensure that it is correctly installed. See http://www.pythonware.com/products/pil/"
    
    #run a check to see if the bug in PIL's fromarray function has been fixed
    #This is vital for PASKIL operation!
    test_im = Image.new('I',(10,10)) #create 32bit image
    im_arr = numpy.asarray(test_im) #convert to an array
    im_from_arr = Image.fromarray(im_arr) #convert back to an image
    
    if im_from_arr.mode != 'I': #check that it is still 32bit
        print "##################################################"
        print "PASKIL has found a bug in the Python Image Library"
        print ""
        print "To fix:"
        print "      * Open the file \"Image.py\" located in" 
        print "       \"site-packages/PIL\" in your python" 
        print "        installation folder."
        print "      * In the \"fromarray\" function (~line 1833)"
        print "        change the line \"typestr = typestr[:2]\""
        print "        to \"typestr = typestr[1:]\""
        print "      * Rerun the PASKIL installation."
        print ""
        print "##################################################"
        sys.exit(1)

libs = []
#If we are bulding under windows then we need to link to the wsock32 library
if sys.platform == 'win32':
    libs.append('wsock32')


#Then build/install it!
setup(name='PASKIL',
	  version='3.2',
	  description='Python All-Sky Image Library', 
	  author = 'Nial Peters', 
	  author_email='nonbiostudent@hotmail.com',
	  url='http://code.google.com/p/paskil/',
	  packages=['PASKIL','PASKIL.plugins','PASKIL.extensions'],
	  ext_modules=[Extension("PASKIL.extensions.cRaw", 
	                       ["PASKIL/extensions/cRaw.c"],
	                       define_macros=[('NO_JPEG',None),('NO_LCMS', None)],
	                       include_dirs=[numpyincludedirs]+numarrayincludedirs,
                           libraries=libs)])


