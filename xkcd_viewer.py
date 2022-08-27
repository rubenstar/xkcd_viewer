from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt, QTimer, QTime
from PyQt6.QtGui import QPixmap, QResizeEvent
import sys
from urllib import request
import requests
from bs4 import BeautifulSoup

URL = "https://c.xkcd.com/random/comic/"

timeframes = [QTime(0, 0, 0, 0), QTime(12, 0, 0, 0), QTime(16, 0, 0, 0)]


class MainWindow(QMainWindow):

    receivedPic = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        self.pic_pixmap = None
        self.old_timeframe_idx = 0
        self.print_string = ""

        self.setWindowTitle("xkcd viewer v1.0 by rust")

        # Set up button widget
        self.button = QPushButton("Click for new comic now!")
        self.button.setCheckable(True)
        self.button.clicked.connect(self.downloadThreadStart)

        # Set up center image widget
        self.pic = QLabel(self)
        self.pic.setMinimumSize(1, 1)
        self.pic.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set up text widget
        self.text = QLabel(self)
        self.text.setFixedHeight(30)
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Start a timer
        self.timer = QTimer()
        self.timer.start(1000)  # Generate signal every 10s
        self.timer.timeout.connect(self.checkTime)

        self.time = QTime()

        # Set up layouting
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.pic)
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.button)

        self.widget = QWidget()
        self.widget.setLayout(self.layout)

        self.setCentralWidget(self.widget)

    def checkTime(self):
        no_of_timeframes = len(timeframes)
        self.current_time = self.time.currentTime()

        for i in range(no_of_timeframes):
            if self.current_time > timeframes[i]:
                self.current_timeframe_idx = i

        if self.current_timeframe_idx != self.old_timeframe_idx:
            self.downloadThreadStart()
            self.old_timeframe_idx = self.current_timeframe_idx

        self.next_timeframe_idx = (self.current_timeframe_idx + 1) % no_of_timeframes
        seconds_to_next = self.current_time.secsTo(timeframes[self.next_timeframe_idx])

        if seconds_to_next < 0:
            seconds_to_next = seconds_to_next + 86400

        self.hours_to_next = seconds_to_next // 3600
        self.minutes_to_next = ((seconds_to_next % 3600) // 60) + 1

        next_time = timeframes[self.next_timeframe_idx].toString("hh:mm")

        #print(seconds_to_next)
        print_string = (
            "Next comic at "
            + str(next_time)
            + ". (That's in "
            + str(self.hours_to_next)
            + " hour(s) and "
            + str(self.minutes_to_next)
            + " minutes.)"
        )

        self.text.setText(print_string)

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
        self.finished.connect(lambda: window.button.setText("Click for new comic now!"))

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

        self.downloadDone.emit(filepath)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
