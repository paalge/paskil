"""
Introduction:

    The allskyData module provides a set of tools to simplify the use of large data sets which may span 
    across a complicated directory structure. It provides an abstraction layer between the user and the 
    locations of the images to be used, allowing image access by time rather than filename.
    
    
Concepts:
    
    The allskyData module contains a dataset class. This is essentially three ordered lists. One of 
    filenames, one of times and one of filenames for site information files. A dataset object is created by 
    indexing the images in a directory structure. A dataset can only contain images of the same Wavelength
    and mode (see PIL handbook for description of mode). However, datasets containing different image 
    formats are possible. Once created, a dataset object allows images to be retrieved by their creation time 
    rather than their filename.

    For very large datasets, the indexing process can take some time. There is therefore the option to save
    the dataset object once it is created. This allows the same dataset to be loaded rapidly in the future. 
    However, no checks are made to ensure that the dataset object still matches the actual data. If the data
    has been changed in any way, then this may lead to unexpected results.
    

Example:
    
    The following example creates a dataset of all the png and jpg files in the directory "Allsky Images". 
    The recursive option is not used, so subfolders will not be included. Only images corresponding to a 
    wavelength of 630nm are included. A list of all the files between 18:30 and 19:30 on the 4/2/2003 is 
    then printed to the screen.

        from PASKIL import allskyData

        #create dataset object
        dataset=allskyData.new("Allsky Images","630",["png","jpg"],site_info_file="site_info.txt") 
        
        #create datetime object defining start time for list
        start_time=datetime.datetime.strptime("04 Feb 2003 18:30:00 GMT","%d %b %Y %H:%M:%S %Z")
        
        #create datetime object defining end time for list 
        end_time=datetime.datetime.strptime("04 Feb 2003 19:30:00 GMT","%d %b %Y %H:%M:%S %Z") 
    
        #get names of files between start and end times.
        filenames=dataset.getFilenamesInRange(start_time,end_time) 

        print filenames
"""

################################################################################################################################################################

import allskyImage,misc #imports from PASKIL
import glob,datetime,cPickle,os #imports from other python modules

#Functions:

###################################################################################        

def combine(datasets):
    """
    Returns a dataset object which is the combination of all the datasets in the specified list. The 
    datasets argument should be a list of dataset objects. It is not possible to combine datasets with 
    different wavelengths, image modes or colour tables. It is however, possible to combine datasets with 
    different filetypes and different site information files. Files which appear in more than one of the 
    datasets to be combined, will only appear once in the new dataset.
    """
    for i in range(1,len(datasets)):
        #check if datasets can be combined
        if datasets[0].getWavelength() != datasets[i].getWavelength() or datasets[0].getMode() != datasets[i].getMode() or datasets[0].getColour_table() != datasets[i].getColour_table():
            raise ValueError, "Incompatible datasets"
    
    #create tuple list from dataset data
    tuple_list=[]
    filetypes=[]
    radii=[]
    fov_angles=[]
    for i in range(len(datasets)):
        filetypes=filetypes+datasets[i].filetypes()
        
        for j in range(len(datasets[i].getFilenames())):
            tuple_list.append((datasets[i].getTimes()[j],datasets[i].getFilenames()[j],datasets[i].getSite_info_files()[j]))
        
        #get radii and fov angles
        radii.append(datasets[i].getRadii())
        fov_angles.append(datasets[i].getFov_angles())
        
    #sort the list into chronological order and remove duplicate entries
    tuple_list=list(set(tuple_list))
    tuple_list.sort(misc.tupleCompare)
    
    #remove duplicate entries from filetypes list
    filetypes=list(set(filetypes))
    
    return dataset(tuple_list,datasets[0].getWavelength(),filetypes,datasets[0].getMode(),set(radii),set(fov_angles),datasets[0].getColour_table())

###################################################################################        

def fromList(file_names,wavelength,filetype,site_info_file=""):
    """
    Creates a dataset from a list of filenames. The file_names argument should be a list of strings specifying
    the filenames of the files to be included. The wavelength argument should be a string that matches the 
    value of the 'Wavelength' field in the image metadata see allskyImagePlugins module for details. The 
    site_info_file option should be the filename of the site information file (if one is required). This is
    an optional file containing image metadata. A filepointer to this file is passed to the allskyImagePlugin
    open method, see the allskyImagePlugins module for details. The default value is "", no site_info_file. The
    filetype argument is a list of filetypes (e.g. ["png","jpg"]), so a dataset spanning many filetypes can be 
    prodcued using this function (if only a single filetype is desired then it must be specified as ["filetype"]).
    A dataset spanning images with different site info files can only be produced by combining several datasets 
    with different site info files. Note that images in the list supplied which do not conform to the dataset's 
    parameters will be ignored. If no images are found that can be added to the dataset then ValueError is raised.
    """
    data=[]
    mode=None
    radii=[]
    fov_angles=[]
    
    #check that filetypes argument is a list - this is a common user error!
    if type(filetype) != type(list()):
        raise TypeError,"Incorrect type for filetype argument. Expecting list."
    
    for filename in file_names:
        #check if file is of correct type
        if not filename.endswith(tuple(filetype)):
            continue #if not then skip it
        
        #attempt to create an allskyImage object, if there is no plugin for it, then skip this file
        try:    
            current_image=allskyImage.new(filename,site_info_file) #create an allskyImage
        
        except TypeError:
            continue
        
        #check if the image has the correct wavelength
        if current_image.getInfo()['header']['Wavelength'].find(wavelength) == -1:
            continue #if image has wrong wavelength then skip it
        
        #check the image has the correct mode and colour table
        try:
            current_colour_table=current_image.getInfo()['processing']['colour_table']
        except KeyError:
            current_colour_table=None
        
        if mode == None:
            mode = current_image.getMode()
            colour_table=current_colour_table
            
        if current_image.getMode() != mode:
            print "Warning! allskyData.fromList(): Skipping file ",filename,". Incorrect image mode."
            continue
        
        if current_colour_table != colour_table:
            print "Warning! allskyData.fromList(): Skipping file ",filename,". Incorrect colour table."
            continue
            
        #add radius of image to radii list    
        if radii.count(current_image.getInfo()['camera']['Radius']) ==0:
            radii.append(float(current_image.getInfo()['camera']['Radius']))
        
        #add fov_angle of image to fov list
        fov=float(current_image.getInfo()['camera']['fov_angle'])
        if fov_angles.count(fov) ==0:
            fov_angles.append(fov)
        
        time=datetime.datetime.strptime(current_image.getInfo()['header']['Creation Time'],"%d %b %Y %H:%M:%S %Z")#read creation time from header
        data.append((time,filename,site_info_file)) #store filename and creation time as a tuple in the data list
    
    #check to make sure the dataset is not empty
    if len(data) ==0:
        raise ValueError,"No images were compatible with the dataset format, ensure you have imported the required plugins,that the wavelength string matches that in the image header, and that you have specified any relevant site info files."
    
    #sort the list into chronological order
    data.sort(misc.tupleCompare)
    
    #return a dataset object
    return dataset(data,wavelength,[filetype],mode,radii,fov_angles,colour_table)    

    
###################################################################################    

def load(filename):
    """
    Loads a dataset object from a file. Dataset files can be produced using the save() method.
    """
    f=open(filename,"r")
    dataset=cPickle.load(f)
    f.close()
    return dataset
    
###################################################################################    
    
def new(directory,wavelength,filetype,site_info_file="",recursive=""):
    """
    Returns a dataset object containing images of type filetype, taken at a wavelength of wavelength (needs
    to be the same value as in the image header under 'Wavelength' see allskyImagePlugins module for details), 
    contained in the specified directory. If recursive is set to "r" then all subdirectories of "directory" 
    will be searched, the default value is "" no recursive search. The site_info_file option should be the 
    filename of the site information file (if one is required). This is an optional file containing image 
    metadata. A filepointer to this file is passed to the allskyImagePlugin open method, see the allskyImagePlugins 
    module for details. The default value is "", no site_info_file. The filetype argument is a list of 
    filetypes (e.g. ["png","jpg"]), so a dataset spanning many filetypes can be prodcued using this function 
    (if only a single filetype is desired then it must be specified as ["filetype"]). A dataset spanning images 
    with different site info files can only be produced by combining several datasets with different site info files.  
    All arguments to this function should be strings, including wavelength. All images in a dataset must have the 
    same mode and the same colour table. Note that images in the directory supplied which do not conform to the 
    dataset's parameters will be ignored.
    """
    
    search_list=[]
    
    #check that filetypes argument is a list - this is a common user error!
    if type(filetype) != type(list()):
        raise TypeError,"Incorrect type for filetype argument. Expecting list."
    
    for i in range(len(filetype)):
        if recursive == "r":
            #sweep the directory structure recursively
            search_list=search_list+misc.findFiles(directory,"*."+filetype[i])

        else:
            #only look in current directory
            search_list=search_list+glob.glob(directory+os.sep+"*."+filetype[i])
    
    return fromList(search_list,wavelength,filetype,site_info_file)
        
###################################################################################

#class definition
class dataset:
    """
    Essentially the dataset class operates like a hash table, with times (datetime objects) as keys and 
    filenames of images and their corresponding site_info_files (if any) as values.
    """
    def __init__(self,data,wavelength,filetype,mode,radii,fov_angles,colour_table):
        
        #check that the filetype argument is of the correct type - this is a common error to make
        if type(filetype) != type(list()):
            raise TypeError, "Incorrect type, "+str(type(filetype))+" for filetype argument, expecting list"
        
        #set class attributes
        self.__wavelength = wavelength
        self.__radii=list(set(radii))
        self.__fov_angles = fov_angles
        self.__mode=mode
        self.__filetype=filetype
        self.__times=[]
        self.__filenames=[]
        self.__site_info_files=[]
        self.__colour_table=colour_table

        for i in range(len(data)):
            self.__times.append(data[i][0])
            self.__filenames.append(data[i][1])
            self.__site_info_files.append(data[i][2])
            
    ###################################################################################    
    #define getters
    def getWavelength(self):
        """
        Returns a string containing the wavelength of the dataset. This will have the same format as the
        'Wavelength' field in the image metadata, see the allskyImagePlugins module for details.
        """
        return self.__wavelength
        
    def getColour_table(self):
        """
        Returns the colour table that has been applied to the images in the dataset, or None.
        """
        return self.__colour_table
        
    def getRadii(self):
        """
        Returns a set (only unique values) of the field of view radii of the images in the dataset in pixels.
        """
        return self.__radii
        
    def getFov_angles(self):
        """
        Returns a set (only unique values) of field of view angles contained in the dataset
        """
        return set(self.__fov_angles)
    
    def getMode(self):
        """
        Returns a string containing the mode of the images in the dataset, e.g. "RGB" see the PIL handbook
        for details about different image modes.
        """
        return self.__mode
    
    def getFiletypes(self):
        """
        Returns a list of strings of the filetypes contained in the dataset e.g. ["png","jpg"]
        """
        copy=[]
        for element in self.__filetype:
            copy.append(element)
        return copy
    
    def getFilenames(self):
        """
        Returns a list of strings containing the filenames of all the images contained in the dataset.
        The list will be ordered chronologically with respect to the capture times of the images.
        """
        copy=[]
        for element in self.__filenames:
            copy.append(element)
        return copy
    
    def getTimes(self):
        """
        Returns a list of datetime objects corresponding to the capture times of all the images in the
        dataset. The list will be ordered chronologically.
        """
        copy=[]
        for element in self.__times:
            copy.append(element)
        return copy
    
    def getSite_info_files(self):
        """
        Returns a list of strings containing the filenames of the site_info_files corresponding to the 
        images in the dataset. The list will have one entry for each image in the dataset and will be 
        ordered chronologically with respect to the capture times of the images. If the images don't 
        have site_info_files then a list of empty strings will be returned.
        """
        copy=[]
        for element in self.__site_info_files:
            copy.append(element)
        return copy    
    ###################################################################################    
    
    def crop(self,start_time,end_time):
        """
        Returns a new dataset object which only spans the time range between start_time and end_time.
        Both arguments should be datetime objects.
        """
        cropped_data=[]
        
        #get selection of dataset
        cropped_filenames=self.getFilenamesInRange(start_time,end_time)
        
        for filename in cropped_filenames:
            #get index of name in list
            index=self.__filenames.index(filename[0])
            
            #create data entry
            cropped_data.append((self.__times[index],filename[0],self.__site_info_files[index]))
        
        if len(self.__radii)==1 and len(self.__fov_angles) == 1:
            #create new dataset
            cropped_dataset=dataset(cropped_data,self.__wavelength,self.__filetype,self.__mode,self.__radii,self.__fov_angles,self.__colour_table)
        else:
            raise ValueError, "Operation not permitted on a dataset containing different fov angles and radii"
        
        return cropped_dataset
    
    ###################################################################################    
            
    def getAll(self):
        """
        Returns a list of tuples of strings containing the names of all the files in the dataset and 
        their corresponding site info files, e.g. [(image1,site_info1),(image2,site_info2)...]
        """
        tuple_list=[]
        for i in range(len(self.__filenames)):
            tuple_list.append((self.__filenames[i],self.__site_info_files[i]))
        
        return tuple_list
        
    ###################################################################################            
    
    def getFilenamesInRange(self,time1,time2):
        """
        Returns a list of tuples of strings containing the names of all the files in the dataset that 
        correspond to times between time1 and time2 inclusive and their corresponding site info files, 
        e.g. [(image1,site_info1),(image2,site_info2)...]
        
        The list will be ordered in chronological order. The time arguments should be datetime objects.
        If there are a lot of images in the range then it is recommended to use this method rather than
        getImagesInRange(time1,time2), as it uses far less memory. Both arguments should be datetime objects.
        """
        try:
            start_index=self.__times.index(time1)
        except ValueError:
            start_index=0
        try:
            end_index=self.__times.index(time2)
        except ValueError:
            end_index=len(self.__times)-1
        
        filenames=[]
        for i in range(start_index,end_index+1):
            if self.__times[i] >= time1 and self.__times[i] <= time2:
                filenames.append((self.__filenames[i],self.__site_info_files[i]))
                
        
        if filenames == []:
            return None    
        
        return filenames
        
    ###################################################################################            
    
    def getImage(self,time):
        """
        Returns an allskyImage object containing the image data for the specified time. If no image 
        exists for the specified time then None is returned. The time argument should be a datetime 
        object.
        """
        try:
            index = self.__times.index(time)
        except ValueError:
            return None
        
        return allskyImage.new(self.__filenames[index],self.__site_info_files[index])
        
    ###################################################################################        
    
    def getImagesInRange(self,time1,time2):
        """
        Returns a list of allskyImage objects containing all the images that correspond to times between
        time1 and time2 inclusive. The list will be ordered in chronological order. The time arguments 
        should be datetime objects. This function creates a new instance of the allskyImage class for 
        each image in the range. If there are a large number of images in the range then it will use a 
        lot of memory and may result in memory overflow - you have been warned!
        """
        try:
            start_index=self.__times.index(time1)
        except ValueError:
            start_index=0
        try:
            end_index=self.__times.index(time2)
        except ValueError:
            end_index=len(self.__times)-1
        
        images=[]
        for i in range(start_index,end_index+1):
            if self.__times[i] >= time1 and self.__times[i] <= time2:
                images.append(allskyImage.new(self.__filenames[i],self.__site_info_files[i]))
        
        if images == []:
            return None
        
        return images
        
    ###################################################################################    
    
    def getNearest(self,time):
        """
        Returns an allskyImage object corresponding to the image in the dataset which has a creation time 
        closest to the specified time. The time argument should be a datetime object. 
        """
        try:
            index = self.__times.index(time) #see if an image exists with the exact time
            
        except ValueError:
            index=0
            while self.__times[index]<time and index < len(self.__times)-1: #if not then search for the nearest time
                index=index+1
            if self.__times[index] - time > self.__times[index-1] - time:
                index=index-1
                    
        return allskyImage.new(self.__filenames[index],self.__site_info_files[index])
        
    ###################################################################################
    
    def save(self,filename):
        """
        Saves the dataset object in specified file. It can be retrieved at a later date using the load()
        function. However, be aware that changing the image files, the site information files or the 
        directory structure of the images stored in a dataset after it has been created may cause 
        unpredictable results. If you need to change the files somehow, then it is better to create a 
        new dataset object using the new files.
        """
        #open file for writing
        f=open(filename,"w")
        
        #pickle the dataset object and save it to the file
        cPickle.dump(self,f,cPickle.HIGHEST_PROTOCOL)
        
        #close file
        f.close()
    
    ###################################################################################                
###################################################################################    
    
            
