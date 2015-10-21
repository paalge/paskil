## Introduction ##
The Python All-Sky Image Library (PASKIL) is a collection of Python modules designed to manipulate and process all-sky images.  Its plug-in architecture enables it to process images and image meta-data of any format.

PASKIL is largely built on top of the powerful Python Image Library (PIL) and it is advised that users familiarise themselves with the concepts behind PIL before trying to use PASKIL.

##  ##

## Installation ##
Installation instructions can now be found on the Installation [wiki](http://code.google.com/p/paskil/wiki/Installation).

##  ##

## Citing ##
If you use PASKIL in published research, please include the following citation:

Peters N, Python All-Sky Imaging Library, `http://code.google.com/p/paskil/`, 2009

For the sake of others who may wish to repeat your work, please include the version, revision or check-out date of the PASKIL code that you used in your bibliography entry. See [here](http://software.ac.uk/so-exactly-what-software-did-you-use) for some useful advice on citing software in academic publications.

##  ##

## Documentation ##
Documentation produced using pydoc can be found in the Docs folder of the source distributions. Alternatively, you can produce them yourself using pydoc!

Solutions to some of the common problems with PASKIL can be found [here](http://code.google.com/p/paskil/wiki/CommonProblems)

There is also an overview of the software (with more information about doing absolute calibration of images) in chapter 4 of my [thesis](http://hdl.handle.net/10852/11226).

##  ##

## Other Stuff ##
Do you operate an all-sky imager? Check out [pysces-asi](http://code.google.com/p/pysces-asi/) for Python-based all-sky camera control software.

---

### Version 4.1 ###
  * Numerous minor bug fixes.
  * Proper y-axes labeling on keograms

### Version 4.0 ###
  * Re-written keogram module, using numpy and multiprocessing
  * New cKeo extension module to handle keogram interpolation
  * Variable, asymmetric fields of view on keograms
  * Specification of time labels on keograms
  * automatic thresholds on colour tables
  * Full JPEG support with exif read/write functions
  * Significant optimisations in dataset creation and manipulation.
  * New (experimental) allskyVideo module for producing mpegs from datasets.

### Version 3.2 ###
  * Major testing and debugging work
  * Added allskyPlot module for data visualisation
  * Extended keogram functionality
  * Some optimization - plenty left to do though!

### Version 3.1.4 ###
  * Added iterator protocol to datasets.
  * Minor bug fixes in allskyData (cPickle problem under Windows).
  * Added psyco to allskyImage module to speed up computationally expensive operations.

### Version 3.1.3 ###
  * Major bug fix in cSquish extension.
  * Additional Windows compatibility.
  * Plug-in architecture now ready to support raw\_image objects.

### Version 3.1.2 ###
  * Numerous bug fixes.
  * Compatible with matplotlib 0.98 and basemap 0.99.
  * First Windows compatible version.
  * Moved project to here!
  * Improved PMIS file compatibility.

### Version 3.1.1 ###
  * cRaw and cSquish extension modules for raw image processing - not stable yet!
  * allskyRaw module - not stable either!

### Version 3.1 ###
  * Added allskyProj module for producing map projections.

### Version 3.0 ###
  * Added full pydocs.
  * Fast dataset storage and retrieval using cPickle module.
  * Added limited 16bit image support.
  * Fixed alignNorth bugs.
  * Added proper exception handling.
  * Multi-threaded keogram creation.
  * Added FITS file support.

### Version 2.0 ###
  * Large scale refactoring.
  * Split into modules and adopted object-orientated structure.
  * Added allskyCalib module.

### Version 1 ###
  * Proof of concept.
  * Functional structure with basic image processing options.