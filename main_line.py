import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QRubberBand, QWidget
from PyQt5.QtCore import QRect, QPoint, Qt
from PyQt5.QtGui import QPainter, QPen

class LineDrawer(QWidget):
    def __init__(self):
        super().__init__()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.drawing = False
        self.rubber_band = QRubberBand(QRubberBand.Line, self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.rubber_band.setGeometry(QRect(self.start_point, QSize()))
            self.rubber_band.show()
            self.drawing = True

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.rubber_band.setGeometry(QRect(self.start_point, self.end_point).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.end_point = event.pos()
            self.rubber_band.hide()
            self.drawing = False
            self.update()

    def paintEvent(self, event):
        if not self.start_point.isNull() and not self.end_point.isNull():
            painter = QPainter(self)
            pen = QPen(Qt.black, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.start_point, self.end_point)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setCentralWidget(LineDrawer())
        self.setWindowTitle("Line Drawer")
        self.setGeometry(100, 100, 800, 600)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())