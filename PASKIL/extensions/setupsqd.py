from distutils.core import setup, Extension

setup(name="cSquish", version="1.0",
      ext_modules=[Extension("PASKIL.extensions.cSquish", ["cSquish.c",
                                                           "bitarray.c",
                                                           "chuffman.c",
                                                           "huflocal.c" ])])
