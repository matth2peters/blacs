#####################################################################
#                                                                   #
# /plugins/monitor_analog_inputs/__init__.py                        #
#                                                                   #
#                                                                   #
# This file is part of the program BLACS, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import logging
import os
import subprocess
import threading
import sys
from queue import Queue

from qtutils import UiLoader
from qtutils.qt.QtCore import*
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from PyQt5.QtWidgets import QGridLayout, QLabel, QWidget, QLineEdit

import numpy as np

from labscript_utils.shared_drive import path_to_agnostic
from labscript_utils.ls_zprocess import Lock
from blacs.plugins import PLUGINS_DIR

name = "Monitor"
module = "monitor" # should be folder name
logger = logging.getLogger('BLACS.plugin.%s'%module)


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("My App")

        ui = UiLoader().load(os.path.join(PLUGINS_DIR, module, 'monitor.ui'))


        name_label = QLabel()
        name_label.setText("Dev Name: {}".format('empty'))
        ui.widget.layout().addWidget(name_label, 0, 0, 1, 2)
        dev_name_edit = QLineEdit()
        dev_name_edit.setText('asd')
        ui.widget.layout().addWidget(dev_name_edit, 0, 2, 1, 2)

        self.ai_dict = {}

        for ai in range(4):
            ai_label = QLabel()
            ai_label.setText("AI #{}".format(ai))
            ui.widget.layout().addWidget(ai_label, 1, ai)
            self.ai_dict[ai] = QLabel()
            self.ai_dict[ai].setText("rdm{}".format(ai))
            ui.widget.layout().addWidget(self.ai_dict[ai], 2, ai)

        self.setCentralWidget(ui)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ai_labels)
        self.timer.start(1000)  # every 10,000 milliseconds

    def update_ai_labels(self):

        for ai_num in range(len(self.ai_dict)):
            self.ai_dict[ai_num].setText(str(np.random.rand()))
        

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()