import fileinput
import csv
import requests
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove
import os
import pandas as pd
import fnmatch
import wget
from requests.auth import HTTPBasicAuth
import time
import openpyxl
import math
from datetime import datetime
import numpy as np
from astropy.time import Time
from PyAstronomy import pyasl
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
    rr = requests.get(url=url, auth=HTTPBasicAuth('djones','BossTent1'))
    fout = open(name+'tmp','w')
    print(rr._content.decode('utf-8'),file=fout)
    #fout.close()

def getTargetSet(names, priority,r):
    for name in names:
        #pull data from ziggy
        print("start " +name)
        query_mag(name)
        print("finish" +name)
        band = ''

        #Fix the file from ziggy and make it into a csv 
        txt_file = (name+"tmp")
        old="s"
        with open(txt_file,'r') as in_text:
            old = in_text.read() # read everything in the file
            old = old.replace('      ', ',')
            old = old.replace('  ', ',')
        with open(txt_file,'w') as in_text:
            in_text.truncate(0)
            in_text.write(old)


        with open(name+'tmp', 'r') as f:
            content = f.readlines()
            with open(name+'ziggy.csv', 'w+',  newline = '') as csvFile:
                csvWriter = csv.writer(csvFile, delimiter = ' ')
                for elem in content:
                    csvWriter.writerow([elem.strip()])

        phots = list(csv.reader(open(name+"ziggy.csv")))
        startRow=0
        startRow = find_index("VARLIST:,MJD,,FLT,FLUXCAL, FLUXCALERR,,MAG,, MAGERR,, TELESCOPE,, INSTRUMENT", name+'ziggy.csv',0)
        try:
            phots[startRow+1]
        except:
            print("There was a problem dealing with this file. Recheck the google sheet to make sure nothing is going wrong there.")
            continue
        lastswope = startRow+1;
        
        ct = False
        inc=True
        r1=find_index("Swope",name+'ziggy.csv',7)
        startRow=r1
        lastswope = startRow+1;
        for row in phots[startRow+1:]:
            try:
                if row[7] == "Swope": 
                    ct = True  
                if (ct and row[7] != "Swope"):
                    break
                lastswope=lastswope+1 
            except:
                break
        if inc==False:
            continue
        ct = False
        index = lastswope-6

        skip = False
        if name=='2018bcb' or name=='2018dyb' or name=='2018fyk' or name=='2018hyz' or name=='2018ido' or name=='2018lna' or name=='2018jbv':
            skip = True

        for row in phots[lastswope-6:lastswope]:
            if skip:
                break
            if row[2] == "V":
                ct = True
                band = 'V'
                break
            index=index+1
        skip = False
        if name=='2005ip' or name=='2009ip' or name=='2010da' or name=='2013L':
            skip = True
        if not ct:
            index = lastswope-6
            for row in phots[lastswope-6:lastswope]:
                if row[2] == "r":
                    ct = True
                    band = 'r'
                    break
                index=index+1
        
        if not ct:
            index = lastswope-6
            for row in phots[lastswope-6:lastswope]:
                if skip:
                    break
                if row[2] == "g":
                    ct = True
                    band = 'g'
                    break
                index=index+1
        if not ct:
            print("No valid band found. Check ziggy phot file. ")

        #Find mag and date of magnitude
        dateOfMagMJD = float(phots[index][1])
        mag = float(phots[index][5])
        print(mag)
        pong = Time(dateOfMagMJD, format = 'mjd')
        pong.format = 'decimalyear'
        dateOfMagUT = pyasl.decimalYearGregorianDate(pong.value, form='yyyy-mm-dd')
        dateOfMagUT = datetime.strptime(dateOfMagUT, "%Y-%m-%d").strftime("%m/%d/%Y")
        print(dateOfMagUT)

        row = find_index(name, time.strftime('%Y%m%d') + '_Targets.csv',0)

        readTargets = csv.reader(open(time.strftime('%Y%m%d') + '_Targets.csv'))
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
        if linesTargets[row][3] == 1:
            linesTargets[row][3] = priority
        linesTargets[row].append(band)
        

        writeTargets = csv.writer(open(time.strftime('%Y%m%d') + '_Targets.csv', 'w'))
        writeTargets.writerows(linesTargets)

        del writeTargets

        print("Done working with " +name)

        r=1



cadence_min = -1
cadence_min2 = -70
r=0

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('Python Sheets B-e2ab6d0240c1.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open('Swope SN Observing June 2019').sheet1
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

writer = csv.writer(open(time.strftime('%Y%m%d') + '_Targets.csv', 'w')) # This should generate the new target list

with open(time.strftime('%Y%m%d') + '_Targets.csv', "w") as my_empty_csv:
  pass 

writer.writerows([wks.row_values(1)[2:9]])

for i in indices:
    writer.writerows([wks.row_values(1+i)[2:9]])
del writer

names=[]
with open(time.strftime('%Y%m%d') + "_Targets.csv") as csv_file:
    for row in csv.reader(csv_file, delimiter=','):
        if row[0] == '':
            print("NOTICE THIS")
            continue;
        names.append(row[0])
print(names)

getTargetSet(names, 1,0)

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


writer = csv.writer(open(time.strftime('%Y%m%d') + '_Targets.csv', 'a')) # This should generate the new target list

names2=[]
for i in indices2:
    writer.writerows([wks.row_values(1+i)[2:9]])
    names2.append(wks.row_values(1+i)[2])
del writer
print(names2)

getTargetSet(names2,2,1)


print("Done! Check the targets.csv file. ")