#####################################################################
#                                                                   #
# /plugins/monitor_inputs/__init__.py                               #
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
import numpy as np
import datetime
import time

from qtutils import UiLoader
from qtutils.qt.QtCore import*
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from PyQt5.QtWidgets import QGridLayout, QLabel, QWidget, QLineEdit

from labscript_utils.shared_drive import path_to_agnostic
from labscript_utils.ls_zprocess import Lock
from blacs.plugins import PLUGINS_DIR

name = "Monitor"
module = "monitor_inputs" # should be folder name
logger = logging.getLogger('BLACS.plugin.%s'%module)

from PyDAQmx.DAQmxFunctions import *
from PyDAQmx.DAQmxConstants import *

class MultiChannelAnalogInput():
    """Class to create a multi-channel analog input
    
    Usage: AI = MultiChannelInput(physicalChannel)
        physicalChannel: a string or a list of strings
    optional parameter: limit: tuple or list of tuples, the AI limit values
                        reset: Boolean
    Methods:
        read(name), return the value of the input name
        read_all(), return a dictionary name:value
    """
    def __init__(self,physicalChannel, limit = None, reset = False, Mock=False):
        self.Mock = Mock
        if type(physicalChannel) == type(""):
                self.physicalChannel = [physicalChannel]
        else:
                self.physicalChannel  =physicalChannel
        if not self.Mock:
            
            self.numberOfChannel = physicalChannel.__len__()
            if limit is None:
                self.limit = dict([(name, (-10.0,10.0)) for name in self.physicalChannel])
            elif type(limit) == tuple:
                self.limit = dict([(name, limit) for name in self.physicalChannel])
            else:
                self.limit = dict([(name, limit[i]) for  i,name in enumerate(self.physicalChannel)])           
            if reset:
                DAQmxResetDevice(physicalChannel[0].split('/')[0] )
    def configure(self):
        if not self.Mock:
            # Create one task handle per Channel
            taskHandles = dict([(name,TaskHandle(0)) for name in self.physicalChannel])
            for name in self.physicalChannel:
                DAQmxCreateTask("",byref(taskHandles[name]))
                DAQmxCreateAIVoltageChan(taskHandles[name],name,"",DAQmx_Val_RSE,
                                        self.limit[name][0],self.limit[name][1],
                                        DAQmx_Val_Volts,None)
            self.taskHandles = taskHandles
    def read_all(self):

        return dict([(name,self.read(name)) for name in self.physicalChannel])

    def read(self,name = None):
        if not self.Mock:
            if name is None:
                name = self.physicalChannel[0]
            taskHandle = self.taskHandles[name]                    
            DAQmxStartTask(taskHandle)
            data = numpy.zeros((1,), dtype=numpy.float64)
    #        data = AI_data_type()
            read = int32()
            DAQmxReadAnalogF64(taskHandle,1,10.0,DAQmx_Val_GroupByChannel,data,1,byref(read),None)
            DAQmxStopTask(taskHandle)
            #DAQmxClearTask(taskHandle)
            return data[0]
        else:
            return np.random.rand()


class Plugin(object):
    def __init__(self, initial_settings):
        self.Mock = True
        if self.Mock:
            self.dev_name = 'Mock'
        else:
            self.dev_name = 'Dev2'
        self.num_ai = 4
        self.menu = None
        self.notifications = {}
        self.BLACS = None
        self.ui = None
        self.continue_measurement = True

        self.ai_card = MultiChannelAnalogInput(["Dev2/ai3", "Dev2/ai2", "Dev2/ai1","Dev2/ai0"], Mock=True)
        self.ai_card.configure()



        
    def plugin_setup_complete(self, BLACS):
        """Do additional plugin setup after blacs has done more starting up.

        Plugins are initialized early on in blacs's start up. This method is
        called later on during blacs's startup once more things, such as the
        experiment queue, have been created. Therefore any setup that requires
        access to those other parts of blacs must be done here rather than in
        the plugin's `__init__()` method.

        Args:
            BLACS (dict): A dictionary where the keys are strings and the values
                are various parts of `blacs.__main__.BLACS`. For more details on
                exactly what is included in that dictionary, examine the code in
                `blacs.__main__.BLACS.__init__()` (there this dictionary, as of
                this writing, is called `blacs_data`).
        """
        
        self.BLACS = BLACS

        self.ui = UiLoader().load(os.path.join(PLUGINS_DIR, module, 'monitor_inputs.ui'))
        BLACS['ui'].queue_controls_frame.layout().addWidget(self.ui)

        name_label = QLabel()
        name_label.setText("Dev Name: ")
        self.ui.widget.layout().addWidget(name_label, 0, 0, 1, 2)
        dev_name_edit = QLabel()
        dev_name_edit.setText(self.dev_name)
        self.ui.widget.layout().addWidget(dev_name_edit, 0, 2, 1, 2)


        self.ai_dict = {}

        for ai in range(4):
            ai_label = QLabel()
            ai_label.setText("AI #{}".format(ai))
            self.ui.widget.layout().addWidget(ai_label, 1, ai)
            self.ai_dict[ai] = QLabel()
            self.ai_dict[ai].setText("rdm{}".format(ai))
            self.ui.widget.layout().addWidget(self.ai_dict[ai], 2, ai)


        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ai_labels)
        self.timer.start(1000)
        

    def update_ai_labels(self):
        """Update the labels for the analog inputs of the device
        """
        
        if self.continue_measurement:
            vals_dict = self.ai_card.read_all()

            for ai_num in range(len(self.ai_dict)):
                self.ai_dict[ai_num].setText("{:.3f}".format(vals_dict['Dev2/ai{}'.format(ai_num)]))
        

    def get_save_data(self):
        return {}

    def stop_measurement(self, path):
        self.continue_measurement = False

    def start_measurement(self, path):
             self.continue_measurement = True
    
    def get_callbacks(self):
        """See https://github.com/labscript-suite/blacs/blob/8551005e0e3ee7934f4524e2a85f7c5437ee68e8/blacs/experiment_queue.py
        for the possible callbacks. These are functions to call when blacs enters certain states.

        Returns:
            Callback: the callback function to call when the experiment queue enters the given state.
        """
        callbacks = {
            'pre_transition_to_buffered': self.stop_measurement,
            'shot_complete': self.start_measurement,
        }
        return callbacks

    def mainloop(self):
        pass
        
    def close(self):
        pass


    # The rest of these are boilerplate:
    def get_menu_class(self):
        return None
        
    def get_notification_classes(self):
        return []
        
    def get_setting_classes(self):
        return []
    
    def set_menu_instance(self, menu):
        self.menu = menu
        
    def set_notification_instances(self, notifications):
        self.notifications = notifications