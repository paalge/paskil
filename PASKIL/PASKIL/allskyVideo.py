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
This is something of an experimental module, and is largely unfinished. It is designed 
to make producing videos from allsky images easy. It may be removed in future versions
of PASKIL.
"""
from __future__ import with_statement
import sys, os, time
import pymedia.video.vcodec as vcodec

def createQuicklookVideo(dataset, filename, images_per_sec=2):
    """
    Creates an mpeg2 video clip of quicklook images of images in the dataset. The
    dataset argument should be an allskyData.dataset object, the filename is the output
    filename.
    """   
    #ensure correct file extension
    if not filename.endswith((".mpg",".mpeg")):
        filename = filename + ".mpeg"
    
    #work out size that a quicklook will be
    first_im = dataset.getImage(dataset.getTimes()[0])
    size = first_im.createQuicklook().size
    
    #create video encoder
    params= { \
          'type': 0,
          'gop_size': 12,
          'frame_rate_base': 1,
          'max_b_frames': 0,
          'height': size[1],
          'width': size[0],
          'frame_rate': images_per_sec,
          'deinterlace': 2000,
          'bitrate': 9800000,
          'id': vcodec.getCodecID('mpeg2video')
        }
    encoder = vcodec.Encoder( params )
        
    with open(filename, 'wb') as ofp:
        for im in dataset:
            ql = im.createQuicklook()
            
            if ql.size != size:
                ql = ql.resize(size)
            
            bmpFrame= vcodec.VFrame( vcodec.formats.PIX_FMT_RGB24, size, (ql.convert('RGB').tostring(),None,None))
            yuvFrame= bmpFrame.convert( vcodec.formats.PIX_FMT_YUV420P )
            d = encoder.encode( yuvFrame )
            ofp.write(d.data)
        
        #add the last image to the stream again - otherwise you won't see it!    
        bmpFrame = vcodec.VFrame(vcodec.formats.PIX_FMT_RGB24, size, (ql.convert('RGB').tostring(),None,None))
        yuvFrame = bmpFrame.convert(vcodec.formats.PIX_FMT_YUV420P)
        d = encoder.encode(yuvFrame)
        ofp.write(d.data)
