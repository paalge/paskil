"""
Module containing miscellaneous statistical functions used internally by PASKIL
"""
import math

def variance_mean(data):
    """
    Function returns the variance and mean of the data in a list
    """
    sum_x=0.0
    sum_sqd_x=0.0
    for i in range(len(data)):
        sum_x=sum_x+data[i]
        sum_sqd_x=sum_sqd_x+data[i]*data[i]
        
    mean = sum_x/float(len(data))
    mean_of_squares = sum_sqd_x/float(len(data))
    
    return (mean_of_squares-(mean*mean), mean)
    
def variance(data):
    """
    Function returns the variance of the data in a list
    """
    sum_x=0.0
    sum_sqd_x=0.0
    for i in range(len(data)):
        sum_x=sum_x+data[i]
        sum_sqd_x=sum_sqd_x+data[i]*data[i]
        
    mean = sum_x/float(len(data))
    mean_of_squares = sum_sqd_x/float(len(data))
    
    return mean_of_squares-(mean*mean)
    
def median(data):
    """
    Function returns the median value of the data in a list
    """
    #copy data list
    data_copy=[]
    for i in range(len(data)):
        data_copy.append(data[i])
    
    data_copy.sort()
    
    if len(data_copy)%2 == 0:
        return (data_copy[len(data_copy)/2-1]+data_copy[len(data_copy)/2])/2.0
    return data_copy[len(data_copy)/2]
    
def mean(data):
    """
    Returns the mean of a list of data.
    """
    return float(sum(data))/float(len(data))
    
def stdDev(data):
    """
    Function returns standard deviation of data in a list
    """
    return math.sqrt(variance(data))
