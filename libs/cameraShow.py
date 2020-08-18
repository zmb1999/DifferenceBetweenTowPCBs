# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CameraShow.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!

import sys
from ctypes import *
from PyQt5.QtWidgets import QApplication, QMainWindow
from libs.cameraUI import Ui_Frame
from libs.cameraControl import Cross

class MyMainForm(QMainWindow, Ui_Frame):
    def __init__(self, parent=None):
        super(MyMainForm, self).__init__(parent)
        self.setupUi(self)
        self.cross = Cross(cdll.LoadLibrary(".\MVGigE.dll"))
        self.pushButton.clicked.connect(self.openC)
        self.pushButton_2.clicked.connect(self.closeC)

    # def StreamCB(self, pInfo, UserVal):
    #     # self.MVGigE.MVInfo2Image(self.hCam, pInfo, m_hImage)
    #     print("666")
    #     return
    #
    # def captureSnap(self, handle):
    #     self.MVGigE.MVSetTriggerMode(self.hCam, 0)
    #     callBack = CFUNCTYPE(None, c_void_p, c_void_p)
    #     print(cdll.LoadLibrary(".\MVGigE.dll").MVStartGrab(self.hCam, callBack(self.StreamCB), handle))
    #     return

    def openC(self):
        self.cross.crossLoad()
        print(c_ulong(self.winId()))
        self.cross.captureSnap(c_ulong(self.scrollArea.winId()))
        print('open')

    def closeC(self):
        self.cross.Stop()
        print('close')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MyMainForm()
    myWin.show()
    sys.exit(app.exec_())
