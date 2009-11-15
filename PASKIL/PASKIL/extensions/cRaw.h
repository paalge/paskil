/*
Copyright (C) Nial Peters 2009

This file is part of PASKIL.

PASKIL is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PASKIL is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PASKIL.  If not, see <http://www.gnu.org/licenses/>.
*/

//define a structure to hold all the global variables

struct glob_var {
FILE* ifp;
short order;
char *ifname, *meta_data;
char cdesc[5], desc[512], make[64], model[64], model2[64], artist[64];
float flash_used, canon_ev, iso_speed, shutter, aperture, focal_len;
time_t timestamp;
unsigned shot_order, kodak_cbpp, filters, exif_cfa, unique_id;
off_t    strip_offset, data_offset;
off_t    thumb_offset, meta_offset, profile_offset;
unsigned thumb_length, meta_length, profile_length;
unsigned thumb_misc, *oprof, fuji_layout, shot_select, multi_out;
unsigned tiff_nifds, tiff_samples, tiff_bps, tiff_compress;
unsigned black, maximum, mix_green, raw_color, use_gamma, zero_is_bad;
unsigned zero_after_ff, is_raw, dng_version, is_foveon, data_error;
unsigned tile_width, tile_length, gpsdata[32];
ushort raw_height, raw_width, height, width, top_margin, left_margin;
ushort shrink, iheight, iwidth, fuji_width, thumb_width, thumb_height;
int flip, tiff_flip, colors;
double pixel_aspect, aber[4];
ushort (*image)[4], white[8][8], curve[0x4001], cr2_slice[3], sraw_mul[4];
float bright, user_mul[4], threshold;
int half_size, four_color_rgb, document_mode, highlight;
int verbose, use_auto_wb, use_camera_wb, use_camera_matrix;
int output_color, output_bps, output_tiff, med_passes;
int no_auto_bright;
unsigned greybox[4];
float cam_mul[4], pre_mul[4], cmatrix[3][4], rgb_cam[3][4];
double xyz_rgb[3][3];
float d65_white[3];
int histogram[4][0x2000];
void (*write_thumb)(FILE *), (*write_fun)(FILE *);
void (*load_raw)(), (*thumb_load_raw)();
jmp_buf failure;

struct decode {
  struct decode *branch[2];
  int leaf;
} first_decode[2048], *second_decode, *free_decode;

struct {
  int loc_width, loc_height, bps, comp, phint, offset, loc_flip, samples, bytes;
} tiff_ifd[10];

struct {
  int format, key_off, loc_black, black_off, split_col, tag_21a;
  float tag_210;
} ph1;
	
};

//prototype free globals function
void free_globals(struct glob_var *globals);

#define timestamp globals->timestamp
#define ifp globals->ifp
#define order globals->order
#define ifname globals->ifname
#define meta_data globals->meta_data
#define cdesc globals->cdesc
#define desc globals->desc
#define make globals->make
#define model globals->model
#define model2 globals->model2
#define artist globals->artist
#define flash_used globals->flash_used
#define canon_ev globals->canon_ev
#define iso_speed globals->iso_speed
#define shutter globals->shutter
#define aperture globals->aperture
#define focal_len globals->focal_len
#define shot_order globals->shot_order
#define kodak_cbpp globals->kodak_cbpp
#define filters globals->filters
#define exif_cfa globals->exif_cfa
#define unique_id globals->unique_id
#define strip_offset globals->strip_offset
#define data_offset globals->data_offset
#define thumb_offset globals->thumb_offset
#define meta_offset globals->meta_offset
#define profile_offset globals->profile_offset
#define thumb_length globals->thumb_length
#define meta_length globals->meta_length
#define profile_length globals->profile_length
#define thumb_misc globals->thumb_misc
#define oprof globals->oprof
#define fuji_layout globals->fuji_layout
#define shot_select globals->shot_select
#define multi_out globals->multi_out
#define tiff_nifds globals->tiff_nifds
#define tiff_samples globals->tiff_samples
#define tiff_bps globals->tiff_bps
#define tiff_compress globals->tiff_compress
#define black globals->black
#define maximum globals->maximum
#define mix_green globals->mix_green
#define raw_color globals->raw_color
#define use_gamma globals->use_gamma
#define zero_is_bad globals->zero_is_bad
#define zero_after_ff globals->zero_after_ff
#define is_raw globals->is_raw
#define dng_version globals->dng_version
#define is_foveon globals->is_foveon
#define data_error globals->data_error
#define tile_width globals->tile_width
#define tile_length globals->tile_length
#define gpsdata globals->gpsdata
#define raw_height globals->raw_height
#define raw_width globals->raw_width
#define height globals->height
#define width globals->width
#define top_margin globals->top_margin
#define left_margin globals->left_margin
#define shrink globals->shrink
#define iheight globals->iheight
#define iwidth globals->iwidth
#define fuji_width globals->fuji_width
#define thumb_width globals->thumb_width
#define thumb_height globals->thumb_height
#define flip globals->flip
#define tiff_flip globals->tiff_flip
#define colors globals->colors
#define pixel_aspect globals->pixel_aspect
#define aber globals->aber
#define image globals->image
#define white globals->white
#define curve globals->curve
#define cr2_slice globals->cr2_slice
#define sraw_mul globals->sraw_mul
#define bright globals->bright
#define user_mul globals->user_mul
#define threshold globals->threshold
#define half_size globals->half_size
#define four_color_rgb globals->four_color_rgb
#define document_mode globals->document_mode
#define highlight globals->highlight
#define verbose globals->verbose
#define use_auto_wb globals->use_auto_wb
#define use_camera_wb globals->use_camera_wb
#define use_camera_matrix globals->use_camera_matrix
#define output_color globals->output_color
#define output_bps globals->output_bps
#define output_tiff globals->output_tiff
#define med_passes globals->med_passes
#define no_auto_bright globals->no_auto_bright
#define greybox globals->greybox
#define cam_mul globals->cam_mul
#define pre_mul globals->pre_mul
#define cmatrix globals->cmatrix
#define rgb_cam globals->rgb_cam
#define xyz_rgb globals->xyz_rgb
#define d65_white globals->d65_white
#define histogram globals->histogram
#define write_thumb globals->write_thumb
#define write_fun globals->write_fun
#define load_raw globals->load_raw
#define thumb_load_raw globals->thumb_load_raw
#define failure globals->failure
#define first_decode globals->first_decode
#define second_decode globals->second_decode
#define free_decode globals->free_decode
#define tiff_ifd globals->tiff_ifd
#define ph1 globals->ph1
