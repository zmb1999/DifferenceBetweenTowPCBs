# coding: utf-8
import cv2
import numpy as np
import imutils
from skimage.measure import compare_ssim
# print('cv version: ', cv2.__version__)

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class Compare:
    def __init__(self, filePath1, filePath2):
        self.filePath1 = filePath1
        self.filePath2 = filePath2
        self.shapesA = []
        self.shapesB = []

    def cv_imread(self, file_path):
        cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        return cv_img

    def findPCB(self, image,w_ = 0, h_ = 0):
        canny = cv2.Canny(image, 10, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))  # 定义结构元素的形状和大小
        canny = cv2.dilate(canny, kernel)  # 膨胀操作
        binary, contours, h = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            # cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # cv2.imwrite("D:\\rectangle_A.jpg", image)
            if w * h < 10000000:
                continue

            if w_ == 0 and h_ == 0:
                # cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                # cv2.imwrite("D:\\rectangle_A.jpg", image)
                # print(x, y, w, h)
                return x, y, w, h
            else:
                # cv2.rectangle(image, (x, y), (x + w_, y + h_), (0, 255, 0), 2)
                # print(x, y, w_, h_)
                return x, y, w_, h_

    def siftDetect(self, img1, img2):
        print("surf detector......")

        img1 = img1[1000:1500, 1000:1500]
        img2 = img2[1000:1500, 1000:1500]
        sift = cv2.xfeatures2d.SURF_create()
        kp2, des2 = sift.detectAndCompute(img2, None)
        print("关键点的个数：%d" % len(kp2))
        kp1, des1 = sift.detectAndCompute(img1, None)
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)
        good0 = [[m] for m, n in matches if m.distance < 0.5 * n.distance]

        kpoint2 = []
        kpoint1 = []
        for mat1 in good0:
            for mat in mat1:
                # Get the matching keypoints for each of the images
                img1_idx = mat.queryIdx  # DMatch.queryIdx - 查询图像中描述符的索引。
                img2_idx = mat.trainIdx  # DMatch.trainIdx - 目标图像中描述符的索引。

                # x - columns
                # y - rows
                (x1, y1) = kp1[img1_idx].pt
                (x2, y2) = kp2[img2_idx].pt
                if abs(x1 - x2) > 50 or abs(y1 - y2) > 100:
                    continue
                kpoint1.append([x1, y1])
                kpoint2.append([x2, y2])
        pointListA = np.array(kpoint1,dtype=float)
        pointListB = np.array(kpoint2,dtype=float)
        # print(pointListA.shape, pointListB.shape, "\n", pointListA,'\n',pointListB)
        return pointListA, pointListB

    def ssimMatch(self, imgA, xA, yA, wA, hA, imgB, xB, yB, wB, hB):
        PCBA = imgA[yA:yA + hA, xA:xA + wA]
        PCBB = imgB[yB:yB + hB, xB:xB + wB]
        PCBA = cv2.resize(PCBA, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_NEAREST)
        PCBB = cv2.resize(PCBB, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_NEAREST)
        # grayA = cv2.cvtColor(PCBA, cv2.COLOR_BGR2GRAY)
        # grayB = cv2.cvtColor(PCBB, cv2.COLOR_BGR2GRAY)
        # grayA = cv2.Laplacian(grayA,cv2.CV_16S,ksize = 3)
        # grayB = cv2.Laplacian(grayB,cv2.CV_16S,ksize = 3)
        # grayA = 2.0 * grayA
        # grayB = 2.0 * grayB
        # grayA[grayA > 255] = 255
        # grayB[grayB > 255] = 255
        grayA = cv2.GaussianBlur(PCBA, (45, 45), 0)
        grayB = cv2.GaussianBlur(PCBB, (45, 45), 0)
        # cv2.imwrite(savePath + img1Name + "grayA.jpg",grayA)
        # cv2.imwrite(savePath + img2Name + "grayB.jpg",grayB)
        height , width = grayA.shape
        # grayA = cv2.Canny(grayA, 20, 150)
        # grayB = cv2.Canny(grayB, 20, 150)
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))  # 定义结构元素的形状和大小
        # grayA = cv2.dilate(grayA, kernel)
        # grayB = cv2.dilate(grayB, kernel)
        # cv2.imshow("grayA",grayA)
        # cv2.imshow("grayB",grayB)
        # cv2.waitKey(0)
        # print(grayA.shape, grayB.shape)
        try:
            (score, diff) = compare_ssim(grayA, grayB, full=True)
        except ValueError:
            print("shape不同")
            return
        diff = (diff * 255).astype("uint8")

        # print("SSIM: {}".format(score))

        thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        for c in cnts:
            shapeA = []
            shapeB = []
            x, y, w, h = cv2.boundingRect(c)
            if x == 0 or y == 0 or x + w == width or y + h == height or w * h < 2500:
                continue
            score = compare_ssim(grayA[y:y + h, x:x + w], grayB[y:y + h, x:x + w])
            if score > 0.8:
                print("same",score)
                continue
            shapeA.append(str(score))
            shapeA.append([(x * 2 + xA,y * 2 + yA),(x * 2 + xA + w * 2, y * 2 + yA),(x * 2 + xA + w * 2, y * 2 + yA + h * 2),(x * 2 + xA, y * 2 + yA + h * 2)])
            shapeB.append(str(score))
            shapeB.append([(x * 2 + xB, y * 2 + yB), (x * 2 + xB + w * 2, y * 2 + yB), (x * 2 + xB + w * 2, y * 2 + yB + h * 2),(x * 2 + xB, y * 2 + yB + h * 2)])
            # cv2.rectangle(imgA, (x * 2 + xA, y * 2 + yA), (x * 2 + xA + w * 2, y * 2 + yA + h * 2), (0, 0, 255), 2)
            # cv2.rectangle(imgB, (x * 2 + xB, y * 2 + yB), (x * 2 + xB + w * 2, y * 2 + +yB +h * 2), (0, 0, 255), 2)
            self.shapesA.append(shapeA)
            self.shapesB.append(shapeB)

    def compare(self,flag = None):
        # load image
        imgA = self.cv_imread(self.filePath1)
        imgB = self.cv_imread(self.filePath2)
        xA, yA, wA, hA = self.findPCB(imgA)
        xB, yB, wB, hB = self.findPCB(imgB, wA, hA)
        if flag:
            pointListA, pointListB = self.siftDetect(imgA[yA:yA + hA, xA:xA + wA], imgB[yB:yB + hB, xB:xB + wB])
            if len(pointListA) != 0 and len(pointListB) != 0:
                mean = np.mean(pointListA - pointListB, axis=0)
                print(mean)
                M = np.float32([[1,0,-mean[0]],[0,1,-mean[1]]])
                imgA = cv2.warpAffine(imgA, M, (imgA.shape[1], imgA.shape[0]))
                self.ssimMatch(imgA, xA, yA, wA, hA, imgB, xB, yB, wB, hB)
                return self.shapesA, self.shapesB
            else:
                print("SIFT校正失败，采取普通方式识别！")
                self.ssimMatch(imgA, xA, yA, wA, hA, imgB, xB, yB, wB, hB)
                return self.shapesA, self.shapesB
        else:
            self.ssimMatch(imgA, xA, yA, wA, hA, imgB, xB, yB, wB, hB)
            return self.shapesA, self.shapesB

