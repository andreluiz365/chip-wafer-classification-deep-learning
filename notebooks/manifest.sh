#!/bin/bash
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

INDIR=$1
OUTFILE=$2

if [ "$INDIR" == "" ]
then
    echo "Usage: $0 <input folder> <output file>"
    exit 1
fi
if [ "$OUTFILE" == "" ]
then
    echo "Usage: $0 <input folder> <output file>"
    exit 1
fi

declare -A classmap
classmap["Center"]="0"
classmap["Donut"]="1"
classmap["Edge-Loc"]="2"
classmap["Edge-Ring"]="3"
classmap["Loc"]="4"
classmap["Near-full"]="5"
classmap["Random"]="6"
classmap["Scratch"]="7"
classmap["none"]="8"

# Desired format:
# index label relative path
#5      1   your_image_directory/train_img_dog1.jpg
#1000   0   your_image_directory/train_img_cat1.jpg
#22     1   your_image_directory/train_img_dog2.jpg

for F in `ls $INDIR`; do
        echo Processing files in $F
        for IMG in `ls $INDIR/$F`; do
                #echo Processing $IMG
                BASENAME=`basename -s .png $IMG`
                LABEL=${classmap[$F]}
                echo $BASENAME $LABEL $F/$IMG >> $OUTFILE
        done
done
