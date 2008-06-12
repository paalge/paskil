from distutils.core import setup, Extension

setup(name="cSquish", version="1.0",
      ext_modules=[Extension("PASKIL.extensions.cSquish", ["PASKIL/extensions/cSquish.c",
                                                           "PASKIL/extensions/bitarray.c",
                                                           "PASKIL/extensions/chuffman.c",
                                                           "PASKIL/extensions/huflocal.c" ])])
