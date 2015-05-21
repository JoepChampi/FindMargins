import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import numpy as np
import RegistrationHierarchy


class Patient():
  def __init__(self):
    self.name = ""
    self.databaseNumber = 0
    self.structureSet = self.dicom()
    self.fourDCT = {}
    for i in range(0,11):
      self.fourDCT[i] = self.dicom() # 0-9 4DCT, 10 Planning CT
    self.targetContour = ""
    self.regParameters = None

  class dicom():
    def __init__(self):
      self.uid = ""
      self.file = ""
      self.node = None
      self.transform = None
      self.contour = None
      self.vectorField = None
      self.origin = [0,0,0]
      self.relOrigin = [0,0,0]

  def loadDicom(self,position):
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    if not self.fourDCT[position].node == None or self.findNode(position):
      return True

    seriesUIDs = [self.fourDCT[position].uid]
    dicomWidget.detailsPopup.offerLoadables(seriesUIDs, 'SeriesUIDList')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()
    if not self.findNode(position):
        print "Can't find Node"
        return False
    return True

  def loadStructureSet(self):
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    if len(self.structureSet.uid) == 0:
      return False

    seriesUIDs = [self.structureSet.uid]
    dicomWidget.detailsPopup.offerLoadables(seriesUIDs, 'SeriesUIDList')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()
    return True

  def createPlanParameters(self,referencePosition,vectorDir):
    self.regParameters = None
    self.regParameters = RegistrationHierarchy.registrationParameters(self.name)
    self.regParameters.vectorDirectory = vectorDir
    self.regParameters.movingNumber = "Plan"
    self.regParameters.referenceNumber = str(referencePosition) + "0"
    self.regParameters.bsplineOn = True
    self.regParameters.stageThreeOn = True

  def create4DParameters(self,referencePosition,vectorDir):
    self.regParameters = None
    self.regParameters = RegistrationHierarchy.registrationParameters(self.name)
    self.regParameters.movingNumber = str(referencePosition) + "0"
    self.regParameters.vectorDirectory = vectorDir
    self.regParameters.bsplineOn = True

  def getTransform(self,position):
    if self.regParameters == None:
      print "No parameters have been set."
      return False
    bsplineName = self.regParameters.checkBspline()
    bspline = slicer.util.getNode(bsplineName)
    if bspline is None:
      success, bspline = slicer.util.loadTransform(self.regParameters.bspline_F_name, returnNode=True)
      if not success:
        print "Can't load " + self.regParameters.bspline_F_name
        return False

    self.fourDCT[position].transform = bspline
    return True

  def getVectorField(self,position):
      transformLogic = slicer.modules.transforms.logic()

      #First check if vector field already exist on disk, if not then create it
      vfName = self.regParameters.checkVf()
      if len(vfName) > 0:

          vf = self.findVectorNode(vfName)

          if vf is None:
            success, vf = slicer.util.loadVolume(self.regParameters.vf_F_name, properties = {'name' : vfName}, returnNode=True)
            if not success:
                print "Can't load " + self.regParameters.vf_F_name
                return False
            vf = self.findVectorNode(vfName)

      else:
          if self.fourDCT[position].node is None:
            if not self.loadDicom(position):
              print "Can't load phase" + str(position) + "0%"
              return False
          if not self.getTransform(position):
              print "Can't load transform"
              return False
          transform = self.fourDCT[position].transform
          node = self.fourDCT[position].node

          vf = transformLogic.CreateDisplacementVolumeFromTransform(transform,node,False)

          if vf is not None:
              slicer.util.saveNode(vf,self.regParameters.vf_F_name)
              slicer.mrmlScene.RemoveNode(node)
              slicer.mrmlScene.RemoveNode(transform)

              self.fourDCT[position].transform = None
              self.fourDCT[position].node = None
          else:
              print "Can't generate vf."
              return False

      self.fourDCT[position].vectorField = vf
      return True

  def findNode(self,position):
    finalNode = ""
    if position == 0:
      string = " 0.0%"
    elif position == 10: #Special case, if we need to find planning CT
      string = "Unknown"
    else:
      string = " " + str(position) + "0.0%"
    nodes = slicer.util.getNodes('vtkMRMLScalarVolumeNode*')
    for node in nodes:
      if node.find(string) > -1:
        self.fourDCT[position].node = nodes[node]
        return True

    return False

  def findVectorNode(self,name):
    nodes = slicer.util.getNodes('vtkMRMLVectorVolumeNode*')
    for node in nodes:
        if node.find(name) > -1:
            return nodes[node]

    return None


