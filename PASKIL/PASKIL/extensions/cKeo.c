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

static char mod_doc[] = "The cKeo module provides functions for interpolating \
keogram data in order to fill in the gaps between the image strips. \
It is written in C to reduce the time taken to complete the interpolation.";


/*****************************************************************************/

static inline int findIndex(PyObject *arr, int value, int size){
    //returns index of first occurrence of value in 1D array object, -1 if not
    //found
    int i;
    for (i=0;i<size;i++){
        if (*((int*)PyArray_GETPTR1(arr,i)) == value){
            return i;
        }
    }
    return -1;
}
/*****************************************************************************/

static char lin_interp_doc[] = "linear_interpolate(keo_array, keo_data_points, \
strip_width, max_gap) performs an in-place linear interpolation between the \
image strips in keo_array at positions given by keo_data_points, of width \
strip_width. Spaces larger than max_gap are not interpolated across.";

static PyObject * cKeo_linear_interpolate(PyObject *self, PyObject *args){
    
    PyObject *keo_arr, *data_list;
    int strip_width,max_gap;
    npy_intp keo_arr_dims[2], data_list_dims[1]; 
    int keo_arr_num_dim, data_list_num_dim;
    long int x,y,k;
    int start_pix, end_pix, offset;
    double gradient;
     
    //parse the arguments passed to the function by Python - no increase in ref count
    if(!PyArg_ParseTuple(args, "OOii", &keo_arr, &data_list, &strip_width, &max_gap)){ //no increase to the object's reference count
        PyErr_SetString(PyExc_ValueError,"Invalid parameters");
        return NULL;
    }

    //check that we have been passed array objects
    if (!PyArray_Check(keo_arr)){
    	PyErr_SetString(PyExc_TypeError,"Invalid type for keo_arr argument. Expecting Numpy array.");
    	return NULL;
    }
    if (!PyArray_Check(data_list)){
        	PyErr_SetString(PyExc_TypeError,"Invalid type for data_list argument. Expecting Numpy array.");
        	return NULL;
    }

    //check that keo_arr is two dimensional
    keo_arr_num_dim = PyArray_NDIM(keo_arr);
    if (keo_arr_num_dim != 2){
        PyErr_SetString(PyExc_ValueError,"Keogram array must be two dimensional");
        return NULL;
    }
    
    //check that data_list is 1D
    data_list_num_dim = PyArray_NDIM(data_list);
    if (data_list_num_dim != 1){
        PyErr_SetString(PyExc_ValueError,"Data list array must be one dimensional");
        return NULL;
    }
    
    //check that both are well behaved
    if (! PyArray_ISBEHAVED(keo_arr)){
        PyErr_SetString(PyExc_ValueError,"Keogram array must be well behaved");
        return NULL;
    }   
    if (! PyArray_ISBEHAVED(data_list)){
        PyErr_SetString(PyExc_ValueError,"Data list array must be well behaved");
        return NULL;
    }
    
    //get the dimensions of the keogram and data_list
    keo_arr_dims[0] = PyArray_DIM(keo_arr, 0);
    keo_arr_dims[1] = PyArray_DIM(keo_arr, 1);
    data_list_dims[0] = PyArray_DIM(data_list, 0);

    //do the interpolation
    for(k=0;k<data_list_dims[0]-1;k++){
        start_pix = *((int*)PyArray_GETPTR1(data_list,(int)k))+(strip_width/2);
        end_pix = *((int*)PyArray_GETPTR1(data_list,((int)k)+1))-(strip_width/2);
        
        //check that any interpolation is actually needed
        if (start_pix == end_pix){
            continue;
        }
        
        //check for missing data entries
        if (end_pix-start_pix > max_gap){
            continue; //don't interpolate over large gaps in the data.
        }
        
        for (y=0;y<keo_arr_dims[1];y++){
                offset = keo_arr_dims[1]*y;
                //gradient = (keo_data[(end_pix*y_stride)+(y*x_stride)] - keo_data[(start_pix*y_stride)+(y*x_stride)])/(double)(end_pix-start_pix);
                gradient = (*((int*)PyArray_GETPTR2(keo_arr,end_pix,y))-*((int*)PyArray_GETPTR2(keo_arr,start_pix,y)))/(double)(end_pix-start_pix);
                for(x=start_pix+1;x<end_pix;x++){ 
                    //keo_data[(x*y_stride)+(y*x_stride)] = keo_data[(start_pix*y_stride)+(y*x_stride)] + (x-start_pix)*gradient;
                    *((int*)PyArray_GETPTR2(keo_arr,x,y)) = *((int*)PyArray_GETPTR2(keo_arr,start_pix,y))+ (x-start_pix)*gradient;
                }
        }           
    }
    
    Py_RETURN_NONE;   
}
/*****************************************************************************/

static char ct_lin_interp_doc[] = "ct_lin_interp(keo_array, keo_data_points, \
colour_table, strip_width, max_gap) performs an in-place linear interpolation \
between the image strips in keo_array at positions given by keo_data_points, \
of width strip_width. Spaces larger than max_gap are not interpolated across. \
This differs from the linear_interpolate function in that it is designed for \
data with a false colour mapping applied (defined by colour_table). Instead of \
interpolating the data values themselves, the interpolated values are selected \
from the colour table. In this way, it is equivalent to interpolating the raw \
data and then applying the colour table.";

static PyObject * cKeo_ct_lin_interp(PyObject *self, PyObject *args){
    
    PyObject *keo_arr, *data_list,*colour_table;
    int strip_width,max_gap;
    npy_intp keo_arr_dims[2], data_list_dims[1],ct_dims[1]; 
    int keo_arr_num_dim, data_list_num_dim, ct_num_dim;
    long int x,y,k;
    int start_pix, end_pix, index_in_colour_table;
    int start_colour, end_colour;
    double gradient;
     
    //parse the arguments passed to the function by Python
    if(!PyArg_ParseTuple(args, "OOOii", &keo_arr, &data_list,&colour_table, &strip_width, &max_gap)){ //no increase to the object's reference count
        PyErr_SetString(PyExc_ValueError,"Invalid parameters");
        return NULL;
    }

    //check that we have been passed array objects
    if (!PyArray_Check(keo_arr)){
      	PyErr_SetString(PyExc_TypeError,"Invalid type for keo_arr argument. Expecting Numpy array.");
      	return NULL;
    }
    if (!PyArray_Check(data_list)){
        PyErr_SetString(PyExc_TypeError,"Invalid type for data_list argument. Expecting Numpy array.");
        return NULL;
    }
    if (!PyArray_Check(colour_table)){
        PyErr_SetString(PyExc_TypeError,"Invalid type for colour_table argument. Expecting Numpy array.");
        return NULL;
    }

    //check that keo_arr is two dimensional
    keo_arr_num_dim = PyArray_NDIM(keo_arr);
    if (keo_arr_num_dim != 2){
        PyErr_SetString(PyExc_ValueError,"Keogram array must be two dimensional");
        return NULL;
    }
    
    //check that data_list is 1D
    data_list_num_dim = PyArray_NDIM(data_list);
    if (data_list_num_dim != 1){
        PyErr_SetString(PyExc_ValueError,"Data list array must be one dimensional");
        return NULL;
    }
    
    //check the colour_table is 1D
    ct_num_dim = PyArray_NDIM(colour_table);
    if (ct_num_dim != 1){
        PyErr_SetString(PyExc_ValueError,"Colour table array must be one dimensional");
        return NULL;
    }
    
    //check that all are well behaved
    if (! PyArray_ISBEHAVED(keo_arr)){
        PyErr_SetString(PyExc_ValueError,"Keogram array must be well behaved");
        return NULL;
    }   
    if (! PyArray_ISBEHAVED(data_list)){
        PyErr_SetString(PyExc_ValueError,"Data list array must be well behaved");
        return NULL;
    }
    if (! PyArray_ISBEHAVED(colour_table)){
        PyErr_SetString(PyExc_ValueError,"Colour table array must be well behaved");
        return NULL;
    }
    
    //get the dimensions of the keogram, data_list and colour table
    keo_arr_dims[0] = PyArray_DIM(keo_arr, 0);
    keo_arr_dims[1] = PyArray_DIM(keo_arr, 1);
    data_list_dims[0] = PyArray_DIM(data_list, 0);
    ct_dims[0] = PyArray_DIM(colour_table, 0);
    
/*    //check stride of data list array is what we are expecting
    if (((int)PyArray_STRIDE(data_list, 0) != (int)sizeof(int))){
        PyErr_SetString(PyExc_ValueError,"Incorrect stride for data list array");
        return NULL;
    }
    
    //get pointers to array data
    keo_data = (int*)PyArray_DATA(keo_arr);
    data_points = (int*)PyArray_DATA(data_list);
    ct_data = (int*)PyArray_DATA(colour_table);
 */
    //do the interpolation
    for(k=0;k<data_list_dims[0]-1;k++){
        start_pix = *((int*)PyArray_GETPTR1(data_list,(int)k))+(strip_width/2);
        end_pix = *((int*)PyArray_GETPTR1(data_list,((int)k)+1))-(strip_width/2);

 //   	start_pix = data_points[(int)k]+(strip_width/2);
 //       end_pix = data_points[((int)k)+1]-(strip_width/2);
        
        //check that any interpolation is actually needed
        if (start_pix == end_pix){
            continue;
        }
        
        //check for missing data entries
        if (end_pix-start_pix > max_gap){
            continue; //don't interpolate over large gaps in the data.
        }
        
        for (y=0;y<keo_arr_dims[1];y++){
            start_colour = findIndex(colour_table,*((int*)PyArray_GETPTR2(keo_arr,start_pix,y)),ct_dims[0]);
            end_colour = findIndex(colour_table,*((int*)PyArray_GETPTR2(keo_arr,end_pix,y)),ct_dims[0]);
            gradient = (end_colour - start_colour)/(end_pix - start_pix);

            for(x=start_pix+1;x<end_pix;x++){
                index_in_colour_table = (int)(start_colour + ((x-start_pix)*gradient)+0.5);
                *((int*)PyArray_GETPTR2(keo_arr,x,y)) = *((int*)PyArray_GETPTR1(colour_table,index_in_colour_table));
            }   
        }
    }
    
    Py_RETURN_NONE;   
}

//set up the functions to be visible in Python
static PyMethodDef cKeo_methods[] = {
    {"linear_interpolate", cKeo_linear_interpolate, METH_VARARGS, lin_interp_doc},
    {"ct_lin_interp", cKeo_ct_lin_interp, METH_VARARGS, ct_lin_interp_doc},
    {NULL, NULL}
};

//set up module to be importable in Python
PyMODINIT_FUNC initcKeo(void){
    import_array();
    Py_InitModule3("cKeo", cKeo_methods,mod_doc);
}
