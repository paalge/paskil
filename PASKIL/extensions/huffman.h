/***************************************************************************
*                        Huffman Library Header File
*
*   File    : huffman.h
*   Purpose : Provide header file for programs linking to Huffman library
*             functions.
*   Author  : Michael Dipperstein
*   Date    : February 25, 2004
*
****************************************************************************
*   UPDATES
*
*   $Id: huffman.h,v 1.3 2007/09/20 03:30:06 michael Exp $
*   $Log: huffman.h,v $
*   Revision 1.3  2007/09/20 03:30:06  michael
*   Changes required for LGPL v3.
*
*   Revision 1.2  2004/06/15 13:37:59  michael
*   Incorporate changes in chuffman.c.
*
*   Revision 1.1  2004/02/26 04:58:22  michael
*   Initial revision.  Headers for encode/decode functions.
*
*
****************************************************************************
*
* Huffman: An ANSI C Huffman Encoding/Decoding Routine
* Copyright (C) 2004, 2007 by
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
#include "bitarray.h"
#include <limits.h>
#ifndef _HUFFMAN_H_
#define _HUFFMAN_H_

/***************************************************************************
*                       STRUCTURE DEFINITIONS
***************************************************************************/

typedef struct canonical_list_t
{
    int value;        /* characacter represented */
    int codeLen;     /* number of bits used in code (1 - 255) */
    bit_array_t *code;  /* code used for symbol (left justified) */
} canonical_list_t;

typedef struct encoded_array_t
{
 bit_array_t *data; //encoded data
 canonical_list_t *canonicalList; 
 unsigned long long int size; //length of encoded data in bits
} encoded_array_t;


/* use preprocessor to verify type lengths */
#if (UCHAR_MAX != 0xFF)
#error This program expects unsigned char to be 1 byte
#endif

#if (UINT_MAX != 0xFFFFFFFF)
#error This program expects unsigned int to be 4 bytes
#endif

/* system dependent types */
typedef unsigned char byte_t;       /* unsigned 8 bit */
typedef unsigned int count_t;       /* unsigned 32 bit for character counts */

typedef struct huffman_node_t
{
    int value;          /* character(s) represented by this entry */
    count_t count;      /* number of occurrences of value (probability) */

    char ignore;        /* TRUE -> already handled or no need to handle */
    int level;          /* depth in tree (root is 0) */

    /***********************************************************************
    *  pointer to children and parent.
    *  NOTE: parent is only useful if non-recursive methods are used to
    *        search the huffman tree.
    ***********************************************************************/
    struct huffman_node_t *left, *right, *parent;
} huffman_node_t;



/***************************************************************************
*                                CONSTANTS
***************************************************************************/
#define FALSE   0
#define TRUE    1
#define NONE    -1

#define COUNT_T_MAX     UINT_MAX    /* based on count_t being unsigned int */

#define COMPOSITE_NODE      -1      /* node represents multiple characters */
#define NUM_CHARS           65537     /* 65536 bytes (16bit image data) + EOF */
#define EOF_CHAR    (NUM_CHARS - 1) /* index used for EOF */

/***************************************************************************
*                                 MACROS
***************************************************************************/
#define max(a, b) ((a)>(b)?(a):(b))



/***************************************************************************
*                               PROTOTYPES
***************************************************************************/

/* canonical code */
encoded_array_t *CHuffmanEncodeArray(int *raw_data,int raw_length);
int BuildCanonicalCode(huffman_node_t *ht, canonical_list_t *cl);
int AssignCanonicalCodes(canonical_list_t *cl);
int CompareByCodeLen(const void *item1, const void *item2);
int * histogram(int *data,int length);

/* create/destroy tree */
huffman_node_t *GenerateTreeFromFile(FILE *inFile);
huffman_node_t *GenerateTreeFromArray(int *raw_data,int raw_length);
huffman_node_t *BuildHuffmanTree(huffman_node_t **ht, int elements);
huffman_node_t *AllocHuffmanNode(int value);
void FreeHuffmanTree(huffman_node_t *ht);


#endif /* _HUFFMAN_H_ */
