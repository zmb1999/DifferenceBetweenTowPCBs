from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
from functools import partial
from libs.cameraControl import Cross
from ctypes import *

class struct(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

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

class ToolBar(QToolBar):

    def __init__(self, title):
        super(ToolBar, self).__init__(title)
        layout = self.layout()
        m = (0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setContentsMargins(*m)
        self.setContentsMargins(*m)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

    def addAction(self, action):
        if isinstance(action, QWidgetAction):
            return super(ToolBar, self).addAction(action)
        btn = ToolButton()
        btn.setDefaultAction(action)
        btn.setToolButtonStyle(self.toolButtonStyle())
        self.addWidget(btn)

class ToolButton(QToolButton):
    """ToolBar companion class which ensures all buttons have the same size."""
    minSize = (60, 60)

class Canvas(QWidget):
    zoomRequest = pyqtSignal(int)
    scrollRequest = pyqtSignal(int, int)
    newShape = pyqtSignal()
    selectionChanged = pyqtSignal(bool)
    shapeMoved = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)

    CREATE, EDIT = list(range(2))

    epsilon = 11.0

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        pass

class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))
    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("界面部分")
        self.setWindowIcon(QIcon("./Icon/App.png"))
        self.resize(800, 500)
        self.center()

        ListLayout = QVBoxLayout()
        ListLayout.setContentsMargins(0,0,0,0)

        #新建一个部件用来show已添加的label
        self.labelList = QListWidget()
        labelListContainer = QWidget()
        labelListContainer.setLayout(ListLayout)
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        self.labelList.itemChanged.connect(self.labelItemChanged)
        ListLayout.addWidget(self.labelList)

        # self.dock = QDockWidget(u'元器件名称', self)
        # self.dock.setObjectName(u'Labels')
        # self.dock.setWidget(labelListContainer)

        self.canvas = Canvas(parent=self)
        self.cross = Cross(cdll.LoadLibrary(".\MVGigE.dll"))
        mes = self.cross.crossLoad()
        if mes:
            QMessageBox.warning(self, "警告", mes, QMessageBox.Yes)
        #设置中间加载图像区域
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)

        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll

        self.setCentralWidget(scroll)

        self.filePath = None

        action = partial(newAction , self)

        #新建一大批Actions作为功能按钮
        quit = action('退出', self.close,
                      'Ctrl+Q', 'quit', u'退出应用')

        star = action('&开始采集', self.start,
                      'Ctrl+O', 'open', u'开始采集')

        save = action("保存", self.saveFile,
                      'Ctrl+S', 'save', u'Save labels to file')

        stop = action('停止采集', self.stop, 'Ctrl+W', '停止采集', u'关闭当前图片')

        zoomIn = action('放大', partial(self.addZoom, 10),
                        'Ctrl++', 'zoomIn', u'放大图片')

        zoomOut = action('缩小', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoomOut', u'缩小图片')

        zoomOrg = action('当前缩放比例', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'当前缩放比例')

        fitWindow = action('&适应窗口', self.setFitWindow,
                           None, 'fit-window', u'适应窗口')

        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'适应窗口')

        # self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        # self.dock.setFeatures(QDockWidget.DockWidgetClosable)  # 将labelList这个DockWidget设置成可关闭，不能移动

        # 将活动进行分组
        self.actions = struct(
            fileActions = ( star , stop, save, zoomIn, zoomOut,
                       zoomOrg, fitWindow, quit) ,

        )

        self.tools = self.toolbar("Tools")

        addActions(self.tools, self.actions.fileActions)

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        toolbar.setMovable(False)
        return toolbar

    def scaleFitWindow(self):
        pass

    def scaleFitWidth(self):
        pass

    def togglePolygons(self):
        pass

    def pretreat(self):
        pass

    def resetAll(self):
        pass

    def setCreateMode(self):
        pass

    def setEditMode(self):
        pass

    def createShape(self):
        pass

    def deleteSelectedShape(self):
        pass

    def copySelectedShape(self):
        pass

    def toggleAdvancedMode(self):
        pass

    def newDemoFile(self):
        pass

    def openDirDialog(self):
        self.cross.stop()
        print("close")

    def openNextImg(self):
        pass

    def openPrevImg(self):
        pass

    def change_format(self):
        pass

    def stop(self):
        self.cross.stop()
        print("close")

    def contrast(self):
        pass

    def newDemo(self):
        pass

    def newDemo(self):
        pass

    def newDemoImg(self):
        pass

    def setFitWindow(self):
        pass

    def setZoom(self):
        pass

    def setFitWidth(self):
        pass

    def addZoom(self):
        pass

    def copySelectedShape(self):
        pass

    def deleteSelectedShape(self):
        pass

    def createShape(self):
        pass

    def setCreateMode(self):
        pass

    def setEditMode(self):
        pass

    def resetAll(self):
        pass


    def saveFile(self):
        pass

    def start(self):
        # self.cross.crossLoad()
        print(c_ulong(self.winId()))
        self.cross.start(c_ulong(self.canvas.winId()))
        print('open')

    def closed(self):
        pass

    def setDirty(self):
        pass

    def shapeMoved(self):
        pass

    def scrollRequest(self):
        pass

    def newShape(self):
        pass

    def zoomRequest(self):
        pass

    def center(self):
        size = self.geometry() #窗口大小
        screen = QDesktopWidget().screenGeometry()

        center_x = int((screen.width() - size.width())/2)
        center_y = int((screen.height() - size.height())/2)

        self.move(center_x, center_y)


    def labelItemChanged(self, item):
        pass

    def labelSelectionChanged(self):
        pass

    def editLabel(self):
        pass

def generateColorByText(text):
    pass

def newIcon(icon):
    return QIcon('Icon/' + icon+".png")

def newAction(parent, text, slot=None, shortcut=None, icon=None,
              tip=None, checkable=False, enabled=True):
    """Create a new action and assign callbacks, shortcuts, etc."""
    a = QAction(text, parent)
    if icon is not None:
        a.setIcon(newIcon(icon))
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            a.setShortcuts(shortcut)
        else:
            a.setShortcut(shortcut)
    if tip is not None:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    if slot is not None:
        a.triggered.connect(slot)
    if checkable:
        a.setCheckable(True)
    a.setEnabled(enabled)
    return a

def addActions(widget, actions):
    for action in actions:
        if action is None:
            widget.addSeparator()
        elif isinstance(action, QMenu):
            widget.addMenu(action)
        else:
            widget.addAction(action)

def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName("myLabelImag")
    win = MainWindow()
    win.show()
    return app, win


def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
