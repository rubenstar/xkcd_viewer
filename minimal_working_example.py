from re import I
from PyQt5.QtWidgets import (
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QObject
from io import BytesIO
from PIL import Image, ImageQt

import sys
import requests


class MainWindow(QMainWindow):

    receivedPic = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.pic_pixmap = None

        # Set up button widget
        self.button = QPushButton("New picture")
        self.button.setCheckable(True)
        self.button.clicked.connect(self.downloadThreadStart)

        # Set up center image widget
        self.pic = QLabel(self)
        self.pic.setAlignment(Qt.AlignCenter)

        # Set up layouting
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pic)
        self.layout.addWidget(self.button)

        self.widget = QWidget()
        self.widget.setLayout(self.layout)

        self.setCentralWidget(self.widget)

    def loadImage(self):
        self.pic.setPixmap(self.pic_pixmap)

    def updateImage(self, pic_raw):
        print("Received pic")
        self.pic_pixmap = ImageQt.toqpixmap(pic_raw) 
        self.receivedPic.emit() #Signal back to worker that we're done

        self.loadImage()

    def downloadThreadStart(self):
        self.workerThread = QThread()
        self.worker = DownloadWorker()
        self.worker.moveToThread(self.workerThread)

        self.workerThread.started.connect(self.worker.downloadPicRaw)

        self.worker.downloadDone.connect(self.updateImage)
        #Cleanup
        self.receivedPic.connect(self.workerThread.quit) #Shut down thread
        self.receivedPic.connect(self.worker.deleteLater) #Schedule worker for deletion
        self.workerThread.finished.connect(self.workerThread.deleteLater) #Schedule worker thread itself for deletion


        #Start thread
        print("Start thread")
        self.workerThread.start()


class DownloadWorker(QObject):
    downloadDone = pyqtSignal(object)
    deleteMe = pyqtSignal()

    def downloadPicRaw(self):
        print("Downloading pic")
        pic_bytestring = requests.get("https://pngimg.com/uploads/bear/small/bear_PNG23466.png")
        pic_raw = Image.open(BytesIO(pic_bytestring.content))
        pic_pixmap = ImageQt.toqpixmap(pic_raw) 
        print("Downloaded pic")
        self.downloadDone.emit(pic_pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec_()
