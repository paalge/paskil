#include "Python.h"
#include "numarray/libnumarray.h"
#include "huffman.h"
#include "bitarray.h"
#include <math.h>
#include <string.h>

/*STRUCTURES*/

struct sqd_header_t
{
	int header_length;
	int image_width;
	int image_height;
	char *header_data;
	int num_chars;
};

typedef struct sqd_header_t sqd_header_t;

/*PROTOTYPES*/
FILE * openSqd(PyObject *args);
sqd_header_t * readSqdHeader(FILE *ifp);
void freeHeader(sqd_header_t *header);

/************************************************************************/

static PyObject * cSquish_compress(PyObject *self, PyObject *args){

	PyArrayObject *numarray_data,*numarray_mask; //pointers to python array object
	PyObject *indata,*inmask; //pointer to python object to hold input arguments
	int *raw_data=NULL,*mask=NULL; //pointer to C array to hold raw data
	int *masked_data=NULL;
	int raw_width,raw_height,raw_length,mask_width,mask_height;//dimensions of python array
	int masked_length=0; //length of array needed to hold the masked data
	int i,k; //counters
	encoded_array_t *encoded_data;
	char *header_data,*filename;
	
	//parse the arguments passed to the function
	if(!PyArg_ParseTuple(args, "OOss", &indata,&inmask,&header_data,&filename))//no increase to the object's reference count
	{ 
		PyErr_SetString(PyExc_ValueError,"Invalid parameters");
		return NULL;
	}
	
	numarray_data = NA_InputArray(indata, tInt32, NUM_C_ARRAY); //increased numarray_data ref count by one
	numarray_mask = NA_InputArray(inmask, tInt32, NUM_C_ARRAY); //increased numarray_mask ref count by one
	
	//check that there were no problems converting the array
	if(!numarray_data || !numarray_mask)
	{
		PyErr_SetString(PyExc_ValueError,"Failed to convert the array to C_TYPE");
		goto _fail;	
	}
	
	//get array width and height (before it is cast into a 1D C array)
	raw_width=(int)numarray_data->dimensions[0];
	raw_height=(int)numarray_data->dimensions[1];
	
	if(raw_width == 0 || raw_height== 0)
	{
		raw_length=raw_width+raw_height;
	}else
	{
		raw_length=raw_width*raw_height;
	}
	
	mask_width=(int)numarray_mask->dimensions[0];
	mask_height=(int)numarray_mask->dimensions[1];
	

	printf("mask_height = %d mask_width = %d\n",mask_height,mask_width);
	printf("raw_height = %d raw_width = %d\n",raw_height,raw_width);

	
	//check that the mask and raw arrays are the same shape
	if ((raw_width != mask_width) || (raw_height != mask_height))
	{
		PyErr_SetString(PyExc_ValueError,"Mask and Data arrays must have same shape");
		goto _fail;	
	}
	
	//create pointer to C data array
	raw_data=NA_OFFSETDATA(numarray_data);
	mask = NA_OFFSETDATA(numarray_mask);
	
	//check that there were no problems converting the array
	if(!raw_data || !mask)
	{
		PyErr_SetString(PyExc_ValueError,"Failed to convert the array to C_TYPE");
		goto _fail;	
	}
	
	/*Now we have finished with all the Python to C conversions and we can get on with the compression!*/
	
	/*calculate the size of the masked data array - this is the array that will hold the pixel
	  data of the pixels within the field of view */
	for (i = raw_length - 1; i >= 0; i--)
	{
		if (mask[i] != 0)
		{
			masked_length += 1;
		}
	}
	
	masked_data = malloc(masked_length * sizeof(int));
	
	/*apply the mask to the data - this involves copying the pixels from the image that correspond to 
	  non-zero pixels in the mask image into the masked_data array */
	k = masked_length -1;
	
	for (i = raw_length-1; i >= 0; i--)
	{
		if (mask[i] != 0)
		{
			masked_data[k] = raw_data[i];
			k--;
		}
	}

	/*compress the masked data using the canonical Huffman algorithm*/
	encoded_data=CHuffmanEncodeArray(masked_data,masked_length);

	free(masked_data);
	masked_data=NULL;
	
	/*open the output file for writing*/
	FILE *ofp;
	ofp = fopen(strcat(filename, ".sqd"),"wb"); 
	if (ofp == NULL)
	{
		PyErr_SetString(PyExc_IOError,"Cannot open file ");
		return NULL;
	}

	//write header data
	fputs("sqd",ofp);
	fprintf(ofp,"%d %d %d ",strlen(header_data),raw_width,raw_height);
	fputs(header_data,ofp);
	fprintf(ofp,"%d ",(int)NUM_CHARS);
	
	//write decoding table
	for (i = 0; i < NUM_CHARS; i++)
    {
        fprintf(ofp,"%d ",encoded_data->canonicalList[i].codeLen);
    }

	//write data
	double num_bytes = ceil((double)encoded_data->size/8.0); //calculate number of bytes in bit array
	
	fprintf(ofp,"%d ",(int)num_bytes);
	
	for (i=0; i < num_bytes; i++)
	{
		fprintf(ofp,"%c",(encoded_data->data->array[i]));
	}	

	fclose(ofp);
	
	/*free memory*/
	free(encoded_data->canonicalList);
	BitArrayDestroy(encoded_data->data);
	free(encoded_data);
	encoded_data = NULL;
	Py_XDECREF(numarray_data);
	Py_XDECREF(numarray_mask);
	
	Py_RETURN_NONE;
	

_fail:
	//decrease reference count of numarray_data and numarray_mask
	Py_XDECREF(numarray_data);
	Py_XDECREF(numarray_mask);
	
	if (masked_data != NULL)
	{
		free(masked_data);
		masked_data=NULL;
	}
	
	return NULL;
}

/************************************************************************/

static PyObject * cSquish_decompress(PyObject *self, PyObject *args){

	int *decode_table;
	int num_bytes,raw_length;
	int i,k;
	unsigned long long int j,length;
    char decodedEOF;
    int *lenIndex;
	unsigned char *data;
	canonical_list_t *canonicalList;
	bit_array_t *code;
	int *decoded_data;
	sqd_header_t *header;	
	
	FILE *ifp = openSqd(args);
	
	if (ifp == NULL)
	{
		return NULL;
	}

	/*read header data*/
	header = readSqdHeader(ifp);
	
	if (header == NULL)
	{
		return NULL;
	}

	/*read decode table*/
	decode_table = malloc(header->num_chars*sizeof(int));
	
	for (i = 0; i < header->num_chars; i++)
    {
        fscanf(ifp,"%d ",&decode_table[i]);
    }
    
    /*read encoded data*/
    fscanf(ifp,"%d ",&num_bytes); //read length of data

    data = malloc(num_bytes*sizeof(unsigned char));
    i = 0;
    while (fscanf(ifp,"%c",&data[i])!=EOF)
    {
    	i++;
	}	
    
    fclose(ifp);
	
	
    /*convert decode table to canonicalList*/
    /* initialize canonical list */
    canonicalList = malloc(header->num_chars * sizeof(canonical_list_t));
    
    for (i = 0; i < header->num_chars; i++)
    {
        canonicalList[i].codeLen = decode_table[i];
        canonicalList[i].code = NULL;
        canonicalList[i].value = i;
    }

    /* sort the header by code length */
    qsort(canonicalList, header->num_chars, sizeof(canonical_list_t), CompareByCodeLen);
    
    /* assign the codes using same rule as encode */
    if (AssignCanonicalCodes(canonicalList) == 0)
    {
        for (i = 0; i < header->num_chars; i++)
        {
            if(canonicalList[i].code != NULL)
            {
                BitArrayDestroy(canonicalList[i].code);
            } 
        }
        
        free(canonicalList);
        free(data);
        free(decode_table);
        freeHeader(header);
		PyErr_SetString(PyExc_RuntimeError,"Failed to assign the codes.");
        return NULL;
    }
    
    /* now we have a huffman code that matches the code used on the encode */
	
	/*convert the data array back to a bit array*/
	bit_array_t *bit_arr_data;
	bit_arr_data = malloc(sizeof(bit_array_t));
	
	bit_arr_data->array = data;
	bit_arr_data->numBits = num_bytes*8; 
	
	/*create an array to hold the decoded data*/
	
	
    /* create an index of first code at each possible length */
    lenIndex = malloc(header->num_chars * sizeof(int));
  
    for (i = 0; i < header->num_chars; i++)
    {
        lenIndex[i] = header->num_chars;
    }

    for (i = 0; i < header->num_chars; i++)
    {	
        if (lenIndex[canonicalList[i].codeLen] > i)
        {
            /* first occurance of this code length */
            lenIndex[canonicalList[i].codeLen] = i;
        }
    }
	
	/* allocate canonical code list */
    code = BitArrayCreate(header->num_chars-1);
    if (code == NULL)
    {
        PyErr_SetString(PyExc_MemoryError,"Failed to create bit array for code");
        for (i = 0; i < header->num_chars; i++)
        {
            if(canonicalList[i].code != NULL)
            {
                BitArrayDestroy(canonicalList[i].code);
            } 
        }
        free(canonicalList);
        free(decode_table);
        freeHeader(header);
        BitArrayDestroy(bit_arr_data);
        return NULL;
    }


    /* decode input file */
    length = 0; //used to be 1
    BitArrayClearAll(code);
    decodedEOF = FALSE;
    j=0;
    k=0;
    
    /*guess the size that the decoded data will be - it can't be bigger than the unmasked image
     * so raw_length is an upper bound*/
    if(header->image_width == 0 || header->image_height== 0)
	{
		raw_length = header->image_width + header->image_height;
	}else
	{
		raw_length = header->image_width * header->image_height;
	}
    
    decoded_data = malloc(raw_length*sizeof(int));

    while(!decodedEOF)
    {	
        if (BitArrayTestBit(bit_arr_data,j))
        {
            BitArraySetBit(code, length); 
        }
        
        length++;
		j++;

        if (lenIndex[length] != header->num_chars)
        {
            /* there are code of this length */
            for(i = lenIndex[length]; (i < header->num_chars) && (canonicalList[i].codeLen == length); i++)
            {
                if ((BitArrayCompare(canonicalList[i].code, code) == 0) && (canonicalList[i].codeLen == length))
                {
                    if (canonicalList[i].value != EOF_CHAR)
                    {
                       decoded_data[k] = canonicalList[i].value;
                       k++;
                    }
                    else
                    {
                        decodedEOF = TRUE;
                    }
                      
                    BitArrayClearAll(code);
                    length = 0;
                    break;
                }
            }
        }
    }
    
    
    /*clean up*/
    for (i = 0; i < header->num_chars; i++)
    {
            if(canonicalList[i].code != NULL)
            {
                BitArrayDestroy(canonicalList[i].code);
            } 
    }
    
    free(lenIndex);
    freeHeader(header);
    free(canonicalList);
    free(decode_table);
    BitArrayDestroy(bit_arr_data);
    BitArrayDestroy(code);
    
    
    /*Unmask the decoded data*/
    
    //convert C image array into a numpy array object
  	PyArrayObject *image_data = NA_NewArray(decoded_data, tInt32,1,raw_length);
    
	return image_data;
}

/************************************************************************/

static PyObject * cSquish_getHeader(PyObject *self, PyObject *args){
	
	sqd_header_t *header;
	PyObject *header_py;	
	
	FILE *ifp = openSqd(args);
	
	if (ifp == NULL)
	{
		return NULL;
	}

	/*read header data*/
	header = readSqdHeader(ifp);
	
	if (header == NULL)
	{
		return NULL;
	}
	
	fclose(ifp);
	
	/*convert the string to a python string*/
	header_py = PyString_FromString(header->header_data);
	
	if (header_py == NULL)
	{
		PyErr_SetString(PyExc_MemoryError,"Failed to create Python string");
	}
	
	freeHeader(header);
	return header_py;
}
		
/************************************************************************/

static PyObject * cSquish_isSqd(PyObject *self, PyObject *args){

	FILE *ifp = openSqd(args);	
		
	if (ifp == NULL)
	{
		Py_RETURN_FALSE;
	}else
	{
		fclose(ifp);
		Py_RETURN_TRUE;
	}
}

/************************************************************************/

static PyObject * cSquish_getSize(PyObject *self, PyObject *args){

	FILE *ifp = openSqd(args);
	sqd_header_t *header;
	PyObject *size;	
	
	if (ifp == NULL)
	{
		return NULL;
	}
	
	/*read header data*/
	header = readSqdHeader(ifp);
	
	if (header == NULL)
	{
		return NULL;
	}
	
	fclose(ifp);
	
	/*build a python tuple of the size*/
	size = PyTuple_Pack(2, PyInt_FromLong((long)header->image_width),PyInt_FromLong((long)header->image_height));
	
	freeHeader(header);
	
	if (size == NULL)
	{
		PyErr_SetString(PyExc_MemoryError,"Failed to create Python Tuple");
		return NULL;	
	}
	return size;
}

/************************************************************************/

FILE * openSqd(PyObject *args){
	char *filename;
	FILE *ifp;
	char id[4];
	
	if(!PyArg_ParseTuple(args, "s", &filename))
	{ 
		PyErr_SetString(PyExc_ValueError,"Filename argument must be a string");
		return NULL;
	}
	
	ifp=fopen(filename,"rb");
	
	if (ifp == NULL)
	{
		PyErr_SetString(PyExc_IOError,"Cannot open file.");
		return NULL;
	}

	/*check that file is an sqd file*/
	fgets(id,4,ifp);
	
	if (strcmp(id,"sqd"))
	{
		PyErr_SetString(PyExc_IOError,"Unrecognised file format");
		fclose(ifp);
		return NULL;	
	}
	
	return ifp;
}

/************************************************************************/

sqd_header_t * readSqdHeader(FILE *ifp){
	
	sqd_header_t *header = NULL;
	
	header = malloc(sizeof(sqd_header_t));
	
	if (header == NULL)
	{
		PyErr_SetString(PyExc_MemoryError,"Failed to allocate memory for header data structure");
		return NULL;
	}
	
	//move to end of id string
	rewind(ifp);
	fseek(ifp,3,SEEK_SET);
	
	/*read header data*/
	fscanf(ifp,"%d %d %d ",&header->header_length, &header->image_width, &header->image_height);
	header->header_data = malloc((header->header_length+1)*sizeof(char));
	
	fgets(header->header_data, header->header_length+1, ifp);
	
	fscanf(ifp,"%d",&header->num_chars);
	
	return header;
	
}
	
/************************************************************************/

void freeHeader(sqd_header_t *header){
	free(header->header_data);
	free(header);
}	
				
/************************************************************************/
//               Define Python Extension bits
/************************************************************************/
static PyMethodDef cSquish_methods[] = {
	{"compress", cSquish_compress, METH_VARARGS, ""},
	{"decompress", cSquish_decompress, METH_VARARGS, ""},
	{"getHeader", cSquish_getHeader, METH_VARARGS,""},
	{"isSqd", cSquish_isSqd,METH_VARARGS,""},
	{"getSize",cSquish_getSize,METH_VARARGS,""},
	{NULL, NULL}
};

PyMODINIT_FUNC initcSquish(void){
	import_libnumarray();
	Py_InitModule3("cSquish", cSquish_methods,"The cSquish module compresses an array of 32bit integers using the Huffman algorithm");
		       
}
