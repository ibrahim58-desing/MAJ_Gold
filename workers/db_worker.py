"""
QThread-based DB worker to run service calls off the UI thread.
Usage:
    worker = DBWorker(service_fn, arg1, kwarg=val)
    worker.result.connect(self.on_result)
    worker.error.connect(self.on_error)
    worker.start()
"""
from PyQt6.QtCore import QThread, pyqtSignal


class DBWorker(QThread):
    result = pyqtSignal(object)
    error  = pyqtSignal(str)

    _active_workers = set()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        DBWorker._active_workers.add(self)
        self.finished.connect(self._on_finished)

    def run(self):
        try:
            out = self._fn(*self._args, **self._kwargs)
            self.result.emit(out)
        except Exception as e:
            self.error.emit(str(e))

    def _on_finished(self):
        if self in DBWorker._active_workers:
            DBWorker._active_workers.remove(self)
