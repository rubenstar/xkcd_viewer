from PyQt5.QtGui import QResizeEvent, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)
from PyQt5.QtCore import QThread, pyqtSignal, QObject, Qt
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageQt

import sys
import requests

URL = "https://c.xkcd.com/random/comic/"


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle("xkcd viewer v1.0 by rust")

        self.comic_pixmap = None

        # Set up worker thread for picture fetch and display
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.starting.connect(lambda: self.button.setEnabled(False))
        self.worker.scraping_url.connect(
            lambda: self.button.setText("Scraping xkcd.com for comic URL...")
        )
        self.worker.download_pic.connect(
            lambda: self.button.setText("Downloading comic...")
        )
        self.worker.pass_pic.connect(self.updateImage)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.resizeImage)
        self.worker.finished.connect(lambda: self.button.setEnabled(True))
        self.thread.finished.connect(lambda: self.button.setText("New random comic!"))

        # Set up center image widget
        self.pic = QLabel(self)
        self.pic.setMinimumSize(1, 1)
        self.pic.setAlignment(Qt.AlignCenter)

        # Set up button widget
        self.button = QPushButton("New random comic!")
        self.button.setCheckable(True)
        self.button.clicked.connect(self.setImage)

        # Set up layouting
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pic)
        self.layout.addWidget(self.button)

        self.widget = QWidget()
        self.widget.setLayout(self.layout)

        self.setCentralWidget(self.widget)

    # Overwrite resizeEvent
    def resizeEvent(self, a0: QResizeEvent):
        self.resizeImage()

    def resizeImage(self):
        if self.comic_pixmap is not None:
            self.pic.setPixmap(
                self.comic_pixmap.scaled(
                    self.pic.width(),
                    self.pic.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def updateImage(self, pixmap):
        self.comic_pixmap = pixmap

    def setImage(self):
        self.thread.start()


class Worker(QObject):
    starting = pyqtSignal()
    scraping_url = pyqtSignal()
    download_pic = pyqtSignal()
    pass_pic = pyqtSignal(QPixmap)
    finished = pyqtSignal()

    def run(self):
        self.scraping_url.emit()

        webpage_html = requests.get(URL)
        webpage_soup = BeautifulSoup(webpage_html.content, "html5lib")

        table = webpage_soup.find("div", attrs={"id": "comic"})

        if table.img.has_attr("srcset"):
            comic_url = table.img["srcset"]
            comic_url = comic_url[: len(comic_url) - 3]  # Remove " 2x" at end of string
        else:
            comic_url = table.img["src"]

        comic_url = "http:" + comic_url
        print(comic_url)

        self.download_pic.emit()
        comic_bytestring = requests.get(comic_url)

        comic_raw = Image.open(BytesIO(comic_bytestring.content))

        comic_pixmap = ImageQt.toqpixmap(comic_raw)

        self.pass_pic.emit(comic_pixmap)

        self.finished.emit()


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()
