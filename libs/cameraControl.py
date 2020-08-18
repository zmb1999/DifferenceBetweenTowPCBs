from ctypes import *
from enum import Enum
from libs.cameraStruct import *


class Cross():
    def __init__(self, MVGigE):
        self.MVGigE = MVGigE
        self.hCam = c_void_p(None)
        self.pInfo = None
        self.m_hImage = None
        self.w, self.h = c_int(), c_int()
        self.m_hImage = c_void_p(None)

    def crossLoad(self):
        self.MVGigE.MVInitLib()
        self.MVGigE.MVUpdateCameraList()
        camNum = c_int()
        # mvDll.MVGetNumOfCameras.argtypes = (POINTER(c_int), )
        self.MVGigE.MVGetNumOfCameras(pointer(camNum))
        print(camNum.value)
        if camNum.value == 0:
            return "没有找到相机"

        # mvDll.MVOpenCamByIndex.argtypes = (c_int, POINTER(c_void_p))
        r = (self.MVGigE.MVOpenCamByIndex(0, pointer(self.hCam)))
        if r == MVSTATUS.MVST_ACCESS_DENIED:
            return "无法打开相机，可能正被别的软件控制"

        r = self.MVGigE.MVGetWidth(self.hCam, pointer(self.w))
        print(self.w)
        if r != MVSTATUS.MVST_SUCCESS:
            return "取得图像宽度失败"

        r = self.MVGigE.MVGetHeight(self.hCam, pointer(self.h))
        print(self.h)
        if r!= MVSTATUS.MVST_SUCCESS:
            return "取得图像高度失败"

        m_PixelFormat = c_int()
        r = self.MVGigE.MVGetPixelFormat(self.hCam, pointer(m_PixelFormat))
        print(m_PixelFormat)
        if r != MVSTATUS.MVST_SUCCESS:
            return "取得图像颜色模式失败"

        self.MVGigE.MVImageCreate.restype = c_void_p
        if (m_PixelFormat == MV_PixelFormatEnums.PixelFormat_Mono8):
            self.m_hImage = self.MVGigE.MVImageCreate(self.w, self.h, 8)
        else:
            self.m_hImage = self.MVGigE.MVImageCreate(self.w, self.h, 24)
        print(self.m_hImage)
        r = self.MVGigE.MVSetStrobeSource(self.hCam, LineSourceEnums.LineSource_ExposureActive)
        if r != MVSTATUS.MVST_SUCCESS:
            return "设置外闪光同步信号源失败"
        return None

    def StreamCB(self, pInfo, UserVal):
        # self.MVGigE.MVInfo2Image(self.hCam, pInfo, m_hImage)
        print(pInfo)
        print(UserVal)
        print("666")
        return

    def start(self, handle):
        self.MVGigE.MVSetTriggerMode(self.hCam, TriggerModeEnums.TriggerMode_Off)
        callBack = CFUNCTYPE(MV_IMAGE_INFO, c_ulong)
        print(self.MVGigE.MVStartGrab(self.hCam, callBack(self.StreamCB), handle))
        # pInfo = MV_IMAGE_INFO()
        # m_hImage = c_void_p(None)
        # self.MVGigE.MVInfo2Image.argtypes(c_void_p, c_void_p, c_void_p)
        # print("123",self.MVGigE.MVInfo2Image(self.hCam, pointer(pInfo), m_hImage))

    def stop(self):
        self.MVGigE.MVStopGrab(self.hCam)

if __name__ == '__main__':
    MVGigE = cdll.LoadLibrary(".\MVGigE.dll")
    cross = Cross(MVGigE)
    cross.crossLoad()
    cross.captureSnap(pointer(c_ulong()))