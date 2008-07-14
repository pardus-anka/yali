# -*- coding: utf-8 -*-
#
# Copyright (C) 2008, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

# linux ?
import os
import dbus
import time
import shutil

# we need i18n
import gettext
__trans = gettext.translation('yali4', fallback=True)
_ = __trans.ugettext

# PyQt4 Rocks
from PyQt4 import QtGui
from PyQt4.QtCore import *

# yali base
from yali4.exception import *
from yali4.constants import consts
import yali4.gui.context as ctx
import yali4.localeutils
import yali4.sysutils
import yali4.fstab

# pisi base
import pisi.ui
import yali4.pisiiface

# partitioning
import yali4.partitiontype as parttype
import yali4.partitionrequest as request
from yali4.partitionrequest import partrequests
from yali4.parteddata import *

# gui
from yali4.gui.YaliDialog import Dialog, Yimirta
from yali4.gui.YaliDialog import WarningDialog, WarningWidget, InformationWindow

# debugger
from yali4.gui.debugger import Debugger
from yali4.gui.debugger import DebuggerAspect

# screens
import yali4.gui.ScrKahyaCheck
import yali4.gui.ScrWelcome
import yali4.gui.ScrCheckCD
import yali4.gui.ScrKeyboard
import yali4.gui.ScrDateTime
import yali4.gui.ScrAdmin
import yali4.gui.ScrUsers
import yali4.gui.ScrPartitionAuto
import yali4.gui.ScrPartitionManual
import yali4.gui.ScrBootloader
import yali4.gui.ScrInstall
import yali4.gui.ScrSummary
import yali4.gui.ScrGoodbye

PARTITION_ERASE_ALL, PARTITION_USE_AVAIL, PARTITION_USE_OLD = range(3)
YALI_INSTALL, \
        YALI_FIRSTBOOT, \
        YALI_OEMINSTALL, \
        YALI_PARTITIONER = range(4)

class Yali:
    def __init__(self, install_type=YALI_INSTALL):

        self._screens = {}

        # Normal Installation process
        self._screens[YALI_INSTALL] = [                                  # Numbers can be used with -s paramter
                                       yali4.gui.ScrKahyaCheck,          # 00
                                       yali4.gui.ScrWelcome,             # 01
                                       yali4.gui.ScrCheckCD,             # 02
                                       yali4.gui.ScrKeyboard,            # 03
                                       yali4.gui.ScrDateTime,            # 04
                                       yali4.gui.ScrUsers,               # 05
                                       yali4.gui.ScrAdmin,               # 06
                                       yali4.gui.ScrPartitionAuto,       # 07
                                       yali4.gui.ScrPartitionManual,     # 08
                                       yali4.gui.ScrBootloader,          # 09
                                       yali4.gui.ScrSummary,             # 10
                                       yali4.gui.ScrInstall,             # 11
                                       yali4.gui.ScrGoodbye              # 12
                                      ]

        # FirstBoot Installation process
        self._screens[YALI_FIRSTBOOT] = [                                # Numbers can be used with -s paramter
                                         yali4.gui.ScrWelcome,           # 00
                                         yali4.gui.ScrKeyboard,          # 01
                                         yali4.gui.ScrDateTime,          # 02
                                         yali4.gui.ScrUsers,             # 03
                                         yali4.gui.ScrAdmin,             # 04
                                         yali4.gui.ScrGoodbye            # 05
                                        ]

        # Oem Installation process
        self._screens[YALI_OEMINSTALL] = [                                  # Numbers can be used with -s paramter
                                          yali4.gui.ScrWelcome,             # 00
                                          yali4.gui.ScrCheckCD,             # 01
                                          yali4.gui.ScrPartitionAuto,       # 02
                                          yali4.gui.ScrPartitionManual,     # 03
                                          yali4.gui.ScrBootloader,          # 04
                                          yali4.gui.ScrInstall,             # 05
                                          yali4.gui.ScrGoodbye              # 06
                                         ]

        # Use YALI just for partitioning
        self._screens[YALI_PARTITIONER] = [
                                           yali4.gui.ScrPartitionManual  # Manual Partitioning
                                          ]

        # Let the show begin..
        self.screens = self._screens[install_type]
        self.install_type = install_type
        self.info = InformationWindow(_("YALI Is Working..."))
        # self.yimirta = Yimirta(self.info)
        # self.yimirta.stop()
        self.info.hide()
        self.checkCDStop = True

    # def toggleYimirta(self):
    #     if self.yimirta.isVisible():
    #         self.yimirta.stop()
    #     else:
    #         self.yimirta.start()

    def checkCD(self, rootWidget):
        ctx.mainScreen.disableNext()
        ctx.mainScreen.disableBack()

        self.info.updateAndShow(_("Starting for CD Check"))
        class PisiUI(pisi.ui.UI):
            def notify(self, event, **keywords):
                pass
            def display_progress(self, operation, percent, info, **keywords):
                pass

        yali4.pisiiface.initialize(ui = PisiUI(), with_comar = False, nodestDir = True)
        yali4.pisiiface.add_cd_repo()
        ctx.mainScreen.processEvents()
        pkg_names = yali4.pisiiface.get_available()

        rootWidget.progressBar.setMaximum(len(pkg_names))

        cur = 0
        for pkg_name in pkg_names:
            cur += 1
            ctx.debugger.log("Checking %s " % pkg_name)
            self.info.updateMessage(_("Checking: %s") % pkg_name)
            if self.checkCDStop:
                continue
            if yali4.pisiiface.check_package_hash(pkg_name):
                rootWidget.progressBar.setValue(cur)
            else:
                self.showError(_("Check Failed"),
                               _("<b><p>Integrity check for packages failed.\
                                  It seems that installation CD is broken.</p></b>"))

        if not self.checkCDStop:
            rootWidget.checkLabel.setText(_('<font color="#FFF"><b>Check succeeded. You can proceed to the next screen.</b></font>'))
            rootWidget.checkButton.setText(_("Check CD Integrity"))
        else:
            rootWidget.checkLabel.setText("")
            rootWidget.progressBar.setValue(0)

        yali4.pisiiface.remove_repo(ctx.consts.cd_repo_name)

        ctx.mainScreen.enableNext()
        ctx.mainScreen.enableBack()

        self.info.hide()

    def setKeymap(self, keymap):
        yali4.localeutils.set_keymap(keymap["xkblayout"], keymap["xkbvariant"])
        ctx.installData.keyData = keymap

    def setTime(self, rootWidget):
        self.info.updateAndShow(_("Setting time settings.."))
        date = rootWidget.calendarWidget.selectedDate()
        args = "%02d%02d%02d%02d%04d.%02d" % (date.month(), date.day(),
                                              rootWidget.timeHours.time().hour(), rootWidget.timeMinutes.time().minute(),
                                              date.year(), rootWidget.timeSeconds.time().second())

        # Set current date and time
        ctx.debugger.log("Date/Time setting to %s" % args)
        os.system("date %s" % args)

        # Sync date time with hardware
        ctx.debugger.log("YALI's time is syncing with the system.")
        os.system("hwclock --systohc")
        self.info.hide()

    def setTimeZone(self, rootWidget):
        # Store time zone selection we will set it in processPending actions.
        ctx.installData.timezone = rootWidget.timeZoneList.currentItem().text()
        ctx.debugger.log("Time zone selected as %s " % ctx.installData.timezone)

    def scanPartitions(self, rootWidget):

        def sortBySize(x,y):
            if x["newSize"]>y["newSize"]:return -1
            elif x["newSize"]==y["newSize"]: return 0
            return 1

        self.info.updateAndShow(_("Disk analyze started.."))
        rootWidget.resizablePartitions = []
        rootWidget.resizableDisks = []
        ctx.debugger.log("Disk analyze started.")
        ctx.debugger.log("%d disk found." % len(yali4.storage.devices))
        for dev in yali4.storage.devices:
            ctx.debugger.log("In disk %s, %d mb is free." % (dev.getPath(), dev.getLargestContinuousFreeMB()))
            if dev.primaryAvailable():
                #if dev.getLargestContinuousFreeMB() > ctx.consts.min_root_size + 100:
                #    rootWidget.resizableDisks.append(dev)
                for part in dev.getOrderedPartitionList():
                    ctx.debugger.log("Partition %s found on disk %s, formatted as %s" % (part.getPath(), dev.getPath(), part.getFSName()))
                    if part.isResizable():
                        minSize = part.getMinResizeMB()
                        possibleFreeSize = part.getMB() - minSize
                        ctx.debugger.log(" - This partition is resizable")
                        ctx.debugger.log(" - Total size of this partition is %.2f MB" % part.getMB())
                        ctx.debugger.log(" - It can resizable to %.2f MB" % minSize)
                        ctx.debugger.log(" - Usable size for this partition is %.2f MB" % possibleFreeSize)
                        rootWidget.resizablePartitions.append({"partition":part,"newSize":possibleFreeSize})
                        if possibleFreeSize / 2 > ctx.consts.min_root_size:
                            if dev not in rootWidget.resizableDisks:
                                rootWidget.resizableDisks.append(dev)
                    else:
                        ctx.debugger.log("This partition is not resizable")
            else:
                ctx.debugger.log("In disk %s, there is no primary avaliable" % (dev.getPath()))

        # Sort by Resize..
        rootWidget.resizablePartitions.sort(sortBySize)

        self.info.hide()

    def getResizableFirstPartition(self):
        # Hacky .. :)
        arp = []
        class __v:
            pass
        mean = __v()
        self.scanPartitions(mean)
        for partition in mean.resizablePartitions:
            if partition["newSize"] / 2 >= ctx.consts.min_root_size:
                arp.append(partition)
        if len(arp)>0:
            return arp[0]
        else:
            raise YaliException, "No Resizable partition found !"

    def autoPartDevice(self):
        self.info.updateAndShow(_("Writing disk tables ..."))

        ctx.partrequests.remove_all()
        dev = ctx.installData.autoPartDev

        # first delete partitions on device
        dev.deleteAllPartitions()
        dev.commit()

        ctx.mainScreen.processEvents()

        p = dev.addPartition(None,
                             parttype.root.parted_type,
                             parttype.root.filesystem,
                             dev.getFreeMB(),
                             parttype.root.parted_flags)
        p = dev.getPartition(p.num) # get partition.Partition

        # create the partition
        dev.commit()
        ctx.mainScreen.processEvents()

        # make partition requests
        ctx.partrequests.append(request.MountRequest(p, parttype.root))
        ctx.partrequests.append(request.FormatRequest(p, parttype.root))
        ctx.partrequests.append(request.LabelRequest(p, parttype.root))
        ctx.partrequests.append(request.SwapFileRequest(p, parttype.root))

        time.sleep(2)

    def checkSwap(self):
        # check swap partition, if not present use swap file
        rt = request.mountRequestType
        pt = parttype.swap
        swap_part_req = ctx.partrequests.searchPartTypeAndReqType(pt, rt)

        if not swap_part_req:
            # No swap partition defined using swap as file in root
            # partition
            rt = request.mountRequestType
            pt = parttype.root
            root_part_req = ctx.partrequests.searchPartTypeAndReqType(pt, rt)
            ctx.partrequests.append(request.SwapFileRequest(root_part_req.partition(),
                                    root_part_req.partitionType()))

    def autoPartUseAvail(self):
        dev = ctx.installData.autoPartDev
        _part = ctx.installData.autoPartPartition
        part = _part["partition"]

        newPartSize = int(_part["newSize"]/2)
        ctx.debugger.log("UA: newPartSize : %s " % newPartSize)
        ctx.debugger.log("UA: resizing to : %s " % (int(part.getMB()) - newPartSize))

        _np = dev.resizePartition(part._fsname, part.getMB() - newPartSize, part)

        self.info.updateMessage(_("Resize Finished ..."))
        ctx.debugger.log("UA: Resize finished.")
        time.sleep(1)

        newStart = _np.geom.end
        np = dev.getPartition(_np.num)

        if np.isLogical():
            ptype = PARTITION_LOGICAL
        else:
            ptype = PARTITION_PRIMARY

        self.info.updateMessage(_("Creating new partition ..."))
        ctx.debugger.log("UA: newStart : %s " % newStart)
        _newPart = dev.addPartition(None,
                                    ptype,
                                    parttype.root.filesystem,
                                    newPartSize - 150,
                                    parttype.root.parted_flags,
                                    newStart)

        newPart = dev.getPartition(_newPart.num)

        dev.commit()
        ctx.mainScreen.processEvents()

        # make partition requests
        ctx.partrequests.append(request.MountRequest(newPart, parttype.root))
        ctx.partrequests.append(request.FormatRequest(newPart, parttype.root))
        ctx.partrequests.append(request.LabelRequest(newPart, parttype.root))
        ctx.partrequests.append(request.SwapFileRequest(newPart, parttype.root))

        time.sleep(2)

    def guessBootLoaderDevice(self,root_part=None):
        if root_part:
            pardus_path = root_part
        else:
            root_part_req = ctx.partrequests.searchPartTypeAndReqType(parttype.root,
                                                                      request.mountRequestType)
            if not root_part_req:
                raise YaliException, "No Root Part request found !"
            pardus_path = root_part_req.partition().getPath()

        if len(yali4.storage.devices) > 1 or ctx.isEddFailed:
            ctx.installData.bootLoaderDev = os.path.basename(ctx.installData.orderedDiskList[0])
        else:
            if pardus_path.find("cciss") > 0:
                # HP Smart array controller (something like /dev/cciss/c0d0p1)
                ctx.installData.bootLoaderDev = pardus_path[:-2]
            else:
                ctx.installData.bootLoaderDev = str(filter(lambda u: not u.isdigit(),
                                                           os.path.basename(pardus_path)))
        return ctx.installData.bootLoaderDev

    def fillFstab(self):
        # fill fstab
        fstab = yali4.fstab.Fstab()
        for req in ctx.partrequests:
            req_type = req.requestType()
            if req_type == request.mountRequestType:
                p = req.partition()
                pt = req.partitionType()

                # Use default label for root partition (PARDUS_ROOT)
                # TODO: Trigger udev to get new label info.
                ####
                path = "LABEL=%s" % p.getTempLabel()

                fs = pt.filesystem._sysname or pt.filesystem._name
                mountpoint = pt.mountpoint
                # TODO: consider merging mountoptions in filesystem.py
                opts = ",".join([pt.filesystem.mountOptions(), pt.mountoptions])

                e = yali4.fstab.FstabEntry(path, mountpoint, fs, opts)
                fstab.insert(e)
            elif req_type == request.swapFileRequestType:
                path = "/" + ctx.consts.swap_file_name
                mountpoint = "none"
                fs = "swap"
                opts = "sw"
                e = yali4.fstab.FstabEntry(path, mountpoint, fs, opts)
                fstab.insert(e)
        fstab.close()

    def backupInstallData(self):
        import piksemel

        def insert(root,tag,data):
            _ = root.insertTag(tag)
            _.insertData(data)

        # let create a yali piksemel..
        yali = piksemel.newDocument("yali")

        # let store keymap and language options
        insert(yali,"language",ctx.consts.lang)
        insert(yali,"keymap",ctx.installData.keyData["xkblayout"])
        insert(yali,"variant",ctx.installData.keyData["xkbvariant"])

        # we will store passwords as shadowed..
        insert(yali,"root_password",yali4.sysutils.getShadowed(ctx.installData.rootPassword))

        # time zone..
        insert(yali,"timezone",ctx.installData.timezone)

        # hostname ..
        insert(yali,"hostname",ctx.installData.hostName)

    def processPendingActions(self, rootWidget):
        global bus
        bus = None
        def connectToDBus():
            global bus
            for i in range(20):
                try:
                    ctx.debugger.log("trying to start dbus..")
                    bus = dbus.bus.BusConnection(address_or_type="unix:path=%s" % ctx.consts.dbus_socket_file)
                    break
                except dbus.DBusException:
                    time.sleep(1)
                    ctx.debugger.log("wait dbus for 1 second...")
            if bus:
                return True
            return False

        def setHostName():
            global bus
            obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")
            obj.setHostName(str(ctx.installData.hostName), dbus_interface="tr.org.pardus.comar.Net.Stack")
            ctx.debugger.log("Hostname set as %s" % ctx.installData.hostName)
            return True

        def addUsers():
            global bus
            obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")
            for u in yali4.users.pending_users:
                ctx.debugger.log("User %s adding to system" % u.username)
                uid = obj.addUser(-1, u.username, u.realname, "", "", unicode(u.passwd), u.groups, [], [], dbus_interface="tr.org.pardus.comar.User.Manager")
                ctx.debugger.log("New user's id is %s" % uid)

                # Use random user icon from YALI Archive
                iconPath = os.path.join(ctx.consts.target_dir,"home/%s/.face.icon" % u.username)
                shutil.copy(u.icon, iconPath)
                os.chmod(iconPath, 0644)
                os.chown(iconPath, uid, 100)

                # Chown for old users..
                user_home_dir = os.path.join(consts.target_dir, 'home', u.username)
                self.info.updateAndShow(_("User <b>%s</b>'s home directory is being prepared..") % u.username)
                os.system('chown -R %d:%d %s ' % (uid, 100, user_home_dir))
                os.chmod(user_home_dir, 0711)
                self.info.hide()

                # Enable auto-login
                if u.username == ctx.installData.autoLoginUser:
                    u.setAutoLogin()
            return True

        def setRootPassword():
            if not ctx.installData.useYaliFirstBoot:
                global bus
                obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")
                obj.setUser(0, "", "", "", str(ctx.installData.rootPassword), "", dbus_interface="tr.org.pardus.comar.User.Manager")
            return True

        def writeConsoleData():
            yali4.localeutils.write_keymap(ctx.installData.keyData["consolekeymap"])
            ctx.debugger.log("Keymap stored.")
            return True

        def migrateXorgConf():
            if not self.install_type == YALI_FIRSTBOOT:
                yali4.postinstall.migrate_xorg()
                ctx.debugger.log("xorg.conf and other files merged.")
            return True

        def copyPisiIndex():
            target = os.path.join(ctx.consts.target_dir, "var/lib/pisi/index/%s" % ctx.consts.pardus_repo_name)

            if os.path.exists(ctx.consts.pisiIndexFile):
                # Copy package index
                shutil.copy(ctx.consts.pisiIndexFile, target)
                shutil.copy(ctx.consts.pisiIndexFileSum, target)

                # Extract the index
                import bz2
                pureIndex = file(os.path.join(target,"pisi-index.xml"),"w")
                pureIndex.write(bz2.decompress(open(ctx.consts.pisiIndexFile).read()))
                pureIndex.close()

                ctx.debugger.log("pisi index files copied.")
            else:
                ctx.debugger.log("pisi index file not found!")
            return True

        def setPackages():
            global bus
            if self.install_type == YALI_OEMINSTALL:
                ctx.debugger.log("OemInstall selected.")
                try:
                    obj = bus.get_object("tr.org.pardus.comar", "/package/kdebase")
                    obj.setState("off", dbus_interface="tr.org.pardus.comar.System.Service")
                    obj = bus.get_object("tr.org.pardus.comar", "/package/yali4_firstBoot")
                    obj.setState("on", dbus_interface="tr.org.pardus.comar.System.Service")
                except:
                    ctx.debugger.log("Dbus error: package doesnt exist !")
                    return False
            elif self.install_type in [YALI_INSTALL, YALI_FIRSTBOOT]:
                try:
                    obj = bus.get_object("tr.org.pardus.comar", "/package/kdebase")
                    obj.setState("on", dbus_interface="tr.org.pardus.comar.System.Service")
                    obj = bus.get_object("tr.org.pardus.comar", "/package/yali4_firstBoot")
                    obj.setState("off", dbus_interface="tr.org.pardus.comar.System.Service")
                except:
                    ctx.debugger.log("Dbus error: package doesnt exist !")
                    return False
            return True

        rootWidget.steps.setOperations([{"text":_("Trying to connect DBUS..."),"operation":connectToDBus}])

        steps = [{"text":_("Setting Hostname..."),"operation":setHostName},
                 {"text":_("Setting TimeZone..."),"operation":yali4.postinstall.setTimeZone},
                 {"text":_("Setting Root Password..."),"operation":setRootPassword},
                 {"text":_("Adding Users..."),"operation":addUsers},
                 {"text":_("Writing Console Data..."),"operation":writeConsoleData},
                 {"text":_("Copy Pisi index..."),"operation":copyPisiIndex},
                 {"text":_("Migrating X.org Configuration..."),"operation":migrateXorgConf}]

        stepsBase = [{"text":_("Setting misc. package configurations..."),"operation":setPackages},
                     {"text":_("Installing BootLoader..."),"operation":self.installBootloader}]

        if self.install_type in [YALI_INSTALL, YALI_FIRSTBOOT]:
            rootWidget.steps.setOperations(steps)

        rootWidget.steps.setOperations(stepsBase)

    def installBootloader(self):
        if not ctx.installData.bootLoaderDev:
            ctx.debugger.log("Dont install bootloader selected; skipping.")
            return

        loader = yali4.bootloader.BootLoader()
        root_part_req = ctx.partrequests.searchPartTypeAndReqType(parttype.root,
                                                                  request.mountRequestType)
        _ins_part = root_part_req.partition().getPath()
        _ins_part_label = root_part_req.partition().getTempLabel()

        loader.write_grub_conf(_ins_part, ctx.installData.bootLoaderDev, _ins_part_label)

        # Check for windows partitions.
        ctx.debugger.log("Checking for Windows ...")
        for d in yali4.storage.devices:
            for p in d.getPartitions():
                fs = p.getFSName()
                if fs in ("ntfs", "fat32"):
                    if yali4.sysutils.is_windows_boot(p.getPath(), fs):
                        ctx.debugger.log("Windows Found on device %s partition %s " % (p.getDevicePath(), p.getPath()))
                        win_fs = fs
                        win_dev = os.path.basename(p.getDevicePath())
                        win_root = os.path.basename(p.getPath())
                        loader.grub_conf_append_win(ctx.installData.bootLoaderDev,
                                                    win_dev,
                                                    win_root,
                                                    win_fs)
                        continue

        # check for linux partitions.

        # grubutils
        import pardus.grubutils

        # our grub.conf
        grubConf = pardus.grubutils.grubConf()
        grubConfPath = os.path.join(ctx.consts.target_dir,"boot/grub/grub.conf")
        grubConf.parseConf(grubConfPath)

        ctx.debugger.log("Checking for Other Distros (Linux) ...")
        for d in yali4.storage.devices:
            for p in d.getPartitions():
                fs = p.getFSName()
                if fs in ("ext3", "reiserfs", "xfs") and not p.getPath() == _ins_part:
                    ctx.debugger.log("Partition found which has usable fs (%s)" % p.getPath())
                    guest_grub_conf = yali4.sysutils.is_linux_boot(p.getPath(), fs)
                    if guest_grub_conf:
                        ctx.debugger.log("GRUB Found on device %s partition %s " % (p.getDevicePath(), p.getPath()))
                        guestGrubConf = pardus.grubutils.grubConf()
                        guestGrubConf.parseConf(guest_grub_conf)
                        for entry in guestGrubConf.entries:
                            entry.title = entry.title + " [ %s ]" % p.getName()
                            grubConf.addEntry(entry)
                        continue

        # write the new grub.conf
        grubConf.write(grubConfPath)

        try:
            ctx.debugger.log("Trying to umount %s" % "/tmp/pcheck")
            yali4.sysutils.umount_("/tmp/pcheck")
            ctx.debugger.log("Trying to umount %s" % (ctx.consts.target_dir + "/mnt/archive"))
            yali4.sysutils.umount_(ctx.consts.target_dir + "/mnt/archive")
            ctx.debugger.log("Trying to umount %s" % (ctx.consts.target_dir + "/mnt/home"))
            yali4.sysutils.umount_(ctx.consts.target_dir + "/mnt/home")
        except:
            ctx.debugger.log("Umount Failed ")

        # GPT stuff
        gptsync_path = yali4.sysutils.find_executable("gptsync")
        if gptsync_path:
            gptsync = os.popen("%s %s" % (gptsync_path, root_part_req.partition().getDevicePath()))
            for line in gptsync.readlines():
                if line.startswith("Status:"):
                    ctx.debugger.log("GPTSYNC: %s" % line.split("Status: ")[1])
            gptsync.close()
            time.sleep(1)
        else:
            ctx.debugger.log("GPTSYNC: Command Not Found !")

        # finally install it
        return loader.install_grub(ctx.installData.bootLoaderDev)

    def showError(self, title, message):
        r = ErrorWidget(self)
        r.label.setText(message)
        d = Dialog(title, r, self)
        d.resize(300,200)
        d.exec_()

class ErrorWidget(QtGui.QWidget):
    def __init__(self, *args):
        apply(QtGui.QWidget.__init__, (self,) + args)

        self.gridlayout = QtGui.QGridLayout(self)
        self.vboxlayout = QtGui.QVBoxLayout()

        self.label = QtGui.QLabel(self)
        self.vboxlayout.addWidget(self.label)

        self.hboxlayout = QtGui.QHBoxLayout()

        spacerItem = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)

        self.reboot = QtGui.QPushButton(self)
        self.reboot.setFocusPolicy(Qt.NoFocus)
        self.reboot.setText(_("Reboot"))

        self.hboxlayout.addWidget(self.reboot)
        self.vboxlayout.addLayout(self.hboxlayout)
        self.gridlayout.addLayout(self.vboxlayout,0,0,1,1)

        yali4.sysutils.eject_cdrom()

        self.connect(self.reboot, SIGNAL("clicked()"),self.slotReboot)

    def slotReboot(self):
        yali4.sysutils.reboot()

