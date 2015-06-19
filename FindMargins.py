import os
import unittest
import math
import numpy as np

from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

# import time
# import threading

import FindMarginsLib


#
# FindMargins
#

class FindMargins(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "FindMargins" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["Kristjan Anderle (GSI)"] # replace with "Firstname Lastname (Org)"
    self.parent.helpText = """
    This is a module that finds tumor margins due to motion
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc. and Steve Pieper, Isomics, Inc.  and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# qFindMarginsWidget
#

class FindMarginsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)


    # #
    # # Reload and Test area
    # #
    # reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    # reloadCollapsibleButton.text = "Reload && Test"
    # self.layout.addWidget(reloadCollapsibleButton)
    # reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)
    #
    # ## reload button
    # ## (use this during development, but remove it when delivering
    # ##  your module to users)
    # self.reloadCTXButton = qt.QPushButton("Reload")
    # self.reloadCTXButton.toolTip = "Reload this module."
    # self.reloadCTXButton.name = "LoadCTX Reload"
    # reloadFormLayout.addWidget(self.reloadCTXButton)
    # self.reloadCTXButton.connect('clicked()', self.onReload)
    #
    # ## reload and test button
    # ## (use this during development, but remove it when delivering
    # ##  your module to users)
    # self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    # self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    # reloadFormLayout.addWidget(self.reloadAndTestButton)
    # self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    self.tags = {}
    self.tags['seriesDescription'] = "0008,103e"
    self.tags['patientName'] = "0010,0010"
    self.tags['patientID'] = "0010,0020"
    self.tags['seriesDate'] = "0008,0022"

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    # Load all patients
    self.patientComboBox = qt.QComboBox()
    self.patientComboBox.setToolTip( "Select Patient" )
    self.patientComboBox.enabled = True
    #self.parametersFormLayout.addWidget("Patient:", self.patientComboBox)
    parametersFormLayout.addRow("Select Patient",self.patientComboBox)

    self.patientList = []
    self.getPatientList()

    for patient in self.patientList:
      self.patientComboBox.addItem(patient.name)

    #
    # input volume selector
    #
    self.inputContourSelector = slicer.qMRMLNodeComboBox()
    self.inputContourSelector.nodeTypes = ( ("vtkMRMLContourNode"), "" )
    # self.inputContourSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.inputContourSelector.selectNodeUponCreation = True
    self.inputContourSelector.addEnabled = False
    self.inputContourSelector.removeEnabled = False
    self.inputContourSelector.noneEnabled = False
    self.inputContourSelector.showHidden = False
    self.inputContourSelector.showChildNodeTypes = False
    self.inputContourSelector.setMRMLScene( slicer.mrmlScene )
    self.inputContourSelector.setToolTip( "Pick the CTV voi." )
    self.inputContourSelector.enabled = False
    parametersFormLayout.addRow("Desired Contour: ", self.inputContourSelector)
    
    #
    # planning CT selector
    #
    self.inputPlanCTSelector = slicer.qMRMLNodeComboBox()
    self.inputPlanCTSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    # self.inputPlanCTSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.inputPlanCTSelector.selectNodeUponCreation = True
    self.inputPlanCTSelector.addEnabled = False
    self.inputPlanCTSelector.removeEnabled = False
    self.inputPlanCTSelector.noneEnabled = True
    self.inputPlanCTSelector.showHidden = False
    self.inputPlanCTSelector.showChildNodeTypes = False
    self.inputPlanCTSelector.setMRMLScene( slicer.mrmlScene )
    self.inputPlanCTSelector.setToolTip( "Pick the planning CT, if it can't be found by default." )
    self.inputPlanCTSelector.enabled = True
    parametersFormLayout.addRow("Planning CT: ", self.inputPlanCTSelector)


    #
    # Select if contour is already in 4D CT
    #

    self.contourIn4D = qt.QCheckBox()
    self.contourIn4D.toolTip = "Select if selected contour was already deliniated in 4D CT (it will skip the planning registration."
    self.contourIn4D.setCheckState(2)
    parametersFormLayout.addRow("Contour deliniated in 4D: ",self.contourIn4D)

    #
    # Display contours
    #

    self.showContours = qt.QCheckBox()
    self.showContours.toolTip = "Select if you want to display all the generated contours."
    self.showContours.setCheckState(0)
    parametersFormLayout.addRow("Show created ontours: ",self.showContours)

    #
    # Registration from planning CT to all ref phase
    #

    # self.planToAll = qt.QCheckBox()
    # self.planToAll.toolTip = "Select if you want to register planning CT to all phases of 4D CT."
    # self.planToAll.setCheckState(0)
    # parametersFormLayout.addRow("Full 4D: ",self.planToAll)
    
    #
    # Keep amplitudes 
    #

    self.keepAmplituedCheckBox = qt.QCheckBox()
    self.keepAmplituedCheckBox.toolTip = "Select if you want to use motion from markers or some other organs for PTV definition."
    self.keepAmplituedCheckBox.setCheckState(0)
    parametersFormLayout.addRow("Keep amplitudes: ",self.keepAmplituedCheckBox)
    
    #
    # Find axis of motion 
    #

    self.axisOfMotionCheckBox = qt.QCheckBox()
    self.axisOfMotionCheckBox.toolTip = "Select if you want to find axis of motion with principal component analysis."
    self.axisOfMotionCheckBox.setCheckState(2)
    parametersFormLayout.addRow("Find Axis of Motion: ",self.axisOfMotionCheckBox)

    
    #
    # Select reference phase:
    #
    
    self.refPhaseSpinBox = qt.QSpinBox()     
    self.refPhaseSpinBox.setToolTip( "Reference phase to base registration and mid ventilation." )
    self.refPhaseSpinBox.setValue(3)
    self.refPhaseSpinBox.setRange(0, 9)
    parametersFormLayout.addRow("Reference phase:", self.refPhaseSpinBox)
    
    #
    # Select systematic error:
    #
    
    self.SSigmaSpinBox = qt.QSpinBox()     
    self.SSigmaSpinBox.setToolTip("Systematic error to be used in PTV calculations.")
    self.SSigmaSpinBox.setValue(2)
    self.SSigmaSpinBox.setRange(0, 10)
    parametersFormLayout.addRow("Systematic Error [mm]:", self.SSigmaSpinBox)
    
    #
    # Select random error:
    #
    
    self.RsigmaSpinBox = qt.QSpinBox()     
    self.RsigmaSpinBox.setToolTip("Random error to be used in PTV calculations.")
    self.RsigmaSpinBox.setValue(0)
    self.RsigmaSpinBox.setRange(0, 10)
    parametersFormLayout.addRow("Random Error [mm]:", self.RsigmaSpinBox)
    
    #
    # Do registration
    #
    self.registerButton = qt.QPushButton("Register")
    self.registerButton.toolTip = "Does the registration on planning CT and 4DCT."
    parametersFormLayout.addRow(self.registerButton)

    #
    # Load DICOM
    #
    self.loadContoursButton = qt.QPushButton("Load Contours")
    self.loadContoursButton.toolTip = "Loads contours from DICOM data."
    parametersFormLayout.addRow(self.loadContoursButton)
    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Find amplitudes")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    #
    # MidV Button
    #
    self.midVButton = qt.QPushButton("Create MidV CT")
    self.midVButton.toolTip = "Creates the Mid ventilation CT from 4DCT and registration files."
    self.midVButton.enabled = True
    parametersFormLayout.addRow(self.midVButton)
    
    #
    # Average 4DCT Button
    #
    self.averageButton = qt.QPushButton("Create Average 4D CT")
    self.averageButton.toolTip = "Creates time average CT from 4DCTs."
    self.averageButton.enabled = True
    parametersFormLayout.addRow(self.averageButton)
    
    #
    # ITV Button
    #
    self.itvButton = qt.QPushButton("Create ITV")
    self.itvButton.toolTip = "Creates the ITV from CTV and registration files."
    self.itvButton.enabled = False
    self.itvButton.visible = False
    parametersFormLayout.addRow(self.itvButton)
    
    #
    # PTV Button
    #
    self.ptvButton = qt.QPushButton("Create margin PTV")
    self.ptvButton.toolTip = "Creates the ITV from CTV and registration files."
    self.ptvButton.enabled = True
    parametersFormLayout.addRow(self.ptvButton)
    
    #
    # Color Button
    #
    self.colorButton = qt.QPushButton("Change contour color and thickness")
    self.colorButton.toolTip = "Changes contour color and thickness of closed surface for better display."
    self.colorButton.enabled = True
    parametersFormLayout.addRow(self.colorButton)
    
    #
    # Register planning CT to midV Button
    #
    self.registerMidButton = qt.QPushButton("Register Planning CT to MidV")
    self.registerMidButton.toolTip = "Register planning CT to mid ventilation phase."
    self.registerMidButton.enabled = True
    self.registerMidButton.visible = True
    parametersFormLayout.addRow(self.registerMidButton)

    #
    # Table with amplitudes
    #

    self.table = qt.QTableWidget()
    self.table.setColumnCount(3)
    self.table.setHorizontalHeaderLabels(["L-R","A-P","I-S"])
    self.table.setRowCount(2)
    self.table.setVerticalHeaderLabels(["Max","Min"])
    self.table.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
    self.table.enabled = False
    parametersFormLayout.addRow(self.table)



    # connections
    self.applyButton.connect('clicked(bool)', self.onFindAmplitudes)
    self.loadContoursButton.connect('clicked(bool)', self.onLoadContoursButton)
    self.registerButton.connect('clicked(bool)', self.onRegisterButton)
    self.midVButton.connect('clicked(bool)', self.onMidVButton)
    self.averageButton.connect('clicked(bool)', self.onAverageButton)
    self.itvButton.connect('clicked(bool)', self.onItvButton)
    self.ptvButton.connect('clicked(bool)', self.onPtvButton)
    self.colorButton.connect('clicked(bool)', self.onColorButton)
    self.registerMidButton.connect('clicked(bool)', self.onRegisterMidButton)
    self.inputPlanCTSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onPlanCTChange)
    self.inputContourSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onContourChange)
    self.refPhaseSpinBox.connect("valueChanged(int)", self.onRefPhaseChange)
    # self.patientComboBox.connect('currentIndexChanged(QString)', self.setSeriesComboBox)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.inputContourSelector.currentNode()
    self.itvButton.enabled = self.inputContourSelector.currentNode()
    self.inputContourSelector.enabled = self.inputContourSelector.currentNode()

  def onPlanCTChange(self, planningCT):
      if planningCT is not None:
          patientNumber = self.patientComboBox.currentIndex
          patient = self.patientList[patientNumber]
          if patient is not None:
            patient.fourDCT[10].node = planningCT
            # print patient.name + "has now" + patient.fourDCT[10].node.GetName()

  def onContourChange(self, targetContour):
      if targetContour is not None:
          patientNumber = self.patientComboBox.currentIndex
          patient = self.patientList[patientNumber]
          if patient is not None:
            patient.fourDCT[10].contour = targetContour
            # print patient.name + "has now" + patient.fourDCT[10].node.GetName()
  def onRefPhaseChange(self, refPhase):
      patientNumber = self.patientComboBox.currentIndex
      patient = self.patientList[patientNumber]
      if patient is not None:
          patient.refPhase = refPhase
  
  def onFindAmplitudes(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    skipPlanRegistration = False
    if self.contourIn4D.checkState() == 2:
      skipPlanRegistration = True

    showContours = False
    if self.showContours.checkState() == 2:
      showContours = True

    axisOfMotion = False
    if self.axisOfMotionCheckBox.checkState() == 2:
      axisOfMotion = True

    if patient.fourDCT[10].contour is None:
      self.errorMessage("No contour was set.")
      return
    
    #Calculate amplitudes
    exitString = logic.calculateMotion(patient, skipPlanRegistration, showContours, axisOfMotion)
    if len(exitString) > 0:
      self.errorMessage(exitString)
      return

    maxminAmplitudes = patient.maxminAmplitudes
    if not maxminAmplitudes:
        print "Can't get amplitudes."
        return
    self.item={}
    n = 0
    for i in range(0,2):
        for j in range(0,3):
            self.item[n] = qt.QTableWidgetItem()
            self.item[n].setText(str(round(maxminAmplitudes[i][j], 2)))
            self.table.setItem(i, j, self.item[n])
            n += 1


  def onLoadContoursButton(self):
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if  len(patient.structureSet.uid) == 0:
      self.errorMessage("Can't get Structure Set DICOM data for " + patient.name)
      return

    if not patient.loadStructureSet():
      self.errorMessage("Can't load Contours - check python console")
      return


    self.applyButton.enabled = True
    self.inputContourSelector.enabled = True
    self.itvButton.enabled = True

  def onRegisterButton(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    planToAll = False
    # if self.planToAll.checkState() == 2:
    #   planToAll = True
    logic.register(patient, planToAll)

  def onMidVButton(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    # planToAll = False
    # if self.planToAll.checkState() == 2:
    #   logic.createMidVentilationFromPlanningCT(patient)
    # else:
    logic.createMidVentilation(patient)

  def onAverageButton(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    logic.createAverageFrom4DCT(patient)

  def onRegisterMidButton(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    logic.registerMidV(patient)


  def onItvButton(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    skipPlanRegistration = False
    if self.contourIn4D.checkState() == 2:
        skipPlanRegistration = True

    showContours = False
    if self.showContours.checkState() == 2:
        showContours = True

    logic.createITV(patient, skipPlanRegistration, showContours)


  def onPtvButton(self):
    logic = FindMarginsLogic()
    patientNumber = self.patientComboBox.currentIndex
    patient = self.patientList[patientNumber]
    targetContour = self.inputContourSelector.currentNode()

    if patient is None:
      self.errorMessage("Can't find patient.")
      return

    SSigma = self.SSigmaSpinBox.value
    Rsigma = self.RsigmaSpinBox.value

    patient.fourDCT[10].contour = targetContour

    if self.keepAmplituedCheckBox.checkState() == 2:
      keepAmplitudes = True
    else:
      keepAmplitudes = False

    axisOfMotion = False
    if self.axisOfMotionCheckBox.checkState() == 2:
      axisOfMotion = True

    logic.createPTV(patient, SSigma, Rsigma, keepAmplitudes, axisOfMotion)

    self.item={}
    for i in range(0,3):
      self.item[i] = qt.QTableWidgetItem()
      self.item[i].setText(str(round(patient.ptvMargins[i], 2)))
      self.table.setItem(0, i, self.item[i])

  def onColorButton(self):
    logic = FindMarginsLogic()
    targetContour = self.inputContourSelector.currentNode()
    logic.setColorAndThickness(targetContour)
      
  
  def getPatientList(self):

    nPatient = 0

    self.patientList = []
    for patient in slicer.dicomDatabase.patients():
      newPatient = FindMarginsLib.Patient()
      for study in slicer.dicomDatabase.studiesForPatient(patient):
        for series in slicer.dicomDatabase.seriesForStudy(study):
          files = slicer.dicomDatabase.filesForSeries(series)
          if len(files) > 0:
            instance = slicer.dicomDatabase.instanceForFile(files[0])
            try:
              patientName = slicer.dicomDatabase.instanceValue(instance, self.tags['patientID'])
            except RuntimeError:
                # this indicates that the particular instance is no longer
                # accessible to the dicom database, so we should ignore it here
              continue
            serialDescription = slicer.dicomDatabase.instanceValue(instance, self.tags['seriesDescription'])
            # print "Series date: " + slicer.dicomDatabase.instanceValue(instance,self.tags['seriesDate'])
            # if len(slicer.dicomDatabase.instanceValue(instance,self.tags['seriesDate'])) > 0:
            #   print "Hello"
            #   newPatient.planCT.uid = series
            #   newPatient.planCT.file = files[0]

            # print serialDescription
            if serialDescription.find('Structure Sets') > -1:
              newPatient.structureSet.uid = series

            if serialDescription.find('%') > -1:
              for i in range(0, 100, 10):
                tmpName = str(i) + ".0%"
                if serialDescription.find(tmpName) > -1:
                  #Special case for 0.0%
                  if i == 0:
                    position = serialDescription.find(tmpName)
                    try:
                      int(serialDescription[position-1])
                      continue
                    except ValueError:
                      if serialDescription.find(" " + tmpName) < 0 and not serialDescription == tmpName:
                        continue
                  # print patientName + " found " + serialDescription + " so " + files[0]
                  newPatient.fourDCT[i/10].uid = series
                  newPatient.fourDCT[i/10].file = files[0]
                  if len(newPatient.patientDir) == 0:
                    newPatient.patientDir = os.path.dirname(files[0])
                if len(newPatient.vectorDir) == 0 and os.path.exists(files[0]):
                    dicomDir = os.path.dirname(files[0])
                    newPatient.vectorDir = dicomDir + "/VectorFields/"
                    if not os.path.exists(newPatient.vectorDir):
                        os.makedirs(newPatient.vectorDir)
                        print "Created " + newPatient.vectorDir

      newPatient.databaseNumber = nPatient
      newPatient.name = patientName
      self.patientList.append(newPatient)

      nPatient += 1

  def errorMessage(self, message):
    print(message)
    self.info = qt.QErrorMessage()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.info.showMessage(message)
#
# FindMarginsLogic
#
class FindMarginsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """


  def register(self, patient, planToAll = False):

    refPhase = patient.refPhase

    for i in range(0,10):
      if not planToAll:
        if not i == refPhase:
          continue

      patient.refPhase = i
      patient.createPlanParameters()
      if patient.getTransform(10):
        print "Planning transform already exist."
        slicer.mrmlScene.RemoveNode(patient.fourDCT[10].transform)
        patient.fourDCT[10].transform = None
      else:
        print "Registering planning CT"
        if not patient.loadDicom(10):
          print "Cant load planning CT."
          return

        if not patient.loadDicom(patient.refPhase):
          print "Can't load reference phase"
          return

        patient.regParameters.movingNode = patient.fourDCT[10].node.GetID()
        patient.regParameters.referenceNode = patient.fourDCT[patient.refPhase].node.GetID()
        patient.regParameters.register()
        # slicer.mrmlScene.RemoveNode(patient.fourDCT[10].node)
        # patient.fourDCT[10].node = None

    # Prepare everything for 4D registration
    patient.refPhase = refPhase
    patient.create4DParameters()


    for i in range(0,10):
      if i == refPhase:
        continue

      patient.regParameters.referenceNumber = str(i) + "0"
      if patient.getTransform(i):
        print "Transform for phase " + str(i) + "0% already exist."
        slicer.mrmlScene.RemoveNode(patient.fourDCT[i].transform)
        patient.fourDCT[i].transform = None
        continue
      else:
        print "Registering phase " + str(i) + "0%."
        patient.regParameters.referenceNumber = str(i) + "0"
        if not patient.loadDicom(refPhase):
          print "Can't load reference phase"
          continue
        if not patient.loadDicom(i):
          print "Can't load phase " + str(i) + "0%."
          continue

        patient.regParameters.movingNode = patient.fourDCT[refPhase].node.GetID()
        patient.regParameters.referenceNode = patient.fourDCT[i].node.GetID()
        patient.regParameters.register()

        slicer.mrmlScene.RemoveNode(patient.fourDCT[i].node)
        patient.fourDCT[i].node = None

        slicer.mrmlScene.RemoveNode(patient.fourDCT[refPhase].node)
        patient.fourDCT[refPhase].node = None
    print "Finished"
    return


  def calculateMotion(self, patient, skipPlanRegistration, showContours, axisOfMotion = False, showPlot = True):
    # logging.info('Processing started')
    self.delayDisplay("Calculating motion")
    origins = np.zeros([3, 10])
    relOrigins = np.zeros([3, 10])
    patient.minmaxAmplitudes = [[-1e3, -1e3, -1e3], [1e3, 1e3, 1e3]]
    amplitudes = [0, 0, 0]
    patient.amplitudes = {}
    parentNodeID = ""

    refPhase = patient.refPhase

    #This is the relative difference between planning CT and reference position
    #Amplitudes are shifted for this value, so we can get an estimate, where is our planning CT in 4DCT
    if patient.fourDCT[10].contour is None:
      print "Can't find contour"
      return None
    planOrigins = self.getCenterOfMass(patient.fourDCT[10].contour)
    print planOrigins
    contourName = patient.fourDCT[10].contour.GetName().replace("_Contour", "")

    #Find parent hierarchy, if we want to show contours
    if showContours:
      subjectHierarchyNode = slicer.util.getNode(contourName + "*_SubjectHierarchy")
      if subjectHierarchyNode:
        parentNodeID = subjectHierarchyNode.GetParentNodeID()

    #If there's a labelmap, then contours are not propagated right.
    #This is a workaround
    contourLabelmap = patient.fourDCT[10].contour.GetLabelmapImageData()
    if contourLabelmap:
      patient.fourDCT[10].contour.SetAndObserveLabelmapImageData(None)
    
    if skipPlanRegistration:
        contour = patient.fourDCT[10].contour
    else:
        #Propagate contour
        contour = self.propagateContour(patient, 10, showContours, None, parentNodeID)
        if contour is None:
            print "Can't propagate contour to reference phase."
            return None

    patient.fourDCT[refPhase].contour = contour
    origins[:, refPhase] = self.getCenterOfMass(contour)
    relOrigins[:, refPhase] = [0, 0, 0]
    relOrigins[:, refPhase] += origins[:, refPhase] - planOrigins

    # Propagation in 4D
    patient.create4DParameters()
    for i in range(0, 10):
      if i == refPhase:
        continue

      #Create & propagate contour
      contour = self.propagateContour(patient, i, showContours, None, parentNodeID)
      if contour is None:
        print "Can't propagate contour for phase " + str(i) + "0 %"
        continue
      patient.fourDCT[i].contour = contour
      origins[:, i] = self.getCenterOfMass(contour)
      if not showContours:
          slicer.mrmlScene.RemoveNode(contour)
          patient.fourDCT[i].contour = None
    if not showContours and not skipPlanRegistration:
        slicer.mrmlScene.RemoveNode(patient.fourDCT[refPhase].contour)
        patient.fourDCT[refPhase].contour = None

    # Find axis of motion
    if axisOfMotion:
      matrix_W = self.findAxisOfMotion(origins)
      origins = np.dot(matrix_W.T, origins)
      patient.matrix = matrix_W

    #Find relative motion
    for i in range(0, 10):
      relOrigins[:, i] = origins[:, i] - origins[:, refPhase] + relOrigins[:, refPhase]

    # Absolute motion & max & min motion
    relOrigins = np.vstack([relOrigins, np.zeros([1, 10])])
    for j in range(0, 10):
      amplitude = 0
      for i in range(0, 3):
        #Max
        if relOrigins[i, j] > minmaxAmplitudes[0][i]:
          minmaxAmplitudes[0][i] = relOrigins[i, j]
        #Min
        if relOrigins[i, j] < minmaxAmplitudes[0][i]:
          minmaxAmplitudes[1][i] = relOrigins[i, j]
        amplitude += relOrigins[i, j]*relOrigins[i, j]
      relOrigins[3, j] = np.sqrt(amplitude)
      patient.fourDCT[j].origin = origins[:, i]
      patient.fourDCT[j].relOrigin = relOrigins[:, i]

    #Find & save peak-to-peak amplitudes
    amplitudesTmp = [-1, -1, -1]
    for j in range(0, 3):
      amplitudesTmp[j] = abs(minmaxAmplitudes[0][j] - minmaxAmplitudes[1][j])
      if amplitudesTmp[j] > amplitudes[j]:
        amplitudes[j] = amplitudesTmp[j]
    patient.amplitudes = amplitudes
    patient.minmaxAmplitudes = minmaxAmplitudes
    print amplitudes
    # Plot
    if showPlot:
      self.plotMotion(relOrigins, contourName)

    if contourLabelmap:
      patient.fourDCT[10].contour.SetAndObserveLabelmapImageData(contourLabelmap)

    return minmaxAmplitudes

  def createMidVentilation(self, patient):

    transformLogic = slicer.modules.transforms.logic()
    mathMultiply = vtk.vtkImageMathematics()
    mathAddVector = vtk.vtkImageMathematics()
    mathAddCT = vtk.vtkImageMathematics()

    vectorImageData = vtk.vtkImageData()
    ctImageData = vtk.vtkImageData()

    gridAverageTransform = slicer.vtkOrientedGridTransform()

    refPhase = patient.refPhase

    #Check if midVentilation is already on disk
    if patient.loadMidV(refPhase):
      return

    patient.create4DParameters()


    print "Starting process"

    firstRun = True
    # vector = slicer.vtkMRMLVectorVolumeNode()
    # slicer.mrmlScene.AddNode(vector)
    for i in range(0, 10):

        if i == refPhase:
            continue

        patient.regParameters.referenceNumber = str(i) + "0"
        print "Getting transformation for phase" + str(i) + "0 %"
        if not patient.getVectorField(i):
            print "Can't get vector field for phase " + str(i) + "0 %"
            return

        mathMultiply.RemoveAllInputs()
        mathAddVector.RemoveAllInputs()

        mathMultiply.SetOperationToMultiplyByK()
        mathMultiply.SetConstantK(0.1)


        vectorField = patient.fourDCT[i].vectorField
        mathMultiply.SetInput1Data(vectorField.GetImageData())
        mathMultiply.Modified()
        mathMultiply.Update()

        if firstRun:
            vectorImageData.DeepCopy(mathMultiply.GetOutput())


            matrix = vtk.vtkMatrix4x4()
            vectorField.GetIJKToRASDirectionMatrix(matrix)
            gridAverageTransform.SetGridDirectionMatrix(matrix)

            # vector.SetOrigin(vectorField.GetOrigin())
            # vector.SetSpacing(vectorField.GetSpacing())
            # vector.SetIJKToRASDirectionMatrix(matrix)

            firstRun = False
        else:
            mathAddVector.SetOperationToAdd()
            mathAddVector.SetInput1Data( mathMultiply.GetOutput())
            mathAddVector.SetInput2Data( vectorImageData)
            mathAddVector.Modified()
            mathAddVector.Update()
            vectorImageData.DeepCopy(mathAddVector.GetOutput())

        vectorImageData.SetSpacing(vectorField.GetSpacing())
        vectorImageData.SetOrigin(vectorField.GetOrigin())
        slicer.mrmlScene.RemoveNode(vectorField)
        patient.fourDCT[i].vectorField = None

    # print vector.GetID()
    #
    # vector.SetAndObserveImageData(vectorImageData)
    gridAverageTransform.SetDisplacementGridData(vectorImageData)
    gridAverageTransform.SetInterpolationModeToCubic()
    gridAverageTransform.Inverse()
    gridAverageTransform.Update()
    transformNode = slicer.vtkMRMLGridTransformNode()
    storageNode = slicer.vtkMRMLTransformStorageNode()
    slicer.mrmlScene.AddNode(storageNode)
    transformNode.SetAndObserveStorageNodeID(storageNode.GetID())
    transformNode.SetName('MidV_ref' + str(refPhase))
    slicer.mrmlScene.AddNode(transformNode)
    transformNode.SetAndObserveTransformFromParent(gridAverageTransform)
    # return

    midVCT = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(midVCT)
    midVCT.SetName(patient.name + "_midV_ref"+str(refPhase))

    firstRun = True
    for i in range(0, 10):
        print "Propagating phase " + str(i) + "0 % to midV position."
        patient.regParameters.referenceNumber = str(i) + "0"

        if not patient.loadDicom(i):
            print "Can't get CT for phase " + str(i) + "0 %"
            return

        ctNode = patient.fourDCT[i].node

        if not i == refPhase:
            if not patient.getTransform(i):
                print "Can't get transform for phase " + str(i) + "0 %"
                return
            patient.fourDCT[i].transform.Inverse()
            ctNode.SetAndObserveTransformNodeID(patient.fourDCT[i].transform.GetID())
            if not transformLogic.hardenTransform(ctNode):
                print "Can't harden transform for phase " + str(i) + "0 %"
                return

            slicer.mrmlScene.RemoveNode(patient.fourDCT[i].transform)
            patient.fourDCT[i].transform = None

        # ctNode.ApplyTransform(gridAverageTransform)
        ctNode.SetAndObserveTransformNodeID(transformNode.GetID())
        if not transformLogic.hardenTransform(ctNode):
            print "Can't harden transform for phase " + str(i) + "0 %"
            return

        mathMultiply.RemoveAllInputs()
        mathAddCT.RemoveAllInputs()

        mathMultiply.SetOperationToMultiplyByK()
        mathMultiply.SetConstantK(0.1)

        mathMultiply.SetInput1Data(ctNode.GetImageData())

        mathMultiply.Modified()
        mathMultiply.Update()

        if firstRun:
          ctImageData.DeepCopy(mathMultiply.GetOutput())
          midVCT.SetSpacing(ctNode.GetSpacing())
          midVCT.SetOrigin(ctNode.GetOrigin())

          matrix = vtk.vtkMatrix4x4()
          ctNode.GetIJKToRASDirectionMatrix(matrix)
          midVCT.SetIJKToRASDirectionMatrix(matrix)
          firstRun = False
        else:
          mathAddCT.SetOperationToAdd()
          mathAddCT.SetInput1Data( mathMultiply.GetOutput())
          mathAddCT.SetInput2Data( ctImageData)
          mathAddCT.Modified()
          mathAddCT.Update()
          ctImageData.DeepCopy(mathAddCT.GetOutput())

        slicer.mrmlScene.RemoveNode(ctNode)
        patient.fourDCT[i].node = None


    midVCT.SetAndObserveImageData(ctImageData)
    patient.midVentilation.node = midVCT

    #Save midVCT

    slicer.util.saveNode(midVCT, patient.patientDir + "/" + midVCT.GetName() + ".nrrd")

    #Save transformation as vector field (it crashes when saving as transform)
    transformLogic = slicer.modules.transforms.logic()
    if not patient.loadDicom(refPhase):
      print "Can't get CT for phase " + str(i) + "0 %"
      return
    vf = transformLogic.CreateDisplacementVolumeFromTransform(transformNode, patient.fourDCT[refPhase].node, False)
    slicer.mrmlScene.RemoveNode(patient.fourDCT[refPhase].node)
    patient.fourDCT[refPhase].node = None
    slicer.util.saveNode(vf,patient.vectorDir + "/" + vf.GetName() + ".nrrd")
    slicer.mrmlScene.RemoveNode(vf)



  def createMidVentilationFromPlanningCT(self, patient):

    mathMultiply = vtk.vtkImageMathematics()
    mathAddVector = vtk.vtkImageMathematics()

    vectorImageData = vtk.vtkImageData()

    gridAverageTransform = slicer.vtkOrientedGridTransform()

    refPhase = patient.refPhase

    #Check if midVentilation is already on disk
    if patient.loadMidV(10):
      return

    print "Starting process"

    firstRun = True
    # vector = slicer.vtkMRMLVectorVolumeNode()
    # slicer.mrmlScene.AddNode(vector)
    for i in range(0, 10):
        patient.refPhase = i
        patient.createPlanParameters()
        print "Getting transformation for phase" + str(i) + "0 %"
        if not patient.getVectorField(i):
            print "Can't get vector field for phase " + str(i) + "0 %"
            continue

        mathMultiply.RemoveAllInputs()
        mathAddVector.RemoveAllInputs()

        mathMultiply.SetOperationToMultiplyByK()
        mathMultiply.SetConstantK(0.1)


        vectorField = patient.fourDCT[i].vectorField
        mathMultiply.SetInput1Data(vectorField.GetImageData())
        mathMultiply.Modified()
        mathMultiply.Update()

        if firstRun:
            vectorImageData.DeepCopy(mathMultiply.GetOutput())
            matrix = vtk.vtkMatrix4x4()
            vectorField.GetIJKToRASDirectionMatrix(matrix)
            gridAverageTransform.SetGridDirectionMatrix(matrix)
            firstRun = False
        else:
            mathAddVector.SetOperationToAdd()
            mathAddVector.SetInput1Data( mathMultiply.GetOutput())
            mathAddVector.SetInput2Data( vectorImageData)
            mathAddVector.Modified()
            mathAddVector.Update()
            vectorImageData.DeepCopy(mathAddVector.GetOutput())

        vectorImageData.SetSpacing(vectorField.GetSpacing())
        vectorImageData.SetOrigin(vectorField.GetOrigin())
        slicer.mrmlScene.RemoveNode(vectorField)
        patient.fourDCT[i].vectorField = None

    # print vector.GetID()
    #
    # vector.SetAndObserveImageData(vectorImageData)
    gridAverageTransform.SetDisplacementGridData(vectorImageData)
    gridAverageTransform.SetInterpolationModeToCubic()
    gridAverageTransform.Inverse()
    gridAverageTransform.Update()
    transformNode = slicer.vtkMRMLGridTransformNode()
    slicer.mrmlScene.AddNode(transformNode)
    transformNode.SetAndObserveTransformFromParent(gridAverageTransform)
    # return

    # midVCT = slicer.vtkMRMLScalarVolumeNode()
    # slicer.mrmlScene.AddNode(midVCT)
    # midVCT.SetName(patient.name + "_midV_ref"+str(refPhase))

  def registerMidV(self, patient):
    if not patient.loadMidV(patient.refPhase):
      print "Can't get mid ventilation."

    patient.createPlanParameters()
    patient.regParameters.referenceNumber = "MidV_ref" + str(patient.refPhase)

    if patient.getTransform(11):
      print "Mid Ventilation transform loaded."
      return

    if not patient.loadDicom(10):
      print "Can't get planning CT."
      return

    print "Starting registration."
    patient.regParameters.movingNode = patient.fourDCT[10].node.GetID()
    patient.regParameters.referenceNode = patient.midVentilation.node.GetID()
    patient.regParameters.register()

    print "Registration finished"

  def createAverageFrom4DCT(self,patient):
    mathMultiply = vtk.vtkImageMathematics()
    mathAddCT = vtk.vtkImageMathematics()
    ctImageData = vtk.vtkImageData()

    print "Starting process"
    midVCT = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(midVCT)
    midVCT.SetName(patient.name + "average4DCT")
    firstRun = True
    for i in range(0, 10):
        if not patient.loadDicom(i):
            print "Can't get CT for phase " + str(i) + "0 %"
            return
        ctNode = patient.fourDCT[i].node
        mathMultiply.RemoveAllInputs()
        mathAddCT.RemoveAllInputs()
        mathMultiply.SetOperationToMultiplyByK()
        mathMultiply.SetConstantK(0.1)
        mathMultiply.SetInput1Data(ctNode.GetImageData())
        mathMultiply.Modified()
        mathMultiply.Update()

        if firstRun:
          ctImageData.DeepCopy(mathMultiply.GetOutput())
          midVCT.SetSpacing(ctNode.GetSpacing())
          midVCT.SetOrigin(ctNode.GetOrigin())

          matrix = vtk.vtkMatrix4x4()
          ctNode.GetIJKToRASDirectionMatrix(matrix)
          midVCT.SetIJKToRASDirectionMatrix(matrix)
          firstRun = False
        else:
          mathAddCT.SetOperationToAdd()
          mathAddCT.SetInput1Data(mathMultiply.GetOutput())
          mathAddCT.SetInput2Data(ctImageData)
          mathAddCT.Modified()
          mathAddCT.Update()
          ctImageData.DeepCopy(mathAddCT.GetOutput())

        slicer.mrmlScene.RemoveNode(ctNode)
        patient.fourDCT[i].node = None
    midVCT.SetAndObserveImageData(ctImageData)

  def createPTV(self, patient, SSigma, Rsigma, keepAmplitudes, axisOfMotion):
    import vtkSlicerContourMorphologyModuleLogic
    from vtkSlicerContoursModuleMRML import vtkMRMLContourNode

    # First we need planning CT for reference
    if not patient.loadDicom(10):
        print "Can't get planning CT."
        return

    ## Propagate Contour from Plan to MidV:
    # contour = self.propagateContour(patient, 11, True)
    # if contour is None:
    #   print "Can't get contour."
    #   return
    # patient.fourDCT[10].contour = contour

    contour = patient.fourDCT[10].contour
    #Calculate motion
    if not keepAmplitudes:
      self.calculateMotion(patient, True, False, axisOfMotion, True)
    #Create contourmorphology node and set parameters
    cmNode = vtkSlicerContourMorphologyModuleLogic.vtkMRMLContourMorphologyNode()
    cmLogic = vtkSlicerContourMorphologyModuleLogic.vtkSlicerContourMorphologyModuleLogic()

    slicer.mrmlScene.AddNode(cmNode)
    cmNode.SetScene(slicer.mrmlScene)
    cmNode.SetAndObserveReferenceVolumeNode(patient.fourDCT[10].node)
    cmNode.SetOperation(cmNode.Expand)
    cmNode.SetAndObserveContourANode(contour)

    cmLogic.SetAndObserveContourMorphologyNode(cmNode)
    cmLogic.SetAndObserveMRMLScene(slicer.mrmlScene)

    if not patient.calculatePTVmargins(SSigma, Rsigma):
      print "Can't calculate margins."
      return

    cmNode.SetXSize(patient.ptvMargins[0])
    cmNode.SetYSize(patient.ptvMargins[1])
    cmNode.SetZSize(patient.ptvMargins[2])
    cmLogic.MorphContour()

    print patient.ptvMargins
    #Find newly created contour and rename it

    ptv = slicer.util.getNode('Expanded*Contour')
    if not ptv:
      print "Can't find PTV contour"
      return

    name = patient.name + "_PTV_S" + str(SSigma) + "_s" + str(Rsigma)
    name = slicer.mrmlScene.GenerateUniqueName(name)
    ptv.SetName(name)

    print "Done creating PTV."

  def setColorAndThickness(self, contour):
    if not contour:
      print "No Contour was set."
      return

    index = contour.GetName().find('_Contour')
    if index < 0:
      print "Can't find name of contour"
      return

    contourName = contour.GetName()[0:index]
    ribbonNode = slicer.util.getNode(contourName + '*Ribbon*')
    closedNode = slicer.util.getNode(contourName + '*Closed*')

    if not closedNode:
      print "No closed surface node was set for " + contourName
      return

    #Set thickness
    closedNode.SetSliceIntersectionThickness(3)

    #Set color; Either copy it or set new one
    if ribbonNode:
      closedNode.SetColor(ribbonNode.GetColor())
    else:
      closedNode.SetColor([1, 1, 0])


  def createITV(self,patient, skipPlanRegistration, showContours):
    #TODO: Doesn't work, needs fixing.
    import vtkSlicerContourMorphologyModuleLogic
    from vtkSlicerContoursModuleMRML import vtkMRMLContourNode

    # First we need planning CT for reference
    if not patient.loadDicom(10):
        print "Can't get planning CT."
        return

    #Create contourmorphology node and set parameters
    cmNode = vtkSlicerContourMorphologyModuleLogic.vtkMRMLContourMorphologyNode()
    cmLogic = vtkSlicerContourMorphologyModuleLogic.vtkSlicerContourMorphologyModuleLogic()

    slicer.mrmlScene.AddNode(cmNode)
    cmNode.SetScene(slicer.mrmlScene)
    cmNode.SetAndObserveReferenceVolumeNode(patient.fourDCT[10].node)
    cmNode.SetOperation(cmNode.Union)

    cmLogic.SetAndObserveContourMorphologyNode(cmNode)
    cmLogic.SetAndObserveMRMLScene(slicer.mrmlScene)

    refPhase = patient.refPhase

    if skipPlanRegistration:
        contour = patient.fourDCT[10].contour
    else:
        #Propagate contour
        contour = self.propagateContour(patient, 10, showContours)
        if contour is None:
            print "Can't propagate contour to reference phase."

    patient.fourDCT[refPhase].contour = contour

    # Create contour node
    itv = vtkMRMLContourNode()
    slicer.mrmlScene.AddNode(itv)
    itv.DeepCopy(contour)
    itv.SetName(patient.name + "_ITV")
    self.setDisplayNode(itv)

    cmNode.SetAndObserveContourANode(itv)
    cmNode.SetAndObserveOutputContourNode(itv)

    # Propagation in 4D
    # TODO: Add option to display contours, otherwise delete nodes
    for i in range(0,10):
      print "We are at phase " + str(i)
      if i == refPhase:
        continue
      #Create & propagate contour
      contour = self.propagateContour(patient, i, showContours)
      if contour is None:
          print "Can't propagate contour for phase " + str(i) +"0 %"
          continue

      patient.fourDCT[i].contour = contour
      cmNode.SetAndObserveContourBNode(contour)

      if not showContours:
          slicer.mrmlScene.RemoveNode(contour)
          patient.fourDCT[i].contour = None

    if not showContours:
        slicer.mrmlScene.RemoveNode(patient.fourDCT[refPhase].contour)
        patient.fourDCT[refPhase].contour = None

  def propagateContour(self, patient, position, showContours, contour = None, parentNodeID = ""):
    from vtkSlicerContoursModuleMRML import vtkMRMLContourNode
    transformLogic = slicer.modules.transforms.logic()

    if position == 10 or position == 11:
      patient.createPlanParameters()
      if position == 11:
        patient.regParameters.referenceNumber = "MidV_ref" + str(patient.refPhase)
    else:
      patient.create4DParameters()
      patient.regParameters.referenceNumber = str(position) + "0"

    if not patient.getTransform(position):
      print "Can't load transform"
      return None

    if position == 11:
      bspline = patient.midVentilation.transform
    else:
      bspline = patient.fourDCT[position].transform

    transform = vtk.vtkGeneralTransform()
    bspline.GetTransformToWorld(transform)
    transform.Update()

    # Load contour
    if contour is None:
      contour = vtkMRMLContourNode()
      if position == 10 or position == 11:
        contour.DeepCopy(patient.fourDCT[10].contour)
        if position == 11:
          contour.SetName(patient.fourDCT[10].contour.GetName() + "_midV")
        else:
          contour.SetName(patient.fourDCT[10].contour.GetName() + "_refPosition")
      else:
        contour.DeepCopy(patient.fourDCT[patient.refPhase].contour)
        contour.SetName(patient.fourDCT[patient.refPhase].contour.GetName() + "_phase" + str(position))
          
      slicer.mrmlScene.AddNode(contour)

      if showContours:
        self.setDisplayNode(contour)
        #Create subject hierarchy and add to contour set
        if len(parentNodeID) > 0:
          contourName = contour.GetName().replace("_Contour", "_SubjectHierarchy")
          subjectHierarchyNode = slicer.vtkMRMLSubjectHierarchyNode()
          subjectHierarchyNode.SetName(contourName)
          subjectHierarchyNode.SetLevel('SubSeries')
          # subjectHierarchyNode.SetAttribute('Directory',ctDirectory)
          slicer.mrmlScene.AddNode(subjectHierarchyNode)
          subjectHierarchyNode.SetParentNodeID(parentNodeID)
          subjectHierarchyNode.SetAssociatedNodeID(contour.GetID())

    contour.SetAndObserveTransformNodeID(bspline.GetID())
    if not transformLogic.hardenTransform(contour):
        print "Can't harden transform."
        slicer.mrmlScene.RemoveNode(bspline)
        return None

    slicer.mrmlScene.RemoveNode(bspline)
    return contour

  def setDisplayNode(self, contour, parentHierarchy = None):
      from vtkSlicerContoursModuleMRML import vtkMRMLContourModelDisplayNode

      if contour is None:
          print "No input contour"
          return
      contour.RemoveAllDisplayNodeIDs()
      displayNode = vtkMRMLContourModelDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
      contour.SetAndObserveDisplayNodeID(displayNode.GetID())
      contour.CreateRibbonModelDisplayNode()

  def getCenterOfMass(self,contour):
      comFilter = vtk.vtkCenterOfMass()
      comFilter.SetInputData(contour.GetRibbonModelPolyData())
      comFilter.SetUseScalarsAsWeights(False)
      comFilter.Update()
      return comFilter.GetCenter()

  def plotMotion(self, relOrigins, contourName):
    ln = slicer.util.getNode(pattern='vtkMRMLLayoutNode*')
    ln.SetViewArrangement(25)

    # Get the first ChartView node
    cvn = slicer.util.getNode(pattern='vtkMRMLChartViewNode*')

    # Create arrays of data
    dn = {}
    for i in range(0, 4):
      dn[i] = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
      a = dn[i].GetArray()
      a.SetNumberOfTuples(10)
      for j in range(0,10):
        a.SetComponent(j, 0, j)
        a.SetComponent(j, 1, relOrigins[i, j])
        a.SetComponent(j, 2, 0)

    # Create the ChartNode,
    cn = slicer.mrmlScene.AddNode(slicer.vtkMRMLChartNode())

    # Add data to the Chart
    cn.AddArray('L-R', dn[0].GetID())
    cn.AddArray('A-P', dn[1].GetID())
    cn.AddArray('I-S', dn[2].GetID())
    cn.AddArray('abs', dn[3].GetID())

    # Configure properties of the Chart
    cn.SetProperty('default', 'title','Relative ' + contourName + ' motion')
    cn.SetProperty('default', 'xAxisLabel', 'phase')
    cn.SetProperty('default', 'yAxisLabel', 'position [mm]')
    cn.SetProperty('default', 'showGrid', 'on')
    cn.SetProperty('default', 'xAxisPad', '1')
    cn.SetProperty('default', 'showMarkers', 'on')

    cn.SetProperty('L-R', 'color', '#0000ff')
    cn.SetProperty('A-P', 'color', '#00ff00')
    cn.SetProperty('I-S', 'color', '#ff0000')
    cn.SetProperty('abs', 'color', '#000000')

    # Set the chart to display
    cvn.SetChartNodeID(cn.GetID())

  def findAxisOfMotion(self, origins):
    #Following guide from: http://sebastianraschka.com/Articles/2014_pca_step_by_step.html

    #scale factor for better display:
    scale = 100

    #Calculate mean position
    meanVector = [0, 0 ,0]
    for i in range(3):
      meanVector[i] = np.mean(origins[i, :])

    print origins
    print meanVector
    #Computing covariance matrix
    convMatrix = np.cov([origins[0, :], origins[1, :], origins[2, :]])
    print('Covariance Matrix:\n', convMatrix)
    # for i in range(origins.shape[1]):
    #   scatter_matrix += (origins[: ,i].reshape(3, 1) - meanVector).dot((origins[:, i].reshape(3, 1) - meanVector).T)

    #Get eigenvectors
    eig_val, eig_vec = np.linalg.eig(convMatrix)
    for i in range(len(eig_vec)):
      print "Eigen vector " + str(i+1)
      print eig_vec[i]
      print "Eigen value " + str(i+1)
      print eig_val[i]

    # Make a list of (eigenvalue, eigenvector) tuples
    eig_pairs = [(np.abs(eig_val[i]), eig_vec[:,i]) for i in range(len(eig_val))]

    # Sort the (eigenvalue, eigenvector) tuples from high to low
    eig_pairs.sort()
    eig_pairs.reverse()
    matrix_w = np.hstack((eig_pairs[0][1].reshape(3, 1),
                          eig_pairs[1][1].reshape(3, 1),
                          eig_pairs[2][1].reshape(3, 1)))
    print('Matrix W:\n', matrix_w)

    #Create linear transform for contour propagation

    vtkMatrix = vtk.vtkMatrix4x4()
    transform = slicer.vtkMRMLLinearTransformNode()
    slicer.mrmlScene.AddNode(transform)

    for i in range(3):
      for j in range(3):
        vtkMatrix.SetElement(j, i, matrix_w[i, j])

    transform.SetAndObserveMatrixTransformFromParent(vtkMatrix)

    #Plot eigenvectors from mean position
    fiducials = slicer.vtkMRMLMarkupsFiducialNode()
    displayNode = slicer.vtkMRMLMarkupsDisplayNode()
	# vtkNew<vtkMRMLMarkupsFiducialStorageNode> wFStorageNode;
    slicer.mrmlScene.AddNode(displayNode)
    slicer.mrmlScene.AddNode(fiducials)
    fiducials.SetAndObserveDisplayNodeID(displayNode.GetID())

    fiducials.AddFiducialFromArray(meanVector, "Mean Position")
    for i in range(len(eig_vec)):
      # fiducials.AddFiducialFromArray(meanVector + scale * eig_vec[i], " P " + str(i+1))
      #Plot ruler
      ruler = slicer.vtkMRMLAnnotationRulerNode()
      displayRuler = slicer.vtkMRMLAnnotationLineDisplayNode()
      displayRuler.SetLabelVisibility(0)
      displayRuler.SetMaxTicks(0)
      displayRuler.SetLineWidth(5)
      slicer.mrmlScene.AddNode(displayRuler)
      slicer.mrmlScene.AddNode(ruler)
      ruler.SetAndObserveDisplayNodeID(displayRuler.GetID())

      ruler.SetPosition1(meanVector)
      ruler.SetPosition2(meanVector + scale * eig_vec[i])

    return matrix_w

  def delayDisplay(self, message, msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

class FindMarginsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_FindMargins1()

  def test_FindMargins1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = FindMarginsLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
