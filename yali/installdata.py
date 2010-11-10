# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2010 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

class InstallData:
    keyData = None
    rootPassword = None
    hostName = None
    users = []
    isKahyaUsed = False
    autoLoginUser = None
    autoInstallationKernel = None
    autoInstallationCollection = None
    autoInstallationMethod = 0
    rescuePartition = None
    repoAddr = None
    timezone = ""
    sessionLog = ""
    installAllLangPacks = False
