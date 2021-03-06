import fileinput
import csv
import requests
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove
import os
import pandas as pd
import fnmatch
from requests.auth import HTTPBasicAuth
import time
import openpyxl
import math
from datetime import datetime,timedelta
import numpy as np
from astropy.time import Time
from PyAstronomy import pyasl
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from scipy import optimize
import matplotlib.pyplot as plt
import re

cadence_min=-1
cadence_min2=-60

def find_index(input, file, i): 
	o = open(file, 'r') 
	myData = csv.reader(o) 
	index = 0 
	for row in myData:
		#print(row)
		try:
			if row[i] == input: 
				return index 
			else : index=index+1 #Make sure that this does not return an error if input is not in the file. 
		except:
			index=index+1
			continue

def query_mag(name):
	url = 'https://ziggy.ucolick.org/yse/download_photometry/' + name + '/'
	r = requests.get(url=url, auth=HTTPBasicAuth('djones','BossTent1'))
	fout = open(name+'tmp','w')
	print(r._content.decode('utf-8'),file=fout)
	fout.close()

def column(matrix, i):
	return [row[i] for row in matrix]

def estimateMag(name, date,band):
	query_mag(name)
	with open(name+'tmp', 'r') as f:
		content = f.readlines()
		with open(name+'ziggy.csv', 'w+',  newline = '') as csvFile:
			csvWriter = csv.writer(csvFile, delimiter = ' ')
			ct = False
			for elem in content:
				if "VARLIST" in elem:
					ct = True
					r = True
				if not ct:
					continue
				if r:
					elem = ' '.join(elem.split())
					elem = elem.replace(' ', ',')
					csvWriter.writerow([elem])
					r=False
					continue
				if not ("Swope" in elem):
					continue
				elem = ' '.join(elem.split())
				elem = elem.replace(' ', ',')
				csvWriter.writerow([elem])
			del csvWriter
	data = list(csv.reader(open(name+'ziggy.csv', 'r')))
	data2=[]
	for i,line in enumerate(data):
		if line[2] == band:
			data2.append(line)
	data2 = np.array(data2)
	x_data = column(data2,1)
	y_data = column(data2,5)
	x_data = [ float(x) for x in x_data ]
	y_data = [ float(x) for x in y_data ]
	params, params_covariance = optimize.curve_fit(bazin,x_data,y_data,bounds=((-np.inf, 58600, -np.inf,1,-20), (5000, 58700, 150,np.inf,20)))
	print(params)
	'''plt.scatter(x_data, y_data)
	plt.plot(x_data, bazin(x_data, params[0], params[1], params[2], params[3],params[4]))
	plt.gca().invert_yaxis()
	plt.show()'''
	mag = bazin(date, params[0],params[1],params[2],params[3],params[4])


def getTargetSet(names, priority,r):
	for name in names:
		#pull data from ziggy
		print("start " +name)
		query_mag(name)
		print("finish " +name)
		band = ''

		#Fix the file from ziggy and make it into a csv 
		txt_file = (name+"tmp")
		old="s"
		with open(txt_file,'r') as in_text:
			old = in_text.read() # read everything in the file
			old = old.replace('      ', ',')
			old = old.replace('  ', ',')
			old = old.replace('	', ',')
			old = old.replace('\t', ',')
			old = old.replace(',,', ',')
		with open(txt_file,'w') as in_text: 
			in_text.truncate(0)
			in_text.write(old) 

		#Converting to a csv
		with open(name+'tmp', 'r+') as f:
			content = f.read()
			#content = " ".join(content.split())
			#content = content.replace('	', '')
			content = content.replace('\t', ' ')
			content = content.replace('		 ', ',')
			content = (re.sub('[ \t]+' , ' ', content))
			content = content.replace(' ', ',')
			while ",," in content:
					pos = content.find(",,")
					content = content[:pos] + content[pos+1:]
			f.seek(0)
			f.write(content)
			

		with open(name+'tmp', 'r') as in_file:
			stripped = (line.strip() for line in in_file)
			lines = (line.split(",") for line in stripped if line)
			with open(name+'ziggy.csv', 'w') as out_file:
				writer = csv.writer(out_file)
				writer.writerows(lines)

		phots = list(csv.reader(open(name+"ziggy.csv")))
		startRow=0
		startRow = find_index("VARLIST:", name+'ziggy.csv',0)
		try:
			phots[startRow+1]
		except:
			print("There was a problem dealing with this file. Recheck the google sheet to make sure nothing is going wrong there.")
			continue
		lastswope = startRow+1;
		
		ct = False
		inc=True
		r1=find_index("Swope",name+'ziggy.csv',7)
		new = False
		if not (isinstance(r1, int)):
			new = True
		else:
			startRow=r1
			lastswope = startRow+1;
		if not new:
			for row in phots[startRow+1:]:
				try:
					if row[7] == "Swope": #Finding the Swope photometry from the ysepz files
						ct = True  
					if (ct and row[7] != "Swope"):
						break
					lastswope=lastswope+1 
				except:
					break
		else:
			lastswope = len(phots) - 2
		if inc==False:
			continue
		ct = False
		index = lastswope-6

		skip = False
		#These are the list of supernovae that we want to not use the V band. 
		if name=='2018bcb' or name=='2018dyb' or name=='2018fyk' or name=='2018hyz' or name=='2018ido' or name=='2018lna' or name=='2018jbv':
			skip = True 

		dates=[]
		indexo = []
		if not new: 
			for i,row in enumerate(phots[lastswope-6:lastswope]):
				dates.append(row[1])
				indexo.append(i)
			latest = (dates[len(dates)-1])
			recdates=[]
			for i,num in enumerate(dates):
				if float(num)+1<float(latest):
					continue
				else:
					recdates.append(indexo[i])
			print(recdates)
			index = lastswope-6+int(recdates[0])-1
			for row in phots[lastswope-6+int(recdates[0]-1):lastswope]:
				if skip:
					break
				if row[2] == "V":
					ct = True
					band = 'V'
					break
				index=index+1
			skip = False
			#These are the list of supernovae that we want to actually specifically use r band
			if name=='2005ip' or name=='2009ip' or name=='2010da' or name=='2013L':
				skip = True
			if not ct:
				index = lastswope-6+int(recdates[0])-1
				for row in phots[lastswope-6+int(recdates[0])-1:lastswope]:
					if row[2] == "r":
						ct = True
						band = 'r'
						break
					index=index+1
			
			if not ct:
				index = lastswope-6+int(recdates[0])-1
				for row in phots[lastswope-6+int(recdates[0])-1:lastswope]:
					if skip:
						break
					if row[2] == "g":
						ct = True
						band = 'g'
						break
					index=index+1
			if not ct:
				index = lastswope-6+int(recdates[0])-1
				for row in phots[lastswope-6+int(recdates[0])-1:lastswope]:
					if skip:
						break
					if row[2] == "i":
						ct = True
						band = 'i'
						break
					index=index+1
			if not ct:
				index = lastswope-6+int(recdates[0])-1
				for row in phots[lastswope-6+int(recdates[0])-1:lastswope]:
					if skip:
						break
					if row[2] == "B":
						ct = True
						band = 'B'
						break
					index=index+1
			if not ct:
				print("No valid band found. Check ziggy phot file. ")
		else:
			index = lastswope-1
		#Find mag and date of magnitude
		dateOfMagMJD = float(phots[index][1])
		mag = float(phots[index][5])

		#f = A * exp(-(t-t0)/tfall)/(1+exp(-(t-t0)/trise)) + B


		print(mag)
		#Finding and converting date
		pong = Time(dateOfMagMJD, format = 'mjd')
		pong.format = 'decimalyear'
		dateOfMagUT = pyasl.decimalYearGregorianDate(pong.value, form='yyyy-mm-dd')
		dateOfMagUT = datetime.strptime(dateOfMagUT, "%Y-%m-%d").strftime("%m/%d/%Y")
		print(dateOfMagUT)

		row = find_index(name, datetime.strftime(datetime.today(),'%Y%m%d') + '_Targets.csv',0)

		#Printing everything back into the targets.csv file. 
		readTargets = csv.reader(open(datetime.strftime(datetime.today(),'%Y%m%d') + '_Targets.csv'))
		linesTargets = list(readTargets)
		linesTargets[0][4] = "Recent obs date"
		linesTargets[0][5] = "Recent V_r_g mag"
		
		if r==0:
			linesTargets[0].append("Band")
			r=1

		linesTargets[row][4] = dateOfMagUT
		linesTargets[row][5] = mag
		
		if name=='2018bcb' or name=='2018dyb' or name=='2018fyk' or name=='2018hyz' or name=='2018ido' or name=='2018lna' or name=='2018jbv':
			linesTargets[row][5] = 21
			band = 'V'
		if name=='2005ip' or name=='2009ip' or name=='2010da' or name=='2013L':
			linesTargets[row][4] = '06/07/2019'
			linesTargets[row][5] = 10
			band = 'r'
		
		if linesTargets[row][3] == '1':
			linesTargets[row][3] = str(priority)
		if new:
			band = phots[index][2]
		linesTargets[row].append(band)
		print(linesTargets[row])

		writeTargets = csv.writer(open(datetime.strftime(datetime.today(),'%Y%m%d') + '_Targets.csv', 'w'))
		writeTargets.writerows(linesTargets)

		del writeTargets

		print("Done working with " +name)

		r=1

r=0
#Find supernovaes to query for with the spreadsheet!
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('Python Sheets B-e2ab6d0240c1.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open('Swope SN Observing January 2020').sheet1
print("connected")

indices = []
cadences = wks.col_values(2)


for i,c in enumerate(cadences[2:]):
	try:
		if c=='#VALUE!':
			print("Ending loop!")
			break
		if c!= '' and int(c)>cadence_min:
			print(c)
			indices.append((i+2))
	except TypeError:
		print("Error at " + i)
		continue
print(indices)

writer = csv.writer(open(datetime.strftime(datetime.today(),'%Y%m%d') + '_Targets.csv', 'w')) # This should generate the new target list

with open(datetime.strftime(datetime.today(),'%Y%m%d') + '_Targets.csv', "w") as my_empty_csv:
  pass 

writer.writerows([wks.row_values(1)[2:9]])

for i in indices:
	writer.writerows([wks.row_values(1+i)[2:9]])
del writer

names=[]
with open(datetime.strftime(datetime.today(),'%Y%m%d') + "_Targets.csv") as csv_file:
	for row in csv.reader(csv_file, delimiter=','):
		if row[0] == '':
			print("NOTICE THIS")
			continue;
		names.append(row[0])
print(names)

getTargetSet(names, 1,0) #First priority targets!

print('Done with first pass. Moving on to less important targets.')


indices2=[]
for i,c in enumerate(cadences[2:]):
	try:
		if c=='#VALUE!':
			print("Ending loop!")
			break
		if c!= '' and int(c)<cadence_min and int(c)>cadence_min2:
			print(c)
			indices2.append((i+2))
	except TypeError:
		print("Error at " + i)
		continue
print(indices2)


writer = csv.writer(open(datetime.strftime(datetime.today(),'%Y%m%d') + '_Targets.csv', 'a')) # This should generate the new target list

names2=[]
for i in indices2:
	writer.writerows([wks.row_values(1+i)[2:9]])
	names2.append(wks.row_values(1+i)[2])
del writer
print(names2)

getTargetSet(names2,2,1) #second priority targets here


print("Done! Check the targets.csv file. ")
