#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import os.path
import os
import platform
import re
import sys
import json
import xlrd

from functools import partial
from collections import defaultdict
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


import resources
# Add internal libs
from libs.constants import *
from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut, generateColorByText
from libs.settings import Settings
from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from libs.canvas import Canvas
from libs.zoomWidget import ZoomWidget
from libs.labelDialog import LabelDialog
from libs.colorDialog import ColorDialog
from libs.labelFile import LabelFile, LabelFileError
from libs.toolBar import ToolBar
from libs.pascal_voc_io import PascalVocReader
from libs.pascal_voc_io import XML_EXT
from libs.yolo_io import YoloReader
from libs.yolo_io import TXT_EXT
from libs.ustr import ustr
from libs.compare import Compare
from libs.save import Save
from libs.templateDialog import TemplateDialog

__appname__ = 'PCB板差异识别系统'

# Utility functions and classes.

def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))

def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar


# PyQt5: TypeError: unhashable type: 'QListWidgetItem'
class HashableQListWidgetItem(QListWidgetItem):

    def __init__(self, *args):
        super(HashableQListWidgetItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))


class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None, defaultSaveDir=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Load setting in the main thread
        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        # Save as Pascal voc xml
        self.defaultSaveDir = defaultSaveDir
        self.usingPascalVocFormat = True
        self.usingYoloFormat = False

        # For loading all image under a directory
        self.mImgList = []
        self.mImgList2 = []
        self.dirname = None
        self.labelHist = []
        self.lastOpenDir = None
        self.lastOpenDir2 = None
        # Whether we need to save or not.
        self.dirty = False

        self._noSelectionSlot = False
        self._beginner = True
        self.ExcelPath = '.\excel'
        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)
        self.templateDialog = TemplateDialog(parent=self, listItem=[])
        self.openFlie = ""
        self.itemsToShapes = {}
        self.shapesToItems = {}
        self.itemToItem2 = {}
        self.item2ToItem = {}
        self.itemsCount = 0
        self.prevLabelText = ''

        listLayout = QVBoxLayout()
        listLayout.setContentsMargins(0, 0, 0, 0)

        # Create a widget for using default label
        # self.useDefaultLabelCheckbox = QCheckBox(u'使用默认标签')
        # self.useDefaultLabelCheckbox.setChecked(False)
        # self.defaultLabelTextLine = QLineEdit()
        useDefaultLabelQHBoxLayout = QHBoxLayout()
        # useDefaultLabelQHBoxLayout.addWidget(self.useDefaultLabelCheckbox)
        # useDefaultLabelQHBoxLayout.addWidget(self.defaultLabelTextLine)
        useDefaultLabelContainer = QWidget()
        useDefaultLabelContainer.setLayout(useDefaultLabelQHBoxLayout)

        # Create a widget for edit and diffc button
        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Add some of widgets to listLayout
        listLayout.addWidget(self.editButton)
        listLayout.addWidget(useDefaultLabelContainer)

        # Create and add a widget for showing current label items
        self.labelList = QListWidget()
        self.labelList2 = QListWidget()
        labelListContainer = QWidget()
        labelListContainer.setLayout(listLayout)
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList2.itemActivated.connect(self.labelSelectionChanged2)
        self.labelList2.itemSelectionChanged.connect(self.labelSelectionChanged2)
        # self.labelList.itemDoubleClicked.connect(self.editLabel)
        # Connect to itemChanged to detect checkbox changes.
        self.labelList.itemChanged.connect(self.labelItemChanged)
        self.labelList2.itemChanged.connect(self.labelItemChanged2)

        splitter2 = QSplitter(Qt.Vertical)
        splitter2.addWidget(self.labelList)
        splitter2.addWidget(self.labelList2)

        listLayout.addWidget(splitter2)

        self.dock = QDockWidget(u'标签列表', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(labelListContainer)

        # Tzutalin 20160906 : Add file list and dock to move faster
        self.fileListWidget = QListWidget()
        self.fileListWidget.itemDoubleClicked.connect(self.fileitemDoubleClicked)
        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)
        filelistLayout.addWidget(self.fileListWidget)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)

        self.fileListWidget2 = QListWidget()
        self.fileListWidget2.itemDoubleClicked.connect(self.fileitemDoubleClicked2)
        filelistLayout2 = QVBoxLayout()
        filelistLayout2.setContentsMargins(0, 0, 0, 0)
        filelistLayout2.addWidget(self.fileListWidget2)
        fileListContainer2 = QWidget()
        fileListContainer2.setLayout(filelistLayout2)

        splitter3 = QSplitter(Qt.Vertical)
        splitter3.addWidget(fileListContainer)
        splitter3.addWidget(fileListContainer2)

        self.filedock = QDockWidget(u'文件列表', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(splitter3)

        self.zoomWidget = ZoomWidget()
        self.colorDialog = ColorDialog(parent=self)

        self.canvas = Canvas(parent=self)
        self.canvas.zoomRequest.connect(self.zoomRequest)
        self.canvas.setDrawingShapeToSquare(settings.get(SETTING_DRAW_SQUARE, False))
        self.canvas2 = Canvas(parent=self)
        self.canvas2.zoomRequest.connect(self.zoomRequest)
        self.canvas2.setDrawingShapeToSquare(settings.get(SETTING_DRAW_SQUARE, False))

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        scroll2 = QScrollArea()
        scroll2.setWidget(self.canvas2)
        scroll2.setWidgetResizable(True)
        self.scrollBars2 = {
            Qt.Vertical: scroll2.verticalScrollBar(),
            Qt.Horizontal: scroll2.horizontalScrollBar()
        }

        self.scrollArea = scroll
        self.scrollArea2 = scroll2
        self.canvas.scrollRequest.connect(self.scrollRequest)
        self.canvas2.scrollRequest.connect(self.scrollRequest2)

        self.canvas.newShape.connect(lambda:self.newShape(1))
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        self.canvas2.newShape.connect(lambda:self.newShape(0))
        self.canvas2.shapeMoved.connect(self.setDirty)
        self.canvas2.selectionChanged.connect(self.shapeSelectionChanged2)
        self.canvas2.drawingPolygon.connect(self.toggleDrawingSensitive)

        splitter = QSplitter(Qt.Horizontal)
        # 向Splitter内添加控件
        splitter.addWidget(scroll)
        splitter.addWidget(scroll2)

        self.setCentralWidget(splitter)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        # Tzutalin 20160906 : Add file list and dock to move faster
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)
        self.filedock.setFeatures(QDockWidget.DockWidgetFloatable)

        self.dockFeatures = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)

        # Actions
        action = partial(newAction, self)
        quit = action('&退出', self.close,
                      'Ctrl+Q', 'quit', u'退出系统')

        # open = action('&打开图1', lambda:self.openFile(flag = 1),
        #               'Ctrl+O', 'open', u'Open image or label file')
        #
        open2 = action('&打开图2', lambda:self.openFile(flag = 0),
                      'Ctrl+O', 'open', u'Open image or label file')

        opendir = action('&打开样板文件夹', lambda :self.openDirDialog(flag = 1),
                         None, 'open', u'Open Dir1')

        opendir2 = action('&打开待检测文件夹', lambda :self.openDirDialog(flag = 0),
                         'Ctrl+u', 'open', u'Open Dir1')

        # changeSavedir = action('&改变存储路径', self.changeSavedirDialog,
        #                        'Ctrl+r', 'open', u'Change default saved Annotation dir')

        # openAnnotation = action('&Open Annotation', self.openAnnotationDialog,
        #                         'Ctrl+Shift+O', 'open', u'Open Annotation')

        openNextImg = action('&样板下一张', lambda :self.openNextImg(flag = 1),
                             'd', 'next', u'样板下一张')

        openNextImg2 = action('&检测板下一张', lambda: self.openNextImg(flag = 0),
                             'd', 'next', u'检测板下一张')

        openPrevImg = action('&样板上一张', lambda:self.openPrevImg(flag = 1),
                             'a', 'prev', u'样板上一张')

        openPrevImg2 = action('&检测板上一张', lambda: self.openPrevImg(flag = 0),
                             'a', 'prev', u'检测板上一张')

        comparePCB = action('比较', self.compare,None,'comparePCB',u'比较两张PCB差异')

        # verify = action('&Verify Image', self.verifyImg,
        #                 'space', 'verify', u'Verify Image')

        save = action('&保存', self.saveFile,
                      'Ctrl+S', 'save', u'保存结果', enabled=False)

        openRes = action('&显示结果', self.openRes,
                      None, None, u'显示结果')

        # saveTemplate = action('&保存样本', self.saveTemplate, None,
        #                'save', u'Save Template to file', enabled=False)

        # save_format = action('&PascalVOC', self.change_format,
        #               'Ctrl+', 'format_voc', u'Change save format', enabled=True)

        # saveAs = action('&Save As', self.saveFileAs,
        #                 'Ctrl+Shift+S', 'save-as', u'Save labels to a different file', enabled=False)

        # close = action('&Close', self.closeFile, 'Ctrl+W', 'close', u'Close current file')

        resetAll = action('&恢复出厂设置', self.resetAll, None, 'resetall', u'恢复出厂设置')

        # color1 = action('Box Line Color', self.chooseColor1,
        #                 'Ctrl+L', 'color_line', u'Choose Box line color')

        createMode = action('画框', self.setCreateMode,
                            'w', 'new', u'开始画框', enabled=False)
        editMode = action('&Edit\nRectBox', self.setEditMode,
                          'Ctrl+J', 'edit', u'编辑标签', enabled=False)

        create = action('画框',self.createShape,
                        'w', 'new', u'画框', enabled=False)
        delete = action('删除选中框', self.deleteSelectedShape,
                        'Delete', 'delete', u'删除选中框', enabled=False)
        # copy = action('&Duplicate\nRectBox', self.copySelectedShape,
        #               'Ctrl+D', 'copy', u'Create a duplicate of the selected Box',
        #               enabled=False)

        # advancedMode = action('&Advanced Mode', self.toggleAdvancedMode,
        #                       'Ctrl+Shift+A', 'expert', u'Switch to advanced mode',
        #                       checkable=True)

        hideAll = action('&隐藏框', partial(self.togglePolygons, False),
                         'Ctrl+H', 'hide', u'隐藏所以框',
                         enabled=False)
        showAll = action('&显示框', partial(self.togglePolygons, True),
                         'Ctrl+A', 'hide', u'显示所以框',
                         enabled=False)

        # help = action('&Tutorial', self.showTutorialDialog, None, 'help', u'Show demos')
        # showInfo = action('&Information', self.showInfoDialog, None, 'help', u'Information')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('放大', partial(self.addZoom, 3),
                        'Ctrl++', 'zoom-in', u'放大', enabled=False)
        zoomOut = action('缩小', partial(self.addZoom, -3),
                         'Ctrl+-', 'zoom-out', u'缩小', enabled=False)
        zoomOrg = action('&原尺寸', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'显示原始尺寸', enabled=False)
        fitWindow = action('&适应窗口', self.setFitWindow,
                           'Ctrl+F', 'fit-window', u'适应窗口',
                           checkable=True, enabled=False)
        fitWidth = action('充满窗口', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'充满窗口',
                          checkable=True, enabled=False)
        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&编辑标记', lambda: self.editLabel(),
                      'Ctrl+E', 'edit', u'修改所选框的标签',
                      enabled=False)
        self.editButton.setDefaultAction(edit)

        # shapeLineColor = action('Shape &Line Color', self.chshapeLineColor,
        #                         icon='color_line', tip=u'Change the line color for this specific shape',
        #                         enabled=False)
        # shapeFillColor = action('Shape &Fill Color', self.chshapeFillColor,
        #                         icon='color', tip=u'Change the fill color for this specific shape',
        #                         enabled=False)

        # labels = self.dock.toggleViewAction()
        # labels.setText('Show/Hide Label Panel')
        # labels.setShortcut('Ctrl+Shift+L')

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu)

        # Draw squares/rectangles
        self.drawSquaresOption = QAction('Draw Squares', self)
        self.drawSquaresOption.setShortcut('Ctrl+Shift+R')
        self.drawSquaresOption.setCheckable(True)
        self.drawSquaresOption.setChecked(settings.get(SETTING_DRAW_SQUARE, False))
        self.drawSquaresOption.triggered.connect(self.toogleDrawSquare)

        # Store actions for further handling.
        self.actions = struct(save=save,openRes=openRes,resetAll = resetAll,
                              create=create, delete=delete, edit=edit,
                              createMode=createMode, editMode=editMode,comparePCB = comparePCB,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  opendir, opendir2, save, openRes, resetAll, quit),
                              beginner=(), advanced=(),
                              editMenu=(edit, delete),
                              beginnerContext=(create, edit, delete),
                              advancedContext=(createMode, editMode, edit,
                                               delete),
                              onLoadActive=(
                                    create, createMode, editMode),
                              onShapesPresent=(hideAll, showAll))

        self.menus = struct(
            file=self.menu('&文件'),
            edit=self.menu('&编辑'),
            view=self.menu('&视图'),
            labelList=labelMenu)

        # Auto saving : Enable auto saving if pressing next
        # self.autoSaving = QAction("自动保存", self)
        # self.autoSaving.setCheckable(True)
        # self.autoSaving.setChecked(settings.get(SETTING_AUTO_SAVE, False))
        # Sync single class mode from PR#106
        self.singleClassMode = QAction("Single Class Mode", self)
        self.singleClassMode.setShortcut("Ctrl+Shift+S")
        self.singleClassMode.setCheckable(True)
        self.singleClassMode.setChecked(settings.get(SETTING_SINGLE_CLASS, False))
        self.lastLabel = None
        # Add option to enable/disable labels being painted at the top of bounding boxes
        self.paintLabelsOption = QAction("Paint Labels", self)
        self.paintLabelsOption.setShortcut("Ctrl+Shift+P")
        self.paintLabelsOption.setCheckable(True)
        self.paintLabelsOption.setChecked(settings.get(SETTING_PAINT_LABEL, False))
        self.paintLabelsOption.triggered.connect(self.togglePaintLabelsOption)

        addActions(self.menus.file,
                   (opendir, opendir2, save, openRes, resetAll, quit))
        addActions(self.menus.view, (
            hideAll, showAll, None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        # addActions(self.canvas.menus[1], (
        #     action('&Copy here', self.copyShape),
        #     action('&Move here', self.moveShape)))
        addActions(self.canvas2.menus[0], self.actions.beginnerContext)
        # addActions(self.canvas2.menus[1], (
        #     action('&Copy here', self.copyShape),
        #     action('&Move here', self.moveShape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (
            opendir, opendir2, None, openPrevImg, openPrevImg2, openNextImg, openNextImg2, None, comparePCB, None, save, openRes, None,
            create, delete, None,
            zoomIn, zoom, zoomOut, fitWindow, fitWidth)

        self.actions.advanced = (
            opendir, opendir2, None, openPrevImg, openPrevImg, openNextImg, openNextImg2, None, save, openRes, None,
            createMode, editMode, None,
            hideAll, showAll)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.filePath2 = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        ## Fix the compatible issue for qt4 and qt5. Convert the QStringList to python list
        if settings.get(SETTING_RECENT_FILES):
            if have_qstring():
                recentFileQStringList = settings.get(SETTING_RECENT_FILES)
                self.recentFiles = [ustr(i) for i in recentFileQStringList]
            else:
                self.recentFiles = recentFileQStringList = settings.get(SETTING_RECENT_FILES)

        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = ustr(settings.get(SETTING_SAVE_DIR, None))
        self.lastOpenDir = ustr(settings.get(SETTING_LAST_OPEN_DIR, None))
        self.lastOpenDir2 = ustr(settings.get(SETTING_LAST_OPEN_DIR2, None))
        if self.defaultSaveDir is None and saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.lineColor = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fillColor = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.setDrawingColor(self.lineColor)
        self.canvas2.setDrawingColor(self.lineColor)
        # Add chris
        Shape.difficult = self.difficult

        def xbool(x):
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        if xbool(settings.get(SETTING_ADVANCE_MODE, False)):
            self.toggleAdvancedMode()

        # Populate the File menu dynamically.
        self.updateFileMenu()

        # Since loading the file may take some time, make sure it runs in the background.
        if self.filePath and os.path.isdir(self.filePath):
            self.queueEvent(partial(self.importDirImages, self.filePath or ""))
        elif self.filePath:
            self.queueEvent(partial(self.loadFile, self.filePath or ""))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # Display cursor coordinates at the right of status bar
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)

        # Open Dir if deafult file
        if self.filePath and os.path.isdir(self.filePath):
            self.openDirDialog(dirpath=self.filePath)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.setDrawingShapeToSquare(False)
            self.canvas2.setDrawingShapeToSquare(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            # Draw rectangle if Ctrl is pressed
            self.canvas.setDrawingShapeToSquare(True)
            self.canvas2.setDrawingShapeToSquare(True)

    ## Support Functions ##
    def set_format(self, save_format):
        if save_format == FORMAT_PASCALVOC:
            # self.actions.save_format.setText(FORMAT_PASCALVOC)
            # self.actions.save_format.setIcon(newIcon("format_voc"))
            self.usingPascalVocFormat = True
            self.usingYoloFormat = False
            LabelFile.suffix = XML_EXT

        elif save_format == FORMAT_YOLO:
            # self.actions.save_format.setText(FORMAT_YOLO)
            # self.actions.save_format.setIcon(newIcon("format_yolo"))
            self.usingPascalVocFormat = False
            self.usingYoloFormat = True
            LabelFile.suffix = TXT_EXT

    def change_format(self):
        if self.usingPascalVocFormat: self.set_format(FORMAT_YOLO)
        elif self.usingYoloFormat: self.set_format(FORMAT_PASCALVOC)

    def noShapes(self):
        return not self.itemsToShapes

    def toggleAdvancedMode(self, value=True):
        self._beginner = not value
        self.canvas.setEditing(True)
        self.canvas2.setEditing(True)
        self.populateModeActions()
        self.editButton.setVisible(not value)
        if value:
            self.actions.createMode.setEnabled(True)
            self.actions.editMode.setEnabled(False)
            self.dock.setFeatures(self.dock.features() | self.dockFeatures)
        else:
            self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)

    def populateModeActions(self):
        if self.beginner():
            tool, menu = self.actions.beginner, self.actions.beginnerContext
        else:
            tool, menu = self.actions.advanced, self.actions.advancedContext
        self.tools.clear()
        addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        self.canvas2.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        addActions(self.canvas2.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create,) if self.beginner()\
            else (self.actions.createMode, self.actions.editMode)
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def setBeginner(self):
        self.tools.clear()
        addActions(self.tools, self.actions.beginner)

    def setAdvanced(self):
        self.tools.clear()
        addActions(self.tools, self.actions.advanced)

    def setDirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)

    def setClean(self):
        if self.filePath and self.filePath2:
            self.dirty = False
            self.actions.save.setEnabled(False)
            self.actions.create.setEnabled(True)

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self,flag = None):
        self.itemsToShapes.clear()
        self.shapesToItems.clear()
        self.itemToItem2.clear()
        self.item2ToItem.clear()
        if flag == 3:
            self.labelList.clear()
            self.filePath = None
            self.labelList2.clear()
            self.filePath2 = None
        elif flag:
            self.labelList.clear()
            self.filePath = None
        else:
            self.labelList2.clear()
            self.filePath2 = None
        self.imageData = None
        self.labelFile = None
        if flag:
            self.canvas.resetState()
        else:
            self.canvas2.resetState()
        self.labelCoordinates.clear()

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def currentItem2(self):
        items = self.labelList2.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filePath):
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def beginner(self):
        return self._beginner

    def advanced(self):
        return not self.beginner()


    def createShape(self):
        assert self.beginner()
        if self.filePath and self.filePath2:
            self.canvas.setEditing(False)
            self.canvas2.setEditing(False)
            self.actions.create.setEnabled(False)
        else:
            QMessageBox.warning(self, "警告", "请打开两张图再画框", QMessageBox.Yes)

    def toggleDrawingSensitive(self, drawing=True):
        """In the middle of drawing, toggling between modes should be disabled."""
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            print('Cancel creation.')
            self.canvas.setEditing(True)
            self.canvas.restoreCursor()
            self.canvas2.setEditing(True)
            self.canvas2.restoreCursor()
            self.actions.create.setEnabled(True)

    def toggleDrawMode(self, edit=True):
        self.canvas.setEditing(edit)
        self.canvas2.setEditing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def setCreateMode(self):
        assert self.advanced()
        self.toggleDrawMode(False)

    def setEditMode(self):
        assert self.advanced()
        self.toggleDrawMode(True)
        self.labelSelectionChanged()

    def updateFileMenu(self):
        return
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = newIcon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def editLabel(self):
        if not self.canvas.editing():
            return
        item = self.currentItem()
        item2 = self.currentItem2()
        if item and item2:
            self.labelDialog.listItem = self.labelHist
            text1, text2 = self.labelDialog.popUp(item.text(), item2.text())
            # print(text1,text2)
            if text1 and text2:
                item.setText(text1)
                item.setBackground(generateColorByText(text1))
                item2.setText(text2)
                item2.setBackground(generateColorByText(text2))
                self.setDirty()
            elif (not text1) and (not text2):
                return
            else:
                QMessageBox.warning(self, "警告", "请输入两个标记！", QMessageBox.Yes)
        else:
            QMessageBox.warning(self, "警告", "请选中两个标记！", QMessageBox.Yes)
            return

    # Tzutalin 20160906 : Add file list and dock to move faster
    def fileitemDoubleClicked(self, item=None):
        currIndex = self.mImgList.index(ustr(item.text()))
        if currIndex < len(self.mImgList):
            filename = self.mImgList[currIndex]
            if filename:
                self.loadFile(filename, 1)

    def fileitemDoubleClicked2(self, item=None):
        currIndex = self.mImgList2.index(ustr(item.text()))
        if currIndex < len(self.mImgList2):
            filename = self.mImgList2[currIndex]
            if filename:
                self.loadFile(filename, 0)

    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape:
                self.shapesToItems[shape].setSelected(True)
            else:
                self.labelList.clearSelection()

        self.actions.delete.setEnabled(selected)
        # self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)

    def shapeSelectionChanged2(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas2.selectedShape
            if shape:
                self.shapesToItems[shape].setSelected(True)
            else:
                self.labelList2.clearSelection()
        self.actions.delete.setEnabled(selected)
        # self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)

    def addLabel(self, shape, flag):
        shape.paintLabel = self.paintLabelsOption.isChecked()
        item = HashableQListWidgetItem(shape.label)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setBackground(generateColorByText(shape.label))
        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item
        if flag:
            self.labelList.addItem(item)
        else:
            self.labelList2.addItem(item)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)
        return item

    def remLabel(self, shape):
        if shape is None:
            # print('rm empty label')
            return
        item = self.shapesToItems[shape]
        self.labelList.takeItem(self.labelList.row(item))
        del self.shapesToItems[shape]
        del self.itemsToShapes[item]

    def remLabel2(self, shape):
        if shape is None:
            # print('rm empty label')
            return
        item = self.shapesToItems[shape]
        self.labelList2.takeItem(self.labelList2.row(item))
        del self.shapesToItems[shape]
        del self.itemsToShapes[item]

    def loadLabels(self, shapes, flag = None):
        s = []
        items = []
        for label, points, line_color, fill_color, difficult in shapes:
            shape = Shape(label=label)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.difficult = difficult
            shape.close()
            s.append(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = generateColorByText(label)

            if fill_color:
                shape.fill_color = QColor(*fill_color)
            else:
                shape.fill_color = generateColorByText(label)
            item = self.addLabel(shape, flag)
            items.append(item)

        if flag:
            self.canvas.loadShapes(s)
            return items
        else:
            self.canvas2.loadShapes(s)
            return items

    def saveLabels(self, annotationFilePath, flag = None):
        annotationFilePath = ustr(annotationFilePath)
        if self.labelFile is None:
            self.labelFile = LabelFile()
            if flag:
                self.labelFile.verified = self.canvas.verified
            else:
                self.labelFile.verified = self.canvas2.verified

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                       # add chris
                        difficult = s.difficult)
        if flag:
            shapes = [format_shape(shape) for shape in self.canvas.shapes]
            filePath = self.filePath
        else:
            shapes = [format_shape(shape) for shape in self.canvas2.shapes]
            filePath = self.filePath2
        # for shape in shapes:
        #     print(shape['points'])
        # Can add differrent annotation formats here
        try:
            if self.usingPascalVocFormat is True:
                if ustr(annotationFilePath[-4:]) != ".xml":
                    annotationFilePath += XML_EXT
                # print ('Img: ' + self.filePath + ' -> Its xml: ' + annotationFilePath)
                self.labelFile.savePascalVocFormat(annotationFilePath, shapes, filePath, self.imageData,
                                                   self.lineColor.getRgb(), self.fillColor.getRgb())
            elif self.usingYoloFormat is True:
                if annotationFilePath[-4:] != ".txt":
                    annotationFilePath += TXT_EXT
                # print ('Img: ' + self.filePath + ' -> Its txt: ' + annotationFilePath)
                self.labelFile.saveYoloFormat(annotationFilePath, shapes, self.filePath, self.imageData, self.labelHist,
                                                   self.lineColor.getRgb(), self.fillColor.getRgb())
            else:
                self.labelFile.save(annotationFilePath, shapes, self.filePath, self.imageData,
                                    self.lineColor.getRgb(), self.fillColor.getRgb())
            return True
        except LabelFileError as e:
            self.errorMessage(u'Error saving label data', u'<b>%s</b>' % e)
            return False

    def copySelectedShape(self):
        self.addLabel(self.canvas.copySelectedShape())
        # fix copy and delete
        self.shapeSelectionChanged(True)

    def labelSelectionChanged(self):
        self.labelList2.itemActivated.disconnect()
        self.labelList2.itemSelectionChanged.disconnect()
        item = self.currentItem()
        if item and self.canvas.editing():
            try:
                item2 = self.itemToItem2[item]
            except:
                item2 = None
            if item2:
                self._noSelectionSlot = True
                self.canvas.selectShape(self.itemsToShapes[item])
                self.canvas2.selectShape(self.itemsToShapes[item2])
                shape = self.itemsToShapes[item]
        else:
            if self.itemsCount == self.labelList.count():
                self.canvas2.deSelectShape()
        self.labelList2.itemActivated.connect(self.labelSelectionChanged2)
        self.labelList2.itemSelectionChanged.connect(self.labelSelectionChanged2)

    def labelSelectionChanged2(self):
        self.labelList.itemActivated.disconnect()
        self.labelList.itemSelectionChanged.disconnect()
        item2 = self.currentItem2()
        if item2 and self.canvas2.editing():
            try:
                item = self.item2ToItem[item2]
            except:
                item = None
            if item:
                self._noSelectionSlot = True
                self.canvas2.selectShape(self.itemsToShapes[item2])
                self.canvas.selectShape(self.itemsToShapes[item])
                shape = self.itemsToShapes[item2]
        else:
            if self.itemsCount == self.labelList.count():
                self.canvas.deSelectShape()
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)

    def labelItemChanged(self, item):
        shape = self.itemsToShapes[item]
        label = item.text()
        if label != shape.label:
            shape.label = item.text()
            shape.line_color = generateColorByText(shape.label)
            self.setDirty()
        else:  # User probably changed item visibility
            self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelItemChanged2(self, item):
        shape = self.itemsToShapes[item]
        label = item.text()
        if label != shape.label:
            shape.label = item.text()
            shape.line_color = generateColorByText(shape.label)
            self.setDirty()
        else:  # User probably changed item visibility
            self.canvas2.setShapeVisible(shape, item.checkState() == Qt.Checked)

    # Callback functions:
    def newShape(self,flag):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        # if not self.useDefaultLabelCheckbox.isChecked() or not self.defaultLabelTextLine.text():
        if len(self.labelHist) > 0:
            self.labelDialog = LabelDialog(
                parent=self, listItem=self.labelHist)

        # Sync single class mode from PR#106
        if self.singleClassMode.isChecked() and self.lastLabel:
            text = self.lastLabel
        else:
            text, text2 = self.labelDialog.popUp(text=self.prevLabelText, text2=self.prevLabelText)
            self.lastLabel = text

        # Add Chris
        if text and text2:
            self.prevLabelText = text
            generate_color = generateColorByText(text)
            if flag:
                shape = self.canvas.setLastLabel(text, generate_color, generate_color)
                shape2 = shape.copy()
                shape2.label = text2
                self.canvas2.copyShapeToCanvas(shape2)
                item = self.addLabel(shape, flag)
                item2 = self.addLabel(shape2, (not flag))
                self.itemToItem2[item] = item2
                self.item2ToItem[item2] = item
                self.itemsCount += 1
            else:
                shape = self.canvas2.setLastLabel(text2, generate_color, generate_color)
                shape2 = shape.copy()
                shape2.label = text
                self.canvas.copyShapeToCanvas(shape2)
                item2 = self.addLabel(shape, flag)
                item = self.addLabel(shape2, (not flag))
                self.itemToItem2[item] = item2
                self.item2ToItem[item2] = item
                self.itemsCount += 1
            if self.beginner():  # Switch to edit mode.
                self.canvas.setEditing(True)
                self.canvas2.setEditing(True)
                self.actions.create.setEnabled(True)
            else:
                self.actions.editMode.setEnabled(True)
            self.setDirty()

            if text not in self.labelHist:
                self.labelHist.append(text)
        else:
            # self.canvas.undoLastLine()
            if flag:
                self.canvas.resetAllLines()
            else:
                self.canvas2.resetAllLines()

    def scrollRequest(self, delta, orientation):
        units = - delta / (8 * 15)
        bar = self.scrollBars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def scrollRequest2(self, delta, orientation):
        units = - delta / (8 * 15)
        bar = self.scrollBars2[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=3):
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]
        h_bar2 = self.scrollBars2[Qt.Horizontal]
        v_bar2 = self.scrollBars2[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 3
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)
        h_bar2.setValue(new_h_bar_value)
        v_bar2.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def togglePolygons(self, value):
        for item, shape in self.itemsToShapes.items():
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def loadFile(self, filePath=None, flag = None):
        """Load the specified file, or the last opened file if None."""
        self.resetState(flag)
        if flag:
            self.canvas.setEnabled(False)
        else:
            self.canvas2.setEnabled(False)
        if filePath is None:
            filePath = self.settings.get(SETTING_FILENAME)

        # Make sure that filePath is a regular python string, rather than QString
        filePath = ustr(filePath)

        unicodeFilePath = ustr(filePath)
        # Tzutalin 20160906 : Add file list and dock to move faster
        # Highlight the file item
        if flag:
            if unicodeFilePath and self.fileListWidget.count() > 0:
                print(unicodeFilePath)
                index = self.mImgList.index(unicodeFilePath)
                fileWidgetItem = self.fileListWidget.item(index)
                fileWidgetItem.setSelected(True)
        else:
            if unicodeFilePath and self.fileListWidget2.count() > 0:
                print(unicodeFilePath)
                index = self.mImgList2.index(unicodeFilePath)
                fileWidgetItem = self.fileListWidget2.item(index)
                fileWidgetItem.setSelected(True)

        if unicodeFilePath and os.path.exists(unicodeFilePath):
            if LabelFile.isLabelFile(unicodeFilePath):
                try:
                    self.labelFile = LabelFile(unicodeFilePath)
                except LabelFileError as e:
                    self.errorMessage(u'Error opening file',
                                      (u"<p><b>%s</b></p>"
                                       u"<p>Make sure <i>%s</i> is a valid label file.")
                                      % (e, unicodeFilePath))
                    self.status("Error reading %s" % unicodeFilePath)
                    return False
                self.imageData = self.labelFile.imageData
                self.lineColor = QColor(*self.labelFile.lineColor)
                self.fillColor = QColor(*self.labelFile.fillColor)
                if flag:
                    self.canvas.verified = self.labelFile.verified
                else:
                    self.canvas2.verified = self.labelFile.verified
            else:
                # Load image:
                # read data first and store for saving into label file.
                self.imageData = read(unicodeFilePath, None)
                self.labelFile = None
                if flag:
                    self.canvas.verified = False
                else:
                    self.canvas2.verified = False

            image = QImage.fromData(self.imageData)
            if image.isNull():
                self.errorMessage(u'Error opening file',
                                  u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
                self.status("Error reading %s" % unicodeFilePath)
                return False
            self.status("Loaded %s" % os.path.basename(unicodeFilePath))
            self.image = image
            if flag:
                self.filePath = unicodeFilePath
                self.canvas.loadPixmap(QPixmap.fromImage(image))
            else:
                self.filePath2 = unicodeFilePath
                self.canvas2.loadPixmap(QPixmap.fromImage(image))
            if self.labelFile and (not flag):
                self.loadLabels(self.labelFile.shapes)
            self.setClean()
            if flag:
                self.canvas.setEnabled(True)
            else:
                self.canvas2.setEnabled(True)
            self.adjustScale(initial=True)
            self.paintCanvas()
            self.addRecentFile(self.filePath)
            self.toggleActions(True)

            # Label xml file and show bound box according to its filename
            # if self.usingPascalVocFormat is True:
            # if self.defaultSaveDir is not None:
            #     if flag:
            #         basename = os.path.basename(os.path.splitext(self.filePath)[0])
            #     else:
            #         basename = os.path.basename(os.path.splitext(self.filePath2)[0])
            #     xmlPath = os.path.join(self.defaultSaveDir, basename + XML_EXT)
            #     txtPath = os.path.join(self.defaultSaveDir, basename + TXT_EXT)
            #     """Annotation file priority:
            #     PascalXML > YOLO
            #     """
            #     if os.path.isfile(xmlPath):
            #         self.loadPascalXMLByFilename(xmlPath, flag)
            #     elif os.path.isfile(txtPath):
            #         self.loadYOLOTXTByFilename(txtPath)
            # else:
            #     xmlPath = os.path.splitext(filePath)[0] + XML_EXT
            #     txtPath = os.path.splitext(filePath)[0] + TXT_EXT
            #     # print(xmlPath)
            #     if os.path.isfile(xmlPath):
            #         self.loadPascalXMLByFilename(xmlPath, flag)
            #     elif os.path.isfile(txtPath):
            #         self.loadYOLOTXTByFilename(txtPath)

            self.setWindowTitle(__appname__ + ' ' + filePath)

            # Default : select last item if there is at least one item

            if flag:
                if self.labelList.count():
                    self.labelList.setCurrentItem(self.labelList.item(self.labelList.count() - 1))
                    self.labelList.item(self.labelList.count() - 1).setSelected(True)
                self.canvas.setFocus(True)
            else:
                if self.labelList2.count():
                    self.labelList2.setCurrentItem(self.labelList2.item(self.labelList2.count() - 1))
                    self.labelList2.item(self.labelList2.count() - 1).setSelected(True)
                self.canvas2.setFocus(True)
                self.openFlie = filePath
            return True
        return False

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()
        self.canvas2.scale = 0.01 * self.zoomWidget.value()
        self.canvas2.adjustSize()
        self.canvas2.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2_1 = self.canvas.pixmap.width() - 0.0
        h2_1 = self.canvas.pixmap.height() - 0.0
        w2_2 = self.canvas2.pixmap.width() - 0.0
        h2_2 = self.canvas2.pixmap.height() - 0.0
        try:
            a2 = w2_1 / h2_1
            return w1 / w2_1 if a2 >= a1 else h1 / h2_1
        except:
            a2 = w2_2 / h2_2
            return w1 / w2_2 if a2 >= a1 else h1 / h2_2


    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        w2_1 = self.canvas.pixmap.width()
        w2_2 = self.canvas2.pixmap.width()
        try:
            return w / w2_1
        except:
            return w / w2_2

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        settings = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            settings[SETTING_FILENAME] = self.filePath if self.filePath else ''
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.lineColor
        settings[SETTING_FILL_COLOR] = self.fillColor
        settings[SETTING_RECENT_FILES] = self.recentFiles
        settings[SETTING_ADVANCE_MODE] = not self._beginner
        if self.defaultSaveDir and os.path.exists(self.defaultSaveDir):
            settings[SETTING_SAVE_DIR] = ustr(self.defaultSaveDir)
        else:
            settings[SETTING_SAVE_DIR] = ""

        if self.lastOpenDir and os.path.exists(self.lastOpenDir):
            settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir

        if self.lastOpenDir2 and os.path.exists(self.lastOpenDir2):
            settings[SETTING_LAST_OPEN_DIR2] = self.lastOpenDir2
        else:
            settings[SETTING_LAST_OPEN_DIR] = ""

        settings[SETTING_SINGLE_CLASS] = self.singleClassMode.isChecked()
        settings[SETTING_PAINT_LABEL] = self.paintLabelsOption.isChecked()
        settings[SETTING_DRAW_SQUARE] = self.drawSquaresOption.isChecked()
        settings.save()
    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def scanAllImages(self, folderPath):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        images = []

        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.join(root, file)
                    path = ustr(os.path.abspath(relativePath))
                    images.append(path)
        images.sort(key=lambda x: x.lower())
        return images

    def openFile(self, _value=False, flag = None):
        if not self.mayContinue():
            return
        path = os.path.dirname(ustr(self.filePath)) if self.filePath else '.'
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename[0] != '':
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
                filename = filename.replace('/','\\')
            self.loadFile(filename, flag)

    def openDirDialog(self, _value=False, dirpath=None, flag = None):
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else '.'
        if flag:
            if self.lastOpenDir and os.path.exists(self.lastOpenDir):
                defaultOpenDirPath = self.lastOpenDir
            else:
                defaultOpenDirPath = os.path.dirname(self.filePath) if self.filePath else '.'

            targetDirPath = ustr(QFileDialog.getExistingDirectory(self,
                                                         '%s - Open Directory' % __appname__, defaultOpenDirPath,
                                                         QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
            self.importDirImages(targetDirPath, flag)
        else:
            if self.lastOpenDir2 and os.path.exists(self.lastOpenDir2):
                defaultOpenDirPath = self.lastOpenDir2
            else:
                defaultOpenDirPath = os.path.dirname(self.filePath) if self.filePath else '.'

            targetDirPath = ustr(QFileDialog.getExistingDirectory(self,
                                                                  '%s - Open Directory' % __appname__,
                                                                  defaultOpenDirPath,
                                                                  QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
            self.importDirImages(targetDirPath, flag)

    def readFromClient(self, c):
        try:
            return c.recv(1024).decode('utf-8')
        except IOError as e:
            # 如果异常的话可能就是会话中断 那么直接删除
            print(e.strerror)
            return

    def openRExcel(self, path = None):
        excel_data = xlrd.open_workbook(path)
        sheet = excel_data.sheet_by_index(0)  # 根据sheet索引读取sheet中的所有内容
        # print(sheet.name, sheet.nrows, sheet.ncols)  # sheet的名称、行数、列数
        name = sheet.col_values(1)
        if len(name) > 5:
            self.labelHist = name[5:]
            return True
        else:
            return False

    def importDirImages(self, dirpath, flag = None):
        if not self.mayContinue() or not dirpath:
            return

        if flag:
            self.mImgList = []
            self.filePath = None
        else:
            self.mImgList2 = []
            self.filePath2 = None
        if flag:
            self.lastOpenDir = dirpath
        else:
            self.lastOpenDir2 = dirpath
        self.dirname = dirpath
        if flag:
            self.fileListWidget.clear()
            self.mImgList = self.scanAllImages(dirpath)
        else:
            self.fileListWidget2.clear()
            self.mImgList2 = self.scanAllImages(dirpath)
        self.openNextImg(flag = flag)
        for i in range(max(len(self.mImgList), len(self.mImgList2))):
            if flag:
                if i < len(self.mImgList):
                    item1 = QListWidgetItem(self.mImgList[i])
                    self.fileListWidget.addItem(item1)
            else:
                if i < len(self.mImgList2):
                    item2 = QListWidgetItem(self.mImgList2[i])
                    self.fileListWidget2.addItem(item2)

        # for imgPath1, imgPath2 in zip(self.mImgList, self.mImgList2):
        #     item1 = QListWidgetItem(imgPath1)
        #     item2 = QListWidgetItem(imgPath2)
        #     if flag:
        #         self.fileListWidget.addItem(item1)
        #     else:
        #         self.fileListWidget2.addItem(item2)

    def verifyImg(self, _value=False):
        # Proceding next image without dialog if having any label
        if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.saveFile()
                if self.labelFile != None:
                    self.labelFile.toggleVerify()
                else:
                    return

            self.canvas.verified = self.labelFile.verified
            self.canvas2.verified = self.labelFile.verified
            self.paintCanvas()
            self.saveFile()

    def openPrevImg(self, _value=False, flag = None):
        # Proceding prev image without dialog if having any label
        if not self.mayContinue():
            return

        if flag:
            if len(self.mImgList) <= 0:
                return

            if self.filePath is None:
                return

            currIndex = self.mImgList.index(self.filePath)
            if currIndex - 1 >= 0:
                filename = self.mImgList[currIndex - 1]
                if filename:
                    self.loadFile(filename, flag)
        else:
            if len(self.mImgList2) <= 0:
                return

            if self.filePath2 is None:
                return

            currIndex = self.mImgList2.index(self.filePath2)
            if currIndex - 1 >= 0:
                filename = self.mImgList2[currIndex - 1]
                if filename:
                    self.loadFile(filename, flag)

    def openNextImg(self, _value=False, flag = None):
        # Proceding prev image without dialog if having any label
        if not self.mayContinue():
            return

        if flag:
            if len(self.mImgList) <= 0:
                return

            filename = None
            if self.filePath is None:
                filename = self.mImgList[0]
            else:
                currIndex = self.mImgList.index(self.filePath)
                if currIndex + 1 < len(self.mImgList):
                    filename = self.mImgList[currIndex + 1]

            if filename:
                self.loadFile(filename, flag)
        else:
            if len(self.mImgList2) <= 0:
                return

            filename = None
            if self.filePath2 is None:
                filename = self.mImgList2[0]
            else:
                currIndex = self.mImgList2.index(self.filePath2)
                if currIndex + 1 < len(self.mImgList2):
                    filename = self.mImgList2[currIndex + 1]

            if filename:
                self.loadFile(filename, flag)

    def saveFile(self, _value=False):
        # labelList1 = []
        # labelList2 = []
        # count1 = self.labelList.count()
        # count2 = self.labelList2.count()
        # if count1 != count2:
        #     QMessageBox.warning(self, "警告", "图1图2框选数量不同！", QMessageBox.Yes)
        #     return
        # for i in range(count1):
        #     labelList1.append(self.labelList.item(i).text())
        #     labelList2.append(self.labelList2.item(i).text())
        # # print(labelList1,"\n",labelList2)
        # def format_shape(s):
        #     return dict(label=s.label,
        #                 line_color=s.line_color.getRgb(),
        #                 fill_color=s.fill_color.getRgb(),
        #                 points=[(p.x(), p.y()) for p in s.points],
        #                 difficult = s.difficult)
        #
        # shapes1 = [format_shape(shape) for shape in self.canvas.shapes]
        # shapes2 = [format_shape(shape) for shape in self.canvas2.shapes]
        #
        # save = Save(self.filePath, self.filePath2, shapes1, shapes2)
        # if (save.saveImg() and save.saveExcel()):
        #     QMessageBox.information(self, "提示", "保存成功！", QMessageBox.Yes)
        #     self.setClean()
        # else:
        #     QMessageBox.warning(self, "提示", "保存失败！", QMessageBox.Yes)
        imgFileDir = os.path.dirname(self.filePath)
        imgFileName = os.path.basename(self.filePath)
        savedFileName = os.path.splitext(imgFileName)[0]
        savedPath = os.path.join(imgFileDir, savedFileName)
        imgFileDir2 = os.path.dirname(self.filePath2)
        imgFileName2 = os.path.basename(self.filePath2)
        savedFileName2 = os.path.splitext(imgFileName2)[0]
        savedPath2 = os.path.join(imgFileDir2, savedFileName2)
        self._saveFile(savedPath, 1)
        self._saveFile(savedPath2, 0)
        self.saveRes(savedPath,savedPath2)

    def openRes(self):
        try:
            with open(".\\data\\SaveFileData.json", "r", encoding='UTF-8-sig') as jsonFile:
                data = json.load(jsonFile)
        except:
            QMessageBox.warning(self, "警告", "请检查数据文件格式是否出错！", QMessageBox.Yes)
            return
        self.templateDialog = TemplateDialog(parent = self, listItem = list(data.keys()))
        key, removeItems = self.templateDialog.popUp()
        if key:
            path1, path2 = data[key].split(" ")
            imgPath1 = path1 + ".bmp"
            imgPath2 = path2 + ".bmp"
            xmlPath1 = path1 + XML_EXT
            xmlPath2 = path2 + XML_EXT
            self.fileListWidget.clear()
            self.fileListWidget2.clear()
            if os.path.isfile(imgPath1) and os.path.isfile(imgPath2) and \
                    os.path.isfile(xmlPath1) and os.path.isfile(xmlPath2):
                self.loadFile(path1 + ".bmp", 1)
                self.loadFile(path2 + '.bmp', 0)
                self.loadPascalXMLByFilename(xmlPath1, xmlPath2)
            else:
                QMessageBox.warning(self, "警告", "文件已经不存在,将会自动删除该记录！", QMessageBox.Yes)
                data.pop(key, 'error')
                try:
                    with open(".\\data\\SaveFileData.json", 'w') as jsonFile:
                        json.dump(data, jsonFile)
                except:
                    QMessageBox.warning(self, "警告", "删除失败！", QMessageBox.Yes)
        if removeItems:
            for item in removeItems:
                path1, path2 = data[item].split(" ")
                xmlPath1 = path1 + XML_EXT
                xmlPath2 = path2 + XML_EXT
                if os.path.exists(xmlPath1):
                    os.remove(xmlPath1)
                    os.remove(xmlPath2)
                data.pop(item, 'error')
            try:
                with open(".\\data\\SaveFileData.json", 'w') as jsonFile:
                    json.dump(data, jsonFile)
            except:
                QMessageBox.warning(self, "警告", "删除失败！", QMessageBox.Yes)
                return

    def hasSameTemplate(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'该结果已经保存，是否覆盖?'
        return yes == QMessageBox.warning(self, u'注意', msg, yes | no)

    def saveRes(self, savePath1, savePath2):
        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                        difficult = s.difficult)

        shapes1 = [format_shape(shape) for shape in self.canvas.shapes]
        shapes2 = [format_shape(shape) for shape in self.canvas2.shapes]

        save = Save(self.filePath, self.filePath2, shapes1, shapes2)
        if not save.saveExcel():
            QMessageBox.warning(self, "警告", "保存失败！", QMessageBox.Yes)
            return
        fileName = os.path.splitext(savePath2)[0].split('\\')[-1]
        # file = self.mImgList[0]
        # pathList = file.split("\\")
        # pathList.pop()
        # dirName = pathList[-1]
        # path = "\\".join(pathList)
        dit = {fileName: savePath1 + " " + savePath2}
        if not os.path.exists(".\\data"):
            os.mkdir("data")
        if os.path.exists(".\\data\\SaveFileData.json"):
            with open(".\\data\\SaveFileData.json", "r", encoding='UTF-8-sig') as jsonFile:
                data = json.load(jsonFile)
            flag = True
            # print(data)
            if fileName in data:
                if not self.hasSameTemplate():
                    flag = False
                else:
                    data[fileName] = savePath1 + " " + savePath2
                    flag = False
            if flag:
                data.update(dit)
            with open(".\\data\\SaveFileData.json", 'w') as jsonFile:
                json.dump(data, jsonFile)
            QMessageBox.information(self, "提示", "保存成功！", QMessageBox.Yes)
        else:
            with open(".\\data\\SaveFileData.json", 'w') as jsonFile:
                json.dump(dit, jsonFile)
            QMessageBox.information(self, "提示", "保存成功！", QMessageBox.Yes)
        self.setClean()

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        openDialogPath = self.currentPath()
        dlg = QFileDialog(self, caption, openDialogPath, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            fullFilePath = ustr(dlg.selectedFiles()[0])
            return os.path.splitext(fullFilePath)[0] # Return file path without the extension.
        return ''

    def _saveFile(self, annotationFilePath, flag = None):
        if annotationFilePath and self.saveLabels(annotationFilePath, flag):
            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState(3)
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.canvas2.setEnabled(False)

    def resetAll(self):
        self.settings.reset()
        self.close()
        proc = QProcess()
        proc.startDetached(os.path.abspath(__file__))

    def mayContinue(self):
        return not (self.dirty and not self.discardChangesDialog())

    def discardChangesDialog(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'您还未保存对其的修改，确认要离开吗?'
        return yes == QMessageBox.warning(self, u'注意', msg, yes | no)
        return QMessageBox.Yes

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def chooseColor1(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.lineColor = color
            Shape.line_color = color
            self.canvas.setDrawingColor(color)
            self.canvas.update()
            self.canvas2.setDrawingColor(color)
            self.canvas2.update()
            self.setDirty()

    def deleteSelectedShape(self):
        self.itemsCount -= 1
        shape1 = self.canvas.deleteSelected()
        shape2 = self.canvas2.deleteSelected()
        self.remLabel(shape1)
        self.remLabel2(shape2)
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def chshapeLineColor(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selectedShape.line_color = color
            self.canvas.update()
            self.canvas2.selectedShape.line_color = color
            self.canvas2.update()
            self.setDirty()

    def chshapeFillColor(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selectedShape.fill_color = color
            self.canvas.update()
            self.canvas2.selectedShape.fill_color = color
            self.canvas2.update()
            self.setDirty()

    def loadPredefinedClasses(self, predefClassesFile):
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.labelHist = [line]
                    else:
                        self.labelHist.append(line)

    def loadPascalXMLByFilename(self, xmlPath, xmlPath2):
        if self.filePath is None:
            return
        if os.path.isfile(xmlPath) is False or os.path.isfile(xmlPath2) is False:
            return

        self.set_format(FORMAT_PASCALVOC)

        tVocParseReader = PascalVocReader(xmlPath)
        tVocParseReader2 = PascalVocReader(xmlPath2)
        shapes = tVocParseReader.getShapes()
        shapes2 = tVocParseReader2.getShapes()
        items1 = self.loadLabels(shapes,1)
        items2 = self.loadLabels(shapes2,0)
        for i in range(len(items1)):
            self.itemToItem2[items1[i]] = items2[i]
            self.item2ToItem[items2[i]] = items1[i]
        self.itemsCount = self.labelList.count()
        self.canvas.verified = tVocParseReader.verified
        self.canvas2.verified = tVocParseReader2.verified

    def togglePaintLabelsOption(self):
        paintLabelsOptionChecked = self.paintLabelsOption.isChecked()
        for shape in self.canvas.shapes:
            shape.paintLabel = paintLabelsOptionChecked

    def toogleDrawSquare(self):
        self.canvas.setDrawingShapeToSquare(self.drawSquaresOption.isChecked())
        self.canvas2.setDrawingShapeToSquare(self.drawSquaresOption.isChecked())

    def putRec(self, shape):
        line_color, fill_color,difficult = None, None, False
        # label, points, line_color, fill_color, difficult
        shape.append(line_color)
        shape.append(fill_color)
        shape.append(difficult)
        # print(shape)
        return shape

    def compare(self, flag = None):
        if self.filePath is None or self.filePath2 is None:
            QMessageBox.warning(self, "提示", "请确保两个文件都打开了", QMessageBox.Yes)
            return
        compare = Compare(self.filePath, self.filePath2)
        shapesA, shapesB = compare.compare()
        if len(shapesA) == 0 or len(shapesB) == 0:
            QMessageBox.warning(self, "提示", "识别失败！", QMessageBox.Yes)
            return
        sA = []
        sB = []
        for i in range(len(shapesA)):
            sA.append(self.putRec(shapesA[i]))
            sB.append(self.putRec(shapesB[i]))
        self.shapesToItems.clear()
        self.itemsToShapes.clear()
        self.itemToItem2.clear()
        self.item2ToItem.clear()
        self.labelList.clear()
        self.labelList2.clear()
        items1 = self.loadLabels(sA, 1)
        items2 = self.loadLabels(sB, 0)
        count = self.labelList.count()
        self.itemsCount = count
        for i in range(len(items1)):
            self.itemToItem2[items1[i]] = items2[i]
            self.item2ToItem[items2[i]] = items1[i]
        # print(self.itemToItem2)
        self.setDirty()

def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])

def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("app"))
    # Tzutalin 201705+: Accept extra agruments to change predefined class file
    # Usage : labelImg.py image predefClassFile saveDir
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join(
                         os.path.dirname(sys.argv[0]),
                         'data', 'predefined_classes.txt'),
                     argv[3] if len(argv) >= 4 else None)
    win.show()
    return app, win


def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
