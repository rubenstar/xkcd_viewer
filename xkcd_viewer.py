import string
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

# Timeframes have to be in order from earliest to latest
timeframes = [QTime(9, 0, 0, 0), QTime(12, 0, 0, 0), QTime(15, 0, 0, 0)]


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
    downloadDone = pyqtSignal(object, object, object)

    def downloadPicRaw(self):
        self.scrapingUrl.emit()
        webpage_html = requests.get(URL)
        webpage_soup = BeautifulSoup(webpage_html.content, "html.parser")

        comic_html = webpage_soup.find(id="comic")
        main_title = webpage_soup.find(id="ctitle").string
        if comic_html.img["title"] is not None:
            sub_title = str(comic_html.img["title"])

        if comic_html.img.has_attr("srcset"):
            comic_url = comic_html.img["srcset"]
            comic_url = comic_url[: len(comic_url) - 3]  # Remove "2x" at end of string
        else:
            comic_url = comic_html.img["src"]

        comic_url = "http:" + comic_url
        print(comic_url)

        self.downloadingPic.emit()

        file_tuple = request.urlretrieve(comic_url)
        filepath = file_tuple[0]

        self.downloadDone.emit(filepath, main_title, sub_title)


class MainWindow(QMainWindow):

    receivedPic = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        self.pic_pixmap = None
        self.main_title_string = None
        self.sub_title_string = None
        self.old_timeframe_idx = 0
        self.print_string = ""

        self.setWindowTitle("xkcd viewer (github: rubenstar/xkcd_viewer)")

        # Set up button widget
        self.button = QPushButton("Click for new comic now!")
        self.button.setFixedHeight(30)
        self.button.setCheckable(True)
        self.button.clicked.connect(self.downloadThreadStart)

        # Set up center image widget
        self.pic = QLabel(self)
        self.pic.setMinimumSize(1, 1)
        self.pic.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set up text widgets
        self.time_text = QLabel(self)
        self.time_text.setFixedHeight(30)
        self.time_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_title_text = QLabel(self)
        self.main_title_text.setFixedHeight(40)
        self.main_title_text.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.main_title_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.sub_title_text = QLabel(self)
        self.sub_title_text.setFixedHeight(40)
        self.sub_title_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sub_title_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Start a timer
        self.timer = QTimer()
        self.timer.start(10000)  # Generate signal every 10s
        self.timer.timeout.connect(self.checkTime)

        self.time = QTime()

        # Set up layouting
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.main_title_text)
        self.layout.addWidget(self.pic)
        self.layout.addWidget(self.sub_title_text)
        self.layout.addWidget(self.time_text)
        self.layout.addWidget(self.button)

        self.widget = QWidget()
        self.widget.setLayout(self.layout)

        self.setCentralWidget(self.widget)

    def checkTime(self):
        no_of_timeframes = len(timeframes)
        self.current_time = self.time.currentTime()

        # Initial value. If current time is smaller then the first timeframe, its the same as bigger than the last
        self.current_timeframe_idx = len(timeframes)
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

        print_string = (
            "Next comic at "
            + str(next_time)
            + ". (That's in "
            + str(self.hours_to_next)
            + " hour(s) and "
            + str(self.minutes_to_next)
            + " minute(s).)"
        )

        self.time_text.setText(print_string)

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

    def loadTitle(self):
        if self.main_title_string is not None:
            self.main_title_text.setText(
                "<h1><strong>" + self.main_title_string + "</strong></h1>"
            )
        else:
            self.main_title_text.setText(
                "<h1><strong> No main title found :( </strong></h1>"
            )

        if self.sub_title_string is not None:
            self.sub_title_text.setText(
                "<h3><strong>" + self.sub_title_string + "<h3><strong>"
            )
        else:
            self.sub_title_text.setText("<h6><strong> No subtitle found :(<h6><strong>")

    def updateImage(self, filepath, main_title, sub_title):
        self.pic_pixmap = QPixmap(filepath)
        self.main_title_string = main_title
        self.sub_title_string = sub_title
        self.receivedPic.emit()  # Signal back to thread/worker that we're done
        self.button.setEnabled(True)
        self.button.setChecked(False)

        self.loadImage()
        self.loadTitle()

    def downloadThreadStart(self):
        self.button.setEnabled(False)
        self.downloadThread = DownloadThread()
        self.downloadThread.startThread()

    # Overwrite resizeEvent
    def resizeEvent(self, a0: QResizeEvent):
        self.loadImage()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    window.checkTime()

    app.exec()
