Since I no longer have access to a Windows machine, I have given up on making PASKIL multi-platform. While I am sure it could be made to work (probably quite easily) on Windows, I think that it is best I concentrate my efforts on making it work properly on linux. If you desperately want to use it on Windows, then get in touch and I will see what I can do.


# Prerequisites #
Before installing PASKIL you will need to install several other packages that it uses and depends on. Before downloading these from the web and trying to build them from source, you should check out your usual software repositories as most of them are probably available (and this is by far the easiest method to get them). However, where specific versions are required, you should check that the version in your repository is recent enough.


The packages you will need before PASKIL-4.0 will work are:

> ### Python ###
> Version 2.6 or 2.7. Download from http://www.python.org/
> ### The Python Image Library (PIL) ###
> Download from http://www.pythonware.com/products/pil/
> ### Matplotlib ###
> Version > 0.99. Download from http://matplotlib.sourceforge.net/
> ### Numpy ###
> Version > 1.1. Download from http://numpy.scipy.org/
> ### Matplotlib Basemap Toolbox ###
> Download from http://matplotlib.sourceforge.net/toolkits.html
> ### Pyfits ###
> Version > 2.3.1. Download from http://www.stsci.edu/resources/software_hardware/pyfits
> ### Pyexiv2 ###
> Version > 0.1.3. Download from http://tilloy.net/dev/pyexiv2/download.htm. If you get problems linking to the libexiv2.so.? library then you might  need to add /usr/local/lib to your library path. You can do this by adding /usr/local/lib to the /etc/ld.so.conf file and then running ldconfig. Or you can create a link to libexiv2.so.? in /lib.


# Pymedia #
From V4.0 PASKIL includes an allskyVideo module, which uses the pymedia package to create mpeg videos from allsky images. To use this module, you will need to install pymedia. However, the rest of PASKIL will work fine without it - so this should be considered optional.

It appears that pymedia is no longer being developed, and so installation can be a bit tricky. The most important thing to realise is that it can ONLY be built with gcc-3.x, trying to build it with gcc-4.0 or later will not work. The following installation sequence worked for me:

  * Install gcc-3.4 and g++-3.4. For Ubuntu users, the easiest way to do this is to add an old repository (in my case the Dapper one) to /etc/apt/sources.list. Open /etc/apt/sources.list in a text editor and add a line that says:`deb http://gb.archive.ubuntu.com/ubuntu dapper main` Then do:
```
$ sudo apt-get update
$ sudo apt-get install gcc-3.4 g++3.4
```

  * Download pymedia from http://sourceforge.net/projects/pymedia/files/pymedia/pymedia-1.3.7.3/pymedia-1.3.7.3.tar.gz/download
  * Install the prerequisites for pymedia (you need to get the development versions of all the packages)
  * Unpack the archive: ` $ tar -xzf pymedia-1.3.7.3.tar.gz `
  * If you have a 64bit version of Linux, then you need to patch the version of pymedia that you have just downloaded (you don't need to do this if you are running a 32bit version):
    * Download the patch from http://indashpc.org/vbullettin/viewtopic.php?p=4990&sid=c0b60e304ee8aa3b884fd83196e5734e
    * Unpack the patch archive and follow the instructions for applying the patch.
  * Build and install pymedia:
```
$ cd pymedia-1.3.7.3
$ export CC=gcc-3.4
$ export CXX=g++-3.4
$ python setup.py build
$ python setup.py install
```
  * Take a deep breath, and test the installation:
```
$ python
>>> import pymedia
```


# Installing PASKIL #
Once all the prerequisite packages have been installed PASKIL can be installed:

  * Download the PASKIL package from the download page
  * Install it:
```
$ tar -xzf PASKIL-4.0.tar.gz
$ cd PASKIL-4.0
$ python setup.py build
$ sudo python setup.py install
```