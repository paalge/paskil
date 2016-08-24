// Copyright (C) Nial Peters 2009
//
// This file is part of PASKIL.
//
// PASKIL is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// PASKIL is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with PASKIL.  If not, see <http://www.gnu.org/licenses/>.

#include"Python.h"
#include "structmember.h"
#include <numpy/arrayobject.h>
#include<math.h>
#include<stdio.h>

#define PI 3.1415926535897931

static char mod_doc[] = "The cFit module provides functions for fitting a normal distribution to a histogram.";

inline double norm(int x, int mean, double var){
	return (1.0 / sqrt(2.0 * PI * var)) * exp((-((x-mean)*(x-mean))) / (2.0* var));
}

inline double z(int mean, double var){
	double sum = 0;
	int i;
	for(i=255;i>0;i--){
		sum += norm(i, mean, var);
	}
	return sum;
}

inline double likelyhood(int x, int mean , double var, double z_value){
	return norm(x,mean,var)/z_value;
}

/*****************************************************************************/

void fit_norm_dist(double *results, double *norm_hist, int min_mean, int max_mean, int mean_step,
		int min_std_dev, int max_std_dev, int std_dev_step){

	int std_dev, mean, x;
	double var; //variance
	long double current_likelyhood;
	long double max_likelyhood=0.0;
	double z_value; //normalisation factor


	for (std_dev=min_std_dev; std_dev <= max_std_dev; std_dev+=std_dev_step){
		var = pow(((double)std_dev),2.0);

		for (mean=min_mean; mean <= max_mean; mean+=mean_step){


		    //skip results we don't care about
		    if ((mean+(2*std_dev) > 255) && (mean-(2*std_dev) < 0)){
		    	continue;
		    }

		    //initialise likelyhood
		    current_likelyhood = 1.0;

		    //work out the likelyhood at these parameters
		    z_value = z(mean,var);
		    for (x=0; x<255; x++){
		    	current_likelyhood *= pow(likelyhood(x+1,mean,var,z_value),norm_hist[x]);
		    }

		    if (current_likelyhood > max_likelyhood){
		    	max_likelyhood = current_likelyhood;
		    	results[0] = mean;
		    	results[1] = std_dev;
		    }
		}
	}
}

/*****************************************************************************/

static char fit_norm_dist_doc[] = "Fits a normal distribution to a histogram and returns the mean and standard deviation of the maximum likelyhood distribution";

static PyObject * cFit_fit_norm_dist(PyObject *self, PyObject *args){
		PyObject *hist_arr;
	    npy_intp hist_arr_dims[1];
	    int hist_arr_num_dim;
	    int i, max_count=0;
	    double norm_hist[255];
	    double results[2];

	    //parse the arguments passed to the function by Python - no increase in ref count
	    if(!PyArg_ParseTuple(args, "O", &hist_arr)){ //no increase to the object's reference count
	        PyErr_SetString(PyExc_ValueError,"Invalid parameters");
	        return NULL;
	    }

	    //check that we have been passed an array object
	    if (!PyArray_Check(hist_arr)){
	        	PyErr_SetString(PyExc_TypeError,"Invalid type for histogram argument. Expecting Numpy array.");
	        	return NULL;
	    }

	    //check that it is an integer array
	    if (!PyArray_ISINTEGER(hist_arr)){
	    	        	PyErr_SetString(PyExc_TypeError,"Invalid data type for histogram array. Expecting integers.");
	    	        	return NULL;
	    	    }

	    //check that histogram is 1D
	    hist_arr_num_dim = PyArray_NDIM(hist_arr);
	    if (hist_arr_num_dim != 1){
	        PyErr_SetString(PyExc_ValueError,"Histogram array must be one dimensional");
	        return NULL;
	    }

	    //check array is well behaved
	    if (! PyArray_ISBEHAVED(hist_arr)){
	        PyErr_SetString(PyExc_ValueError,"Histogram array must be well behaved");
	        return NULL;
	    }

	    //get the dimensions of the keogram and data_list
	    hist_arr_dims[0] = PyArray_DIM(hist_arr, 0);

	    //check length of histogram
	    if ((int)hist_arr_dims[0] != 256){
	    	PyErr_SetString(PyExc_ValueError,"Histogram array must contain 256 elements");
	    	return NULL;
	    }

	    //find max count in histogram
	    for (i=1; i<256; i++){

	    	if (*((int*)PyArray_GETPTR1(hist_arr,i)) > max_count){
	    		max_count = *((int*)PyArray_GETPTR1(hist_arr,i));
	    	}
	    }


	    //generate normalised histogram skipping the value at index 0
	    for (i=0; i<255; i++){
	    	norm_hist[i] = (double)(*((int*)PyArray_GETPTR1(hist_arr,i+1)) / ((double) max_count));
	    }

	    //first pass through data use steps of 10 for mean and std_dev
	    fit_norm_dist(results,norm_hist,0,250,10,0,130,10);

	    //check if the mean is outside of the range of the histogram
	    if (results[0] == 0.0){
	    	fit_norm_dist(results,norm_hist,-100,0,10,0,180,10);
	    }
	    if (results[0] == 250.0){
	    	fit_norm_dist(results,norm_hist,250,350,10,0,180,10);
	    }

	    //second pass through using steps size of one, and looking either side of previously found values
	    fit_norm_dist(results,norm_hist,results[0]-10,results[0]+10,1,results[1]-10,results[1]+10,1);

	    return Py_BuildValue("dd",results[0],results[1]);

}

//set up the functions to be visible in Python
static PyMethodDef cFit_methods[] = {
    {"fit_norm_dist", cFit_fit_norm_dist, METH_VARARGS, fit_norm_dist_doc},
    {NULL, NULL}
};

// Module definition
static struct PyModuleDef cFit_module = {
   PyModuleDef_HEAD_INIT,
   "cFit",   /* name of module */
   mod_doc, /* module documentation, may be NULL */
   -1,       /* size of per-interpreter state of the module,
                or -1 if the module keeps state in global variables. */
   cFit_methods
};

// Init function
PyMODINIT_FUNC
PyInit_cFit(void)
{
	import_array();
    return PyModule_Create(&cFit_module);
}




