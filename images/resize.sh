#!/bin/bash

# Assumes you have imagemagick installed
# sudo apt install imagemagick

for infile in large-to-be-resized-with-script/*.jpg; do
    outfile=$(basename $infile)
    echo "$infile --> $outfile"
    convert -resize 1000x1000 $infile $outfile
done
