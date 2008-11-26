import matplotlib
import matplotlib.pyplot
import math

def plot(objects,columns=1,size=None):
    print "allskyPlot: creating figure"
    fig = matplotlib.pyplot.figure()
    print "allskyPlot: done"
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
        print "allskyPlot: creating subplot"
        s = matplotlib.pylab.subplot(rows,columns,i)
        print "allskyPlot: done"
        #add the object to the figure
        print "allskyPlot: adding subplot to figure"
        fig.add_subplot(s)
        print "allskyPlot: done"
        object._plot(s)
        i+=1    
    print "returning figure"
    return fig

    
    
