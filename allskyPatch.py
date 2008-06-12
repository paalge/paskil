import allskyKeo,stats

import calendar,sys


#Functions:

###################################################################################
			
def locatePatchlinesInKeogram(keo,time_res,angle_res):
	
	#calculate time resolution in pixels
	start_secs=calendar.timegm(keo.start_time.timetuple()) #start time of keogram in seconds since epoch
	end_secs=calendar.timegm(keo.end_time.timetuple()) #end time of keogram in seconds since epoch
	
	time_res_pix=int((float(keo.width)/float(end_secs-start_secs))*time_res)

	#calculate angular resolution in pixels
	angle_res_pix=int((float(keo.height)/float(2.0*keo.fov_angle))*angle_res)
	
	#define start and end pixels for patch search (needed to prevent median filtering from exceeding array dimensions)
	start_time_pix=int(float(time_res_pix)/2.0)
	end_time_pix=int(keo.width-(float(time_res_pix)/2.0)-1)
	
	start_angle_pix=int(float(angle_res_pix)/2.0)
	end_anlge_pix= int(keo.height-(float(angle_res_pix)/2.0)-1)
	
	#define angles and times which will be looked at
	angles = range(start_angle_pix,end_anlge_pix,angle_res_pix)
	times = range(start_time_pix,end_time_pix,time_res_pix)

	#create pixel access object
	keo_pix=keo.image.load()
	
	#sweep keogram from top to bottom looking for patches
	horizontal_strips=[]
	for y in angles:
		#create list to hold filtered intensities
		filtered_intensities=[]

		#take slice through keogram, median filtering each element with a box size defined by the angle and time resolution
		for x in times:
			intensities=[]
			for i in range(int(-time_res_pix/2)+1,int(time_res_pix/2)+1):
				for j in range(int(-angle_res_pix/2)+1,int(angle_res_pix/2)+1):
					intensities.append(keo_pix[x+i,y+j]) #store all intensities in a box of size time_res_pix by angle_res_pix
					
			filtered_intensities.append(stats.median(intensities)) #store median intensity in intensities list

		#exclude any list elements which lie within the auroral region
		if min(keo.OCB) <= y: #note that the y dimensions of the image start from the top left corner
			inten_no_aurora=[]
			j=0
			for i in times:
				if keo.OCB[i]>y:
					inten_no_aurora.append(filtered_intensities[j])
				j=j+1
			if len(inten_no_aurora)==0:
				median_intensity=256
				stdDev=100
			else:
				#find median and stdDev of intensities without aurora
				median_intensity=stats.median(inten_no_aurora)
				stdDev=stats.stdDev(inten_no_aurora)
			
			#set elements within the auroral region to the median intensity so that they don't interfere with patch location
			j=0
			for i in times:
				if keo.OCB[i]<=y:
					filtered_intensities[j]=median_intensity
				j=j+1
		
		else:
			#find median and stdDev of intensities
			median_intensity=stats.median(filtered_intensities)
			stdDev=stats.stdDev(filtered_intensities)
		
		#Look for patches (regions with an intensity greater than two stdDevs above the median)
		threshold=median_intensity + stdDev
		
		i=0
		patch_lines=[]
		
		#skip strips with no intensities over the threshold
		if max(filtered_intensities)<=threshold:
			continue
		
		while i<len(filtered_intensities)-1:
			if filtered_intensities[i]<threshold:
				i=i+1
				continue
			else:
				patch_start_pix=(start_time_pix+(i*time_res_pix))
				while i<len(filtered_intensities)-1 and filtered_intensities[i]>=threshold and keo.OCB[times[i]]>=y:
					i=i+1
				if keo.OCB[times[i]]<=y:
					patch_end_pix=(start_time_pix+((i-1)*time_res_pix))
				else:
					patch_end_pix=(start_time_pix+(i*time_res_pix))
				
			patch_lines.append(patchLine(patch_start_pix,patch_end_pix,y))
	
		horizontal_strips.append(horizontalStrip(patch_lines,y))
		
	
	return horizontal_strips
		
###################################################################################					
		
def plotPatchLines(keo,horizontal_strips):

	#create new keogram object
	new_keogram=allskyKeo.keogram(keo.image,keo.mode,keo.colour_table,keo.start_time,keo.end_time,keo.angle,keo.fov_angle,keo.OCB,keo.strip_width,keo.intensities)
	
	#load the pixel values
	keo_pix = new_keogram.image.load()
	
	#set the colour of the patchline depending on the image mode of the keogram
	if new_keogram.mode == "RGB":
		black = (0,0,0)
	elif new_keogram.mode == "L":
		black = 0
	else:
		print "Error! allskyPatch.plotPatchLines(): Unsupported image mode for keogram: ",keo.mode
		sys.exit()
	
	for i in range(len(horizontal_strips)):
		for x in range(len(horizontal_strips[i].occupied_pixels)):
			keo_pix[horizontal_strips[i].occupied_pixels[x],horizontal_strips[i].y_pixel]=black
					
	return new_keogram
	
###################################################################################

def plotPaths(keo,path_list):
	
	#create list to store patchlines that have already been plotted
	already_plotted=[]
	
	#create new keogram object
	new_keogram=allskyKeo.keogram(keo.image,keo.mode,keo.colour_table,keo.start_time,keo.end_time,keo.angle,keo.fov_angle,keo.OCB,keo.strip_width,keo.intensities)
	
	#load the pixel values
	keo_pix = new_keogram.image.load()

	#set the colour of the patchline depending on the image mode of the keogram
	if new_keogram.mode == "RGB":
		black = (0,0,0)
	elif new_keogram.mode == "L":
		black = 0
	else:
		print "Error! allskyPatch.plotPaths(): Unsupported image mode for keogram: ",keo.mode
		sys.exit()
	
	for path in path_list:
		for patch_line in path.patchlines_on_path:
			
			if already_plotted.count(patch_line) == 0:
				#plot patchline
				for x in range(patch_line.start_pix, patch_line.end_pix+1):
					keo_pix[x,patch_line.y_pix] = black
				
				already_plotted.append(patch_line)
			
	return new_keogram
	
###################################################################################
					
def newPath(patch_lines,path_list):
	path(patch_lines,path_list)

###################################################################################					

class horizontalStrip:

	def __init__(self, patch_lines,y_pixel):
		self.patch_lines=patch_lines
		self.y_pixel=y_pixel
		self.__findOccupiedPix__()
		
	###################################################################################	
		
	def findOccupiedPix(self):
		self.occupied_pixels=[]
		self.empty_pixels=[]
		
		if len(self.patch_lines)!=0:
			
			#list start and end pixels in patch_lines
			start_pixs=[]
			end_pixs=[]
			
			for line in self.patch_lines:
				start_pixs.append(line.start_pix)
				end_pixs.append(line.end_pix)
			
			#calculate occupied and empty pix lists
			for i in range(len(self.patch_lines)):
				for x in range(self.patch_lines[i].start_pix,self.patch_lines[i].end_pix+1):
					self.occupied_pixels.append(x)
			for x in range(min(start_pixs),max(end_pixs)):
				if self.occupied_pixels.count(x) == 0:
					self.empty_pixels.append(x)
					
	###################################################################################
						
	def addPatchline(self,patch_line):
		overlap=False
		
		#find out if the new patchline overlaps with an existing one
		for i in range(patch_line.start_pix,patch_line.end_pix+1):
			if self.occupied_pixels.count(i) !=0:
				overlap=True
		#if the new patch_line doesn't overlap with any existing lines, then simply add it to the list
		if overlap:
			self.patch_lines.append(patch_line)
			self.findOccupiedPix()
		
		#else, merge it with the existing lines that it overlaps with. This is done by adding the patchline to the list, finding the occupied pixels and then recalculating the patchlines
		
		else:
			self.patch_lines.append(patch_line)
			self.findOccupiedPix()
			
			#sort empty and occupied pixel lists and delete duplicate entries
			self.occupied_pixels=list(set(self.occupied_pixels))
			self.empty_pixels=list(set(self.empty_pixels))
			self.occupied_pixels.sort()
			self.empty_pixels.sort()
			
			#create new patchlines corresponding to new occupied pixel configuration
			start_pix=self.occupied_pixels[0]
			self.patch_lines = []
			for j in range(len(self.occupied_pixels)-1):
				if self.occupied_pixels[j+1]-self.occupied_pixels[j] == 1:
					end_pix=self.occupied_pixels[j+1]
					continue
				else:
					end_pix=self.occupied_pixels[j]
					self.patch_lines.append(patchLine(start_pix,end_pix,self.y_pixel))
					start_pix=self.occupied_pixels[j+1]
			if start_pix != end_pix:
				self.patch_lines.append(patchLine(start_pix,end_pix,self.y_pixel))
				
	###################################################################################	
		
	def removePatchline(self,patch_line):
		for i in range(patch_line.start_pix,patch_line.end_pix+1):
			self.occupied_pixels.remove(i)
			self.empty_pixels.append(i)
		for current_line in self.patch_lines:
			if current_line.start_pix == patch_line.start_pix and current_line.end_pix == patch_line.end_pix:
				self.patch_lines.remove(current_line)
				
	###################################################################################					
###################################################################################
							
class patchLine:
	def __init__(self, start,end,y_pixel):
		self.start_pix=start
		self.end_pix=end
		self.y_pix=y_pixel
		self.neighbours=[]
		
	###################################################################################
							
	def addNeighbour(self,patchLine):
		self.neighbours.append(patchLine)
		
	###################################################################################						
###################################################################################		

class path:

	def __init__(self,patch_lines,path_list):
		self.patchlines_on_path = patch_lines
		self.length=len(self.patchlines_on_path)
		self.forks=[]

		flag = 0
		while flag == 0:
			self.patchlines_on_path.sort(PatchlineCompare) #sort into ascending y_pixel order
			lower_patchlines=[]
			lowest=len(self.patchlines_on_path)-1
			
			for i in range(len(self.patchlines_on_path[lowest].neighbours)):
				if self.patchlines_on_path[lowest].neighbours[i].y_pix > self.patchlines_on_path[lowest].y_pix:
					lower_patchlines.append(self.patchlines_on_path[lowest].neighbours[i])
						
			if len(lower_patchlines) == 1:
				self.patchlines_on_path.append(lower_patchlines[0])
				self.length=self.length+1
			elif len(lower_patchlines) > 1:
				
				for i in range(1,len(lower_patchlines)):
					patchlines_on_new_path=[]
					 
					#copy list of patchlines on path
					for j in range(len(self.patchlines_on_path)):
						patchlines_on_new_path.append(self.patchlines_on_path[j])
					
					#append neighbour to list
					patchlines_on_new_path.append(lower_patchlines[i])
					
					#create new path object for the new path
					path(patchlines_on_new_path,path_list)
					
				#extend current path	
				self.patchlines_on_path.append(lower_patchlines[0])
				self.length=self.length+1
					
			elif len(lower_patchlines) == 0:
				flag = 1
			
			else:
				print "Error! allskyPatch.path.__init__(): Something went wrong!"
				sys.exit()
		
		#add path to path list
		path_list.append(self)
			
###################################################################################	
						
class patchFinder:
	
	def __init__(self,horizontal_strips):
		self.horizontal_strips=[]
		for i in range(len(horizontal_strips)):
			self.horizontal_strips.append(horizontal_strips[i])
		self.horizontal_strips.sort(horizontalStripCompare)

		#close gaps
		self.closeGaps()

		#find neighbours for each patch line object
		for strip in range(len(self.horizontal_strips)):
			if self.horizontal_strips[strip].patch_lines == []: #skip strips with no patch lines
				continue
				
			for patchline in range(len(self.horizontal_strips[strip].patch_lines)):
				
				#look at strips above the current patchline and see if it overlaps with any other patch lines
				if strip != 0: #skip first strip
					for neighbour_patchline in range(len(self.horizontal_strips[strip-1].patch_lines)):
						if self.horizontal_strips[strip].patch_lines[patchline].start_pix > self.horizontal_strips[strip-1].patch_lines[neighbour_patchline].end_pix or self.horizontal_strips[strip].patch_lines[patchline].end_pix < self.horizontal_strips[strip-1].patch_lines[neighbour_patchline].start_pix:
							continue #discard any that don't overlap at all
						else:
							self.horizontal_strips[strip].patch_lines[patchline].addNeighbour(self.horizontal_strips[strip-1].patch_lines[neighbour_patchline])
						
				#look at strips below the current patchline and see if it overlaps with any other patch lines
				if strip != len(self.horizontal_strips)-1:#skip last strip
					for neighbour_patchline in range(len(self.horizontal_strips[strip+1].patch_lines)):
						if self.horizontal_strips[strip].patch_lines[patchline].start_pix > self.horizontal_strips[strip+1].patch_lines[neighbour_patchline].end_pix or self.horizontal_strips[strip].patch_lines[patchline].end_pix < self.horizontal_strips[strip+1].patch_lines[neighbour_patchline].start_pix:
							continue #discard any that don't overlap at all
						else:
							self.horizontal_strips[strip].patch_lines[patchline].addNeighbour(self.horizontal_strips[strip+1].patch_lines[neighbour_patchline])
		#remove patches with no neighbours
		self.removeLonelyPatchLines()
		
	###################################################################################	
							
	def removeLonelyPatchLines(self):
		strip=0	 
		while strip < len(self.horizontal_strips): #loop through all horizontal strips
			patchline=0
			while patchline < len(self.horizontal_strips[strip].patch_lines): #in each strip, loop through all patchlines

				#remove patchlines which don't have any neighbours
				if self.horizontal_strips[strip].patch_lines[patchline].neighbours == []:
						self.horizontal_strips[strip].removePatchline(self.horizontal_strips[strip].patch_lines[patchline])		
						patchline=patchline-1
				patchline=patchline+1
			strip=strip+1
				
	###################################################################################		
	
	def closeGaps(self):		
		
		for i in range(1,len(self.horizontal_strips)-1): #loop through all strips apart from first and last (to prevent exceeding array dimensions)
			if self.horizontal_strips[i].patch_lines == []: #skip strips with no patch lines
				continue
			j=0
			while j < len(self.horizontal_strips[i].empty_pixels): #loop through all empty pixels in the horizontal strip
				#if the strip above and below has an occupied pixel at the same position as the empty pixel then change the pixel to occupied
				if self.horizontal_strips[i-1].occupied_pixels.count(self.horizontal_strips[i].empty_pixels[j]) != 0 and self.horizontal_strips[i+1].occupied_pixels.count(self.horizontal_strips[i].empty_pixels[j]) != 0:
					self.horizontal_strips[i].occupied_pixels.append(self.horizontal_strips[i].empty_pixels[j])
					self.horizontal_strips[i].empty_pixels.remove(self.horizontal_strips[i].empty_pixels[j])
					j=j-1
				j=j+1
			
			#sort empty and occupied pixel lists
			self.horizontal_strips[i].occupied_pixels.sort()
			self.horizontal_strips[i].empty_pixels.sort()
			
			#create new patchlines corresponding to new occupied pixel configuration
			start_pix=self.horizontal_strips[i].occupied_pixels[0]
			self.horizontal_strips[i].patch_lines = []
			for j in range(len(self.horizontal_strips[i].occupied_pixels)-1):
				if self.horizontal_strips[i].occupied_pixels[j+1]-self.horizontal_strips[i].occupied_pixels[j] == 1:
					end_pix=self.horizontal_strips[i].occupied_pixels[j+1]
					continue
				else:
					end_pix=self.horizontal_strips[i].occupied_pixels[j]
					self.horizontal_strips[i].patch_lines.append(patchLine(start_pix,end_pix,self.horizontal_strips[i].y_pixel))
					start_pix=self.horizontal_strips[i].occupied_pixels[j+1]
			if start_pix != end_pix:
				self.horizontal_strips[i].patch_lines.append(patchLine(start_pix,end_pix,self.horizontal_strips[i].y_pixel))		
			
	###################################################################################	
	
	def calculatePaths(self):
		path_list=[]
		
		for current_strip in self.horizontal_strips: #loop through all horizontal strips
			
			for current_patchline in current_strip.patch_lines: #loop through all patchlines in the strip
				already_on_a_path=0
				
				#check if patchline is already on a path
				for path in path_list:
					if path.patchlines_on_path.count(current_patchline) !=0:
						already_on_a_path=1
						break
				
				#if it is then skip it
				if already_on_a_path==1:
					continue
				else:
				#otherwise create a new path starting at the current patchline
					newPath(list([current_patchline]),path_list)	
		
		return 	path_list
		
	###################################################################################								
###################################################################################
				
def horizontalStripCompare(first,second):
	return cmp( first.y_pixel, second.y_pixel )	

###################################################################################
				
def PatchlineCompare(first,second):
	return cmp( first.y_pix, second.y_pix )	

###################################################################################

class pathGroup:

	def __init__(self,path):
		self.path_list=[]
		self.path_list.append(path)
		self.max_path_length=path.length
		self.stripsFlag=False #tells if list of horizontal strips is up to date
		
	###################################################################################	
			
	def __calculateHorizontalStrips__(self):
			self.horizontal_strips=[] # a list of the horizontal strips in the pathgroup
			
			#create list of horizontal strips in the group. The strips only contain the patchlines in the group
			
			#create a list of patchlines in the group
			patchline_list=[]
			for current_path in self.path_list:
				for current_patchline in current_path.patchlines_on_path:
					if patchline_list.count(current_patchline) == 0:
						patchline_list.append(current_patchline)
			
			#sort list into ascending y_pixel order
			patchline_list.sort(PatchlineCompare)
			
			
			#create horizontal strips
	
			while len(patchline_list) != 0:
				patchlines_in_current_strip = []
				patchlines_in_current_strip.append(patchline_list[0])
				patchline_list.remove(patchline_list[0])
				
				i=0
				while i < len(patchline_list):
					if patchline_list[i].y_pix == patchlines_in_current_strip[len(patchlines_in_current_strip)-1].y_pix:
						patchlines_in_current_strip.append(patchline_list[i])
						patchline_list.remove(patchline_list[i])
						i-=1
					i+=1
				
	
				y_pix=patchlines_in_current_strip[len(patchlines_in_current_strip)-1].y_pix
				
				self.horizontal_strips.append(horizontalStrip(patchlines_in_current_strip,y_pix))
			self.horizontal_strips.sort(horizontalStripCompare)
			self.stripsFlag=True	
		
	###################################################################################	
	
	def belongsInGroup(self,path):
		#returns true if path belongs in group, false otherwise
		if self.path_list.count(path) != 0:
			return False #do not add a path already in the group
		
		for path_in_group in self.path_list:
			for patchline_in_group in path_in_group.patchlines_on_path:
				if path.patchlines_on_path.count(patchline_in_group)!=0:
					return True
		
		return False
	
	###################################################################################			
		
	def addPath(self,path):
		#adds a new path to the group
		if path.length > self.max_path_length:
			self.max_path_length=path.length
		self.path_list.append(path)
		self.stripsFlag=False
		
	###################################################################################					
	
	def getStrips(self):
	
		if self.stripsFlag:
			return self.horizontal_strips
		
		else:
			self.__calculateHorizontalStrips__()
			return self.horizontal_strips
		
	###################################################################################							
###################################################################################		

def groupPaths(path_list):
	path_groups=[]
	path_list_copy=[]
	
	#copy path list
	for path in path_list:
		path_list_copy.append(path)
		
	path_groups.append(pathGroup(path_list_copy[0])) #add first path in path list to a group
	path_list_copy.remove(path_list_copy[0])
	i=0
	while i < len(path_groups):
		path_added_to_group = True
		while path_added_to_group:
			path_added_to_group = False
			for path in path_list_copy:
				if path_groups[i].belongsInGroup(path):
					path_added_to_group = True
					path_groups[i].addPath(path)
					path_list_copy.remove(path)
		
		i=i+1
		if len(path_list_copy) != 0:
			path_groups.append(pathGroup(path_list_copy[0])) #create new path group
			path_list_copy.remove(path_list_copy[0])
	return path_groups
	
###################################################################################			
	
def removeSmallGroups(path_groups,threshold_length):
	#remove path_groups which are below a certain length
	
	allowed_groups=[]	
		
	for group in path_groups:
		if group.max_path_length > threshold_length:
			allowed_groups.append(group)
		
	return allowed_groups
	
###################################################################################				

				
				











###################################################################################				

def patchLineXPosCompare(first,second):
	return cmp(first.start_pix,second.start_pix)


###################################################################################	
						
class gapFinder:
	
	def __init__(self,path_group):
	
		self.horizontal_strips=[]
		self.inverted_strips=[]
		
		#get horizontal strips from path group
		self.horizontal_strips=path_group.getStrips()

		#invert the strips so that occupied pixels become unoccupied and patchlines become gaps
		for strip in self.horizontal_strips:
		
			 #sort the patchlines on the strip into x_pixel order
			 strip.patch_lines.sort(patchLineXPosCompare)
		
			 #if the strip only has one patchline then it will not contain any gaps
			 #if the strip has no patchlines then is a gap spanning the whole keogram and should be ignored
			 if len(strip.patch_lines) == 1 or len(strip.patch_lines) == 0 :
			 	self.inverted_strips.append(horizontalStrip([],strip.y_pixel))

			 else: #it must contain at least one gap, so the strip is inverted
			 	i=0
			 	inverted_patchlines=[]
				while i < len(strip.patch_lines)-1:
					inverted_patchlines.append(patchLine(strip.patch_lines[i].end_pix,strip.patch_lines[i+1].start_pix,strip.y_pixel))
					i+=1
			
				self.inverted_strips.append(horizontalStrip(inverted_patchlines,strip.y_pixel))
			
		self.inverted_strips.sort(horizontalStripCompare)
		
		self.closeGaps()
		
		#find neighbours for each patch line object
		for strip in range(len(self.inverted_strips)):
			if self.inverted_strips[strip].patch_lines == []: #skip strips with no patch lines
				continue
				
			for patchline in range(len(self.inverted_strips[strip].patch_lines)):
				
				#look at strips above the current patchline and see if it overlaps with any other patch lines
				if strip != 0: #skip first strip
					for neighbour_patchline in range(len(self.inverted_strips[strip-1].patch_lines)):
						if self.inverted_strips[strip].patch_lines[patchline].start_pix > self.inverted_strips[strip-1].patch_lines[neighbour_patchline].end_pix or self.inverted_strips[strip].patch_lines[patchline].end_pix < self.inverted_strips[strip-1].patch_lines[neighbour_patchline].start_pix:
							continue #discard any that don't overlap at all
						else:
							self.inverted_strips[strip].patch_lines[patchline].addNeighbour(self.inverted_strips[strip-1].patch_lines[neighbour_patchline])
						
				#look at strips below the current patchline and see if it overlaps with any other patch lines
				if strip != len(self.inverted_strips)-1:#skip last strip
					for neighbour_patchline in range(len(self.inverted_strips[strip+1].patch_lines)):
						if self.inverted_strips[strip].patch_lines[patchline].start_pix > self.inverted_strips[strip+1].patch_lines[neighbour_patchline].end_pix or self.inverted_strips[strip].patch_lines[patchline].end_pix < self.inverted_strips[strip+1].patch_lines[neighbour_patchline].start_pix:
							continue #discard any that don't overlap at all
						else:
							self.inverted_strips[strip].patch_lines[patchline].addNeighbour(self.inverted_strips[strip+1].patch_lines[neighbour_patchline])
		#remove patches with no neighbours
		self.removeLonelyPatchLines()
		
		
	###################################################################################	
	
	def closeGaps(self):		
		
		for i in range(1,len(self.inverted_strips)-1): #loop through all strips apart from first and last (to prevent exceeding array dimensions)
			if self.inverted_strips[i].patch_lines == []: #skip strips with no patch lines
				continue
			j=0
			while j < len(self.inverted_strips[i].empty_pixels): #loop through all empty pixels in the horizontal strip
				#if the strip above and below has an occupied pixel at the same position as the empty pixel then change the pixel to occupied
				if self.inverted_strips[i-1].occupied_pixels.count(self.inverted_strips[i].empty_pixels[j]) != 0 and self.inverted_strips[i+1].occupied_pixels.count(self.inverted_strips[i].empty_pixels[j]) != 0:
					self.inverted_strips[i].occupied_pixels.append(self.inverted_strips[i].empty_pixels[j])
					self.inverted_strips[i].empty_pixels.remove(self.inverted_strips[i].empty_pixels[j])
					j=j-1
				j=j+1
			
			#sort empty and occupied pixel lists
			self.inverted_strips[i].occupied_pixels.sort()
			self.inverted_strips[i].empty_pixels.sort()
			
			#create new patchlines corresponding to new occupied pixel configuration
			start_pix=self.inverted_strips[i].occupied_pixels[0]
			self.inverted_strips[i].patch_lines = []
			for j in range(len(self.inverted_strips[i].occupied_pixels)-1):
				if self.inverted_strips[i].occupied_pixels[j+1]-self.inverted_strips[i].occupied_pixels[j] == 1:
					end_pix=self.inverted_strips[i].occupied_pixels[j+1]
					continue
				else:
					end_pix=self.inverted_strips[i].occupied_pixels[j]
					self.inverted_strips[i].patch_lines.append(patchLine(start_pix,end_pix,self.inverted_strips[i].y_pixel))
					start_pix=self.inverted_strips[i].occupied_pixels[j+1]
			if start_pix != end_pix:
				self.inverted_strips[i].patch_lines.append(patchLine(start_pix,end_pix,self.inverted_strips[i].y_pixel))		
			
	###################################################################################	
							
	def removeLonelyPatchLines(self):
		for strip in self.inverted_strips: #loop through all horizontal strips
			for patchline in strip.patch_lines: #in each strip, loop through all patchlines

				#remove gaps which don't have any neighbours
				if patchline.neighbours == []:
				
					#find the corresponding non-inverted strip
					for non_inv_strip in self.horizontal_strips:
						current_strip = non_inv_strip
						if strip.y_pixel == non_inv_strip.y_pixel:
							break
					current_strip.addPatchline(patchline) #adding an inverted patchline is equivalent to removing a gap		
	
	###################################################################################	
	
	def calculatePaths(self):
		path_list=[]
		
		for current_strip in self.inverted_strips: #loop through all horizontal strips

			for current_patchline in current_strip.patch_lines: #loop through all patchlines in the strip
				already_on_a_path=0
				
				#check if patchline is already on a path
				for path in path_list:
					if path.patchlines_on_path.count(current_patchline) !=0:
						already_on_a_path=1
						break
				
				#if it is then skip it
				if already_on_a_path==1:
					continue
				else:
				#otherwise create a new path starting at the current patchline
					newPath(list([current_patchline]),path_list)	
		
		return 	path_list
		
	###################################################################################














				
