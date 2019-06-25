import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import csv

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('Python Sheets B-e2ab6d0240c1.json', scope)

gc = gspread.authorize(credentials)

sh = gc.open('Swope SN Observing June 2019')
print('connected')
names=[]

night = sh.get_worksheet(14) ##12 for 20190623
list_of_lists = night.get_all_values()
cell = (night.find("focus"))
start = cell.row+2

nameRows=[]
for i,r in enumerate(list_of_lists[start:]):
	if r[1] != '':
		nameRow = i + 22
		nameRows.append(nameRow)
listofnames=[]
for i,rownum in enumerate(nameRows):
	if list_of_lists[rownum-2][8]!='':
		added=0
		while list_of_lists[rownum-2][9]=='':
			rownum+=1
			added+=1
		print(rownum)
		if rownum<nameRows[i+1]: #### BE CAREFUL HERE. MIGHT BE BUGGY. 
			listofnames.append(list_of_lists[rownum-2-added][1])

print(listofnames)

sheet = sh.get_worksheet(0)

for name in listofnames:
	try:
		cell = sheet.find(name)
		print("Found " + name)
	except:
		print("Did not find "+ name)
		continue;
	fullrow = sheet.row_values(cell.row)
	fullrow.append(time.strftime('%Y%m%d'))
	sheet.insert_row(fullrow,cell.row+1)
	sheet.delete_row(cell.row)
	

	#night.update_cell(cell.row, cell.col, time.strftime('%Y%m%d')) #Make this do yesterday's date, not today!