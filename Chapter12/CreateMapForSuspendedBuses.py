import os, glob
from PyPDF2 import PdfFileMerger, PdfFileReader
arcpy.env.overwriteOutput = True

projectGDB = arcpy.GetParameterAsText(0)
censusPoly = arcpy.GetParameterAsText(1)
busRoute = arcpy.GetParameterAsText(2)
summStats = arcpy.GetParameterAsText(3)
demoType = arcpy.GetParameterAsText(4)
numerField = arcpy.GetParameterAsText(5)
denomField = arcpy.GetParameterAsText(6)
refField = arcpy.GetParameterAsText(7)
prcField = arcpy.GetParameterAsText(8)
tableHeaderText = arcpy.GetParameterAsText(9)
figNumb = arcpy.GetParameterAsText(10)


arcpy.AddMessage(summStats)
arcpy.AddMessage(prcField)

# derived name of the feature class for use as map name field.
censusPolyName = censusPoly.split("\\")[-1]

# Project gdb and folder locations
projectFolder = "\\".join(projectGDB.split("\\")[:-1])

# bus and census data that already exists in the project gdb
busLines = os.path.join(projectGDB,"Summer21RouteShape")
newBusLines = os.path.join(projectGDB,"AC_Transit_AdditionalTransbay")

# summary stat table to be created for the reference community calculations
demoName = demoType
if demoName.find(" "):
    demoName = demoName.replace(" ","")
    arcpy.AddWarning("Input value for summary statistic table name {0} has a space in it and has been changed to {1}".format(demoType,demoName))
sumStatTable = os.path.join(projectGDB,"SummStat_{0}_StudyArea".format(demoName))

# Feature layers created for selections
studyAreaFL = "SelectedCensus_FL"
busLinesFL = "SelectedBusLines_FL"
newBusCBGs = "NewBusCBGsRefComm"

# Suspended bus route and data created for suspsended bus route

newBusLinesSel = os.path.join(projectGDB,"NewTransbayLine_{0}".format(busRoute))
cbgStudyArea = os.path.join(projectGDB,"CBG_StudyArea_Bus_{0}".format(busRoute))

# Project and map and layout object for the map, inset map, and map frames for map and inset map
project = arcpy.mp.ArcGISProject("CURRENT")
m = project.listMaps("Map")[0]
inset = project.listMaps("Inset")[0]
layout = project.listLayouts("Layout")[0]
mf = layout.listElements("mapframe_element","Map Frame")[0]
mfInset = layout.listElements("mapframe_element","Inset")[0]

# table header, table box, title text elements, and legend element
tableHeader = layout.listElements("TEXT_ELEMENT","DetailsHeader")[0]
tableBox = layout.listElements("TEXT_ELEMENT","DetailsBox")[0]
title = layout.listElements("TEXT_ELEMENT","Title")[0]
legend = layout.listElements("LEGEND_ELEMENT","Legend")[0]

with arcpy.EnvManager(addOutputsToMap=False):
    arcpy.management.MakeFeatureLayer(censusPoly,studyAreaFL)
    arcpy.management.MakeFeatureLayer(busLines,busLinesFL,"PUB_RTE IN ('W', 'V', 'U', 'P', 'O', 'NX', 'NL', 'LA', 'L', 'J', 'G', 'F', 'DB1', 'DB')")
    arcpy.management.SelectLayerByLocation(studyAreaFL,"INTERSECT",busLinesFL,"0.5 Miles")
    
summStatList = summStats.split(";")
summStatInput = []
for summ in summStatList:
    summStatInput.append([summ, "SUM"])

arcpy.analysis.Statistics(studyAreaFL,sumStatTable,summStatInput)

arcpy.management.AddField(sumStatTable,"refCommPrct","FLOAT")

arcpy.management.CalculateField(sumStatTable,"refCommPrct","(!SUM_{0}!/!SUM_{1}!)*100".format(numerField,denomField))

with arcpy.da.SearchCursor(sumStatTable,["refCommPrct"]) as cursor:
    row = next(cursor)
    refCommPrct = row[0]

arcpy.AddMessage("Reference Community Number is {0}".format(str(refCommPrct)))

with arcpy.EnvManager(addOutputsToMap=False):
    arcpy.analysis.Select(newBusLines,newBusLinesSel,"route_s_nm = '{0}'".format(busRoute))
    arcpy.management.MakeFeatureLayer(censusPoly,newBusCBGs)
    arcpy.management.SelectLayerByLocation(newBusCBGs,"INTERSECT",newBusLinesSel,"0.5 Miles")
    arcpy.management.SelectLayerByAttribute(newBusCBGs,"REMOVE_FROM_SELECTION","{0} = 0".format(denomField))
    minorityGEOIDs = []
    allGEOIDs = []
    with arcpy.da.SearchCursor(newBusCBGs,["GEOID",refField]) as cursor:
        for row in cursor:                             
            allGEOIDs.append(row[0])
            if row[1] >= refCommPrct:
                minorityGEOIDs.append(row[0])
                arcpy.AddMessage("Added {0} to minority GEOID list".format(row[0]))

    cbgStudyAreaTuple = tuple(allGEOIDs)
    cgbStudyAreaSQL = "GEOID in {0}".format(cbgStudyAreaTuple)
    arcpy.AddMessage(cgbStudyAreaSQL)
    arcpy.analysis.Select(censusPoly,cbgStudyArea,cgbStudyAreaSQL)

m.addDataFromPath(cbgStudyArea)
cbgStudyAreaLyr = m.listLayers("CBG_StudyArea_Bus_{0}".format(busRoute))[0]
cbgStudyAreaLyrSym = cbgStudyAreaLyr.symbology
cbgStudyAreaLyrSym.updateRenderer('GraduatedColorsRenderer')
cbgStudyAreaLyrSym.renderer.classificationField = refField
cbgStudyAreaLyrSym.renderer.breakCount = 2
breakValue = refCommPrct
firstVal = 0
for brk in cbgStudyAreaLyrSym.renderer.classBreaks:
    brk.upperBound = breakValue
    if firstVal == 0:
        brk.label = "Population > Reference Community"
        brk.symbol.color = {'RGB' : [255, 0, 0, 30]}
        brk.symbol.outlineColor = {'RGB' : [255, 0, 0, 50]}
    else:
        brk.label = "Population < Reference Community"
        brk.symbol.color = {'RGB' : [0, 255, 0, 30]}
        brk.symbol.outlineColor = {'RGB' : [0, 255, 0, 50]}
    breakValue = 100
    firstVal += 1
cbgStudyAreaLyr.symbology = cbgStudyAreaLyrSym

m.addDataFromPath(newBusLinesSel)
newBusLyr = m.listLayers("NewTransbayLine_{0}".format(busRoute))[0]
newBusLyrSym = newBusLyr.symbology
newBusLyrSym.renderer.symbol.color = {"RGB" : [169, 0, 230, 100]}
newBusLyrSym.renderer.symbol.size = 1.5
newBusLyr.symbology = newBusLyrSym
newBusLyr.name = "Transbay Bus Route"

curInsentLayers = [l.name for l in inset.listLayers()]
if cbgStudyAreaLyr.name in curInsentLayers:
    insetCBGLyr = inset.listLayers(cbgStudyAreaLyr.name)[0]
    inset.removeLayer(insetCBGLyr)
    arcpy.AddMessage("Removing old CBG Study Area Layer to Inset")
    inset.addLayer(cbgStudyAreaLyr)
    arcpy.AddMessage("Adding new CBG Study Area Layer to Inset")
else:
    inset.addLayer(cbgStudyAreaLyr)
    arcpy.AddMessage("Adding new CBG Study Area Layer to Inset")
if newBusLyr.name in curInsentLayers:
    insetBusLyr = inset.listLayers(newBusLyr.name)[0]
    inset.removeLayer(insetBusLyr)
    arcpy.AddMessage("Removing old Transbay Bus Route to Inset")
    inset.addLayer(newBusLyr)
    arcpy.AddMessage("Adding new Transbay Bus Route to Inset")
else:
    inset.addLayer(newBusLyr)
    arcpy.AddMessage("Adding new Transbay Bus Route to Inset")

insetStudyAreaLayer = inset.listLayers("CBG_StudyArea_Bus_{0}".format(busRoute))[0]
insetExtent = mfInset.getLayerExtent(insetStudyAreaLayer,False,True)
arcpy.AddMessage(insetExtent)
mfInset.camera.setExtent(insetExtent)
mfInset.camera.scale = round((mfInset.camera.scale + 2000),0)
arcpy.AddMessage(mfInset.camera.scale)

cbgLayerLabels = cbgStudyAreaLyr.listLabelClasses()[0]
cbgLayerLabels.expression = "$feature.GEOID"
cbgLayerLabels.visible = True
cbgStudyAreaLyr.showLabels = True

legendItemNames = [item.name for item in legend.items]
if cbgStudyAreaLyr.name not in legendItemNames:
    legend.addItem(cbgStudyAreaLyr,"TOP")
if newBusLyr.name not in legendItemNames:
    legend.addItem(newBusLyr,"TOP")

for item in legend.items:
    if item.name in (cbgStudyAreaLyr.name,newBusLyr.name,censusPolyName ):
        item.visible = True   
    else:
        item.visible = False

prcFieldList = prcField.split(";")
prcDataDict = {}
for field in arcpy.ListFields(censusPoly):
    if field.name in prcFieldList:
        arcpy.AddMessage("Added {0} field name and alias {1} to field data dictionary".format(field.name,field.aliasName))
        prcDataDict[field.name] = field.aliasName
tableHeader.text = tableHeaderText

#cbgStudyAreaLayer = m.listLayers("CBG_StudyArea_Bus*")[0]
cbgLayer = m.listLayers(censusPolyName )[0]
i = 1
for geoid in minorityGEOIDs:
    arcpy.AddMessage(i)
    arcpy.AddMessage(geoid)
    ### Check and see why aren't you just doing a not equal query on the GEOID for the cbgStudyAreaLayer
    #geoidForMap = [g for g in allGEOIDs if g != geoid]
    #geoidForMapTuple = tuple(geoidForMap)
    #arcpy.AddMessage(geoidForMapTuple)
    cbgStudyAreaLyr.definitionQuery = "GEOID <> '{0}'".format(geoid)
    cbgLayer.definitionQuery = "GEOID = '{0}'".format(geoid)
    textBox = []
    with arcpy.da.SearchCursor(censusPoly,prcFieldList,"GEOID = '{0}'".format(geoid)) as cursor2:
        row = next(cursor2)
        j=0
        while j < len(row):
            arcpy.AddMessage(cursor2.fields[j])
            arcpy.AddMessage(row[j])
            if j != (len(row)-1):
                tempVal = "{0}: {1}\r\n".format(prcDataDict[cursor2.fields[j]],round(row[j],2))
                arcpy.AddMessage(tempVal)
            else:
                arcpy.AddMessage("the last value")
                tempVal = "{0}: {1}".format(prcDataDict[cursor2.fields[j]],round(row[j],2))
                arcpy.AddMessage(tempVal)
            textBox.append(tempVal)
            j+=1
            
    tableBox.text = ""
    for text in textBox:
        tableBox.text += text
        arcpy.AddMessage(text) 
    tableBox.height = 1.23
    tableBox.elementPositionY = 2.2813
    
    title.text = "Figure {0}.{1}\r\nBus Route: {2}\r\nBlock Group: {3}".format(figNumb,str(i),busRoute,str(geoid))
    arcpy.AddMessage(title.text)
    cbgLayer.name = "Population in Block Group {0}".format(geoid)    
    
    # If scale is less than 10000 set to 10000, otherwise add 2000 and round to 0
    extent = mf.getLayerExtent(cbgLayer,False,True)
    arcpy.AddMessage(extent)
    mf.camera.setExtent(extent)
    arcpy.AddMessage(mf.camera.scale)
    if mf.camera.scale < 10000:
        mf.camera.scale = 10000
    else:
        mf.camera.scale = round((mf.camera.scale + 2000),0)
    arcpy.AddMessage(mf.camera.scale)
    
    pdfFigNum = str(i)
    if len(pdfFigNum) == 1:
        pdfFigNum = "0"+pdfFigNum
    layout.exportToPDF(os.path.join(projectFolder,"Figure_{0}_{1}_BusRoute_{2}_GEOID_{3}.pdf".format(figNumb,pdfFigNum,busRoute,geoid)))
    cbgLayer.name = censusPolyName  
    i+=1
 


pdfMergeObj = PdfFileMerger()

pdfFiles = glob.glob(os.path.join(projectFolder,"*BusRoute_{0}*.pdf".format(busRoute)))
for pdf in pdfFiles:
    arcpy.AddMessage(pdf)
    pdfMergeObj.append(PdfFileReader(pdf,"rb"))

pdfMergeObj.write(os.path.join(projectFolder,"Figure_{0}_BusRoute_{1}_{2}_Greater_RefComm.pdf".format(figNumb,busRoute,demoType)))

# Need to remove layers added to map and legend items
m.removeLayer(newBusLyr)
m.removeLayer(cbgStudyAreaLyr)




