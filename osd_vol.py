#!/usr/bin/python
# 
# Script for on-screen-volume-display using osd_cat
# This does *not* change volume, it just converts 
# the volume (from aumix -q) to bars and displays on screen. 
# 
# By Isam M. http://biodegradablegeek.com 
# License? Public Domain
#

import os
import sys
import re

# Query the volume
f=os.popen('aumix -q', 'r')
query=f.readline()
f.close()
m=re.search(r'vol ([0-9]+)', query)
if not m:
	sys.exit(1)

# m.group(1) is our volume. 
# Each bar will be 5 volume, 
# so that means we need 
# 5/100=20 bars 

r3z='Volume ['

bars=int(m.group(1))/5
for i in range(bars):
	r3z+='\|'

dif=20-bars
for i in range(dif):
	r3z+='-'
r3z+=']'

os.system('echo ' + r3z + ' | osd_cat '\
		'-d 1 -s 2 -c Yellow -p Bottom -A center -o 50 '\
		'-f -*-courier-medium-r-*-*-80-*-*-*-*-*-*-*')


