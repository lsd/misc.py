#!/usr/bin/python 
# 
# PyUp - Python CGI Upload Script 
#   By Isam M. http://biodegradablegeek.com/ 
#   September 21st 2004 
#
# This hideous arrangement of bytes was a 
# direct port from a CGI script I wrote in C 
# 
# This script actually gained a lot of momentum 
# back when ImageShack and RapidShare didn't exist. 
# I had to make it private because the bandwidth usage 
# was lagging me in Counter-Strike. 
# 
# TODO Filter results
# TODO can not have upload list on the same page..
# TODO Arrow to show desc/asc sort display
# TODO ability to browse more than one file at a time 
# TODO Read settings from config file 
# 

import os
import re
import glob
import time
import sys
import string
import cgi
import cgitb; cgitb.enable();
import urllib


###############################################################################
# Modify these to fit your needs. 'True' and 'False' are case sensitive.
###############################################################################

# Used to link to the local files
HOST='http://do.main.me/'

# Uploaded files will go here. Server needs write permission.
UPLOADDIR='../upload/files'

# After a successful upload, a link to the file will be displayed.
# LINK/filename_of_the_uploaded_file
LINK=HOST+'upload/files/'

# Ban file, has a list of the IPS to ban, ascii file, ip on each line
BANFILE='../upload/bans'

# Log files (Server needs write permission)
LOG_ACCESS='../upload/logs/access.log'
LOG_ERROR='../uploadlogs/error.log'

# Templates 
TEMPLATE_BANNED='../upload/templates/banned.html'
TEMPLATE_MAIN='../upload/templates/main.html'
TEMPLATE_FORM='../upload/templates/form.html'
TEMPLATE_FORM_UPFIELD='../upload/templates/uploadfield.html'

# Turning logging off is not r_tttmended.
LOG=True

# Upload file size limit in bytes.
MAXSZ=1024*1024*15

# Chunk of file read and written to disk at a time.
CHUNKSZ=1024*1024

# If False, uploaded files are not publicly displayed.
DISPLAYLOCALFILES=True

# The field name in the HTML code, you need a %d in it.
FIELDFMT='file_%d_'
RENAMEFMT='as_%d'


def StripPath(filename):
	"""Strip the path from file and return filename alone."""
	# Some OSs do not use / in their file system, Windows
	# for example uses \, so let's convert all to /
	if not filename:
		return ''
	tmp=re.sub(r'(%(2f|2F|5c|5C|3a|3A))|\\|:', '/', filename)
	x=string.split(tmp, '/')
	return x[len(x)-1]


def FileExtension(filename):
	dot=filename.rfind('.')
	if (-1==dot):
		return None
	# The user can embed HTML as the file extension.
	return cgi.escape(filename[dot+1:].lower())


def FormatFileSize(sz):
	"""Return filesize in readable human form."""
	# Bytes 
	if 1024>sz:
		ret=str(sz)
		return ret
	# Kilobytes
	if ((1024*1024)>sz):
		kb=float(sz/1024.0)
		ret=str(round(kb,1))+'K'
		return ret
	# Megabytes
	if ((1024*1024*1024)>sz):
		mb=float((sz/1024.0)/1024.0)
		ret=str(round(mb,1))+'M'
	else:
		# Gigabytes
		gb=float(((sz/1024.0)/1024.0)/1024)
		ret=str(round(gb,1))+'G'
	return ret


class Time:
	def __init__(self):
		self.seconds=0
		self.minutes=0
		self.hours=0
	def __str__(self):
		# Omit seconds 
		m=str(self.minutes)
		if len(m)==1: m = '0' + m
		return str(self.hours) + ':' \
				+ m


def TimeToSeconds(t):
	minutes = t.hours * 60 + t.minutes
	seconds = minutes * 60 + t.seconds
	return seconds 


def SecondsToTime(s):
	time = Time()
	time.hours = s/3600
	s = s- time.hours * 3600
	time.minutes = s/60
	s = s- time.minutes * 60
	time.s = s
	return time


def LogLine(logfile, line):
	try:
		fp=file(logfile, 'a')
		entry=time.strftime('[%m/%d/%y %I:%M:%S %p] ')
		entry+=GetVisitorIP()+': '+line
		fp.write(entry+'\n')
		fp.close()
	except:
		# Try to log to error file, if we can not (bad) just leave
		try:
			fp=file(LOG_ERROR, 'a')
			entry=time.strftime('[%m/%d/%y %I:%M:%S %p] ')
			entry+=': Log entry "' + line + '" to file "' + logfile + '"'
			fp.write(entry+'\n')
			fp.close()
		except:
			return


def LogAccess(line):
	LogLine(LOG_ACCESS, line)


def LogUpload(remotefile, uploadedfile):
	x='Uploaded ' + remotefile
	if remotefile != uploadedfile: x += ' as ' + uploadedfile
	LogLine(LOG_ACCESS, x)


def LogError(error):
	x='Error: ' + error
	LogLine(LOG_ERROR, x)


def LinkToLocalFile(file, short=True, maxlen=-1, quote=False):
	"""Return html link code for file.
	
	short, if true will return the link in a short form, 
	<a href="http://asdf/file">file</a>
	as opposed to long form, which is:
	<a href="http://asdf/file">http://asdf/file</a>

	maxlen is used only when short is True, maxlen is the
	of chars to display for file, if the file is too
	long, it returns the link with 3 dots appended to the end
	to show that it continues on.
	<a href="http://asdf/longfileblablablablabla.exe">longfilebl...</a>
	-1 means turn that off and show all of it
	"""
	if quote:
		file=urllib.quote(file)

	if short:
		if -1==maxlen:
			a=file
		else:
			a=file[0:maxlen]
			if (len(file)-len(a)) >= 3:
				a+='...'
	else:
		a=LINK+file

	link='<a href="' + HOST + '/' \
	+ UPLOADDIR + '/' \
	+ file + '">' 
	return link + cgi.escape(a) + '</a>'


def ColumnSortLink(col, order, name=None):
	# <a href="scriptname.cgi?sort=col&order=asc">Col</a>
	if not name: name=col.lower()
	script = os.path.basename(sys.argv[0])
	return '<a href="%s?sort=%s&order=%s">%s</a>' \
		% (script, name, order, col)


def SortDictionary(lidic, column, order):
	""" This is very bad.. bubble sort to sort a list of dictionaries
		by a specific key. """
	for a in range(0, len(lidic)-1):
		for b in range(a, len(lidic)):
			if order=='asc': 
				if lidic[a][column] > lidic[b][column]:
					lidic[a], lidic[b] = lidic[b], lidic[a]
			else:
				if lidic[a][column] < lidic[b][column]:
					lidic[a], lidic[b] = lidic[b], lidic[a]
	return lidic


def ColColor(column, x):
	if column==x:
		return '#cccccc'
	return '#ffffff'


def GetLocalFiles(form):
	"""Print a table of the files in the upload directory."""

	# Let us see how the files are to be sorted 
	accepted_columns = ['name', 'size', 'dt', 'mime', 'ext', 'ip']
	if form.has_key('sort') and \
		form['sort'].value and \
		form['sort'].value.lower() in accepted_columns:
		column=form['sort'].value.lower()
	else:
		column='dt'

	if form.has_key('order') and \
		form['order'].value and \
		form['order'].value.lower() in ['asc', 'desc']: 
		order=form['order'].value.lower()
	else:
		order='asc'

	# We have a 'database' file that lists information
	# about each uploaded file. 
	# filename, type, date uploaded, IP of uploader
	# We want to open up this file now, if it doesn't
	# exist, either something is broken or more likely
	# this is the first time this script is being run.

	try:
		db=file('../upload/files.db', 'r')
		# File is delimeted by \
		fd={}
		files=[]
		f=db.readline()
		while f:
			# Ignore lines that begin with a # 
			if f != '\n' and f.lstrip()[0]!='#':
				d=string.split(f, ' / ')
				fd['name']=d[0]
				fd['size']=int(d[1])
				fd['dt']=d[2]
				fd['mime']=d[3]
				fd['ip']=d[4][:-1] # Ends with \n
				fd['ext']=FileExtension(d[0])
				files.append(fd.copy())
			f=db.readline()
		db.close()
		if files==[]:
			return ''
	except IOError:
		# File doesn't exist? Let's create an empty one
		try:
			# Try to create the file.
			db=file('../upload/files.db', 'w')
			db.close()
			return ''
		except IOError:
			LogError('Could not open/create local list of uploaded files! Check permissions.')
			return ''
	res = ''
	res += '<table class="files">\n<tr>'
	if order=='asc':
		order='desc'
	else:
		order='asc'
	res += '<td class="filerow" bgcolor="' + ColColor('name', column) + '"><b><p>%s</p></b></td>' % ColumnSortLink('Name', order)
	res += '<td class="filerow" bgcolor="' + ColColor('size', column)  + '"><b><p>%s</p></b></td>' % ColumnSortLink('Size', order)
	res += '<td class="filerow" bgcolor="' + ColColor('dt', column)  + '"><b><p>%s</p></b></td>' % ColumnSortLink('Date/Time', order, name='dt')
	res += '<td class="filerow" bgcolor="' + ColColor('ext', column)  + '"><b><p>%s</p></b></td>' % ColumnSortLink('Ext', order)
	res += '<td class="filerow" bgcolor="' + ColColor('mime', column)  + '"><b><p>%s</p></b></td>' % ColumnSortLink('MIME', order)
	res += '<td class="filerow" bgcolor="' + ColColor('ip', column)  + '"><b><p>%s</p></b></td>' % ColumnSortLink('IP', order)
	res += '</tr>'
	sorted=SortDictionary(files, column, order)

	gray = True
	for i in range(len(sorted)):
		lnk=LinkToLocalFile(files[i]['name'], maxlen=35) 
		sz=FormatFileSize(files[i]['size']) 
		dt=files[i]['dt']
		if not files[i]['ext']: files[i]['ext']='N/A'
		if gray:
			res += '<tr bgcolor="#eeeeee">'
			gray=False;
		else:
			res += '<tr bgcolor="#ffffff">'
			gray=True
#		res += '<td><p>' + str(i+1) + '</p></td>'
		res += '<td class="filerow"><p>'       + lnk + '</p></td>\n'
		res += '<td class="filerow"><p>' + sz + '</p></td>\n'
		res += '<td class="filerow"><p>' + dt + '</p></td>\n'
		res += '<td class="filerow"><p>' + files[i]['ext'] + '</p></td>\n'
		res += '<td class="filerow"><p>' + files[i]['mime'] + '</p></td>\n'
		res += '<td class="filerow"><p>' + files[i]['ip'] + '</p></td>\n'
		res += '</tr>'
	res += '</table>'
	return res


def GetVisitorIP():
	return os.getenv('REMOTE_ADDR', 'get.ip.failed')


def HandleUpload(form, NumOfUploads):	
	"""Save from form to file dir."""
	# Let us see if the user DID click the upload button.
	if not form.has_key('upform'): return ''
	
	res=''
	for i in range(NumOfUploads):
		field=FIELDFMT % (i)
		if not form.has_key(field): 
			# This is probably the user's first time on the page.
			continue
		else:
			fs=form[field]
			if not fs.value or not fs.filename:
				continue

			# Check if user wants to save this locally with a different name. 
			renameto=RENAMEFMT % (i)
			if form.has_key(renameto) and ''!=form[renameto].value:
				fn=form[renameto].value
			else:
				fn=StripPath(fs.filename)

			# Check if the name is allowed. 
			if	'/' in fn or \
				'\\' in fn or \
				'.htaccess'==fn or \
				'robots.txt'==fn or \
				fn.startswith('index.'):
				res += '<p class="result_warning">Name "<b>'+fn+'</b>" is not allowed.<br />'
				res += 'Please choose another name for the file.</p>'
				continue

			# At this point, we have the absolute path to the local file.
			pfn=os.path.join(UPLOADDIR, fn)

			# Check if file exists already.
			try:
				tmp=file(pfn, 'rb')
				tmp.close()
				res += '<p class="result_warning">A file named <b>'+fn+\
						'</b> already exists.<br />'\
						'Please choose another name and try again.</p>'
				if LOG: LogAccess('Tried uploaded file "' + fn + '" but it already exists')
			except IOError:
				# We probably caught a file not found exception.
				# Meaning we are good to go.
				try:
					f=file(pfn, 'wb')
				except IOError:
					res += '<p class="result_warning"><b>'+cgi.escape(fn)+'</b> could not be' \
							'uploaded.</p>'
					evidence.append('Upload of ' + fn + 'failed')
					continue

				# Write file to local disk.
				tb=0
				while 1:
					if tb>MAXSZ:
						res += '<p class="result_warning">Max file size limit exceeded (' \
									+FormatFileSize(MAXSZ) + ')</p>'
						evidence.append('Exceeded file limit with file: ' + fn)
						os.remove(pfn)
						return res
					br=fs.file.read(CHUNKSZ)
					if not br:
						break
					tb+=len(br)
					f.write(br)
				f.close()
				if LOG: LogUpload(fs.filename, fn)
				res += '<p class="result_success">Uploaded <b>' + cgi.escape(fn) + \
						'</b> successfully.</p>'
#				res += '<p>ID of file:</p> %d<br />' % (fileid)
				res += '<p>'+LinkToLocalFile(fn, short=False, quote=True)
				res += '</p>'

				# Upload was successful, let's add this file to the db now.
				try:
					f=file('../upload/files.db', 'a')
					dt=time.strftime('%D %I:%M %p')
					tp=fs.type
					# " / " is our delimeter in the file, we can't
					# have it in the type else it will ruin EVERYTHING.
					tp=tp.replace(' / ', '/')
					if len(tp) > 25: 
						tp = tp[0:25] + '...'
					line=fn + ' / ' \
							+ str(tb) + ' / ' \
							+ dt + ' / ' \
							+ tp + ' / ' \
							+ GetVisitorIP()
					f.write(line + '\n')
					f.close()
				except:
					res += 'File could not be added to file list'
					res += 'You will not be able to<br /> see the file'
					res += 'on the file list but you can still access it'
					res += '<br /> using the URL but tell the admin '
					res += 'what happened.'
					return res
	return res


def GetNumFields(form):
	"""Return # of upload fields we should display."""
		# Did user click 'update' to update the number of fields?
	n=0
	if form.has_key('numfields'): 
		n=form['numfields'].value
	else:
		# Guess not, let's see if we have a previous number.
		if form.has_key('numfieldshidden'): 
			n=form['numfieldshidden'].value
	try:
		n = int(n)
		if 0 < n < 100: return n
	except:
		pass
	return 3


def GetTemplate(template):
	"""Open and return a template file"""
	try:
		f = file(template)
		tmp = f.read()
		f.close()
		return tmp
	except:
		return None


def GetUploadForm(NumOfUpFields):
	"""Generate the html upload form and return."""
	raw = GetTemplate(TEMPLATE_FORM)
	if not raw: 
		LogError('Could not open template file "' + TEMPLATE_FORM + '"')
		PrintErrorPage('Could not open form template, check permissions')

	raw = raw.replace('%FORM_SCRIPT_NAME%', os.path.basename(sys.argv[0]))
	raw = raw.replace('%FORM_NUMUP%', str(NumOfUpFields))
	
	upfieldtemp = GetTemplate(TEMPLATE_FORM_UPFIELD)
	if not upfieldtemp: 
		LogError('Could not open template file "' + TEMPLATE_FORM + '"')
		PrintErrorPage('Could not open form upfield template, check permissions')
	
	upfieldtemp = upfieldtemp.replace('%FORM_UPFIELDNAME%', 'file_%d_')
	upfieldtemp = upfieldtemp.replace('%FORM_UPLOADAS%', 'as_%d')
	upfieldtemp = upfieldtemp.replace('%FORM_ARROW%', 'id_%d')
	upfieldtemp = upfieldtemp.replace('%FORM_OPTIONAL_TABLE%', 'optional_' + 'id_%d')

	for n in range(NumOfUpFields):
		tmp = upfieldtemp % (n, n, n, n)
		raw = raw.replace('%FORM_UPFIELDS%', tmp + '%FORM_UPFIELDS%')

	raw = raw.replace('%FORM_UPFIELDS%', '')

	return raw


def ParseTemplate(raw, Replace):
	"""Take the raw template, replace some variables in it and return."""

	if Replace.has_key('%MAIN_RESULT%'): 
		raw = raw.replace('%MAIN_RESULT%', Replace['%MAIN_RESULT%'])

	if Replace.has_key('%LOCAL_FILES%'):
		raw = raw.replace('%LOCAL_FILES%', Replace['%LOCAL_FILES%'])
		
	if Replace.has_key('%UPLOAD_FORM%'):
		raw = raw.replace('%UPLOAD_FORM%', Replace['%UPLOAD_FORM%'])

	if Replace.has_key('%MAX_SIZE%'):
		raw = raw.replace('%MAX_SIZE%', Replace['%MAX_SIZE%'])

	return raw


def PrintErrorPage(error, MIME='Content-type: text/plain\n'):
	print MIME
	print error
	sys.exit(0)


def ParsePrintTemplate(template, NumOfUpFields=None, 
							MainResult='', 
							LocalFiles='',
							MIME='Content-type: text/html\n'):
	"""Parse and print a template file."""
	res = GetTemplate(template)
	# TODO LOG ERROR
	if not res: PrintErrorPage('Could not open main template, check permissions')

	replace = {}
	replace['%MAIN_RESULT%'] = MainResult
	replace['%LOCAL_FILES%'] = LocalFiles
	replace['%UPLOAD_FORM%'] = GetUploadForm(NumOfUpFields)
	replace['%MAX_SIZE%'] = FormatFileSize(MAXSZ)
	res = ParseTemplate(res, replace)
	print MIME
	print res
	sys.exit(0)


def main():
	# ------------------------------------------------
#	print 'Content-type: text/html\n'
#	print '<img src="../under-construction.jpg" />'
#	sys.exit(0)
	# ------------------------------------------------
	form=cgi.FieldStorage()
	numupfields = GetNumFields(form)
	result = HandleUpload(form, numupfields)
	if DISPLAYLOCALFILES: 
		ParsePrintTemplate(TEMPLATE_MAIN, numupfields, result, GetLocalFiles(form))
	else:
		ParsePrintTemplate(TEMPLATE_MAIN, numupfields, result)


def PrintHtmlFile(HtmlFile, MIME='Content-type: text/html\n'):
	"""Print passed file to screen."""
	res = GetTemplate(HtmlFile)
	if res:
		print MIME
		print res
	else:
		LogError('Could not open template file "' + TEMPLATE_FORM + '"')
		PrintErrorPage('You are banned.')


def CheckIP():
	"""Checks if this ip is on the ban list, if so - do something accordingly."""
	try:
		user=GetVisitorIP()
		bf=file(BANFILE, 'r')
		for ip in bf.xreadlines():
			if ip[:-1]==user:
				LogAccess('Banned user tried to access page')
				sys.exit(0)
		bf.close()
	except:
		if sys.exc_type == SystemExit:
			PrintHtmlFile(TEMPLATE_BANNED) # Send this user the banned template 
			sys.exit(0)
		# Something happened while reading bans file.. 
		# Let us log it and move on.
		LogError('Error checking bans files "' + BANFILE + '"')


if __name__=='__main__':
	CheckIP()
	main()


