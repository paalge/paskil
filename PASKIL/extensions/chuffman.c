/***************************************************************************
 * chuffman.c created by Nial Peters May 2008
 * 
 * This file contains a modified version of Michael Dipperstein's Canonical
 * Huffman encoding and Decoding program. I have added functions for
 * compressing arrays rather than files, and removed any source code not used
 * by PASKIL. I have also moved stuff around a lot to make the code function
 * as a library (removing global variables and moving prototypes into a header
 * file etc.)
 * 
 * My code is at the top of the file, and is followed by the (mostly) unaltered
 * code from the original chuffman.c file and the huflocal.c file.
 * 
 * 
****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include "huffman.h"


/***************************************************************************
*                              NEW FUNCTIONS
***************************************************************************/

/****************************************************************************
*   Function   : CHuffmanEncodeArray
*   Description: This routine genrates a huffman tree optimized for an array
*                and returns an encoded version of that array.
*   Parameters : raw_array - pointer to raw_data array
*                raw_length - length of raw_data array
*   Effects    : Array is Huffman encoded
*   Returned   : Pointer to bit array containing encoded data, or NULL on failure.
****************************************************************************/
encoded_array_t *CHuffmanEncodeArray(int *raw_data,int raw_length){
	
	canonical_list_t *canonicalList;      /* list of canonical codes */
	encoded_array_t *result;
    bit_array_t *encoded_data;
    huffman_node_t *huffmanTree;        /* root of huffman tree */
    int c,i,j,k;
    unsigned long long int bit_array_length=0;
    int *hist;

	canonicalList=malloc(NUM_CHARS * sizeof(canonical_list_t));
	
    /* build tree */
    if ((huffmanTree = GenerateTreeFromArray(raw_data,raw_length)) == NULL)
    {
        return NULL;
    }

    /* use tree to generate a canonical code */
    if (!BuildCanonicalCode(huffmanTree, canonicalList))
    {
        FreeHuffmanTree(huffmanTree);     /* free allocated memory */
        return NULL;
    }
	
	/*calculate required length of bit array for encoding*/
	
	//calculate histogram
	hist=histogram(raw_data,raw_length);
	
	for (i=0;i<NUM_CHARS;i++)
	{	
		//c=raw_data[i];
		bit_array_length += hist[i]*canonicalList[i].codeLen;	
	}
	
	free(hist);
	hist=NULL;
	
	//add length of EOF encoding
	bit_array_length += canonicalList[EOF_CHAR].codeLen;

	
	/*create bit array for encoded data*/
	encoded_data = BitArrayCreate(bit_array_length);
	
	
	/*do the encoding*/
	k=0;
	for (i = 0; i < raw_length; i++) 
	{
		c=raw_data[i];
		for (j = 0; j < canonicalList[c].codeLen; j++)
		{
			if (BitArrayTestBit(canonicalList[c].code, j))
			{
				BitArraySetBit(encoded_data, k);
			}
			k++;	
		}				
	}
	
	//encode the EOF
	for (j = 0; j < canonicalList[EOF_CHAR].codeLen; j++)
		{
			if (BitArrayTestBit(canonicalList[EOF_CHAR].code, j))
			{
				BitArraySetBit(encoded_data, k);
			}
			k++;	
		}
    
    /*store encoded data in structure*/
    result=malloc(sizeof(encoded_array_t));
	result->size=bit_array_length;
	result->data=encoded_data;
	result->canonicalList=canonicalList;
	
    return result;
}

/****************************************************************************
*   Function   : histogram
*   Description: generates a histogram of length NUM_CHARS of a specified array
*   Parameters : data - pointer to array
*                length - length of array
*   Returned   : Pointer to histogram array of length NUM_CHARS
****************************************************************************/

int * histogram(int *data,int length){
	int *hist;
	int i; //counter
	
	hist=malloc(NUM_CHARS*sizeof(int));

	//initialise histogram array
	for(i = NUM_CHARS-1; i >= 0; i--){
		hist[i] = 0;
	}
	for(i = length-1; i >= 0; i--){
		hist[data[i]]+=1;
	}	

	return hist;
}

/****************************************************************************
*   Function   : GenerateTreeFromArray
*   Description: This routine creates a huffman tree optimized for encoding
*                the array passed as a parameter.
*   Parameters : raw_data - Pointer to array to create tree for
* 				 raw_length - int length of raw_array
*   Effects    : Huffman tree is built for array.
*   Returned   : Pointer to resulting tree.  NULL on failure.
****************************************************************************/
huffman_node_t *GenerateTreeFromArray(int *raw_data, int raw_length)
{
    huffman_node_t *huffmanTree;              /* root of huffman tree */
    int c,i;
	huffman_node_t *huffmanArray[NUM_CHARS]; /* array of all leaves */
	
    /* allocate array of leaves for all possible characters */
    for (c = 0; c < NUM_CHARS; c++)
    {
        if ((huffmanArray[c] = AllocHuffmanNode(c)) == NULL)
        {
            /* allocation failed clear existing allocations */
            for (c--; c >= 0; c--)
            {
                free(huffmanArray[c]);
            }
            return NULL;
        }
    }

    /* assume that there will be exactly 1 EOF */
    huffmanArray[EOF_CHAR]->count = 1;
    huffmanArray[EOF_CHAR]->ignore = FALSE;
	
    /* count occurrence of each character */
    for (i = 0; i < raw_length; i++)
    {
    	c=raw_data[i];
        if (huffmanArray[c]->count < COUNT_T_MAX)
        {
            /* increment count for character and include in tree */
            huffmanArray[c]->count++;
            huffmanArray[c]->ignore = FALSE;
        }
        else
        {
            fprintf(stderr,
                "Input file contains too many 0x%02X to count.\n", c);
            return NULL;
        }
    }

    /* put array of leaves into a huffman tree */
    huffmanTree = BuildHuffmanTree(huffmanArray, NUM_CHARS);

    return huffmanTree;
}




/***************************************************************************
*                              Unaltered Code
***************************************************************************/


/***************************************************************************
*                  Canonical Huffman Encoding and Decoding
*
*   File    : chuffman.c
*   Purpose : Use canonical huffman coding to compress/decompress files
*   Author  : Michael Dipperstein
*   Date    : November 20, 2002
*
****************************************************************************
*   UPDATES
*
*   Date        Change
*   10/21/03    Fixed one symbol file bug discovered by David A. Scott
*   10/21/03    Dynamically allocate storage for canonical list.
*   11/20/03    Correcly handle codes up to 256 bits (the theoretical
*               max).  With symbol counts being limited to 32 bits, 31
*               bits will be the maximum code length.
*
*   $Id: chuffman.c,v 1.9 2007/09/20 03:30:06 michael Exp $
*   $Log: chuffman.c,v $
*   Revision 1.9  2007/09/20 03:30:06  michael
*   Changes required for LGPL v3.
*
*   Revision 1.8  2005/05/23 03:18:04  michael
*   Moved internal routines and definitions common to both canonical and
*   traditional Huffman coding so that they are only declared once.
*
*   Revision 1.7  2004/06/15 13:37:10  michael
*   Change function names and make static functions to allow linkage with huffman.
*
*   Revision 1.6  2004/02/26 04:55:36  michael
*   Remove main(), allowing code to be generate linkable object file.
*
*   Revision 1.4  2004/01/13 15:49:41  michael
*   Beautify header
*
*   Revision 1.3  2004/01/13 05:55:02  michael
*   Use bit stream library.
*
*   Revision 1.2  2004/01/05 05:03:18  michael
*   Use encoded EOF instead of counting characters.
*
*
*
****************************************************************************
*
* Huffman: An ANSI C Canonical Huffman Encoding/Decoding Routine
* Copyright (C) 2002-2005, 2007 by
* Michael Dipperstein (mdipper@alumni.engr.ucsb.edu)
*
* This file is part of the Huffman library.
*
* The Huffman library is free software; you can redistribute it and/or
* modify it under the terms of the GNU Lesser General Public License as
* published by the Free Software Foundation; either version 3 of the
* License, or (at your option) any later version.
*
* The Huffman library is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
* General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public License
* along with this program.  If not, see <http://www.gnu.org/licenses/>.
*
***************************************************************************/



/***************************************************************************
*                                FUNCTIONS
***************************************************************************/


///****************************************************************************
//*   Function   : CHuffmanDecodeFile
//*   Description: This routine reads a Huffman coded file and writes out a
//*                decoded version of that file.
//*   Parameters : inFile - Name of file to decode
//*                outFile - Name of file to write a tree to
//*   Effects    : Huffman encoded file is decoded
//*   Returned   : TRUE for success, otherwise FALSE.
//****************************************************************************/
//int CHuffmanDecodeFile(char *inFile, char *outFile)
//{
//    bit_file_t *bfpIn;
//    FILE *fpOut;
//    bit_array_t *code;
//    byte_t length;
//    char decodedEOF;
//    int i, newBit;
//    int lenIndex[NUM_CHARS];
//
//    /* open binary output file and bitfile input file */
//    if ((bfpIn = BitFileOpen(inFile, BF_READ)) == NULL)
//    {
//        perror(inFile);
//        return FALSE;
//    }
//
//    if (outFile == NULL)
//    {
//        fpOut = stdout;
//    }
//    else
//    {
//        if ((fpOut = fopen(outFile, "wb")) == NULL)
//        {
//            BitFileClose(bfpIn);
//            perror(outFile);
//            return FALSE;
//        }
//    }
//
//    /* allocate canonical code list */
//    code = BitArrayCreate(256);
//    if (code == NULL)
//    {
//        perror("Bit array allocation");
//        BitFileClose(bfpIn);
//        fclose(fpOut);
//        return FALSE;
//    }
//
//    /* initialize canonical list */
//    for (i = 0; i < NUM_CHARS; i++)
//    {
//        canonicalList[i].codeLen = 0;
//        canonicalList[i].code = NULL;
//    }
//
//    /* populate list with code length from file header */
//    if (!ReadHeader(canonicalList, bfpIn))
//    {
//        BitArrayDestroy(code);
//        BitFileClose(bfpIn);
//        fclose(fpOut);
//        return FALSE;
//    }
//
//    /* sort the header by code length */
//    qsort(canonicalList, NUM_CHARS, sizeof(canonical_list_t),
//        CompareByCodeLen);
//
//    /* assign the codes using same rule as encode */
//    if (AssignCanonicalCodes(canonicalList) == 0)
//    {
//        /* failed to assign codes */
//        BitFileClose(bfpIn);
//        fclose(fpOut);
//
//        for (i = 0; i < NUM_CHARS; i++)
//        {
//            if(canonicalList[i].code != NULL)
//            {
//                BitArrayDestroy(canonicalList[i].code);
//            }
//        }
//
//        return FALSE;
//    }
//
//    /* now we have a huffman code that matches the code used on the encode */
//
//    /* create an index of first code at each possible length */
//    for (i = 0; i < NUM_CHARS; i++)
//    {
//        lenIndex[i] = NUM_CHARS;
//    }
//
//    for (i = 0; i < NUM_CHARS; i++)
//    {
//        if (lenIndex[canonicalList[i].codeLen] > i)
//        {
//            /* first occurance of this code length */
//            lenIndex[canonicalList[i].codeLen] = i;
//        }
//    }
//
//    /* decode input file */
//    length = 0;
//    BitArrayClearAll(code);
//    decodedEOF = FALSE;
//
//    while(((newBit = BitFileGetBit(bfpIn)) != EOF) && (!decodedEOF))
//    {
//        if (newBit != 0)
//        {
//            BitArraySetBit(code, length);
//        }
//
//        length++;
//
//        if (lenIndex[length] != NUM_CHARS)
//        {
//            /* there are code of this length */
//            for(i = lenIndex[length];
//                (i < NUM_CHARS) && (canonicalList[i].codeLen == length);
//                i++)
//            {
//                if ((BitArrayCompare(canonicalList[i].code, code) == 0) &&
//                    (canonicalList[i].codeLen == length))
//                {
//                    /* we just read a symbol output decoded value */
//                    if (canonicalList[i].value != EOF_CHAR)
//                    {
//                        fputc(canonicalList[i].value, fpOut);
//                    }
//                    else
//                    {
//                        decodedEOF = TRUE;
//                    }
//                    BitArrayClearAll(code);
//                    length = 0;
//
//                    break;
//                }
//            }
//        }
//    }
//
//    /* close all files */
//    BitFileClose(bfpIn);
//    fclose(fpOut);
//
//    return TRUE;
//}

/****************************************************************************
*   Function   : CompareByCodeLen
*   Description: Compare function to be used by qsort for sorting canonical
*                list items by code length.  In the event of equal lengths,
*                the symbol value will be used.
*   Parameters : item1 - pointer canonical list item
*                item2 - pointer canonical list item
*   Effects    : None
*   Returned   : 1 if item1 > item2
*                -1 if item1 < item 2
*                0 if something went wrong (means item1 == item2)
****************************************************************************/
int CompareByCodeLen(const void *item1, const void *item2)
{
    if (((canonical_list_t *)item1)->codeLen >
        ((canonical_list_t *)item2)->codeLen)
    {
        /* item1 > item2 */
        return 1;
    }
    else if (((canonical_list_t *)item1)->codeLen <
        ((canonical_list_t *)item2)->codeLen)
    {
        /* item1 < item2 */
        return -1;
    }
    else
    {
        /* both have equal code lengths break the tie using value */
        if (((canonical_list_t *)item1)->value >
            ((canonical_list_t *)item2)->value)
        {
            return 1;
        }
        else
        {
            return -1;
        }
    }

    return 0;   /* we should never get here */
}

/****************************************************************************
*   Function   : CompareBySymbolValue
*   Description: Compare function to be used by qsort for sorting canonical
*                list items by symbol value.
*   Parameters : item1 - pointer canonical list item
*                item2 - pointer canonical list item
*   Effects    : None
*   Returned   : 1 if item1 > item2
*                -1 if item1 < item 2
****************************************************************************/
int CompareBySymbolValue(const void *item1, const void *item2)
{
    if (((canonical_list_t *)item1)->value >
        ((canonical_list_t *)item2)->value)
    {
        /* item1 > item2 */
        return 1;
    }

    /* it must be the case that item1 < item2 */
    return -1;
}

/****************************************************************************
*   Function   : BuildCanonicalCode
*   Description: This function builds a canonical Huffman code from a
*                Huffman tree.
*   Parameters : ht - pointer to root of tree
*                cl - pointer to canonical list
*   Effects    : cl is filled with the canonical codes sorted by the value
*                of the charcter to be encode.
*   Returned   : TRUE for success, FALSE for failure
****************************************************************************/
int BuildCanonicalCode(huffman_node_t *ht, canonical_list_t *cl)
{
    int i;
    int depth = 0;

    /* initialize list */
    for(i = 0; i < NUM_CHARS; i++)
    {
        cl[i].value = i;
        cl[i].codeLen = 0;
        cl[i].code = NULL;
    }

    /* fill list with code lengths (depth) from tree */
    for(;;)
    {
        /* follow this branch all the way left */
        while (ht->left != NULL)
        {
            ht = ht->left;
            depth++;
        }

        if (ht->value != COMPOSITE_NODE)
        {
            /* handle one symbol trees */
            if (depth == 0)
            {
                depth++;
            }

            /* enter results in list */
            cl[ht->value].codeLen = depth;
        }

        while (ht->parent != NULL)
        {
            if (ht != ht->parent->right)
            {
                /* try the parent's right */
                ht = ht->parent->right;
                break;
            }
            else
            {
                /* parent's right tried, go up one level yet */
                depth--;
                ht = ht->parent;
            }
        }

        if (ht->parent == NULL)
        {
            /* we're at the top with nowhere to go */
            break;
        }
    }

    /* sort by code length */
    qsort(cl, NUM_CHARS, sizeof(canonical_list_t), CompareByCodeLen);

    if (AssignCanonicalCodes(cl))
    {
        /* re-sort list in lexical order for use by encode algorithm */
        qsort(cl, NUM_CHARS, sizeof(canonical_list_t), CompareBySymbolValue);
        return TRUE;    /* success */
    }

    perror("Code assignment failed");
    return FALSE;       /* assignment failed */
}

/****************************************************************************
*   Function   : AssignCanonicalCode
*   Description: This function accepts a list of symbols sorted by their
*                code lengths, and assigns a canonical Huffman code to each
*                symbol.
*   Parameters : cl - sorted list of symbols to have code values assigned
*   Effects    : cl stores a list of canonical codes sorted by the length
*                of the code used to encode the symbol.
*   Returned   : TRUE for success, FALSE for failure
****************************************************************************/
int AssignCanonicalCodes(canonical_list_t *cl)
{
    int i;
    byte_t length;
    bit_array_t *code;

    /* assign the new codes */
    code = BitArrayCreate(NUM_CHARS - 1);
    BitArrayClearAll(code);

    length = cl[(NUM_CHARS - 1)].codeLen;

    for(i = (NUM_CHARS - 1); i >= 0; i--)
    {
        /* bail if we hit a zero len code */
        if (cl[i].codeLen == 0)
        {
            break;
        }

        /* adjust code if this length is shorter than the previous */
        if (cl[i].codeLen < length)
        {
            BitArrayShiftRight(code, (length - cl[i].codeLen));
            length = cl[i].codeLen;
        }

        /* assign left justified code */
        if ((cl[i].code = BitArrayDuplicate(code)) == NULL)
        {
            perror("Duplicating code");
            BitArrayDestroy(code);
            return FALSE;
        }

        BitArrayShiftLeft(cl[i].code, NUM_CHARS - 1 - length);

        BitArrayIncrement(code);
    }

    BitArrayDestroy(code);
    return TRUE;
}
/****************************************************************************
*   Function   : AllocHuffmanNode
*   Description: This routine allocates and initializes memory for a node
*                (tree entry for a single character) in a Huffman tree.
*   Parameters : value - character value represented by this node
*   Effects    : Memory for a huffman_node_t is allocated from the heap
*   Returned   : Pointer to allocated node.  NULL on failure to allocate.
****************************************************************************/
huffman_node_t *AllocHuffmanNode(int value)
{
    huffman_node_t *ht;

    ht = (huffman_node_t *)(malloc(sizeof(huffman_node_t)));

    if (ht != NULL)
    {
        ht->value = value;
        ht->ignore = TRUE;      /* will be FALSE if one is found */

        /* at this point, the node is not part of a tree */
        ht->count = 0;
        ht->level = 0;
        ht->left = NULL;
        ht->right = NULL;
        ht->parent = NULL;
    }
    else
    {
        perror("Allocate Node");
    }

    return ht;
}

/****************************************************************************
*   Function   : AllocHuffmanCompositeNode
*   Description: This routine allocates and initializes memory for a
*                composite node (tree entry for multiple characters) in a
*                Huffman tree.  The number of occurrences for a composite is
*                the sum of occurrences of its children.
*   Parameters : left - left child in tree
*                right - right child in tree
*   Effects    : Memory for a huffman_node_t is allocated from the heap
*   Returned   : Pointer to allocated node
****************************************************************************/
huffman_node_t *AllocHuffmanCompositeNode(huffman_node_t *left,
    huffman_node_t *right)
{
    huffman_node_t *ht;

    ht = (huffman_node_t *)(malloc(sizeof(huffman_node_t)));

    if (ht != NULL)
    {
        ht->value = COMPOSITE_NODE;     /* represents multiple chars */
        ht->ignore = FALSE;
        ht->count = left->count + right->count;     /* sum of children */
        ht->level = max(left->level, right->level) + 1;

        /* attach children */
        ht->left = left;
        ht->left->parent = ht;
        ht->right = right;
        ht->right->parent = ht;
        ht->parent = NULL;
    }
    else
    {
        perror("Allocate Composite");
        return NULL;
    }

    return ht;
}

/****************************************************************************
*   Function   : FreeHuffmanTree
*   Description: This is a recursive routine for freeing the memory
*                allocated for a node and all of its descendants.
*   Parameters : ht - structure to delete along with its children.
*   Effects    : Memory for a huffman_node_t and its children is returned to
*                the heap.
*   Returned   : None
****************************************************************************/
void FreeHuffmanTree(huffman_node_t *ht)
{
    if (ht->left != NULL)
    {
        FreeHuffmanTree(ht->left);
    }

    if (ht->right != NULL)
    {
        FreeHuffmanTree(ht->right);
    }

    free(ht);
}

/****************************************************************************
*   Function   : FindMinimumCount
*   Description: This function searches an array of HUFFMAN_STRCUT to find
*                the active (ignore == FALSE) element with the smallest
*                frequency count.  In order to keep the tree shallow, if two
*                nodes have the same count, the node with the lower level
*                selected.
*   Parameters : ht - pointer to array of structures to be searched
*                elements - number of elements in the array
*   Effects    : None
*   Returned   : Index of the active element with the smallest count.
*                NONE is returned if no minimum is found.
****************************************************************************/
int FindMinimumCount(huffman_node_t **ht, int elements)
{
    int i;                          /* array index */
    int currentIndex = NONE;        /* index with lowest count seen so far */
    int currentCount = INT_MAX;     /* lowest count seen so far */
    int currentLevel = INT_MAX;     /* level of lowest count seen so far */

    /* sequentially search array */
    for (i = 0; i < elements; i++)
    {
        /* check for lowest count (or equally as low, but not as deep) */
        if ((ht[i] != NULL) && (!ht[i]->ignore) &&
            (ht[i]->count < currentCount ||
                (ht[i]->count == currentCount && ht[i]->level < currentLevel)))
        {
            currentIndex = i;
            currentCount = ht[i]->count;
            currentLevel = ht[i]->level;
        }
    }

    return currentIndex;
}

/****************************************************************************
*   Function   : BuildHuffmanTree
*   Description: This function builds a huffman tree from an array of
*                HUFFMAN_STRCUT.
*   Parameters : ht - pointer to array of structures to be searched
*                elements - number of elements in the array
*   Effects    : Array of huffman_node_t is built into a huffman tree.
*   Returned   : Pointer to the root of a Huffman Tree
****************************************************************************/
huffman_node_t *BuildHuffmanTree(huffman_node_t **ht, int elements)
{
    int min1, min2;     /* two nodes with the lowest count */

    /* keep looking until no more nodes can be found */
    for (;;)
    {
        /* find node with lowest count */
        min1 = FindMinimumCount(ht, elements);

        if (min1 == NONE)
        {
            /* no more nodes to combine */
            break;
        }

        ht[min1]->ignore = TRUE;    /* remove from consideration */

        /* find node with second lowest count */
        min2 = FindMinimumCount(ht, elements);

        if (min2 == NONE)
        {
            /* no more nodes to combine */
            break;
        }

        ht[min2]->ignore = TRUE;    /* remove from consideration */

        /* combine nodes into a tree */
        if ((ht[min1] = AllocHuffmanCompositeNode(ht[min1], ht[min2])) == NULL)
        {
            return NULL;
        }

        ht[min2] = NULL;
    }

    return ht[min1];
}
