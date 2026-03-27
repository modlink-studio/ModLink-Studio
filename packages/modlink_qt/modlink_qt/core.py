"""PyQt6-backed QtCore compatibility layer.

This package exists so shared runtime code can stop importing Qt bindings
directly. The first implementation stays on PyQt6; later work can swap the
backend without changing core/sdk call sites.
"""

from PyQt6.QtCore import (
    QCoreApplication,
    QObject,
    QStandardPaths,
    QThread,
    QTimer,
    Qt,
    pyqtSignal,
    pyqtSlot,
)

__all__ = [
    "QCoreApplication",
    "QObject",
    "QStandardPaths",
    "QThread",
    "QTimer",
    "Qt",
    "pyqtSignal",
    "pyqtSlot",
]
