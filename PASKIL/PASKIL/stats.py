#Copyright (C) Nial Peters 2009
#
#This file is part of PASKIL.
#
#PASKIL is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#PASKIL is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with PASKIL.  If not, see <http://www.gnu.org/licenses/>.
"""
Module containing miscellaneous statistical functions used internally by PASKIL
"""
import math
#
#def hist_variance_mean(hist):
#    """
#    Function returns the variance and mean of a histogram
#    """
#    sum_x = 0.0
#    sum_sqd_x = 0.0
#    for i in range(len(hist)):
#        sum_x = sum_x + (i*hist[i])
#        sum_sqd_x=sum_sqd_x+(i*hist[i]*hist[i])
#        
#    mean = sum_x/float(sum(hist))
#    mean_of_squares = sum_sqd_x/float(sum(hist))
#    
#    return (mean_of_squares-(mean*mean), mean)

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
