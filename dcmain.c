int CLASS main (int argc, char **argv)
{
  int arg, status=0;
  int timestamp_only=0, thumbnail_only=0, identify_only=0;
  int user_qual=-1, user_black=-1, user_sat=-1, user_flip=-1;
  int use_fuji_rotate=1, write_to_stdout=0, quality, i, c;
  char opm, opt, *ofname, *sp, *cp, *bpfile=0, *dark_frame=0;
  const char *write_ext;
  struct utimbuf ut;
  FILE *ofp;
#ifndef NO_LCMS
  char *cam_profile=0, *out_profile=0;
#endif

#ifndef LOCALTIME
  putenv ("TZ=UTC");
#endif
#ifdef LOCALEDIR
  setlocale (LC_CTYPE, "");
  setlocale (LC_MESSAGES, "");
  bindtextdomain ("dcraw", LOCALEDIR);
  textdomain ("dcraw");
#endif

  if (argc == 1) {
    printf(_("\nRaw photo decoder \"dcraw\" v%s"), VERSION);
    printf(_("\nby Dave Coffin, dcoffin a cybercom o net\n"));
    printf(_("\nUsage:  %s [OPTION]... [FILE]...\n\n"), argv[0]);
    puts(_("-v        Print verbose messages"));
    puts(_("-c        Write image data to standard output"));
    puts(_("-e        Extract embedded thumbnail image"));
    puts(_("-i        Identify files without decoding them"));
    puts(_("-i -v     Identify files and show metadata"));
    puts(_("-z        Change file dates to camera timestamp"));
    puts(_("-w        Use camera white balance, if possible"));
    puts(_("-a        Average the whole image for white balance"));
    puts(_("-A <x y w h> Average a grey box for white balance"));
    puts(_("-r <r g b g> Set custom white balance"));
    puts(_("+M/-M     Use/don't use an embedded color matrix"));
    puts(_("-C <r b>  Correct chromatic aberration"));
    puts(_("-P <file> Fix the dead pixels listed in this file"));
    puts(_("-K <file> Subtract dark frame (16-bit raw PGM)"));
    puts(_("-k <num>  Set the darkness level"));
    puts(_("-S <num>  Set the saturation level"));
    puts(_("-n <num>  Set threshold for wavelet denoising"));
    puts(_("-H [0-9]  Highlight mode (0=clip, 1=unclip, 2=blend, 3+=rebuild)"));
    puts(_("-t [0-7]  Flip image (0=none, 3=180, 5=90CCW, 6=90CW)"));
    puts(_("-o [0-5]  Output colorspace (raw,sRGB,Adobe,Wide,ProPhoto,XYZ)"));
#ifndef NO_LCMS
    puts(_("-o <file> Apply output ICC profile from file"));
    puts(_("-p <file> Apply camera ICC profile from file or \"embed\""));
#endif
    puts(_("-d        Document mode (no color, no interpolation)"));
    puts(_("-D        Document mode without scaling (totally raw)"));
    puts(_("-j        Don't stretch or rotate raw pixels"));
    puts(_("-W        Don't automatically brighten the image"));
    puts(_("-b <num>  Adjust brightness (default = 1.0)"));
    puts(_("-q [0-3]  Set the interpolation quality"));
    puts(_("-h        Half-size color image (twice as fast as \"-q 0\")"));
    puts(_("-f        Interpolate RGGB as four colors"));
    puts(_("-m <num>  Apply a 3x3 median filter to R-G and B-G"));
    puts(_("-s [0..N-1] Select one raw image or \"all\" from each file"));
    puts(_("-4        Write 16-bit linear instead of 8-bit with gamma"));
    puts(_("-T        Write TIFF instead of PPM"));
    puts("");
    return 1;
  }
  argv[argc] = "";
  for (arg=1; (((opm = argv[arg][0]) - 2) | 2) == '+'; ) {
    opt = argv[arg++][1];
    if ((cp = strchr (sp="nbrkStqmHAC", opt)))
      for (i=0; i < "11411111142"[cp-sp]-'0'; i++)
	if (!isdigit(argv[arg+i][0])) {
	  fprintf (stderr,_("Non-numeric argument to \"-%c\"\n"), opt);
	  return 1;
	}
    switch (opt) {
      case 'n':  threshold   = atof(argv[arg++]);  break;
      case 'b':  bright      = atof(argv[arg++]);  break;
      case 'r':
	   FORC4 user_mul[c] = atof(argv[arg++]);  break;
      case 'C':  aber[0] = 1 / atof(argv[arg++]);
		 aber[2] = 1 / atof(argv[arg++]);  break;
      case 'k':  user_black  = atoi(argv[arg++]);  break;
      case 'S':  user_sat    = atoi(argv[arg++]);  break;
      case 't':  user_flip   = atoi(argv[arg++]);  break;
      case 'q':  user_qual   = atoi(argv[arg++]);  break;
      case 'm':  med_passes  = atoi(argv[arg++]);  break;
      case 'H':  highlight   = atoi(argv[arg++]);  break;
      case 's':
	shot_select = abs(atoi(argv[arg]));
	multi_out = !strcmp(argv[arg++],"all");
	break;
      case 'o':
	if (isdigit(argv[arg][0]) && !argv[arg][1])
	  output_color = atoi(argv[arg++]);
#ifndef NO_LCMS
	else     out_profile = argv[arg++];
	break;
      case 'p':  cam_profile = argv[arg++];
#endif
	break;
      case 'P':  bpfile     = argv[arg++];  break;
      case 'K':  dark_frame = argv[arg++];  break;
      case 'z':  timestamp_only    = 1;  break;
      case 'e':  thumbnail_only    = 1;  break;
      case 'i':  identify_only     = 1;  break;
      case 'c':  write_to_stdout   = 1;  break;
      case 'v':  verbose           = 1;  break;
      case 'h':  half_size         = 1;		/* "-h" implies "-f" */
      case 'f':  four_color_rgb    = 1;  break;
      case 'A':  FORC4 greybox[c]  = atoi(argv[arg++]);
      case 'a':  use_auto_wb       = 1;  break;
      case 'w':  use_camera_wb     = 1;  break;
      case 'M':  use_camera_matrix = (opm == '+');  break;
      case 'D':
      case 'd':  document_mode = 1 + (opt == 'D');
      case 'j':  use_fuji_rotate   = 0;  break;
      case 'W':  no_auto_bright    = 1;  break;
      case 'T':  output_tiff       = 1;  break;
      case '4':  output_bps       = 16;  break;
      default:
	fprintf (stderr,_("Unknown option \"-%c\".\n"), opt);
	return 1;
    }
  }
  if (use_camera_matrix < 0)
      use_camera_matrix = use_camera_wb;
  if (arg == argc) {
    fprintf (stderr,_("No files to process.\n"));
    return 1;
  }
  if (write_to_stdout) {
    if (isatty(1)) {
      fprintf (stderr,_("Will not write an image to the terminal!\n"));
      return 1;
    }
#if defined(WIN32) || defined(DJGPP) || defined(__CYGWIN__)
    if (setmode(1,O_BINARY) < 0) {
      perror ("setmode()");
      return 1;
    }
#endif
  }
  for ( ; arg < argc; arg++) {
    status = 1;
    image = 0;
    oprof = 0;
    meta_data = ofname = 0;
    ofp = stdout;
    if (setjmp (failure)) {
      if (fileno(ifp) > 2) fclose(ifp);
      if (fileno(ofp) > 2) fclose(ofp);
      status = 1;
      goto cleanup;
    }
    ifname = argv[arg];
    if (!(ifp = fopen (ifname, "rb"))) {
      perror (ifname);
      continue;
    }
    status = (identify(),!is_raw);
    if (user_flip >= 0)
      flip = user_flip;
    switch ((flip+3600) % 360) {
      case 270:  flip = 5;  break;
      case 180:  flip = 3;  break;
      case  90:  flip = 6;
    }
    if (timestamp_only) {
      if ((status = !timestamp))
	fprintf (stderr,_("%s has no timestamp.\n"), ifname);
      else if (identify_only)
	printf ("%10ld%10d %s\n", (long) timestamp, shot_order, ifname);
      else {
	if (verbose)
	  fprintf (stderr,_("%s time set to %d.\n"), ifname, (int) timestamp);
	ut.actime = ut.modtime = timestamp;
	utime (ifname, &ut);
      }
      goto next;
    }
    write_fun = &CLASS write_ppm_tiff;
    if (thumbnail_only) {
      if ((status = !thumb_offset)) {
	fprintf (stderr,_("%s has no thumbnail.\n"), ifname);
	goto next;
      } else if (thumb_load_raw) {
	load_raw = thumb_load_raw;
	data_offset = thumb_offset;
	height = thumb_height;
	width  = thumb_width;
	filters = 0;
      } else {
	fseek (ifp, thumb_offset, SEEK_SET);
	write_fun = write_thumb;
	goto thumbnail;
      }
    }
    if (load_raw == &CLASS kodak_ycbcr_load_raw) {
      height += height & 1;
      width  += width  & 1;
    }
    if (identify_only && verbose && make[0]) {
      printf (_("\nFilename: %s\n"), ifname);
      printf (_("Timestamp: %s"), ctime(&timestamp));
      printf (_("Camera: %s %s\n"), make, model);
      if (artist[0])
	printf (_("Owner: %s\n"), artist);
      if (dng_version) {
	printf (_("DNG Version: "));
	for (i=24; i >= 0; i -= 8)
	  printf ("%d%c", dng_version >> i & 255, i ? '.':'\n');
      }
      printf (_("ISO speed: %d\n"), (int) iso_speed);
      printf (_("Shutter: "));
      if (shutter > 0 && shutter < 1)
	shutter = (printf ("1/"), 1 / shutter);
      printf (_("%0.1f sec\n"), shutter);
      printf (_("Aperture: f/%0.1f\n"), aperture);
      printf (_("Focal length: %0.1f mm\n"), focal_len);
      printf (_("Embedded ICC profile: %s\n"), profile_length ? _("yes"):_("no"));
      printf (_("Number of raw images: %d\n"), is_raw);
      if (pixel_aspect != 1)
	printf (_("Pixel Aspect Ratio: %0.6f\n"), pixel_aspect);
      if (thumb_offset)
	printf (_("Thumb size:  %4d x %d\n"), thumb_width, thumb_height);
      printf (_("Full size:   %4d x %d\n"), raw_width, raw_height);
    } else if (!is_raw)
      fprintf (stderr,_("Cannot decode file %s\n"), ifname);
    if (!is_raw) goto next;
    shrink = filters &&
	(half_size || threshold || aber[0] != 1 || aber[2] != 1);
    iheight = (height + shrink) >> shrink;
    iwidth  = (width  + shrink) >> shrink;
    if (identify_only) {
      if (verbose) {
	if (use_fuji_rotate) {
	  if (fuji_width) {
	    fuji_width = (fuji_width - 1 + shrink) >> shrink;
	    iwidth = fuji_width / sqrt(0.5);
	    iheight = (iheight - fuji_width) / sqrt(0.5);
	  } else {
	    if (pixel_aspect < 1) iheight = iheight / pixel_aspect + 0.5;
	    if (pixel_aspect > 1) iwidth  = iwidth  * pixel_aspect + 0.5;
	  }
	}
	if (flip & 4)
	  SWAP(iheight,iwidth);
	printf (_("Image size:  %4d x %d\n"), width, height);
	printf (_("Output size: %4d x %d\n"), iwidth, iheight);
	printf (_("Raw colors: %d"), colors);
	if (filters) {
	  printf (_("\nFilter pattern: "));
	  if (!cdesc[3]) cdesc[3] = 'G';
	  for (i=0; i < 16; i++)
	    putchar (cdesc[fc(i >> 1,i & 1)]);
	}
	printf (_("\nDaylight multipliers:"));
	FORCC printf (" %f", pre_mul[c]);
	if (cam_mul[0] > 0) {
	  printf (_("\nCamera multipliers:"));
	  FORC4 printf (" %f", cam_mul[c]);
	}
	putchar ('\n');
      } else
	printf (_("%s is a %s %s image.\n"), ifname, make, model);
next:
      fclose(ifp);
      continue;
    }
    if (use_camera_matrix && cmatrix[0][0] > 0.25) {
      memcpy (rgb_cam, cmatrix, sizeof cmatrix);
      raw_color = 0;
    }
    image = (ushort (*)[4]) calloc (iheight*iwidth, sizeof *image);
    merror (image, "main()");
    if (meta_length) {
      meta_data = (char *) malloc (meta_length);
      merror (meta_data, "main()");
    }
    if (verbose)
      fprintf (stderr,_("Loading %s %s image from %s ...\n"),
	make, model, ifname);
    if (shot_select >= is_raw)
      fprintf (stderr,_("%s: \"-s %d\" requests a nonexistent image!\n"),
	ifname, shot_select);
    fseeko (ifp, data_offset, SEEK_SET);
    (*load_raw)();
    if (zero_is_bad) remove_zeroes();
    bad_pixels (bpfile);
    if (dark_frame) subtract (dark_frame);
    quality = 2 + !fuji_width;
    if (user_qual >= 0) quality = user_qual;
    if (user_black >= 0) black = user_black;
    if (user_sat > 0) maximum = user_sat;
#ifdef COLORCHECK
    colorcheck();
#endif
    if (is_foveon && !document_mode) foveon_interpolate();
    if (!is_foveon && document_mode < 2) scale_colors();
    pre_interpolate();
    if (filters && !document_mode) {
      if (quality == 0)
	lin_interpolate();
      else if (quality == 1 || colors > 3)
	vng_interpolate();
      else if (quality == 2)
	ppg_interpolate();
      else ahd_interpolate();
    }
    if (mix_green)
      for (colors=3, i=0; i < height*width; i++)
	image[i][1] = (image[i][1] + image[i][3]) >> 1;
    if (!is_foveon && colors == 3) median_filter();
    if (!is_foveon && highlight == 2) blend_highlights();
    if (!is_foveon && highlight > 2) recover_highlights();
    if (use_fuji_rotate) fuji_rotate();
#ifndef NO_LCMS
    if (cam_profile) apply_profile (cam_profile, out_profile);
#endif
    convert_to_rgb();
    if (use_fuji_rotate) stretch();
thumbnail:
    if (write_fun == &CLASS jpeg_thumb)
      write_ext = ".jpg";
    else if (output_tiff && write_fun == &CLASS write_ppm_tiff)
      write_ext = ".tiff";
    else
      write_ext = ".pgm\0.ppm\0.ppm\0.pam" + colors*5-5;
    ofname = (char *) malloc (strlen(ifname) + 64);
    merror (ofname, "main()");
    if (write_to_stdout)
      strcpy (ofname,_("standard output"));
    else {
      strcpy (ofname, ifname);
      if ((cp = strrchr (ofname, '.'))) *cp = 0;
      if (multi_out)
	sprintf (ofname+strlen(ofname), "_%0*d",
		snprintf(0,0,"%d",is_raw-1), shot_select);
      if (thumbnail_only)
	strcat (ofname, ".thumb");
      strcat (ofname, write_ext);
      ofp = fopen (ofname, "wb");
      if (!ofp) {
	status = 1;
	perror (ofname);
	goto cleanup;
      }
    }
    if (verbose)
      fprintf (stderr,_("Writing data to %s ...\n"), ofname);
    (*write_fun)(ofp);
    fclose(ifp);
    if (ofp != stdout) fclose(ofp);
cleanup:
    if (meta_data) free (meta_data);
    if (ofname) free (ofname);
    if (oprof) free (oprof);
    if (image) free (image);
    if (multi_out) {
      if (++shot_select < is_raw) arg--;
      else shot_select = 0;
    }
  }
  return status;
}

