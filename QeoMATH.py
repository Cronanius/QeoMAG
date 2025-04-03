'''
#QeoMATH is free software, released under the GNU General Public License v2.0.
This software is provided AS-IS, and the developer is not responsible for ANY
problems that its use may cause.
Originally, this project was supported by Fladgate Exploration and Consulting Corp.
Go check them out at www.fladgateexploration.com!
Requires the following modules:
import numpy as np
import matplotlib.pyplot as plt
import fiona
import shapely
import geopandas as gpd
'''
import numpy as np
import matplotlib.backend_bases as mplb
import matplotlib.pyplot as plt
import matplotlib.widgets as mwidgets
import fiona
import shapely
import traceback
import math
import QeoMAG as qg
import os

def fourthDiff(*vals):
    if len(vals) != 5: return None
    else:
        fdiff = vals[0] - 4*vals[1] + 6*vals[2] - 4*vals[3] + vals[4]
        return fdiff

def eighthDiff(*vals):
    if len(vals) != 9: return None
    else:
        ediff = vals[0] - 8*vals[1] + 28*vals[2] - 56*vals[3] + 70*vals[4] - 56*vals[5] + 28*vals[6] - 8*vals[7] + vals[8]
        return ediff

def diffGen(data_object, headers, diffType='4'):
    vals = []
    diffs = []
    for i in range(len(headers)): channel[headers[i]] = i
    idx = -1
    if diffType == '4':
        for line in data_object:
            idx += 1
            vals.append(line[channel['nT']])
            if len(vals) > 5: vals.pop(0)
            elif len(vals) < 2:
                diffs.append(0)
                continue
            elif len(vals) < 5: continue
            diffs.append(fourthDiff(vals))
        for i in range(2): diffs.append(0) #pads last 2 values with zeroes
        headers.append('4diff')

    elif diffType == '8':
        for line in data_object:
            idx += 1
            vals.append(line[channel['nT']])
            if len(vals) > 9: vals.pop(0)
            elif len(vals) < 4:
                diffs.append(0)
                continue
            elif len(vals) < 9: continue
            diffs.append(eighthDiff(vals))
        for i in range(4): diffs.append(0) #pads last 4 values with zeroes
        headers.append('8diff')
    else: return None

    diffs = np.array(diffs)
    np.append(data_object, diffs, axis=1)

    return data_object, headers;

def dataLoad(filename, data_object): #loads the data from a file
    data_object.clear()
    data_array = None
    with open(filename, 'r') as datafile:
        for line in datafile:
            line = line.strip()
            columns = line.split()
            data_object.append(columns)
        headers = data_object[0]
        convertedData = dataConvert(data_object)
        if type(convertedData) is str:
            print('qm.dataLoad: List Only')
            return False, data_object;
        else:
            print('qm.dataLoad: Array Returned')
            return True, convertedData, headers;


def dataConvert(data_object): #DATA OBJECT MUST ALREADY BE STRIPPED AND SPLIT AND CLEANED!
    testLen = len(data_object[0])
    data = []
    idx = -1
    for line in data_object:
        idx += 1
        if len(line) != 0:
            if idx == 0 and type(line[0]) is str:
                 popidx = 0
                 continue
        for item in line:
            try: float(item)
            except:
                print('qm.dataConvert: return False')
                return 'False'
        if len(line) != testLen:
            print('qm.dataConvert: return False')
            return 'False'
        else:
            data.append(line)
    try: data.pop(popidx)
    except Exception: pass
    finally:
        data = np.array(data, dtype=float)
        print('qm.dataConvert: return npArray')
        return data


def dataClean(data_object): #removes all data except the last chunk in the file.
    glyphdict = {'A': 0.01,'B': 0.02,'C': 0.03,'D': 0.04,'E': 0.05,'F': 0.06,
                 'G': 0.07,'H': 0.08,'I': 0.09,'J': 0.10,'K': 0.11,'L': 0.12,
                 'M': 0.13,'N': 0.14,'O': 0.15,'P': 0.16,'Q': 0.17,'R': 0.18,
                 'S': 0.19,'T': 0.20,'U': 0.21,'V': 0.22,'W': 0.23,'X': 0.24,
                 'Y': 0.25,'Z': 0.26}
    idx = -1
    mdx = len(data_object) - 1
    eofx = -1
    stix = -1
    for line in reversed(data_object):
        idx += 1
        if len(line) > 0:
            if line[0] == 'end':
                eofx = mdx - idx - 2
                print(eofx)
                continue
            if line[0] == 'time':
                stix = mdx - idx
                print(stix)
                break
        else:
            continue
    data = list(data_object[stix:eofx])

    badlineCounter = 0
    template = -1
    #headers = data[0].strip()
    headers = data[0]
    channel = {}
    for i in range(len(headers)): channel[headers[i]] = i
    #CAN NOW CALL COLUMNS by eg. line[channel['utmN']]
    ypr = False #yaw/pitch/roll check
    laserCh = True #defaults to a laser channel existing

    if len(data[0]) >= 22 and 'yaw' in data[0]:
        ypr = True
        idx = -1
        if 'laser' not in data[0]: laserCh = False
        for line in data: #removes pitch roll and yaw data
            idx += 1
            if idx < 1: continue #skips header line
            line.pop(channel['roll'])
            line.pop(channel['pitch'])
            line.pop(channel['yaw'])
            if laserCh == False: line.append('000.00')
        if laserCh == False:
            data[0] = data[0] + ['laser']
            laserCh = True

    #this system uses the length of the line to determine data viability

    if len(data[0]) == 19 and 'laser' not in data[0]: #old sensor no laser
        data[0] = data[0] + ['laser']
        jdx = -1
        for line in data:
            jdx += 1
            if jdx > 0:
                line.append('000.00') #adds dead laser data
    idx = -1
    for line in data:
        idx += 1
        if len(line) < 1: data.pop(idx)
        else: continue

    idx = -1
    for line in data: #concatenates the UTM zone number and letter into a decimal number
        idx =+ 1
        if line[0] == 'time': continue #skips header line
        if len(line) == 21: #"Template 1" Concatenates zone columns only
            template = 1
            if len(line[19]) == 1:
                a = glyphdict[line[19]] + float(line[18])
                line.pop(19)
                line.pop(18)
                line.insert(18, str(a))
                continue
        if len(line) == 19:#'Template 2' splits alt/sat columns only
            template = 2
            if len(line[16]) == 9:
                strA = line[16][:6:]
                strB = line[16][7::]
                line.pop(16)
                line.insert(16, strA)
                line.insert(17, strB)
            if len(line[18]) == 3 and len(line[16]) == 6: #performs UTM conversion if necessary
                a = glyphdict[line[18][2::]] + float(line[18][:2:])
                line[18] = str(a)
            continue
        if len(line) == 20: #"Templates 3 and 4(already perfect)"
            if len(line[18]) == 1 and len(line[16]) == 9: #'Template 3' Splits Alt/Sat cand concatenates UTM zone
                template = 3
                #concatenates UTM
                a = glyphdict[line[18]] + float(line[17])
                line.pop(18)
                line.pop(17)
                line.insert(17, str(a))
                #splits Alt/Sat
                strA = line[16][:6:]
                strB = line[16][7::]
                line.pop(16)
                line.insert(16, strA)
                line.insert(17, strB)
                continue
            elif len(line[18]) == 3 and len(line[16]) == 6: #'Template 4' converts UTM to float
                template = 4
                #converts UTM zone to float
                a = glyphdict[line[18][2::]] + float(line[18][:2:])
                line[18] = str(a)
                continue
            elif len(line[18]) == 3 and len(line[16]) == 7: #'Template 5' converts UTM to float
                template = 5
                #converts UTM zone to float
                a = glyphdict[line[18][2::]] + float(line[18][:2:])
                line[18] = str(a)
                continue
            elif len(line[18]) == 4 or len(line[18]) == 5 and len(line[16]) == 6:
                template = 5 #data is already in "good" format
                continue
            else: #'Template 0' data format unknown, but length is correct
                template = 0
                data_object.pop(idx)
                idx += -1
                badlineCounter += 1
                continue
        data_object.pop(idx)
        idx += -1
        badlineCounter += 1
        #continue unnecessary
    if ypr == True:
        data[0].pop(channel['roll'])
        data[0].pop(channel['pitch'])
        data[0].pop(channel['yaw'])
    print('Bad lines removed: ', badlineCounter)
    print("Template: ", template)
    return data

def dataRepair(filePath): #attempts to repair data from a bad output stream
    with open(filePath, 'r') as datafile:
        data = []
        for line in datafile:
            if line[0] == 't':
                data.append(line)
                continue
            columns = line[:9] + ' ' + line[10:21] + ' ' + line[22] + ' ' + line[24] + ' ' + line[26] + ' ' + line[28:31] + ' ' + line[32:35] + ' ' + line[36:40] + ' ' + line[41:45] + ' ' + line[46:50] + ' ' + line[51:53] + ' ' + line[54:56] + ' ' + line[57:69] + ' ' + line[70:82] + ' ' + line[83:92] + ' ' + line[93:103] + ' ' + line[104:112] + ' ' + line[113:115]+ ' ' + line[116:119] + ' ' + line[120:128] + ' ' + line[129:137] + ' ' + line[138:146] + ' ' + line[147:]
            data.append(columns)
        return data

def basicPurge(data_object): #removes unlocked, bad heater, and ground data
    idx = -1
    idxlist = []
    unlocked_counter = 0
    badheater_counter = 0
    stopped_counter = 0

    for line in data_object:
        idx += 1
        if line[2] == 0: #purges unlocked data
            idxlist.append(idx)
            unlocked_counter += 1
            continue
        elif line[3] == 0: #purges data where the heater temperature is out of range
            idxlist.append(idx)
            badheater_counter += 1
            continue
        elif idx >=2: #positional removal
                if abs(data_object[idx][14] - data_object[idx - 1][14]) < 0.2:
                    if abs(data_object[idx][15] - data_object[idx - 1][15]) < 0.2:
                        idxlist.append(idx)
                        stopped_counter += 1
                        continue
        else:
            continue

    if len(idxlist) > 0:
        idxlist = np.array(idxlist)
        data_object = np.delete(data_object, idxlist, axis=0)

    print('Unlocked data points removed: ', unlocked_counter)
    print('Overheated data points removed: ', badheater_counter)
    print('Stopped data points removed: ', stopped_counter)

    return data_object

def groundPurge(data_object): #removes data where the laser indicates the drone as grounded

    idx = -1
    idxlist = []
    ground_counter = 0

    for line in data_object:
        idx += 1
        if idx >= 0: #purges data where the drone is on the ground or hovering in place
            if abs(data_object[idx][19]) < 0.6:
                idxlist.append(idx)
                ground_counter +=1
                continue

    if len(idxlist) > 0:
        idxlist = np.array(idxlist)
        data_object = np.delete(data_object, idxlist, axis=0)
    print('Ground data points removed: ', ground_counter)

    return data_object

def boundaryPurge(data_object, shapefilename): #removes data from outside of a given boundary SHP file

    with fiona.open(shapefilename) as fiona_collection: #opens the boundary shapefile
        shapefile_record = fiona_collection.next() #assumes only one polygon in the shapefile
        boundary = shapely.geometry.shape(shapefile_record['geometry'])

        idx = -1
        idxlist = []
        boundary_counter = 0

        for line in data_object:
            idx += 1
            if boundary.contains(shapely.geometry.Point(line[14], line[15])) == False:
                idxlist.append(idx)
                boundary_counter += 1
                continue
            else: None

        if len(idxlist) > 0:
            idxlist = np.array(idxlist)
            data_object = np.delete(data_object, idxlist, axis=0)
        print('Data points removed from outside ', shapefilename, ': ', boundary_counter)

        return data_object

def headingPurge(data_object, heading_azimuth=89.75, heading_tolerance=3): #removes data from turns etc

    idx = -1
    idxlist = []
    badheading_counter = 0
    reverse_azimuth = 0

    if heading_azimuth < 0.0: print("Azimuth < 0 degrees. Please input azimuth between 0.0 and 180.0")
    elif heading_azimuth > 180.0: print("Azimuth > 360 degrees. Please input azimuth between 0.0 and 180.0")
    else:
        reverse_azimuth = math.radians(heading_azimuth) - math.pi #atan2 outputs a value between 0 and pi and 0 and -pi. This is how I'm dealing with it.
        heading_azimuth = math.radians(heading_azimuth)
        heading_tolerance = math.radians(heading_tolerance)
        heading_range = ((heading_azimuth + heading_tolerance, heading_azimuth - heading_tolerance), (reverse_azimuth - heading_tolerance, reverse_azimuth + heading_tolerance))
        print(heading_range)
    #elif heading_azimuth >= 180.0: reverse_azimuth = heading_azimuth - 180.0

    for line in data_object:
        idx += 1
        if idx <= 1: continue #skips first line
        x = data_object[idx - 1][14] - data_object[idx][14]
        y = data_object[idx - 1][15] - data_object[idx][15]

        heading = math.atan2(y, x) #atan2 is (y, x), rather than x, y. It's dumb.

        if heading_range[0][0] >= heading >= heading_range[0][1]: continue
        if heading_range[1][0] <= heading <= heading_range[1][1]: continue

        idxlist.append(idx)
        badheading_counter += 1
        continue

    if len(idxlist) > 0:
        idxlist = np.array(idxlist)
        data_object = np.delete(data_object, idxlist, axis=0)
    print('Bad heading data points removed: ', badheading_counter)

    return data_object

def magCutoff(data_object, lower_cutoff, upper_cutoff):

    idx = -1 #indexed for a "header" line
    idxlist = []
    cutoff_counter = 0

    for line in data_object:
        idx += 1
        if idx == 0: continue #skips header line
        if upper_cutoff > line[1] > lower_cutoff:
            continue
        else:
            idxlist.append(idx)
            cutoff_counter += 1

    if len(idxlist) > 0:
        idxlist = np.array(idxlist)
        data_object = np.delete(data_object, idxlist, axis=0)

    print('Data points removed from cutoffs: ', cutoff_counter)
    return data_object

def basicLagCorrection(data_object, headers, correction, heading_azimuth):

    x_cor = math.cos(heading_azimuth)*correction
    y_cor = math.sin(heading_azimuth)*correction

    if "lineNo" in headers:
        shift = -1
        lineIdx = 0
        for i in range(len(headers)): channel[headers[i]] = i
        for line in data_object:
            if lineIdx != line[channel['lineNo']]:
                lineIdx = line[channel['lineNo']]
                shift = shift * -1
            line[channel['utmE']] = line[channel['utmE']] + shift * x_cor
            line[channel['utmN']] = line[channel['utmN']] + shift * y_cor
        return data_object, headers;

    else: return None #might need to change this later; eg raise exception

def lineLabel(data_object, headers, start_number, line_increment, is_tieLine):
    lineNo = float(start_number)
    intLineNo = int(start_number)
    lineList = []
    channel = {}
    for i in range(len(headers)): channel[headers[i]] = i

    #by binning: assign an integer value based on the UTMx value: can be done by truncating the UTMx value.
    #create a table (array): each row has 3 values: [the bin, the frequency, lineNo]
    #axis=0 should be as long as 0 to the maxiumum X value contained in the data. As long as the data is truncated, that's fine.
    #Iterate over the bins to find lines.
    #This algorithm will fail if the line spacing is closer than the fiducials in metres.
    utm = ''
    fiducials = 2 #THIS SHOULD BE USER INPUT. ONE FIDUCIAL = 1 METRE (one "bin")
    if is_tieLine == False: utm = 'UTMx'
    else: utm = 'UTMy'
    utmHigh = -1000000000.0
    utmLow = 1000000000.0
    for line in data_object:
        if line[channel[utm]] > utmHigh: utmHigh = line[channel[utm]]
        if line[channel[utm]] < utmLow: utmLow = line[channel[utm]]
    utmDiff = math.trunc(utmHigh - utmLow) + 2
    utmHighBin = math.trunc(utmHigh)
    utmLowBin = math.trunc(utmLow) #+ 1
    binTable = np.zeros((utmDiff, 3), dtype=int) #[0] is the truncated UTM bin, [1] is the frequency, and [2] is the lineNo

    for line in data_object: #frequency first, as it doesn't technically depend on the indexing column
        #bin = math.trunc(line[channel[utm]]) - utmLowBin - 1
        #binTable[bin][1] += 1
        binTable[math.trunc(line[channel[utm]]) - utmLowBin][1] += 1
    #idx = 0
    #dataLen = len(data_object)
    #while idx < dataLen:
    #    binTable[math.trunc(line[channel[utm]]) - utmLowBin][1] += 1
    #    idx += 1

    #this section operates on the indexing column and creates the line numbers
    newLineTracker = False
    idx = -1
    for row in binTable:
        idx += 1
        row[0] = utmLowBin + idx #adds the 'bindex' to the indexing column

        if idx < fiducials: lowDiff = idx #top of the table
        else: lowDiff = fiducials
        if idx + utmLowBin > utmHighBin - fiducials: highDiff = utmHighBin - utmLowBin - idx #bottom of the table
        else: highDiff = fiducials

        if row[1] > 0: row[2] = intLineNo

        #now test to see if the line number should change or stay the same
        jdx = idx - lowDiff
        counter = 0
        while jdx <= idx + highDiff:
            if binTable[jdx][1] > 0:
                counter += 1
                newLineTracker = False
            jdx += 1
        if counter == 0 and newLineTracker == False:
            intLineNo += int(line_increment)
            newLineTracker = True

    if 'lineNo' not in headers:
        headers.append('lineNo')
        for i in range(len(headers)): channel[headers[i]] = i
        temp = np.transpose(np.array([np.zeros(len(data_object))]))
        #temp = np.transpose(np.array([[0, 0, 0]]))
        #print(temp)
        data = np.append(data_object, temp, axis=1)
        #print(data_object)
    else:
        data = data_object

    for line in data:
        bdx = math.trunc(line[channel[utm]]) - utmLowBin
        if bdx != binTable[bdx][0] - utmLowBin: print('WARNING: Bindex doesnt match index!: ' + str(bdx - 1) + ' : ' + str(binTable[bdx][0] - utmLowBin))
        line[channel['lineNo']] = float(binTable[bdx][2])

    '''
    sortOrder = lineSort(data_object, headers, is_tieLine)
    #print(sortOrder)
    #sequencedData = sequenceLabel(data_object, headers)
    sortedData = data_object[sortOrder]

    for i in range(len(headers)): channel[headers[i]] = i

    #adds a sequential label

    if 'lineNo' not in headers:
        headers.append("lineNo") #adds 'lineNo' column to headers list

        for line in sortedData:
            idx += 1
            if idx == 0:
                lineList.append(lineNo)
                continue
            elif is_tieLine == False:
                if abs(line[channel['UTMx']] - data_object[idx - 1][channel['UTMx']]) > 10: lineNo += line_increment
            elif is_tieLine == True:
                if abs(line[channel['UTMy']] - data_object[idx - 1][channel['UTMy']]) > 10: lineNo += line_increment
            lineList.append(lineNo)

        if len(lineList) > 0:
            lineList = np.transpose(np.array([lineList]))
            data_object = np.append(data_object[sortOrder], lineList, axis=1)

    else:
        for line in sortedData:
            idx += 1
            if idx == 0:
                line[channel['lineNo']] = lineNo
                continue
            elif is_tieLine == False:
                if abs(line[channel['UTMx']] - data_object[idx - 1][channel['UTMx']]) > 10: lineNo += line_increment
            elif is_tieLine == True:
                if abs(line[channel['UTMy']] - data_object[idx - 1][channel['UTMy']]) > 10: lineNo += line_increment
            line[channel['lineNo']] = lineNo
    '''
    '''
        idx = -1 #cleanup stage
        lineNo = float(start_number)
        for line in data_object:
            idx += 1
            if idx == 0: continue
            elif is_tieLine == False:
                if abs(line[channel['UTMx']] - data_object[idx - 1][channel['UTMx']]) > 22: lineNo += line_increment
            elif is_tieLine == True:
                if abs(line[channel['UTMy']] - data_object[idx - 1][channel['UTMy']]) > 22: lineNo += line_increment
            line[channel['lineNo']] = lineNo
    '''

    #lineNo += line_increment

    #return data_object, headers, lineNo;
    #seqList = sequencedData[channel['seq']].tolist()
    #for line in seqList: line = int(line)
    #seqList = np.transpose(np.array([seqList], dtype=int))
    #sortedData = np.array(sortedData[seqList])
    return data, headers, float(intLineNo);

def duplicateCleaner(data_object, data_headers):
    channel = {}
    for i in range(len(headers)): channel[headers[i]] = i
    sorting_order = np.lexsort((data_object[:, channel['utmE']], data_object[:, channel['utmN']]))
    #lexsort will return an array with sorting order from lowest to highest.
    #the sorted array can be returned by the argument: data_object[sorting_order]
    sorted = data_object[sorting_order]
    idx = -1
    for line in sorted:
        idx += 1


def lineLabelTwo(data_object, header_object, heading, start_number, line_increment, is_tieLine, line_spacing=25):
    data = headingRotationTransform(data_object, heading, header_object)
    #data[0] is headers and data[1] is the dataLoad
    header_object = data[0]
    sortOrder = lineSort(data[1])
    lineNo = float(start_number)
    lineList = []
    header_object.append("lineNo") #adds 'lineNo' to column headers list

    idx = -1
    for line in data[1][sortOrder]:
        idx += 1
        if is_tieLine == False:
            if abs(line[-2] - line[idx - 1][-2]) > line_spacing: lineNo += line_increment
        if is_tieLine == True:
            if abs(line[-1] - line[idx - 1][-1]) > line_spacing: lineNo += line_increment
        lineList.append(lineNo)

    if len(lineList) > 0:
        lineList = np.transpose(np.array([lineList]))
        data = np.append(data[1], lineList, axis=1)

    lineNo += line_increment

    return data, header_object, lineNo;

'''
def sequenceLabel(data_object, headers): #used to label each data point with its original position in sequence
    channel = {}
    for i in range(len(headers)): channel[headers[i]] = i
    if 'seq' not in headers:
        headers.append('seq')
        seq = list(range(len(data_object)))
        idx = -1
        for num in seq:
            idx += 1
            seq[idx] = float(seq[idx])
        #print(seq)
        seqlist = np.transpose(np.array([seq], dtype=float))
        np.append(data_object, seqlist, axis=1)
    else: pass #sequencing should only happen once and generally should be immutable

    return data_object;
'''
def labelsBatch(isTie, dirpath, dirpathlabeled, saveFileName):

    listData = []
    #dirpath = "C:\\Users\\Geotech\\Documents\\MT Ventures\\Trap Lake (2023)\\Trap Lake\\Geomag\\Ties_Cleaned"
    #dirpathlabeled = "C:\\Users\\Geotech\\Documents\\MT Ventures\\Trap Lake (2023)\\Trap Lake\\Geomag\\Labeled"
    #shapefilepath = "C:\\Users\\Geotech\\Documents\\KES_Bluffpoint_NewBoundary.shp"
    directory = os.fsencode(dirpath)

    #isTie = True #Check this!

    inc = 10
    dayinc = 1
    daycap = 0
    channel = {}
    headers = []

    if isTie == False:
        lineNo = 10000
        saveFileName = saveFileName + '.txt'
    else:
        lineNo = 90000
        saveFileName = saveFileName + '.txt'

    index = -1
    for file in os.listdir(directory):
        index += 1
        filename = os.fsdecode(file)
        print(filename)
        try:
            a = dataLoad(os.path.join(dirpath, filename), listData)
            if index == 0:
                data = a[1]
                headers = a[2]
            else:
                data = np.append(data, a[1], axis=0)
        except Exception as error:
            print('Execution Failed on ', filename, ' ', error)
            traceback.print_exc()
            continue

    headers.append('lineNo')
    for i in range(len(headers)): channel[headers[i]] = i
    sortOrder = lineSort(data, headers, isTie)
    sortedData = data[sortOrder]

    lineList = []
    idx = -1
    for line in sortedData:
        idx += 1
        if idx == 0:
            lineList.append(lineNo)
            daycap = line[channel['date']]
            continue
        elif isTie == False:
            if abs(line[channel['UTMx']] - sortedData[idx - 1][channel['UTMx']]) > 20:
                lineNo += inc
                daycap = line[channel['date']]
                lineList.append(lineNo)
                continue
            elif daycap == line[channel['date']]: lineList.append(lineNo)
            else: lineList.append(lineNo + dayinc)
        elif isTie == True:
            if abs(line[channel['UTMy']] - sortedData[idx - 1][channel['UTMy']]) > 20:
                lineNo += inc
                daycap = line[channel['date']]
                lineList.append(lineNo)
                continue
            elif daycap == line[channel['date']]: lineList.append(lineNo)
            else: lineList.append(lineNo + dayinc)


    if len(lineList) > 0:
        lineList = np.transpose(np.array([lineList]))
        data = np.append(sortedData, lineList, axis=1)

    saveName = os.path.join(dirpathlabeled, saveFileName)
    with open(saveName, 'w') as saveFile:
        np.savetxt(saveName, data, fmt='%.8g', delimiter=' ', header=' '.join(headers), comments='')

def lineSort(data_object, headers, isTie=False): #needs rotated data to work
    channel = {}
    for i in range(len(headers)): channel[headers[i]] = i
    if isTie == False:
        sorting_order = np.lexsort((data_object[:, channel['UTMy']], data_object[:, channel['UTMx']]))
    else:
        sorting_order = np.lexsort((data_object[:, channel['UTMx']], data_object[:, channel['UTMy']]))
    #lexsort will return an array with sorting order from lowest to highest.
    #the sorted array can be returned by the argument: data_object[sorting_order]
    #MAKE SURE THAT THIS SORTING ORDER IS CORRECT (2024-03-27: it seems to be correct)
    return sorting_order

def headingRotationTransform(data_object, heading, col_headers):
    channel = {}
    theta = math.radians(90.0 - heading)
    R11 = math.cos(theta)
    R12 = -math.sin(theta)
    R21 = math.sin(theta)
    R22 = math.cos(theta)
    R = np.array([[R11, R12],
                  [R21, R22]])

    for i in range(len(col_headers)): channel[col_headers[i]] = i
    UTMs_to_Rprimes = np.array(data_object[:, channel['utmE']:channel['utmE'] + 2])

    for coords in UTMs_to_Rprimes: np.matmul(R, coords, out=coords)
    #note: coords = UTMs_to_Rprimes[idx]

    if 'UTMx' not in col_headers:
        col_headers.append('UTMx')
        col_headers.append('UTMy')
        data_object = np.append(data_object, UTMs_to_Rprimes, axis=1)
    else:
        data_object[:, channel['UTMx']] = UTMs_to_Rprimes[:, 0]
        data_object[:, channel['UTMy']] = UTMs_to_Rprimes[:, 1]

    return col_headers, data_object

def addDateChannel(data_object, headers, date):
    channel = {}
    dateArray = []
    for i in range(len(headers)): channel[headers[i]] = i
    if 'date' not in headers:
        headers.append('date')
        for line in data_object:
            dateArray.append(date)
        dateArray = np.array([dateArray])
        dateArray = np.transpose(dateArray)
        data_object = np.append(data_object, dateArray, axis=1)
    else:
        for line in data_object:
            line[channel['date']] = date

    return headers, data_object
'''
def removeDataChannel(data_object, headers, targetChannel):
    if targetChannel in headers:

    else: print('Channel does not exist')
    return data_object, headers
'''
class dataPlot:
    #This section/class is used for plotting the data
    def __init__(self, data_object):
        self.plotdata = data_object
        self.rectExtents = None
        self.plotIt()

    def plotIt(self):

        self.smallest_E = 1000000.0 #used for plotting data later
        self.largest_E = 0.0
        self.smallest_N = 10000000.0
        self.largest_N = 0.0
        self.utmE = []
        self.utmN = []
        self.nT = []

        for line in self.plotdata:
            if line[14] < self.smallest_E: self.smallest_E = line[14]
            if line[14] > self.largest_E: self.largest_E = line[14]
            if line[15] < self.smallest_N: self.smallest_N = ine[15]
            if line[15] > self.largest_N: self.largest_N = line[15]
            self.utmE.append(line[14])
            self.utmN.append(line[15])
            self.nT.append(line[1])

        self.fig, self.ax = plt.subplots()
        self.cb = self.ax.scatter(self.utmE, self.utmN, s=40, c=self.nT, norm='linear', cmap='viridis')
        self.ax.set(xlim=(self.smallest_E - 100, self.largest_E + 100), ylim=(self.smallest_N - 100, self.largest_N + 100))

        self.props = dict(facecolor='black', alpha=0.1)
        self.rect = mwidgets.RectangleSelector(self.ax, self.onselect, interactive=True, props=self.props, useblit=True)

        self.fig.canvas.mpl_connect("key_press_event", self.ondelete)

        plt.colorbar(self.cb)
        plt.show()

    def onselect(self, eclick, erelease):
        self.rectExtents = self.rect.extents

    '''
    def ondelete(self, event):
        if event.key == "delete":
            idx = -1
            idxlist = []
            delcounter = 0
            for line in self.plotdata:
                idx += 1
                if idx == 0: continue
                if self.rectExtents[0] < float(line[14]) < self.rectExtents[1]:
                    if self.rectExtents[2] < float(line[15]) < self.rectExtents[3]:
                        idxlist.append(idx)
                        delcounter += 1
                        continue
            idx = 0
            if len(idxlist) > 0:
                idxlist.reverse()
                for item in idxlist:
                    self.plotdata.pop(idxlist[idx])
                    idx += 1
            print('Points deleted: ', delcounter)
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()


            try: pullPlotData() #I don't know why this works, but it does
            except Exception: pass #kills this stupid namespace error
            finally: writeDataToTextWidget()

            plt.close() #close the current figure
            self.plotIt() #redraw
    '''
