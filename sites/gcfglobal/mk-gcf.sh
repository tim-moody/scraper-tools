#!/bin/bash -x
# The scraping of gcfglobal may be easy enough to do in bash

WORKDIR=/library/working/rachel/gcf
DISPDIR=/library/www/html/modules/en-GCF2020
mkdir -p $WORKDIR/zip-files

# Get the current download page which has the names o the zip files
if [ ! -f $WORKDIR/download-all.html ];then
   wget -O $WORKDIR/download-all.html https://edu.gcfglobal.org/en/download/all
fi


# make a list of URL's for downloading
grep .*\.zip $WORKDIR/download-all.html | cut -f6 -d'"' >$WORKDIR/ziplist

# If the zip files are not preent, get them
for f in $(cat $WORKDIR/ziplist);do
   if [ ! -f $WORKDIR/zip-files/$(basename $f) ];then
      echo Looking for $WORKDIR/zip-file/$(basename $f)
      wget -P $WORKDIR/zip-files $f
   else
      echo $(basename $f) already downloaded $f
   fi
done

# Establish the directories receive files
mkdir -p $DISPDIR/scrypts
mkdir -p $DISPDIR/styles
mkdir -p $DISPDIR/fonts

# Unzip the content to a place where they can be displayed
curdir=$(pwd)
for f in $(cat $WORKDIR/ziplist);do
   basename=$(basename $f)
   base=${basename%.zip}
   if [ ! -d $DISPDIR/en/$base ];then
      mkdir -p $DISPDIR/en/$base
      cd $DISPDIR/en/$base
      echo unzipping $basename into $DISPDIR/en/$base
      /usr/bin/unzip -q $WORKDIR/zip-files/$basename
   fi
done
cd $curdir

# I was never able to download scripts, style, images in the root
# So I used a recursive wget -- mostly to get the lay of the land
GCF_TREE=/library/www/html/modules/oneline
mkdir -p $GCF_TREE
if [ ! -f $GCF_TREE/index.html ]; then
   wget -nHc -r -P $GCF_TREE/ -k -K --page-requisites https://edu.gcfglobal.org/
fi
/bin/cp -rpf $GCF_TREE/scripts $DISPDIR
/bin/cp -rpf $GCF_TREE/styles/deployment-en/ $DISPDIR/styles

/bin/cp -rpf $GCF_TREE/styles/deployment-en/index-en.concat.css $DISPDIR/styles/
/bin/cp -rpf $GCF_TREE/images $DISPDIR
/bin/cp -rpf $GCF_TREE/en/subjects $DISPDIR/en

mkdir -p $DISPDIR/en/topics
/bin/cp -rpf $GCF_TREE/en/topics/* $DISPDIR/en/topics/

# Get the fonts and icons that gcf refers to from googleapis
cd $WORKDIR/zip-files
if [ ! -f source-sans-pro-v14-latin.zip ];then
   wget http://download.iiab.io/content/source-sans-pro-v14-latin.zip
   wget http://download.iiab.io/content/material-design-icons-3.0.1.zip
   /usr/bin/unzip -q $WORKDIR/zip-files/material-design-icons-3.0.1.zip
   mkdir -p $DISPDIR/fonts
   cd $DISPDIR/fonts
   /usr/bin/unzip -q $WORKDIR/zip-files/source-sans-pro-v14-latin.zip
   cp -rp $WORKDIR/zip-files/material-design-icons-3.0.1/iconfont/* .
fi

# Put in our own css files which refer to the font files we just downloaded
cd $curdir
cp -p source-sans-pro.css $DISPDIR/styles
cp -p material-icons.css $DISPDIR/styles

# If tutorial.html is changed to index.html, the menu system works offline
cd $DISPDIR/en/
for f in $(find .|grep tutorial.html); do
  echo mv $f $(dirname $f)/index.html
  mv $f $(dirname $f)/index.html
done

# Change the absolute links to relative ones in topics directory

# First operate on the children
cd $DISPDIR/en/
for f in $(find {subjects,topics}|grep index.html); do
   echo Topics child $f
   sed -i -e's|href="/styles/|href="../../styles/|' $f
   sed -i -e's|src="/scripts/|src=../../scripts/|' $f
   sed -i -e's|src="/images/|src="../../images/|' $f
   sed -i -e's|https://fonts.googleapis.com/css?family=Source+Sans+Pro:200,300,400,600,700|../../styles/source-sans-pro.css|' $f
   sed -i -e's|https://fonts.googleapis.com/icon?family=Material+Icons|../../styles/material-icons.css|' $f
   sed -i -e's|https://media.gcflearnfree.org/global/gcfglobal-color.png|../../assets/gcfglobal-color.png|' $f
done

cd $DISPDIR/en/
for f in $(find .|grep index.html); do
   sed -i -e's|/en/|../../|' $f
   sed -i -e's|https://fonts.googleapis.com/css?family=Source+Sans+Pro:200,300,400,600,700|../../styles/source-sans-pro.css|' $f
   sed -i -e's|https://fonts.googleapis.com/icon?family=Material+Icons|../../styles/material-icons.css|' $f
   sed -i -e's|https://media.gcflearnfree.org/global/gcfglobal-color.png|../../assets/gcfglobal-color.png|' $f
done

cd $curdir
# copy in my own hand crafted landing page -- extracted from header dropdown
/bin/cp -rpf homepage.index.html $DISPDIR/index.html

# We need a nice logo on our landing page
mkdir -p $DISPDIR/assets
/bin/cp -rpf assets/* $DISPDIR/assets/
/bin/cp -rpf scripts/* $DISPDIR/scripts/
/bin/cp -rpf styles/* $DISPDIR/styles/

# update the main index.html to be relative links
   sed -i -e's|href="/styles/|href="./styles/|' $DISPDIR/index.html
   sed -i -e's|src="/images/|src="./images/|' $DISPDIR/index.html
   sed -i -e's|src="/scripts/|src="./scripts/|' $DISPDIR/index.html
   sed -i -e's|href="/en/|href="./en/|' $DISPDIR/index.html
   sed -i -e's|https://media.gcflearnfree.org/global/gcfglobal-color.png|./assets/gcfglobal-color.png|' $DISPDIR/index.html
   sed -i -e's|https://media.gcflearnfree.org/assets/logo/logo.png|./assets/logo.png|' $DISPDIR/index.html

