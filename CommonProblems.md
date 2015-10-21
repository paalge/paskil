# Introduction #
This page is designed to help users find solutions to their problems with PASKIL. Lets face it, it's not the easiest piece of software to use ever, especially for people not familiar with Python. However, most of the error messages you get will probably have appeared on someone else's screen before and if you're lucky they will have posted their solutions on this page! If not, then maybe you are the first. In which case, please take the time to note down your solution here (unless it is a bug in PASKIL, in which case please tell me) - it's for the greater good :)


# Things to try first #
  * Has someone already solved your problem and described what they did below?
  * Do you have the latest release? It is still under active development and is constantly changing.
  * Have you looked at the documentation for the function/method. Some of the arguments you have to pass are slightly counter-intuitive, be careful!
  * Make sure you have imported all the required plugins for the images you want to open. You have to do this, PASKIL doesn't do it for you, and typing `from PASKIL.plugins import *` won't work, you have to import each one individually.
  * Convert your images to 8bit before doing anything else with them. PASKIL's support of 16bit images is sketchy at best, especially since PIL and matplotlib don't fully support them.


---

# Known Problems #
**Error! allskyImagePlugins.DSLR\_LYR.open(): Cannot read site info file, too many words per line**
  * If you are using Windows then this is probably caused by the difference between Unix and Windows newline characters. Re-type your site info file using a native text editor and make sure that each entry is on its own line.

**TypeError: idle\_showwarning() takes exactly 4 arguments (5 given)**

  * Don't use the Windows IDLE! I haven't had time to look into this properly, but your script will work fine if you run it from the command prompt rather than from the IDLE.

**ValueError: Max threshold is outside of image pixel value range**

  * You have entered a threshold that is larger than the max pixel value for the image that you are trying to apply a colour table to. Or......
  * You have tried to create a histogram for a 16bit image using the PIL histogram method e.g. `hist = im.getImage().histogram()`. This doesn't work, since PIL will always return a histogram with 256 entries (limited 16bit support). Either convert your image to 8bit, or use the allskyColour.histogram method.

**Raw images do not load properly**

  * This is probably caused by a bug in PIL, see [here](http://code.google.com/p/paskil/issues/detail?id=1).



---
