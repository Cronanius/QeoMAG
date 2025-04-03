# -*- coding: utf-8 -*-

'''
#QeoMAG is free software, released under the GNU General Public License v2.0.
#This software is provided AS-IS, and the developer is not responsible for ANY
#problems that its use may cause.
#Originally, this project was supported by Fladgate Exploration and Consulting Corp.
#Go check them out at www.fladgateexploration.com!
'''

import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
#import PysSide2.QtSvg #this stupid shit needs python 3.10
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.widgets as mwidgets
import fiona
import shapely
import os
#import geopandas as gpd
import QeoMATH as qm
import traceback

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'QeoMAG'
        self.left = 100
        self.top = 100
        self.width = 1000
        self.height = 480
        self.datafilename = ''
        self.opendatafilename = ''
        self.boundaryfilename = ''
        #self.savedatafilename = ''
        self.localData = None
        self.masterData = np.array([[]])
        self.listData = []
        self.dataHeaders = []
        self.batchList = ['Label Lines', 'Label Ties', 'Parse Bad Data']
        self.isArrayFulfilled = False
        self.toggleWriteToText = False #True means "yes, write to the text widget"
        self.masterLoadSuccess = ''
        self.isTieLine = False
        #self.npdata = np.array(self.localData)
        self.initUI()

    def initUI(self):
        #Initialize base widget
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.widget = QWidget()

        #Sets background to white
        self.setAutoFillBackground(True)
        colour = self.widget.palette()
        colour.setColor(self.widget.backgroundRole(), Qt.white)
        self.widget.setPalette(colour)

        #menu shit
        self.initMenus()

        #UI Widgetry
        self.setCentralWidget(self.widget)

        self.vLayout = QVBoxLayout(self.widget)
        self.hLayout1 = QHBoxLayout()
        self.hLayout2 = QHBoxLayout()
        self.vLayout.addLayout(self.hLayout1)
        self.vLayout.addLayout(self.hLayout2)

        #Text display area
        self.textwidget = QPlainTextEdit()
        self.textwidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.textwidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        #Array Widgets
        self.arrayLabel = QLabel()
        self.ledToRed()
        self.arrayLoadButton = QPushButton('Upload to Master')
        self.arrayLoadButton.clicked.connect(self.loadToMasterArray)
        self.masterArrayLabel = QLabel()
        self.masterArrayLabel.setText('No data in Master')


        #Data entry boxen
        self.headingBox = QLineEdit()
        self.headingBox.setPlaceholderText('Drone Heading (0-180)')
        self.headingToleranceBox = QLineEdit()
        self.headingToleranceBox.setPlaceholderText('Heading ±Tolerance')
        self.magCutoffBoxUpper = QLineEdit()
        self.magCutoffBoxUpper.setPlaceholderText('Upper Cutoff Mag in nT')
        self.magCutoffBoxLower = QLineEdit()
        self.magCutoffBoxLower.setPlaceholderText('Lower Cutoff Mag in nT')
        self.lineNoStartBox = QLineEdit() #
        self.lineNoStartBox.setPlaceholderText('Line Label Start #')
        self.lineIncrementBox = QLineEdit() #
        self.lineIncrementBox.setPlaceholderText('Line Label Increment')
        self.dateCollectedBox = QLineEdit()
        self.dateCollectedBox.setPlaceholderText('Date: YYYYMMDD')

        self.tieLineCheckBox = QCheckBox('Tie Lines') #
        self.tieLineCheckBox.clicked.connect(self.tieLineCheckBoxSet)

        #Plot Data Retrieval
        #self.dataPullButton = QPushButton("Plot Data Pull", self)
        #self.dataPullButton.clicked.connect(self.pullPlotData)

        #Mag cutoff buttons
        self.magCutoffButton = QPushButton("Run Mag Cutoff", self)
        self.magCutoffButton.clicked.connect(self.magCutoff)

        #Toolbars
        self.hLayout1.addWidget(self.headingBox)
        self.hLayout1.addWidget(self.headingToleranceBox)
        self.hLayout1.addWidget(self.lineNoStartBox)
        self.hLayout1.addWidget(self.lineIncrementBox)
        self.hLayout1.addWidget(self.magCutoffBoxUpper)
        self.hLayout1.addWidget(self.magCutoffBoxLower)

        self.hLayout2.addWidget(self.arrayLabel)
        self.hLayout2.addWidget(self.masterArrayLabel)
        self.hLayout2.addWidget(self.arrayLoadButton)
        self.hLayout2.addWidget(self.tieLineCheckBox)
        self.hLayout2.addWidget(self.dateCollectedBox)
        self.hLayout2.addWidget(self.magCutoffButton)
        self.vLayout.addWidget(self.textwidget)

        #Render the Widgetry
        self.show()


    def initMenus(self):

        #File Menu
        mainmenu = self.menuBar()
        filemenu = mainmenu.addMenu('File')
        datamenu = mainmenu.addMenu('Data')
        toolsmenu = mainmenu.addMenu('Tools')
        plotmenu = mainmenu.addMenu('Plot')
        aboutmenu = mainmenu.addMenu('About')

        openDataButton = QAction('Import Data File', self)
        openDataButton.triggered.connect(self.openDataFileNameDialog)
        openDataButton.setShortcut('Ctrl+O')
        filemenu.addAction(openDataButton)

        openSHPFileButton = QAction('Open Boundary SHP File', self)
        openSHPFileButton.triggered.connect(self.openSHPFileNameDialog)
        openSHPFileButton.setShortcut('Ctrl+P')
        filemenu.addAction(openSHPFileButton)

        saveDataButton = QAction('Export Local Data', self)
        saveDataButton.triggered.connect(self.saveDataFileDialog)
        saveDataButton.setShortcut('Ctrl+S')
        filemenu.addAction(saveDataButton)

        saveMasterDataButton = QAction('Export Master Data', self)
        saveMasterDataButton.triggered.connect(self.saveMasterDataDialog)
        filemenu.addAction(saveMasterDataButton)

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit QeoMAG')
        exitButton.triggered.connect(self.close)
        filemenu.addAction(exitButton)

        #Tools menu
        clearTextButton = QAction('Clear Data', self)
        clearTextButton.setShortcut('Ctrl+N')
        clearTextButton.triggered.connect(self.clearData)
        toolsmenu.addAction(clearTextButton)

        self.toggleWriteToTextButton = QAction('Toggle Text Printout On', self)
        self.toggleWriteToTextButton.setShortcut('Ctrl+T')
        self.toggleWriteToTextButton.triggered.connect(self.writeToTextToggle)
        toolsmenu.addAction(self.toggleWriteToTextButton)

        labelLinesButton = QAction('Label Lines', self)
        labelLinesButton.triggered.connect(self.labelLines)
        toolsmenu.addAction(labelLinesButton)

        rotateDataButton = QAction('Rotate Data by Heading', self)
        rotateDataButton.triggered.connect(self.rotateData)
        toolsmenu.addAction(rotateDataButton)

        addDatesButton = QAction('Add Dates Collected', self)
        addDatesButton.triggered.connect(self.addDates)
        toolsmenu.addAction(addDatesButton)

        #Data Menu
        dataCleanButton = QAction('Data Cleanup', self)
        dataCleanButton.setShortcut('Ctrl+K')
        dataCleanButton.setStatusTip('Preliminary data cleanup.')
        dataCleanButton.triggered.connect(self.dataCleanConnect)
        datamenu.addAction(dataCleanButton)

        dataToArrayButton = QAction('Convert Data to Array', self)
        dataToArrayButton.setShortcut('Ctrl+L')
        dataToArrayButton.triggered.connect(self.loadToArray)
        datamenu.addAction(dataToArrayButton)

        datamenu.addSeparator()

        purgeUnlockedDataButton = QAction('Purge Unlocked & Ground Data', self)
        purgeUnlockedDataButton.triggered.connect(self.purgeUnlockedData)
        datamenu.addAction(purgeUnlockedDataButton)

        purgeExoBoundaryDataButton = QAction('Purge Data Outside Boundary', self)
        purgeExoBoundaryDataButton.triggered.connect(self.purgeExoBoundaryData)
        datamenu.addAction(purgeExoBoundaryDataButton)

        purgeGroundDataButton = QAction('Purge Ground Data', self)
        purgeGroundDataButton.triggered.connect(self.purgeGroundData)
        datamenu.addAction(purgeGroundDataButton)

        purgeBadHeadingDataButton = QAction('Purge Data Outside of Heading', self)
        purgeBadHeadingDataButton.triggered.connect(self.purgeBadHeadingData)
        datamenu.addAction(purgeBadHeadingDataButton)

        datamenu.addSeparator()

        autoEvaluationButton = QAction('Automatic Evaluation', self)
        autoEvaluationButton.setShortcut('Ctrl+E')
        autoEvaluationButton.setStatusTip('Runs all evaluation scripts.')
        autoEvaluationButton.triggered.connect(self.autoEvaluation)
        datamenu.addAction(autoEvaluationButton)

        datamenu.addSeparator()

        dataBatchButton = QAction('Batching Operations', self)
        dataBatchButton.triggered.connect(self.batchHandler)
        datamenu.addAction(dataBatchButton)

        #Plot Menu
        plotDataButton = QAction('Plot Data', self)
        plotDataButton.setShortcut('Ctrl+D')
        plotDataButton.setStatusTip('Show current data.')
        plotDataButton.triggered.connect(self.plotData)
        plotmenu.addAction(plotDataButton)

        plotMasterDataButton = QAction('Plot Master Data', self)
        plotMasterDataButton.setShortcut('Ctrl+M')
        plotMasterDataButton.setStatusTip('Show all data.')
        plotMasterDataButton.triggered.connect(self.plotMasterData)
        plotmenu.addAction(plotMasterDataButton)

        plotRotatedDataButton = QAction('Plot Heading-Rotated Data', self)
        plotRotatedDataButton.setShortcut('Ctrl+R')
        plotRotatedDataButton.setStatusTip('Show rotated data.')
        plotRotatedDataButton.triggered.connect(self.plotRotatedData)
        plotmenu.addAction(plotRotatedDataButton)

        plotLineLabelsButton = QAction('Plot Data Points As Lines', self)
        plotLineLabelsButton.setStatusTip('Show data as lines.')
        plotLineLabelsButton.triggered.connect(self.plotLineLabels)
        plotmenu.addAction(plotLineLabelsButton)

        #About Menu
        aboutButton = QAction('About', self)
        #aboutButton.triggered.connect()
        aboutmenu.addAction(aboutButton)

    #wrappers for connect() to operate on the data list, since it won't accept functions with arguments.
    #clear the text widget and replace it with the latest in the 'data' object
    def writeDataToTextWidget(self):
        if self.toggleWriteToText == True:
            self.textwidget.clear()
            s = ' '
            if self.isArrayFulfilled == False:
                self.textwidget.appendPlainText(s.join(self.dataHeaders))
                for line in self.listData: self.textwidget.appendPlainText(s.join(line))

            else:
                self.textwidget.appendPlainText(s.join(self.dataHeaders))
                for line in self.localData:
                    strLine = ''
                    for item in line:
                        strLine = strLine + str(item) + ' '
                    self.textwidget.appendPlainText(strLine)
        else:
            self.textwidget.clear()
            self.textwidget.appendPlainText('Text outputs currently toggled off, probably to speed things up.\n Toggle text outputs on in order to see data output here.')

    #QeoMath Algorithm Wrappers
    def dataCleanConnect(self):
        try:
            self.listData = qm.dataClean(self.listData)
            #headers into separate list
            self.dataHeaders = self.listData[0]
            self.listData.pop(0)
            #convert to np array
            self.localData = np.array(self.listData, dtype=float)
        except Exception as error:
            print('Failed to float data. Error: ', error)
            traceback.print_exc()
        finally: self.writeDataToTextWidget()

    def purgeUnlockedData(self):
        if self.isArrayFulfilled == True:
            try: self.localData = qm.basicPurge(self.localData)
            except Exception as error:
                print('Failed to purge unlocked data. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    def purgeExoBoundaryData(self):
        if self.isArrayFulfilled == True:
            try: self.localData = qm.boundaryPurge(self.localData, self.boundaryfilename)
            except Exception as error:
                print('Failed to purge data from outside the boundary. Make sure you have loaded a SHP boundary file.', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    def purgeGroundData(self):
        if self.isArrayFulfilled == True:
            try: self.localData = qm.groundPurge(self.localData)
            except Exception as error:
                print('Failed to purge ground data. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()

        else: print('Error: Data not uploaded to Array')

    def purgeBadHeadingData(self):
        if self.isArrayFulfilled == True:
            try: self.localData = qm.headingPurge(self.localData, float(self.headingBox.text()),
                                                  float(self.headingToleranceBox.text()))
            except Exception as error:
                print('Failed to purge bad heading data. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    def labelLines(self): #Update with user input values
        if self.isArrayFulfilled == True:
            try:
                data = qm.lineLabel(self.localData, self.dataHeaders, float(self.lineNoStartBox.text()),
                                    float(self.lineIncrementBox.text()), self.isTieLine)
                self.localData = data[0]
                self.dataHeaders = data[1]
                #self.lineNoStartBox.setText(str(data[3]))
            except Exception as error:
                print('Failed to label lines. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Array not loaded.')

    def rotateData(self):
        if self.isArrayFulfilled == True:
            try:
                data = qm.headingRotationTransform(self.localData, float(self.headingBox.text()), self.dataHeaders)
                self.dataHeaders = data[0]
                self.localData = data[1]
            except Exception as error:
                print('Failed to label lines. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Array not loaded.')

    def magCutoff(self):
        if self.isArrayFulfilled == True:
            try: self.localData = qm.magCutoff(self.localData, float(self.magCutoffBoxLower.text()),
                                               float(self.magCutoffBoxUpper.text()))
            except Exception as error:
                print('Failed to run mag cutoff script. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    def addDates(self):
        if self.isArrayFulfilled == True:
            try:
                data = qm.addDateChannel(self.localData, self.dataHeaders, float(self.dateCollectedBox.text()))
                self.dataHeaders = data[0]
                self.localData = data[1]
            except Exception as error:
                print('Failed to add date channel. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    '''
    def removeChannel(self):
        if self.isArrayFulfilled == True:
            try:
                data = #qm.addDateChannel(self.localData, self.dataHeaders, float(self.dateCollectedBox.text()))
                self.dataHeaders = data[0]
                self.localData = data[1]
            except Exception as error:
                print('Failed to add date channel. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')
    '''

    #GUI Function Wrappers
    def clearData(self):
        self.textwidget.clear()

    def ledToGreen(self):
        self.arrayLabel.setText('Data Array: ✔')
        self.arrayLabel.setStyleSheet('color: green')
        self.isArrayFulfilled = True

    def ledToRed(self):
        self.arrayLabel.setText('Data Array: 🗙')
        self.arrayLabel.setStyleSheet('color: red')
        self.isArrayFulfilled = False

    def masterArrayLabelSetText(self, colour):
        self.masterArrayLabel.setText(self.masterLoadSuccess)
        self.masterArrayLabel.setStyleSheet('color: ' + colour)

    def tieLineCheckBoxSet(self):
        self.isTieLine = self.tieLineCheckBox.isChecked()
        print('Ties?: ', self.isTieLine)

    def writeToTextToggle(self):
        if self.toggleWriteToText == True:
            self.toggleWriteToText = False
            self.toggleWriteToTextButton.setText('Toggle Text Printout On')
        else:
            self.toggleWriteToText = True
            self.toggleWriteToTextButton.setText('Toggle Text Printout Off')
            self.writeDataToTextWidget()

    def batchHandler(self):
        batchWindow = batchToolWindow(self.batchList, 0, parent=self) #see __init__ for full list

    #plotting routines
    def plotData(self):
        if self.isArrayFulfilled == True:
            global dataplot
            try: dataplot = dataPlot(self.localData, self.dataHeaders, State='unrotated')
            except Exception as error:
                print('Error: Could not plot data. ', error)
                traceback.print_exc()
        else: print('Error: Data not uploaded to Array')

    def plotMasterData(self):
        if self.isArrayFulfilled == True and type(self.masterData) != None:
            global masterdataplot
            try: masterdataplot = dataPlot(self.masterData, self.dataHeaders, State='unrotated')
            except Exception as error:
                print('Error: Could not plot data. ', error)
                traceback.print_exc()
        else: print('Error: Data not uploaded to Array(s)')

    def plotRotatedData(self):
        if self.isArrayFulfilled == True:
            global rotateddataplot
            try: rotateddataplot = dataPlot(self.localData, self.dataHeaders, State='rotated')
            except Exception as error:
                print('Error: Could not plot data. ', error)
                traceback.print_exc()
        else: print('Error: Data not uploaded to Array(s)')

    def plotLineLabels(self):
        if self.isArrayFulfilled == True:
            global linelabelplot
            try:
                print('meow')
                linelabelplot = dataPlot(self.localData, self.dataHeaders, State='lineNos')
            except Exception as error:
                print('Error: Could not plot data. ', error)
                traceback.print_exc()
        else: print('Error: Data not uploaded to Array(s)')

    def pullPlotData(self):
        if self.isArrayFulfilled == True:
            try: self.localData = dataplot.plotData
            except Exception as error:
                print('Failed to retrieve plot data. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    def pullRotatedPlotData(self):
        if self.isArrayFulfilled == True:
            try: self.localData = rotateddataplot.plotData
            except Exception as error:
                print('Failed to retrieve plot data. Error: ', error)
                traceback.print_exc()
            finally: self.writeDataToTextWidget()
        else: print('Error: Data not uploaded to Array')

    #Array handling routines
    def loadToArray(self):
        try:
            data = qm.dataConvert(self.listData)
            if type(data) is not str:
                self.localData = data
                self.ledToGreen()
            else:
                self.ledToRed()
                print('Data could not be loaded into an array. Check the input files for inconsitencies.')
        except Exception as error:
            print('Failed to load data into array. Error: ', error)
            traceback.print_exc()
        finally: self.writeDataToTextWidget()

    def loadToMasterArray(self):
        if self.isArrayFulfilled == True:
            if self.masterData.size == 0:
                self.masterData = self.localData
                self.masterLoadSuccess = 'Data Uploaded'
                self.masterArrayLabelSetText('green')
            else:
                try:
                    self.masterData = np.append(self.masterData, self.localData, axis=0)
                except Exception as error:
                    print('Failed to append data to master array. Error: ', error)
                    traceback.print_exc()
                    self.masterLoadSuccess = 'Upload Error'
                    self.masterArrayLabelSetText('red')
                else:
                    self.masterLoadSuccess = 'Data Uploaded'
                    self.masterArrayLabelSetText('green')
        else:
            self.masterLoadSuccess = 'Upload Failure'
            self.masterArrayLabelSetText('red')

    #File Dialogs
    def openDataFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open Data File", "",
                                                  "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            self.datafilename = fileName
            data = qm.dataLoad(fileName, self.listData)
            if data[0] == True:
                self.localData = data[1]
                self.dataHeaders = data[2]
                self.ledToGreen()
            elif data[0] == False:
                self.listData = data[1]
                self.ledToRed()
            self.writeDataToTextWidget()
            self.setWindowTitle(self.title + ' - ' + self.datafilename)

    def openSHPFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open Boundary SHP File", "",
                                                  "All Files (*);;ESRI SHP Files (*.shp)", options=options)
        if fileName:
            self.boundaryfilename = fileName

    def saveDataFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,"Save Data File", self.datafilename,
                                                  "Text Files(*.txt);;All Files (*)", options=options)
        if fileName:
            self.savedatafilename = fileName
            with open(fileName, 'w') as saveFile:
                if self.toggleWriteToText == False: self.writeToTextToggle()
                saveFile.write(str(self.textwidget.toPlainText()))
                if self.toggleWriteToText == True: self.writeToTextToggle()

    def saveMasterDataDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,"Save Master Data File", "",
                                                  "Text Files(*.txt);;All Files (*)", options=options)
        if fileName:
            self.savedatafilename = fileName
            with open(fileName, 'w') as saveFile:
                np.savetxt(fileName, self.masterData, fmt='%.7g', delimiter=' ', header=' '.join(self.dataHeaders), comments='')
                #comments needs to be set to '' in order to avoid a leading '#' on the header line.
                #%.7g will intelligently format everything up to 7 decimal places
                #saveFile.write(str(self.textwidget.toPlainText()))

    #Automatic Evaluation and Batching
    def autoEvaluation(self):
        try:
            print('Evaluating ', self.datafilename)
            #toggles off printing to text
            if self.toggleWriteToText == True:
                self.toggleWriteToText = False
                self.toggleWriteToTextButton.setText('Toggle Text Printout On')
            self.listData = qm.dataClean(self.listData)
            #headers into separate list
            self.dataHeaders = self.listData[0]
            self.listData.pop(0)
            #convert to np array
            self.localData = np.array(self.listData, dtype=float)
            data = qm.dataConvert(self.listData)
            if type(data) is not str:
                self.localData = data
                self.ledToGreen()
            else:
                self.ledToRed()
                print('Data could not be loaded into an array. Check the input files for inconsitencies.')
            self.localData = qm.headingPurge(self.localData, float(self.headingBox.text()),
                                             float(self.headingToleranceBox.text()))
            self.localData = qm.basicPurge(self.localData)
            #self.localData = qm.boundaryPurge(self.localData, self.boundaryfilename)
            data = qm.headingRotationTransform(self.localData, float(self.headingBox.text()), self.dataHeaders)
            self.dataHeaders = data[0]
            self.localData = data[1]
            data = qm.addDateChannel(self.localData, self.dataHeaders, float(self.dateCollectedBox.text()))
            self.dataHeaders = data[0]
            self.localData = data[1]
        except Exception as error:
            print('Failed to run automatic evaluation script. Error: ', error)
            traceback.print_exc()
        finally:
            self.writeDataToTextWidget()
            #self.plotData()
            self.plotRotatedData()

class dataPlot:
    #This section/class is used for plotting the data
    def __init__(self, data_object, headers, State='unrotated'):
        self.plotData = data_object
        self.rectExtents = None
        self.state = State
        self.channel = {}
        for i in range(len(headers)): self.channel[headers[i]] = i #CAN NOW CALL COLUMNS by eg. line[self.channel['utmN']]
        if self.state == 'rotated': self.plotRotate()
        elif self.state == 'lineNos': self.plotLines()
        else: self.plotIt()


    def plotIt(self):

        self.smallest_E = 1000000.0 #used for plotting data later
        self.largest_E = 0.0
        self.smallest_N = 10000000.0
        self.largest_N = 0.0
        self.utmE = []
        self.utmN = []
        self.nT = []


        for line in self.plotData:
            if line[self.channel['utmE']] < self.smallest_E: self.smallest_E = line[self.channel['utmE']]
            if line[self.channel['utmE']] > self.largest_E: self.largest_E = line[self.channel['utmE']]
            if line[self.channel['utmN']] < self.smallest_N: self.smallest_N = line[self.channel['utmN']]
            if line[self.channel['utmN']] > self.largest_N: self.largest_N = line[self.channel['utmN']]
            self.utmE.append(line[self.channel['utmE']])
            self.utmN.append(line[self.channel['utmN']])
            self.nT.append(line[self.channel['nT']])

        self.fig, self.ax = plt.subplots()
        self.cb = self.ax.scatter(self.utmE, self.utmN, s=40, c=self.nT, norm='linear', cmap='viridis')
        self.ax.set(xlim=(self.smallest_E - 100, self.largest_E + 100), ylim=(self.smallest_N - 100, self.largest_N + 100))
        #plt.axis([self.smallest_E - 100, self.largest_E + 100, self.smallest_N - 100, self.largest_N + 100])

        self.props = dict(facecolor='black', alpha=0.1)
        self.rect = mwidgets.RectangleSelector(self.ax, self.onselect, interactive=True, props=self.props, useblit=True)

        self.fig.canvas.mpl_connect("key_press_event", self.ondelete)

        plt.colorbar(self.cb)
        plt.show()

    def plotRotate(self):

        self.smallest_E = 10000000.0 #used for plotting data later
        self.largest_E = -10000000.0
        self.smallest_N = 10000000.0
        self.largest_N = -10000000.0
        self.utmE = []
        self.utmN = []
        self.nT = []


        for line in self.plotData:
            if line[self.channel['UTMx']] < self.smallest_E: self.smallest_E = line[self.channel['UTMx']]
            if line[self.channel['UTMx']] > self.largest_E: self.largest_E = line[self.channel['UTMx']]
            if line[self.channel['UTMy']] < self.smallest_N: self.smallest_N = line[self.channel['UTMy']]
            if line[self.channel['UTMy']] > self.largest_N: self.largest_N = line[self.channel['UTMy']]
            self.utmE.append(line[self.channel['UTMx']])
            self.utmN.append(line[self.channel['UTMy']])
            self.nT.append(line[self.channel['nT']])

        self.fig, self.ax = plt.subplots()
        self.cb = self.ax.scatter(self.utmE, self.utmN, s=40, c=self.nT, norm='linear', cmap='viridis')
        self.ax.set(xlim=(self.smallest_E - 100, self.largest_E + 100), ylim=(self.smallest_N - 100, self.largest_N + 100))

        self.props = dict(facecolor='black', alpha=0.1)
        self.rect = mwidgets.RectangleSelector(self.ax, self.onselect, interactive=True, props=self.props, useblit=True)

        self.fig.canvas.mpl_connect("key_press_event", self.ondelete)

        plt.colorbar(self.cb)
        plt.show()

    def plotLines(self):

        self.smallest_E = 10000000.0 #used for plotting data later
        self.largest_E = -10000000.0
        self.smallest_N = 10000000.0
        self.largest_N = -10000000.0
        self.utmE = []
        self.utmN = []
        self.lineNos = []

        for line in self.plotData:
            if line[self.channel['utmE']] < self.smallest_E: self.smallest_E = line[self.channel['utmE']]
            if line[self.channel['utmE']] > self.largest_E: self.largest_E = line[self.channel['utmE']]
            if line[self.channel['utmN']] < self.smallest_N: self.smallest_N = line[self.channel['utmN']]
            if line[self.channel['utmN']] > self.largest_N: self.largest_N = line[self.channel['utmN']]
            self.utmE.append(line[self.channel['utmE']])
            self.utmN.append(line[self.channel['utmN']])
            self.lineNos.append(line[self.channel['lineNo']])

        self.fig, self.ax = plt.subplots()
        self.cb = self.ax.scatter(self.utmE, self.utmN, s=40, c=self.lineNos, norm='linear', cmap='prism')
        self.ax.set(xlim=(self.smallest_E - 100, self.largest_E + 100), ylim=(self.smallest_N - 100, self.largest_N + 100))

        #self.props = dict(facecolor='black', alpha=0.1)
        #self.rect = mwidgets.RectangleSelector(self.ax, self.onselect, interactive=True, props=self.props, useblit=True)

        #self.fig.canvas.mpl_connect("key_press_event", self.ondelete)

        plt.colorbar(self.cb)
        print('Showing LineNo Plot...')
        plt.show()

    def onselect(self, eclick, erelease):
        self.rectExtents = self.rect.extents

    #def onrselect(self, eclick, erelease):
    #    self.rectExtents = self.rrect.extents

    def ondelete(self, event):
        if event.key == "delete":
            idx = -1
            idxlist = []
            delcounter = 0
            for line in self.plotData:
                idx += 1
                if self.state == 'rotated':
                    if self.rectExtents[0] < line[self.channel['UTMx']] < self.rectExtents[1]:
                        if self.rectExtents[2] < line[self.channel['UTMy']] < self.rectExtents[3]:
                            idxlist.append(idx)
                            delcounter += 1
                            continue
                elif self.state == 'unrotated':
                    if self.rectExtents[0] < line[self.channel['utmE']] < self.rectExtents[1]:
                        if self.rectExtents[2] < line[self.channel['utmN']] < self.rectExtents[3]:
                            idxlist.append(idx)
                            delcounter += 1
                            continue
            if len(idxlist) > 0:
                idxlist = np.array(idxlist)
                self.plotData = np.delete(self.plotData, idxlist, axis=0)
            print('Points deleted: ', delcounter)
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
            if self.state == 'rotated': ex.pullRotatedPlotData()
            else: ex.pullPlotData() #I don't know why this works, but it does
            ex.writeDataToTextWidget()
            plt.close() #close the current figure
            if self.state == 'rotated': self.plotRotate() #redraw
            else: self.plotIt()

        '''
        else:
            if event.key == "delete":
                idx = -1
                idxlist = []
                delcounter = 0
                for line in self.plotData:
                    idx += 1
                    if self.rectExtents[0] < line[self.channel['UTMx']] < self.rectExtents[1]:
                        if self.rectExtents[2] < line[self.channel['UTMy']] < self.rectExtents[3]:
                            idxlist.append(idx)
                            delcounter += 1
                            continue
                if len(idxlist) > 0:
                    idxlist = np.array(idxlist)
                    self.plotData = np.delete(self.plotData, idxlist, axis=0)
                print('Points deleted: ', delcounter)
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
                ex.pullPlotData() #I don't know why this works, but it does
                #except Exception: pass #kills this stupid namespace error
                #ex.localData = self.plotData
                ex.writeDataToTextWidget()
                plt.close() #close the current figure
                self.plotRotate() #redraw
        '''

class batchToolWindow(QMainWindow):
    def __init__(self, batch_types_list, batch_type_index=0, parent=None): #parent may need to be set to None; we shall see
        #batch types can be found in MainWindow.batchList)
        super().__init__(parent)
        self.top    = 150
        self.left   = 300
        self.width  = 350
        self.height = 250
        self.batchTypes = batch_types_list
        self.info = []
        self.initUI()

    def initUI(self):
        #window
        #self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.widget = QWidget()
        self.setAutoFillBackground(True)
        self.vLayout = QVBoxLayout(self.widget)
        self.hLayout00 = QHBoxLayout()
        self.hLayout01 = QHBoxLayout()
        self.hLayout02 = QHBoxLayout()
        self.hLayout03 = QHBoxLayout()

        self.setCentralWidget(self.widget)

        #buttons
        self.closeButton = QPushButton()
        self.closeButton.setFixedSize(80,40)
        self.closeButton.clicked.connect(self.close)
        self.closeButton.setText('Cancel')

        self.batchRunButton = QPushButton()
        self.batchRunButton.setFixedSize(80,40)
        self.batchRunButton.clicked.connect(self.runBatchEvent)
        #self.batchRunButton.setText('')

        self.hLayout03.addWidget(self.batchRunButton)
        self.hLayout03.addWidget(self.closeButton)

        #description labels
        self.descLabel00 = QLabel() #descriptive label below/for batchType dropdown
        self.descLabel00.setFont(QFont("Helvetica", italic=True))
        self.descLabel00.setAlignment(Qt.AlignCenter)
        self.descLabel01 = QLabel() #descriptive label below/for Source box
        self.descLabel01.setFont(QFont("Helvetica", italic=True))
        self.descLabel01.setAlignment(Qt.AlignCenter)
        self.descLabel02 = QLabel() #descriptive label below/for Target box
        self.descLabel02.setFont(QFont("Helvetica", italic=True))
        self.descLabel02.setAlignment(Qt.AlignCenter)

        #batchType dropdown list
        self.label00 = QLabel()
        self.label00.setText('Batch Job: ')
        self.dropDown00 = QComboBox()
        self.dropDown00.addItems(self.batchTypes)
        self.dropDown00.currentIndexChanged.connect(self.batchTypifier)
        self.hLayout00.addWidget(self.label00)
        self.hLayout00.addWidget(self.dropDown00)
        #self.dropDown00.currentText

        #file/folder bars/dialogs - their properties will be changed in the batchTypifier function
        #Source box section
        self.label01 = QLabel()
        self.textBox01 = QLineEdit()
        self.dialogButton01 = QPushButton('Browse...', self)
        self.hLayout01.addWidget(self.label01)
        self.hLayout01.addWidget(self.textBox01)
        self.hLayout01.addWidget(self.dialogButton01)
        #Target box/section
        self.label02 = QLabel()
        self.textBox02 = QLineEdit()
        self.dialogButton02 = QPushButton('Browse...', self)
        self.hLayout02.addWidget(self.label02)
        self.hLayout02.addWidget(self.textBox02)
        self.hLayout02.addWidget(self.dialogButton02)

        #Layout integration
        self.vLayout.addLayout(self.hLayout00)
        self.vLayout.addWidget(self.descLabel00)
        #self.vLayout.addSeparator()
        self.vLayout.addLayout(self.hLayout01)
        self.vLayout.addWidget(self.descLabel01)
        #self.vLayout.addSeparator()
        self.vLayout.addLayout(self.hLayout02)
        self.vLayout.addWidget(self.descLabel02)
        #self.vLayout.addSeparator()
        self.vLayout.addLayout(self.hLayout03)

        self.BTinit = True #used to handle disconnects in the batchTypifier
        self.batchTypifier() #run last in initUI

        self.show()

    def batchTypifier(self):
        self.setWindowTitle(self.dropDown00.currentText())
        if self.BTinit == False:
            self.dialogButton01.clicked.disconnect()
            self.dialogButton02.clicked.disconnect()
        if self.dropDown00.currentText() == 'Label Lines':
            self.batchRunButton.setText('Label Lines')
            self.label01.setText('Source Folder: ')
            self.label02.setText('Destination File: ')
            self.descLabel00.setText('Batch labelling script for MAG lines. Will label and amalgamate all lines in given folder.')
            self.descLabel01.setText('Select a source folder.')
            self.descLabel02.setText('Input destination filename.')
            self.dialogButton01.clicked.connect(self.openFolder)
            self.dialogButton02.clicked.connect(self.targetFile)
        if self.dropDown00.currentText() == 'Label Ties':
            self.batchRunButton.setText('Label Ties')
            self.label01.setText('Source Folder: ')
            self.label02.setText('Destination File: ')
            self.descLabel00.setText('Batch labelling script for TIE lines. Will label and amalgamate all lines in given folder.')
            self.descLabel01.setText('Select a source folder.')
            self.descLabel02.setText('Input destination filename.')
            self.dialogButton01.clicked.connect(self.openFolder)
            self.dialogButton02.clicked.connect(self.targetFile)
        if self.dropDown00.currentText() == 'Parse Bad Data':
            self.batchRunButton.setText('Run Parser')
            self.label01.setText('Source File: ')
            self.label02.setText('Destination File: ')
            self.descLabel00.setText('Attempts to repair a data source file that has corrupted delimiters.')
            self.descLabel01.setText('Select a source file.')
            self.descLabel02.setText('Input destination filename.')
            self.dialogButton01.clicked.connect(self.openFile)
            self.dialogButton02.clicked.connect(self.targetFile)
        self.BTinit = False


    #batch function wrappers
    def runBatchEvent(self):
        #determines what batch function we're running
        if self.dropDown00.currentText() == 'Label Lines': self.batchLabelLines()
        if self.dropDown00.currentText() == 'Label Ties': self.batchLabelTies()
        if self.dropDown00.currentText() == 'Parse Bad Data': self.repairData()

    def batchLabelLines(self):
        try:
            qm.labelsBatch(False, self.textBox01.text(), os.path.dirname(self.textBox02.text()),
                            os.path.basename(self.textBox02.text()))
            self.batchRunButton.setText('Complete')
            self.batchRunButton.setEnabled(False)
            self.closeButton.setText('Close')
        except Exception as error:
            print('Failed to label lines. Error: ', error)
            traceback.print_exc()


    def batchLabelTies(self):
        try:
            qm.labelsBatch(True, self.textBox01.text(), os.path.dirname(self.textBox02.text()),
                            os.path.basename(self.textBox02.text()))
            self.batchRunButton.setText('Complete')
            self.batchRunButton.setEnabled(False)
            self.closeButton.setText('Close')
        except Exception as error:
            print('Failed to label lines. Error: ', error)
            traceback.print_exc()

    def repairData(self):
        try:
            data = qm.dataRepair(self.textBox01.text())
            with open(self.textBox02.text(), 'w') as file:
                file.writelines(data)
                file.close()
            self.batchRunButton.setText('Complete')
            self.batchRunButton.setEnabled(False)
            self.closeButton.setText('Close')
        except Exception as error:
            print('Failed to repair data. Error: ', error)
            traceback.print_exc()


    def openFolder(self): #open Folder dialog
        options = QFileDialog.Options()
        dirName = ''
        try: dirName = QFileDialog.getExistingDirectory(self,"Select Input Folder", self.textBox01.text(),
                                                    QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly)
        except Exception as error: print(error)
        self.textBox01.setText(dirName)

    def openFile(self): #open File dialog
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename = ''
        try: fileName, _ = QFileDialog.getOpenFileName(self,"Open Input File", self.textBox01.text(),
                                                  filter="Text Files(*.txt);;All Files (*)", options=options)
        except Exception as error: print(error)
        self.textBox01.setText(fileName)

    def targetFile(self): #save File dialog
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename = ''
        try: fileName, _ = QFileDialog.getSaveFileName(self,"Save Output File", self.textBox02.text(),
                                                  filter="Text Files(*.txt);;All Files (*)", options=options)
        except Exception as error: print(error)
        self.textBox02.setText(fileName)

def main():
    global ex
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
