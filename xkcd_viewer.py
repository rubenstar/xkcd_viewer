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
from PyQt5.QtGui import QResizeEvent
from io import BytesIO
from PIL import Image, ImageQt
from bs4 import BeautifulSoup

import sys
import requests

URL = "https://c.xkcd.com/random/comic/"


class MainWindow(QMainWindow):

    receivedPic = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        self.pic_pixmap = None

        self.setWindowTitle("xkcd viewer v1.0 by rust")

        # Set up button widget
        self.button = QPushButton("New comic!")
        self.button.setCheckable(True)
        self.button.clicked.connect(self.downloadThreadStart)

        # Set up center image widget
        self.pic = QLabel(self)
        self.pic.setMinimumSize(1, 1)
        self.pic.setAlignment(Qt.AlignCenter)

        # Set up layouting
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pic)
        self.layout.addWidget(self.button)

        self.widget = QWidget()
        self.widget.setLayout(self.layout)

        self.setCentralWidget(self.widget)

    def loadImage(self):
        if self.pic_pixmap is not None:
            self.pic.setPixmap(
                self.pic_pixmap.scaled(
                    self.pic.width(),
                    self.pic.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def updateImage(self, pic_pixmap):
        self.pic_pixmap = pic_pixmap
        self.receivedPic.emit()  # Signal back to thread/worker that we're done

        self.loadImage()

    def downloadThreadStart(self):
        self.downloadThread = DownloadThread()
        self.downloadThread.startThread()

    # Overwrite resizeEvent
    def resizeEvent(self, a0: QResizeEvent):
        self.loadImage()


class DownloadThread(QThread):
    def __init__(self):
        super(DownloadThread, self).__init__()

    def startThread(self):
        self.worker = DownloadWorker()
        self.worker.moveToThread(self)

        # Connects
        self.started.connect(self.worker.downloadPicRaw)
        self.started.connect(lambda: window.button.setEnabled(False))
        self.worker.downloadDone.connect(window.updateImage)
        self.worker.scrapingUrl.connect(
            lambda: window.button.setText("Scraping xkcd.com for comic URL...")
        )
        self.worker.downloadingPic.connect(
            lambda: window.button.setText("Downloading comic...")
        )

        # Cleanup
        window.receivedPic.connect(self.quit)  # Shutdown thread
        window.receivedPic.connect(
            self.worker.deleteLater
        )  # Schedule worker for deletion
        self.finished.connect(self.deleteLater)  # Schedule thread itself for deletion
        self.finished.connect(lambda: window.button.setEnabled(True))
        self.finished.connect(lambda: window.button.setChecked(False))
        self.finished.connect(lambda: window.button.setText("New comic!"))

        self.start()  # Start the thread


class DownloadWorker(QObject):
    scrapingUrl = pyqtSignal()
    downloadingPic = pyqtSignal()
    downloadDone = pyqtSignal(object)

    def downloadPicRaw(self):
        self.scrapingUrl.emit()
        webpage_html = requests.get(URL)
        webpage_soup = BeautifulSoup(webpage_html.content, "html5lib")

        table = webpage_soup.find("div", attrs={"id": "comic"})

        if table.img.has_attr("srcset"):
            pic_url = table.img["srcset"]
            pic_url = pic_url[: len(pic_url) - 3]  # Remove " 2x" at end of string
        else:
            pic_url = table.img["src"]

        pic_url = "http:" + pic_url
        print(pic_url)

        self.downloadingPic.emit()
        pic_bytestring = requests.get(pic_url)
        pic_raw = Image.open(BytesIO(pic_bytestring.content))
        pic_pixmap = ImageQt.toqpixmap(pic_raw)

        self.downloadDone.emit(pic_pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec_()
