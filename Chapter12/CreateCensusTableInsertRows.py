import csv, os
arcpy.env.overwriteOutput = True
arcpy.AddMessage("Starting . . . ")

gdb = arcpy.GetParameterAsText(0)
tract = arcpy.GetParameterAsText(1)
csvFile = arcpy.GetParameterAsText(2)
areaName = arcpy.GetParameterAsText(3)
if areaName.find(" ") != -1:
    areaName = areaName.replace(" ","")
    arcpy.AddWarning("areaName input had spaces and has been updated to the following {0}".format(areaName)) 
table = "{0}_RaceHispanic".format(areaName)
tablePath = os.path.join(gdb,table)
censusType = arcpy.GetParameterAsText(4)
censusPoly = os.path.join(gdb,table+"_{0}".format(censusType))
sql = arcpy.GetParameterAsText(5)

fields = {"geoid_census":["GeoID_Join","STRING"],
          "total_pop":["Total Population","LONG"],
          "white":["White","LONG"],
          "prct_white":["Percent White","FLOAT"],
          "black":["Black","LONG"],
          "prct_black":["Percent Black","FLOAT"],
          "am_indian_nat_alaska":["American Indian/Native Alaskan","LONG"],
          "prct_am_indian_nat_alaska":["Percent American Indian/Native Alaskan","FLOAT"],
          "asian":["Asian","LONG"],
          "prct_asian":["Percent Asian","FLOAT"],
          "nat_hawaiian_pac_island":["Native Hawaiian/Pacific Islander","LONG"],
          "prct_nat_hawiian_pac_island":["Percent Native Hawaiian/Pacific Islander","FLOAT"],
          "some_other":["Some Other Race","LONG"],
          "prct_some_other":["Percent Some Other Race","FLOAT"],
          "two_or_more":["Two Or More Races","LONG"],
          "prct_two_or_more":["Percent Two Or More Races","FLOAT"],
          "hispanic_latino":["Hispanic/Latino","LONG"],
          "prct_hispanic_latino":["Percent Hispanic/Latino","FLOAT"],
          "total_minority":["Total Minority","LONG"],
          "percent_minority":["Percent Minority","FLOAT"],
          }

arcpy.AddMessage("Creating a new table for the csv data")
arcpy.management.CreateTable(gdb,table)


tableFields = []
for field in fields:
    name = field
    alias = fields[field][0]
    dataType = fields[field][1]
    arcpy.AddMessage(name)
    arcpy.AddMessage(alias)
    tableFields.append(field)
    arcpy.management.AddField(tablePath,name,dataType,field_alias = alias)
    arcpy.AddMessage("Adding field {0} to the table".format(field))
    
    

fileRef = open(csvFile)
csvRef = csv.reader(fileRef)

arcpy.AddMessage("Inserting csv values into table, {0}".format(tablePath))
for row in csvRef:
    if csvRef.line_num <= 2:
        continue
    geoJoin = row[0][9:]
    totMinority = int(row[8])+int(row[10])+int(row[12])+int(row[14])+int(row[16])+int(row[18])+int(row[24])
    if int(row[2]) != 0:
        prctWht = round((int(row[6])/float(row[2]))*100,2)
        prctBlk = round((int(row[8])/float(row[2]))*100,2)
        prctAmIn = round((int(row[10])/float(row[2]))*100,2)
        prctAsi = round((int(row[12])/float(row[2]))*100,2)
        prctNatHaw = round((int(row[14])/float(row[2]))*100,2)
        prctSmOth = round((int(row[16])/float(row[2]))*100,2)
        prctTwoMr = round((int(row[18])/float(row[2]))*100,2)
        prctHispLat = round((int(row[24])/float(row[2]))*100,2)
        prctMinority = round((totMinority/float(row[2]))*100,2)
    else:
        prctWht = -999
        prctBlk = -999
        prctAmIn = -999
        prctAsi = -999
        prctNatHaw = -999
        prctSmOth = -999
        prctTwoMr = -999
        prctHispLat = -999
        prctMinority = -999
        prctMinority = -999
        prctMaj = -999
    value =  [geoJoin,int(row[2]),int(row[6]),prctWht,int(row[8]),prctBlk,int(row[10]),prctAmIn,int(row[12]),prctAsi,int(row[14]),prctNatHaw,
                          int(row[16]),prctSmOth,int(row[18]),prctTwoMr,int(row[24]),prctHispLat,totMinority,prctMinority]
    cursor = arcpy.da.InsertCursor(tablePath,tableFields)
    arcpy.AddMessage(value)
    cursor.insertRow(value)
    del cursor

arcpy.AddMessage("Selecting out geographies to join table to")
arcpy.analysis.Select(tract,censusPoly,sql)
arcpy.AddMessage("Select has finished, joining the table to the new feature class")
arcpy.management.JoinField(censusPoly,"GEOID",tablePath,"geoid_census",tableFields)
arcpy.AddMessage("Finished")


