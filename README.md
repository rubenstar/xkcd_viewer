# xkcd_viewer
PyQt GUI to view a random XKCD comic. Made to display on a breakroom, or wherever people want to see these comics in fullscreen. 

Will auto-update to a new random comic at times specified in
```python
timeframes = [QTime(9, 0, 0, 0), QTime(12, 0, 0, 0), QTime(15, 0, 0, 0)] #QTime(h, m, s, ms)
```

Install dependencies
```shell
python3 -m pip install PyQt6 bs4 requests html5lib
```

Run with 
```shell
python3 xkcd_viewer.py
```

Build platform dependant executable with
```shell
pyinstaller -F xkcd_viewer.py
```
