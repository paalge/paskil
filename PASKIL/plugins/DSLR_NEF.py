

#import required modules
from PASKIL import allskyImage, allskyImagePlugins,allskyRaw

#start plugin class definition
class NEF_Format:
    """
    An plugin for NEF files - this is still under construction and is only being used for testing 
    at the moment.
    """
    def __init__(self):
        """
        This method is run when the class is instanciated and is used to set up class attributes
        """
        self.name = "Imaginary image format used for example" #This is not used anywhere in the code yet, but is probably a good idea
    
    ###################################################################################
    
    def test(self, image_filename, info_filename):
        """
        This method should test to see whether the PIL image that is passed to it is of the type that this
        plugin was designed to read. The image argument is a PIL image, and the info_file is either a file
        pointer to a metadata file or None. Remeber that this method may be passed images that are not of 
        the correct type and in this case should return False rather than raising an exception - expect to
        use lots of try except blocks! The method should return True if the image is of the correct type and
        False otherwise. It is your own responsibility to make sure that plugins can uniquely identify their
        image types and do not overlap with other plugins.
        """
        if image_filename.endswith(".NEF"):
            return True
        
        return False
            
    ###################################################################################    
        
    def open(self, image_filename, info_filename):
        """
        This method should return an instance of the allskyImage.allskyImage class. The method needs to 
        read the metadata for the image, either from the image itself or from the optional info file. The
        data should be stored in dictionaries in the format specified in the allskyImagePlugins documentation.
        The image argument is a PIL image, and the info_file is either a file pointer to a metadata file or 
        None.
        """
        
        #read image header data, here we assume that the image header already contains all the metadata in the correct format
        info = {'header':{},'camera':{'fov_angle':'90','lens_projection':'equisolidangle','Radius':'1045','x_center':'1969','y_center':'1342'},'processing':{}}
    
        #return new allskyImage object
        return allskyRaw.rawImage(image_filename,info)
        
    ###################################################################################
###################################################################################

#register the plugin with PASKIL, without this step the plugin will just be ignored! The argument to the register function should be an instance of your plugin class
allskyImagePlugins.register(NEF_Format())
