import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import csv

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('Python Sheets B-e2ab6d0240c1.json', scope)

gc = gspread.authorize(credentials)

wks = gc.open('Swope SN Observing June 2019').sheet1
print('connected')
names=[]

with open('oldTargets.csv', 'rt') as f:
    reader = csv.reader(f)
    #lines = list(reader)
    for row in csv.reader(f, delimiter=','):
        if row[0] == '':
            continue;
        if row[0] =='\ufeff':
        	continue
        names.append(row[0])
print(names)
for name in names:
	cols = wks.col_values(3)
	r = -1
	for i,c in enumerate(cols):
		if c == name:
			print("Found it.")
			r = i+1
	print(r)
	rows = wks.row_values(r)
	print(r)
	print((rows))
	wks.update_cell(r, len(rows)+1, time.strftime('%Y%m%d'))


