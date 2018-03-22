import sys
import math
import cv2
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from strokeExtractingMainwindow import Ui_MainWindow
from utils.Functions import splitConnectedComponents


class StrokeExtractToolMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(StrokeExtractToolMainWindow, self).__init__()
        self.setupUi(self)

        self.image_pix = QPixmap()
        self.temp_image_pix = QPixmap()

        self.scene = GraphicsScene()
        self.image_view.setScene(self.scene)

        self.lastPoint = QPoint()
        self.endPoint = QPoint()

        self.image_gray = None
        self.image_path = ""

        # radicals
        self.radicals = []
        self.radicals_name = []

        self.radical_slm = QStringListModel()
        self.radical_slm.setStringList(self.radicals_name)
        self.radical_listview.setModel(self.radical_slm)
        self.radical_listview.clicked.connect(self.radicalsListView_clicked)

        # add listener
        self.open_btn.clicked.connect(self.openBtn)
        self.extract_btn.clicked.connect(self.extractBtn)
        self.clear_btn.clicked.connect(self.clearBtn)
        self.exit_btn.clicked.connect(self.exitBtn)
        self.radicalExtract_btn.clicked.connect(self.radicalsExtractBtn)

    def openBtn(self):
        """
            Open button clicked function.
        :return:
        """
        print("Open button clicked!")
        self.scene.clear()
        filename, _ = QFileDialog.getOpenFileName(None, "Open file", QDir.currentPath())
        if filename:

            # image file path
            self.image_path = filename

            qimage = QImage(filename)
            if qimage.isNull():
                QMessageBox.information(self, "Image viewer", "Cannot load %s." % filename)
                return

            # grayscale image
            img_ = cv2.imread(filename, 0)
            _, img_ = cv2.threshold(img_, 127, 255, cv2.THRESH_BINARY)
            self.image_gray = img_.copy()

            self.image_pix = QPixmap.fromImage(qimage)
            self.temp_image_pix = self.image_pix.copy()
            self.scene.addPixmap(self.image_pix)
            self.scene.update()

    def radicalsExtractBtn(self):
        """
            Radical extract button clicked function.
        :return:
        """
        print("Radicals extract btn clicked!")
        if self.image_gray is None:
            QMessageBox.information(self, "Grayscale image is None!")
            return
        self.radicals = None
        # get all radicals of character
        radicals = splitConnectedComponents(self.image_gray)

        print("number of radicals: %d" % len(radicals))

        self.radicals = radicals.copy()
        self.radicals_name = []
        for i in range(len(radicals)):
            self.radicals_name.append("radical_" + str(i+1))
        self.radical_slm.setStringList(self.radicals_name)

    def radicalsListView_clicked(self, qModelIndex):
        """
            Radical list view item clicked function.
        :param qModelIndex:
        :return:
        """
        print("radical list %s th clicked!" % str(qModelIndex.row()))

        # numpy.narray to QImage and QPixmap
        img_ = self.radicals[qModelIndex.row()]

        if img_ is None:
            return
        img_ = np.array(img_, dtype=np.uint8)
        print(img_.shape)
        qimg = QImage(img_.data, img_.shape[1], img_.shape[0], QImage.Format_Indexed8)

        self.image_pix = QPixmap.fromImage(qimg)
        self.temp_image_pix = self.image_pix.copy()
        self.scene.addPixmap(self.image_pix)
        self.scene.update()

    def extractBtn(self):
        """
            Extracting button clicked function.
        :return:
        """
        print("Extract button clicked")
        if self.image_gray is None:
            QMessageBox.information(self, "Grayscale image is None!")
            return
        # save image
        saved_img = None
        if self.scene.points is None or len(self.scene.points) == 0:
            # No points selected, return all image
            saved_img = self.image_gray.copy()
        else:
            saved_img = extractStorkeByPolygon(self.image_gray, self.scene.points)

        # get save path
        fileName, _ = QFileDialog.getSaveFileName(self, 'Dialog Title', QDir.currentPath())
        print("save path: " + fileName)
        cv2.imwrite(fileName, saved_img)

    def clearBtn(self):
        """
            Clear button clicked function.
        :return:
        """
        print("Clear !")

        # remove existing points
        self.scene.lastPoint = QPoint()
        self.scene.endPoint = QPoint()
        self.scene.points = []

        # remove points in image
        self.image_pix = self.temp_image_pix.copy()
        self.scene.addPixmap(self.image_pix)
        self.scene.update()

    def exitBtn(self):
        """
            Exiting button clicked function.
        :return:
        """
        qApp = QApplication.instance()
        sys.exit(qApp.exec_())


class GraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        QGraphicsScene.__init__(self, parent)

        self.lastPoint = QPoint()
        self.endPoint = QPoint()

        self.points = []
        self.strokes = []
        self.T_DISTANCE = 10

    def setOption(self, opt):
        self.opt = opt

    def mousePressEvent(self, event):
        print(event.scenePos())
        pen = QPen(Qt.red)
        brush = QBrush(Qt.red)
        x = event.scenePos().x()
        y = event.scenePos().y()

        if len(self.points) == 0:
            self.addEllipse(x, y, 2, 2, pen, brush)
            self.endPoint = event.scenePos()
        else:
            x0 = self.points[0][0]
            y0 = self.points[0][1]

            dist = math.sqrt((x - x0) * (x - x0) + (y - y0) * (y - y0))
            if dist < self.T_DISTANCE:
                pen_ = QPen(Qt.green)
                brush_ = QBrush(Qt.green)
                self.addEllipse(x0, y0, 2, 2, pen_, brush_)
                self.endPoint = event.scenePos()
                x = x0; y = y0
            else:
                self.addEllipse(x, y, 4, 4, pen, brush)
                self.endPoint = event.scenePos()
        self.points.append((x, y))

    def mouseReleaseEvent(self, event):
        pen = QPen(Qt.red)

        if self.lastPoint.x() != 0.0 and self.lastPoint.y() != 0.0:
            self.addLine(self.endPoint.x(), self.endPoint.y(), self.lastPoint.x(), self.lastPoint.y(), pen)

        self.lastPoint = self.endPoint


def extractStorkeByPolygon(image, polygon):

    image_ = image.copy()

    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            if not ray_tracing_method(x, y, polygon):
                image_[y][x] = 255

    return image_


# Ray tracing check point in polygon
def ray_tracing_method(x,y,poly):

    n = len(poly)
    inside = False

    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside

if __name__ == '__main__':
    app = QApplication(sys.argv)
    MainWindow = StrokeExtractToolMainWindow()
    # ui = strokeExtractingMainwindow.Ui_MainWindow()
    # ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())