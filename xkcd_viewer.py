from urllib.parse import parse_qs
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageQt

import sys
import requests


URL = "https://c.xkcd.com/random/comic/"

comic_pixmap = None
mutex = QMutex()


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle("xkcd viewer by rust")

        # Set up thread for picture download
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.resizeImage)
        self.thread.finished.connect(lambda: self.button.setEnabled(True))
        self.worker.starting.connect(lambda: self.button.setEnabled(False))
        self.worker.scraping_url.connect(
            lambda: self.button.setText("Scraping HTML for comic URL...")
        )
        self.worker.download_pic.connect(
            lambda: self.button.setText("Downloading comic...")
        )
        self.thread.finished.connect(lambda: self.button.setText("New comic!"))

        # Set up center image widget
        self.pic = QLabel(self)
        self.pic.setMinimumSize(1, 1)
        self.pic.setAlignment(Qt.AlignCenter)

        # Set up button widget
        self.button = QPushButton("New comic!")
        self.button.setCheckable(True)
        self.button.clicked.connect(self.setImage)

        # Layouting
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
        global comic_pixmap

        if comic_pixmap is not None and mutex.tryLock:
            self.pic.setPixmap(
                comic_pixmap.scaled(
                    self.pic.width(),
                    self.pic.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            mutex.unlock()

    def setImage(self):
        self.thread.start()


class Worker(QObject):
    starting = pyqtSignal()
    scraping_url = pyqtSignal()
    download_pic = pyqtSignal()
    finished = pyqtSignal()

    def run(self):
        global comic_pixmap

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

        mutex.lock()
        comic_pixmap = ImageQt.toqpixmap(comic_raw)
        mutex.unlock()

        self.finished.emit()  # Signal finish!!


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()
