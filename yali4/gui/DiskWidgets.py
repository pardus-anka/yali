# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *

import gettext
__trans = gettext.translation('yali4', fallback=True)
_ = __trans.ugettext

import yali4.storage
import yali4.filesystem as filesystem
import yali4.partitionrequest as request
import yali4.partitiontype as parttype
import yali4.parteddata as parteddata

import yali4.gui.context as ctx
from yali4.gui.Ui.partedit import Ui_PartEdit
from yali4.gui.GUIException import *

class DiskList(QtGui.QWidget):
    def __init__(self, partEdit, *args):
        QtGui.QWidget.__init__(self,None)
        self.resize(QSize(QRect(0,0,600,80).size()).expandedTo(self.minimumSizeHint()))
        self.setAutoFillBackground(False)
        self.diskCount = 1
        self.partEdit = partEdit
        self.setStyleSheet("""
            QTabWidget::pane { border-radius: 4px;
                               border: 2px solid #FFFFFF;
                               background-image:url(':/gui/pics/trans.png'); }
            QTabWidget::tab-bar { left: 5px; }
            QTabBar::tab { background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                       stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
                                                       stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
                           border: 2px solid #C4C4C3;
                           border-bottom-color: #FFFFFF;
                           border-top-left-radius: 4px;
                           border-top-right-radius: 4px;
                           min-width: 8ex;
                           padding: 2px;
                           padding-left:4px;
                           padding-right:4px;}
            QTabBar::tab:selected,
            QTabBar::tab:hover { background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                             stop: 0 #fafafa, stop: 0.4 #f4f4f4,
                                                             stop: 0.5 #e7e7e7, stop: 1.0 #fafafa); }
            QTabBar::tab:selected { border-color: #FFFFFF; border-bottom-color: #FFFFFF; }
            QTabBar::tab:!selected { margin-top: 2px; }
            QRadioButton::indicator { width:1px;height:1px;border-color:white; }
            QRadioButton:checked { border:3px solid #777;border-radius:4px; }
            QSplitter::handle { background-color:white; }
        """)
        self.vbox = QtGui.QVBoxLayout(self)

        self.toolBox = QtGui.QTabWidget(self)
        self.toolBox.setAutoFillBackground(False)
        self.toolBox.setFocusPolicy(Qt.NoFocus)

        self.partEdit = PartEdit()
        self.vbox.addWidget(self.toolBox)
        self.vbox.addWidget(self.partEdit)

        self.connect(self.toolBox,QtCore.SIGNAL("currentChanged(QWidget*)"),self.updatePartEdit)
        self.initDevices()

    def updatePartEdit(self, dw):
        dw.updatePartEdit()

    def addDisk(self,dw):
        self.toolBox.addTab(dw,dw.name)
        self.toolBox.setTabToolTip(self.toolBox.count()-1,"%s - %s" % (dw.model,dw.name))
        self.diskCount+=1

    def update(self):

        #FIXME
        #self.clearList()

        for dev in self.devs:
            ctx.debugger.log("Device Found %s" % dev)
            self.addDevice(dev)

        # self.showPartitionRequests()
        # self.checkRootPartRequest()

    def initDevices(self):
        self.devs = []
        # initialize all storage devices
        if not yali4.storage.init_devices():
            raise GUIException, _("Can't find a storage device!")

        # for consistency list devices in reverse order.
        self.devs = [i for i in yali4.storage.devices]
        self.devs.reverse()

    def resetChanges(self):
        yali4.storage.clear_devices()
        self.initDevices()
        #ctx.partrequests.remove_all()
        #self.update()

    def addDevice(self, dev):

        def sizePix(mb,total):
            _p = (self.toolBox.width() * mb) / total
            if _p<=1:
                return 5
            return _p - 5

        def sizeStr(mb):
            if mb > 1024:
                return _("%0.1f GB free") % long(round(mb/1024.0))
            else:
                return _("%d MB free") % mb

        # add the device to the list
        devstr = u"Disk %d (%s)" % (self.diskCount, dev.getName())
        freespace = dev.getFreeMB()
        if freespace:
            size_str = dev.getSizeStr() + "  (%s)" % sizeStr(freespace)
        else:
            size_str = dev.getSizeStr()

        d = DiskItem("%s - %s" % (devstr,size_str),dev.getModel(),self.partEdit)
        d.setData(dev)
        self.addDisk(d)

        # add partitions on device
        for part in dev.getOrderedPartitionList():
            parent_item = d
            if part.isExtended():
                continue
            if part.getMinor() != -1:
                name = _("Partition %d") % part.getMinor()
            else:
                name = _("Free Space")
            ctx.debugger.log("Partition added with %s mb" % part.getMB())
            parent_item.addPartition(name,part,sizePix(part.getMB(),dev.getTotalMB()))

        d.updateSizes()

class DiskItem(QtGui.QWidget):
    # storage.Device or partition.Partition
    _data = None

    def __init__(self, name, model, partEdit):
        QtGui.QWidget.__init__(self,None)
        self.setAutoFillBackground(False)

        self.layout = QtGui.QVBoxLayout(self)

        self.diskGroup = QtGui.QGroupBox(self)
        self.diskGroup.setMinimumSize(QSize(570,70))
        self.diskGroup.setMaximumSize(QSize(2280,70))

        self.gridlayout = QtGui.QGridLayout(self.diskGroup)
        self.gridlayout.setMargin(0)
        self.gridlayout.setSpacing(0)

        self.splinter = QtGui.QSplitter(Qt.Horizontal,self.diskGroup)
        self.splinter.setHandleWidth(2)

        self.gridlayout.addWidget(self.splinter,0,0,1,1)

        spacerItem = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.layout.addItem(spacerItem)
        self.layout.addWidget(self.diskGroup)
        self.layout.addItem(spacerItem)

        self.partitions = []
        self.name = name
        self.model = model
        self.partEdit = partEdit

    def addPartition(self,name=None,data=None,_size=None):

        def color(fs_type):
            colors = {"fat32":"#18D918",
                      "hfs+" :"#C0A39E",
                      "fat16":"#00FF00",
                      "ext3" :"#7590AE",
                      "ext2" :"#9DB8D2"}
            if colors.has_key(fs_type):
                return colors[fs_type]
            return "#A9A9A9"

        partition = QtGui.QRadioButton("%s\n%s" % (name,data.getSizeStr()),self.diskGroup)
        partition.setFocusPolicy(Qt.NoFocus)
        partition.setStyleSheet("background-color:%s" % color(data.getFSName()))
        partition.setToolTip(_("""<b>Path:</b> %s<br>
        <b>Size:</b> %s<br>
        <b>FileSystem:</b> %s""") % (data.getPath(),data.getSizeStr(),data.getFSName()))
        self.splinter.addWidget(partition)
        self.partitions.append({"name":name,"data":data,"size":_size})
        self.connect(partition,QtCore.SIGNAL("clicked()"),self.updatePartEdit)

    def updatePartEdit(self):
        i=0
        for part in self.partitions:
            if self.splinter.widget(i).isChecked():
                self.partEdit.ui.devicePath.setText(part["data"].getPath())
                self.partEdit.ui.fileSystem.setText(part["data"].getFSName())
                self.partEdit.ui.partitionSize.setMaximum(part["data"].getMB())
                self.partEdit.ui.partitionSize.setValue(part["data"].getMB())
                self.partEdit.ui.deviceGroup.setTitle(part["name"])
            i+=1

    def setData(self, d):
        self._data = d

    def getData(self):
        return self._data

    def updateSizes(self):
        i=0
        for part in self.partitions:
            _h = self.splinter.handle(i)
            _h.setEnabled(False)
            self.splinter.setCollapsible(i,False)
            self.splinter.widget(i).resize(part['size'],70)
            self.splinter.widget(i).setMinimumSize(QSize(part['size'],50))
            if part['size'] == 5:
                self.splinter.widget(i).setMaximumSize(QSize(part['size'],70))
            i+=1
        self.splinter.widget(0).setChecked(True)
        self.updatePartEdit()

class PartEdit(QtGui.QWidget):
    def __init__(self, *args):
        QtGui.QWidget.__init__(self,None)
        self.ui = Ui_PartEdit()
        self.ui.setupUi(self)

