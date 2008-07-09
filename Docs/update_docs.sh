#!/bin/sh
set -e
cd /home/nialp/allsky/PASKIL/Docs
rm *.html

pydoc -w ./
