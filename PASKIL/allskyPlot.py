import matplotlib
import math

def plot(objects,columns=1):
    fig = matplotlib.pyplot.figure()
    
    rows = int(math.ceil(len(objects)/float(columns)))
    
    #for some reason matplotlib messes up the colourbars if there are more columns than 
    #rows. So as a quick fix we make sure that there aren't!
    if columns > rows:
        rows = columns
       
    i = 1
    #if len(objects) > 1:
    #    fig.subplotpars.hspace = 0.4
    
    for object in objects:
        #create a new subplot object
        s = matplotlib.pylab.subplot(rows,columns,i)
        
        #add the object to the figure
        fig.add_subplot(s)
        object._plot(s)
        i+=1    
    return fig

    
    
