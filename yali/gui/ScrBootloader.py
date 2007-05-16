# -*- coding: utf-8 -*-
#
# Copyright (C) 2005, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

from os.path import basename
from qt import *

import gettext
__trans = gettext.translation('yali', fallback=True)
_ = __trans.ugettext


import yali.storage
import yali.bootloader
import yali.partitionrequest as request
import yali.partitiontype as parttype
from yali.sysutils import is_windows_boot
from yali.gui.Ui.bootloaderwidget import BootLoaderWidget
from yali.gui.ScreenWidget import ScreenWidget
from yali.gui.InformationWindow import InformationWindow
from yali.gui.GUIException import *
import yali.gui.context as ctx
import GUIToggler


##
# BootLoader screen.
class Widget(BootLoaderWidget, ScreenWidget):

    help = _('''
<font size="+2">Boot loader setup</font>

<font size="+1">
<p>
Linux makes use of GRUB boot loader, which
can boot the operating system of your taste
during the start up. 
</p>
<p>
If you have more than one operating system,
you can choose which operating system to 
boot also.
</p>

<p>
Please refer to Pardus Installing and Using 
Guide for more information about GRUB boot 
loader.
</p>
</font>
''')

    def __init__(self, *args):
        apply(BootLoaderWidget.__init__, (self,) + args)

        self.device = None
        self.moreOptions = GUIToggler.YaliToggler(self.buttonGroup)
        self.moreOptions.setIcon("toggler")
        self.moreOptions.setText("Show more options")
        self.moreOptions.setToggled(True)
        self.moreOptions.setPaletteBackgroundColor(ctx.consts.bg_color)
        self.moreOptions.setPaletteForegroundColor(ctx.consts.fg_color)

        # This is not correct,
        # It should be in buttonGroupLayout = QGridLayout(self.buttonGroup.layout()) this grid.
        # Baris will fix it :)
        layout = self.buttonGroup.layout()
        layout.addWidget(self.moreOptions,2,0)

        self.device_list.setPaletteBackgroundColor(ctx.consts.bg_color)
        self.device_list.setPaletteForegroundColor(ctx.consts.fg_color)

        self.installFirstMBR.setChecked(True)
        self.device_list.hide()
        self.noInstall.hide()
        self.installMBR.hide()

        # initialize all storage devices
        if not yali.storage.init_devices():
            raise GUIException, _("Can't find a storage device!")

        if len(yali.storage.devices) > 1:
            self.device_list_state = True
            # fill device list
            for dev in yali.storage.devices:
                DeviceItem(self.device_list, dev)
            # select the first disk by default
            self.device_list.setSelected(0, True)
            # be sure first is selected device
            self.device = self.device_list.item(0).getDevice()
        else:
            # don't show device list if we have just one disk
            self.device_list_state = False
            self.device_list.hide()
            self.select_disk_label.hide()

            self.device = yali.storage.devices[0]

        self.connect(self.buttonGroup, SIGNAL("clicked(int)"),
                     self.slotInstallLoader)
        self.connect(self.device_list, SIGNAL("selectionChanged(QListBoxItem*)"),
                     self.slotDeviceChanged)
        self.connect(self.device_list, SIGNAL("clicked()"),
                     self.slotSelect)
        self.connect(self.moreOptions, PYSIGNAL("signalClicked"),
                     self.slotMoreOptions)

    def slotMoreOptions(self):
        if self.moreOptions._toggled:
            if self.device_list_state:
                self.device_list.show()
                self.installMBR.show()
            self.noInstall.show()
        else:
            self.device_list.hide()
            self.noInstall.hide()
            self.installMBR.hide()

    def slotSelect(self):
        self.installMBR.setChecked(True)

    def slotInstallLoader(self, b):
        if self.installMBR.isChecked():
            self.device_list.setEnabled(True)
            self.device_list.setSelected(0,
                                         True)
        else:
            self.device_list.setEnabled(False)
            self.device_list.setSelected(self.device_list.selectedItem(),
                                         False)

    def slotDeviceChanged(self, i):
        self.device = i.getDevice()

    def execute(self):
        # show information window...
        info_window = InformationWindow(self, _("Please wait while installing bootloader!"))

        loader = yali.bootloader.BootLoader()

        root_part_req = ctx.partrequests.searchPartTypeAndReqType(
            parttype.root, request.mountRequestType)

        if self.installPart.isChecked():
            install_dev = basename(root_part_req.partition().getPath())
        elif self.installMBR.isChecked():
            install_dev = basename(self.device.getPath())
        else:
            #install to hd0
            install_dev = None
        install_root = basename(root_part_req.partition().getPath())

        loader.write_grub_conf(install_root)

        # Windows partitions...
        for d in yali.storage.devices:
            for p in d.getPartitions():
                fs = p.getFSName()
                if fs in ("ntfs", "fat32"):
                    if is_windows_boot(p.getPath(), fs):
                        win_fs = fs
                        win_dev = basename(p.getDevicePath())
                        win_root = basename(p.getPath())
                        loader.grub_conf_append_win(install_dev,
                                                    win_dev,
                                                    win_root,
                                                    win_fs)
                        continue

        # finally install it
        if not self.noInstall.isChecked():
            loader.install_grub(install_dev)

        # close window
        info_window.close(True)

        return True



class DeviceItem(QListBoxText):

    def __init__(self, parent, dev):
        text = u"%s - %s (%s)" %(dev.getModel(),
                                dev.getName(),
                                dev.getSizeStr())
        apply(QListBoxText.__init__, (self,parent,text))
        self._dev = dev

    def getDevice(self):
        return self._dev

