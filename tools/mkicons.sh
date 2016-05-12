#!/bin/sh

cd icons
mkdir MufSim.iconset
sips -z 16 16     MufSim1024.png --out MufSim.iconset/icon_16x16.png
sips -z 32 32     MufSim1024.png --out MufSim.iconset/icon_16x16@2x.png
sips -z 32 32     MufSim1024.png --out MufSim.iconset/icon_32x32.png
sips -z 64 64     MufSim1024.png --out MufSim.iconset/icon_32x32@2x.png
sips -z 128 128   MufSim1024.png --out MufSim.iconset/icon_128x128.png
sips -z 256 256   MufSim1024.png --out MufSim.iconset/icon_128x128@2x.png
sips -z 256 256   MufSim1024.png --out MufSim.iconset/icon_256x256.png
sips -z 512 512   MufSim1024.png --out MufSim.iconset/icon_256x256@2x.png
sips -z 512 512   MufSim1024.png --out MufSim.iconset/icon_512x512.png
cp MufSim1024.png MufSim.iconset/icon_512x512@2x.png
iconutil -c icns MufSim.iconset
rm -rf MufSim.iconset

mkdir winicons
for x in 16 32 48 128 256 ; do
    sips -z $x $x MufSim1024.png --out winicons/$x.png
done
convert winicons/16.png winicons/32.png winicons/48.png winicons/128.png winicons/256.png  MufSim.ico
rm -rf winicons

