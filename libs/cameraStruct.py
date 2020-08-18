from ctypes import *

class MVSTATUS():
    MVST_SUCCESS = 0                    # / < 没有错误
    MVST_ERROR = -1001                  # / < 一般错误
    MVST_ERR_NOT_INITIALIZED = -1002    # ! < 没有初始化
    MVST_ERR_NOT_IMPLEMENTED = -1003    # ! < 没有实现
    MVST_ERR_RESOURCE_IN_USE = -1004    # ! < 资源被占用
    MVST_ACCESS_DENIED = -1005          # / < 无法访问
    MVST_INVALID_HANDLE = -1006         # / < 错误句柄
    MVST_INVALID_ID = -1007             # / < 错误ID
    MVST_NO_DATA = -1008                # / < 没有数据
    MVST_INVALID_PARAMETER = -1009      # / < 错误参数
    MVST_FILE_IO = -1010                # / < IO错误
    MVST_TIMEOUT = -1011                # / < 超时
    MVST_ERR_ABORT = -1012              # / < 退出
    MVST_INVALID_BUFFER_SIZE = -1013    # / < 缓冲区尺寸错误
    MVST_ERR_NOT_AVAILABLE = -1014      # / < 无法访问
    MVST_INVALID_ADDRESS = -1015        # / < 地址错误

class MV_PixelFormatEnums():
    PixelFormat_Mono8 = 0x01080001	    #!<8Bit灰度
    PixelFormat_BayerBG8 = 0x0108000B 	#!<8Bit Bayer图,颜色模式为BGGR
    PixelFormat_BayerRG8 = 0x01080009 	#!<8Bit Bayer图,颜色模式为RGGB
    PixelFormat_BayerGB8 = 0x0108000A 	#!<8Bit Bayer图,颜色模式为GBRG
    PixelFormat_BayerGR8 = 0x01080008 	#!<8Bit Bayer图,颜色模式为GRBG
    PixelFormat_BayerGRW8 = 0x0108000C	#!<8Bit Bayer图,颜色模式为GRW8
    PixelFormat_Mono16 = 0x01100007		#!<16Bit灰度
    PixelFormat_BayerGR16 = 0x0110002E	#!<16Bit Bayer图,颜色模式为GR
    PixelFormat_BayerRG16 = 0x0110002F	#!<16Bit Bayer图,颜色模式为RG
    PixelFormat_BayerGB16 = 0x01100030	#!<16Bit Bayer图,颜色模式为GB
    PixelFormat_BayerBG16 = 0x01100031	#!<16Bit Bayer图,颜色模式为BG

class LineSourceEnums():
    LineSource_Off=0              #!<关闭
    LineSource_ExposureActive=5   #!<和曝光同时
    LineSource_Timer1Active=6     #!<由定时器控制
    LineSource_UserOutput0=12	  #!<直接由软件控制

class TriggerModeEnums():
    TriggerMode_Off = 0           #!<触发模式关，即FreeRun模式，相机连续采集
    TriggerMode_On = 1            #!<触发模式开，相机等待软触发或外触发信号再采集图像

# typedef struct _IMAGE_INFO
# {
# 	uint64_t	nTimeStamp;		///< 时间戳，采集到图像的时刻，精度为0.01us
# 	USHORT		nBlockId;		///< 帧号，从开始采集开始计数
# 	UCHAR		*pImageBuffer;	///< 图像指针，即指向(0,0)像素所在内存位置的指针，通过该指针可以访问整个图像
# 	ULONG		nImageSizeAcq;	///< 采集到的图像大小[字节]
# 	UCHAR		nMissingPackets;///< 传输过程中丢掉的包数量
# 	uint64_t	nPixelType;		///< 图像格式
# 	uint32_t	nSizeX;			///< 图像宽度
# 	uint32_t	nSizeY;         ///< 图像高度
# 	uint32_t	nOffsetX;		///< 图像水平坐标
# 	uint32_t	nOffsetY;       ///< 图像垂直坐标
# } MV_IMAGE_INFO, * pMV_IMAGE_INFO ;

class MV_IMAGE_INFO(Structure):
    _fields_ = [
                    ("nTimeStamp", c_uint64),
                    ("nBlockId", c_ushort),
                    ("pImageBuffer", POINTER(c_ubyte)),
                    ("nImageSizeAcq", c_ulong),
                    ("nMissingPackets", c_ubyte),
                    ("nPixelType", c_uint64),
                    ("nSizeX", c_uint32),
                    ("nSizeY", c_uint32),
                    ("nOffsetX", c_uint32),
                    ("nOffsetY", c_uint32)
                ]