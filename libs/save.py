import cv2
import numpy as np
import os
import xlwt

class Save:
    def __init__(self, filePath1, filePath2, shapes1, shapes2):
        self.filePath1 = filePath1
        self.filePath2 = filePath2
        self.shapes1 = shapes1
        self.shapes2 = shapes2

    def getPoints(self):
        points1 = []
        points2 = []
        for point1, point2 in zip(self.shapes1, self.shapes2):
            points1.append(point1['points'])
            points2.append(point2['points'])
        return points1, points2

    def getLabels(self):
        labels1 = []
        labels2 = []
        for label1, label2 in zip(self.shapes1, self.shapes2):
            labels1.append(label1['label'])
            labels2.append(label2['label'])
        return labels1, labels2

    def paintImg(self):
        img1 = cv2.imdecode(np.fromfile(self.filePath1, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        img1 = cv2.cvtColor(img1, cv2.COLOR_GRAY2BGR)
        img2 = cv2.imdecode(np.fromfile(self.filePath2, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
        # filePath1 = self.filePath1.encode('gbk')  # unicode转gbk，字符串变为字节数组
        # filePath2 = self.filePath2.encode('gbk')
        # img1 = cv2.imread(filePath1.decode())
        # img2 = cv2.imread(filePath2.decode())
        points1, points2 = self.getPoints()
        for point1, point2 in zip(points1, points2):
            img1 = cv2.rectangle(img1,(int(point1[0][0]), int(point1[0][1])),(int(point1[2][0]), int(point1[2][1])), (255, 0, 0), 10)
            img2 = cv2.rectangle(img2,(int(point2[0][0]), int(point2[0][1])),(int(point2[2][0]), int(point2[2][1])), (255, 0, 0), 10)

        rows1 = img1.shape[0]
        cols1 = img1.shape[1]
        rows2 = img2.shape[0]
        cols2 = img2.shape[1]
        out = np.zeros((max([rows1, rows2]), cols1 + cols2, 3), dtype='uint8')
        out[:rows1, :cols1] = np.dstack([img1])
        out[:rows2, cols1:] = np.dstack([img2])
        return out

    def saveImg(self):
        img = self.paintImg()
        pathList = self.filePath2.split('\\')
        saveFileName = pathList[-2] + "_" + pathList[-1].split('.')[0] + "_对比结果.bmp"
        pathList.pop()
        pathName = pathList.pop()
        savePath = '\\'.join(pathList) + '\\' + "对比结果" + pathName
        try:
            if not os.path.exists(savePath):
                os.makedirs(savePath)
            savePath = savePath + '\\' +saveFileName
            print(savePath)
            # cv2.imwrite(savePath, img)
            cv2.imencode('.bmp', img)[1].tofile(savePath)
            return True
        except:
            return False

    def saveExcel(self):
        labels1, labels2 = self.getLabels()
        # points1, points2 = self.getPoints()
        pathList = self.filePath2.split('\\')
        saveFileName = (pathList[-2] + '_' + pathList[-1]).split('.')[0] + '_对比结果.xls'
        pathList.pop()
        pathName = pathList.pop()
        savePath = '\\'.join(pathList) + '\\' + "对比结果" + pathName

        xls = xlwt.Workbook()
        sht1 = xls.add_sheet('Sheet1')
        sht1.write_merge(0, 0, 0, 1, saveFileName)

        sht1.write(1, 0, '序号')
        sht1.write(1, 1, '变化')
        try:
            for i in range(len(labels1)):
                sht1.write(i + 2, 0, i)
                sht1.write(i + 2, 1, labels1[i] + "变化为" + labels2[i])
            if not os.path.exists(savePath):
                os.makedirs(savePath)
            savePath = savePath + '\\' + saveFileName
            print(savePath)
            xls.save(savePath)
            return True
        except:
            return False


