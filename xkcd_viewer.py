from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPixmap, QResizeEvent
import sys
from urllib import request
import requests
from bs4 import BeautifulSoup

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
        self.pic.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def updateImage(self, filepath):
        self.pic_pixmap = QPixmap(filepath)
        self.receivedPic.emit()  # Signal back to thread/worker that we're done
        self.button.setEnabled(True)
        self.button.setChecked(False)

        self.loadImage()

    def downloadThreadStart(self):
        self.button.setEnabled(False)
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

        file_tuple = request.urlretrieve(pic_url)
        filepath = file_tuple[0]

        print(f"Temporary filepath: {filepath}")

        self.downloadDone.emit(filepath)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
