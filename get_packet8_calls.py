#!/usr/bin/python
#
# 
# GetPacket8Calls
# License: Public Domain
#		By Isam M. <r0cket(NO_SPAM)jump@yahoo.com> 
#		http://biodegradablegeek.com
# 
# Outputs the last 10 incoming and outgoing calls from 
# your VoIP Packet8 unit, via calllog.html 
# 
# This hack was written in 2002-2003 to keep track of my call-log 
# so I don't miss calls I was getting from a girl I liked 
# 


# TODO On failure, show more debugging info. Stack trace or function.. anything



import sys
import os
import re
import urllib2


# Instead of '1234567890', format numbers as '(123) 456-7890'
PRETTY_FORMAT=True

# IP of your packet8 unit.
IP='192.168.1.100'

# Set the port of your packet8 unit if it is not default (80) 
# PORT=80

# Password of your packet8 unit. Default is 'admin'
PW='admin'


def FormatPhoneNum(digits):
	if digits[0]=='r' or not PRETTY_FORMAT:
		return digits
	
	n=len(digits)
	if n==10:
		return '(%s) %s-%s' % (digits[0:3], digits[3:6], digits[6:10])
	elif n==7:
		return '%s-%s' % (digits[0:3], digits[3:7])
	else:
		return digits


def GetUnparsedLine(body, start):
	end=body.find('";}')
	return body[5:end+1]


def MakeDict(line):
	# Line is in this format.
	# a="1";b="2";c="3"

	m=re.search(r'td="(.+)";n="(.+)";c="(.+)";io="(.+)";ln="(.+)"', line)
	if not m: return {}
	dict={}
	dict['td']=m.group(1)
	dict['n']=m.group(2)
	dict['c']=m.group(3)
	dict['io']=m.group(4)
	dict['ln']=m.group(5)
	return dict


def DisplayList(calllist):
	try:
		n=1
		for call in calllist:
			if call.keys()==[]: continue
			print '%2d: ' % n,
			n+=1
			if call['io']=='O':
				print 'TO   ',
			else:
				print 'FROM ',
			if PRETTY_FORMAT:
				frmt='%14s'
			else:
				frmt='%10s'
			frmt += '  %s'
			print frmt % (FormatPhoneNum(call['n']), call['td'])
	except:
		sys.__stderr__.write('Unable to display calllist..\n')
		sys.exit(1)



def GetCalls(body):
	try:
		calls=[]
		start=body.find('==i){')
		while start != -1:
			calls.append(MakeDict(GetUnparsedLine(body[start:], start)))
			start=body.find('==i){', start+1)
		DisplayList(calls)
	except:
		sys.__stderr__.write('Unable to parse body..\n')
		sys.exit(1)


def GetBody(pw, ip, port=80):
	try:
		req = urllib2.Request('http://%s:%s' % (ip, port))
		post='REDIRECT=calllog.htm&.PASSWORD=%s' % pw
		req.add_data(post)
		urllib2.urlopen(req)

		b = urllib2.urlopen(urllib2.Request('http://192.168.1.100/calllog.htm'))
		body=b.read()
	except:
		sys.__stderr__.write(
				'Error requesting calllog.htm using password "%s" from %s:%s\n' % \
																	(pw, ip, port))
		sys.exit(1)
	return body


if __name__=='__main__':
	try:
		GetCalls(GetBody(PW, IP))
	except:
		sys.__stderr__.write('Something bad happened. Oh no!\n')
		sys.exit(1)


