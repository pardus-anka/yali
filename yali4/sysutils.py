# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2009, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

# sysutils module provides basic system utilities

import os
import sys
import time
import subprocess
from string import ascii_letters
from string import digits
from pardus.sysutils import find_executable
from pardus import procutils

from yali4._sysutils import *
from yali4.constants import consts

_sys_dirs = ['dev', 'proc', 'sys']

def run(cmd, params=None, capture=False, largeBuffer=False):
    import yali4.gui.context as ctx

    # Merge parameters with command
    if params:
        cmd = "%s %s" % (cmd, ' '.join(params))

    # to use Popen we need a tuple
    _cmd = tuple(cmd.split())
    ctx.debugger.log("RUN : %s" % cmd)

    # Create an instance for Popen
    proc = subprocess.Popen(_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # if we dont need a largeBuffer we can wait the process and get the return code
    if not largeBuffer:
        result = proc.wait()

    # Capture the output
    stdout, stderr = proc.communicate()

    # if we need a largeBuffer we need to guess the return code from stderr
    if largeBuffer:
        result = len(stderr)

    ctx.debugger.log(stderr)
    ctx.debugger.log(stdout)

    # if return code larger then zero, means there is a problem with this command
    if result > 0:
        ctx.debugger.log("FAILED : %s" % cmd)
        return False
    ctx.debugger.log("SUCCESS : %s" % cmd)
    if capture:
        return stdout
    return True

def chroot_run(cmd):
    run("chroot %s %s" % (consts.target_dir, cmd))

# run dbus daemon in chroot
def chroot_dbus():

    for _dir in _sys_dirs:
        tgt = os.path.join(consts.target_dir, _dir)
        run("mount --bind /%s %s" % (_dir, tgt))

    chroot_run("/sbin/ldconfig")
    chroot_run("/sbin/update-environment")
    chroot_run("/bin/service dbus start")

def finalize_chroot():
    # close filesDB if it is still open
    import pisi
    filesdb = pisi.db.filesdb.FilesDB()
    if filesdb.is_initialized():
        filesdb.close()

    # stop dbus
    chroot_run("/bin/service dbus stop")

    # kill comar in chroot if any exists
    chroot_run("/bin/killall comar")

    # unmount sys dirs
    c = _sys_dirs
    c.reverse()
    for _dir in c:
        tgt = os.path.join(consts.target_dir, _dir)
        umount_(tgt)

    # store log content
    import yali4.gui.context as ctx
    ctx.debugger.log("Finalize Chroot called this is the last step for logs ..")
    if ctx.debugEnabled:
        open(ctx.consts.log_file,"w").write(str(ctx.debugger.traceback.plainLogs))

    # store session log as kahya xml
    open(ctx.consts.session_file,"w").write(str(ctx.installData.sessionLog))
    os.chmod(ctx.consts.session_file,0600)

    # swap off if it is opened
    if os.path.exists(consts.swap_file_path):
        run("swapoff %s" % consts.swap_file_path)

    # umount target dir
    umount_(consts.target_dir)

def checkYaliParams(param):
    for i in [x for x in open("/proc/cmdline", "r").read().split()]:
        if i.startswith("yali4="):
            if param in i.split("=")[1].split(","):
                return True
    return False

def checkYaliOptions(param):
    for i in [x for x in open("/proc/cmdline", "r").read().split(' ')]:
        if i.startswith("yali4=") and not i.find("%s:" % param) == -1:
            for part in i.split("=")[1].split(","):
                if part.startswith("%s:" % param):
                    return str(part.split(':')[1]).strip()
    return None

def swap_as_file(filepath, mb_size):
    dd, mkswap = find_executable('dd'), find_executable('mkswap')

    if (not dd) or (not mkswap): return False

    create_swap_file = "%s if=/dev/zero of=%s bs=1024 count=%d" % (dd, filepath, (int(mb_size)*1024))
    mk_swap          = "%s %s" % (mkswap, filepath)

    try:
        for cmd in [create_swap_file, mk_swap]:
            p = os.popen(cmd)
            p.close()
        os.chmod(filepath, 0600)
    except:
        return False

    return True

def swap_on(partition):
    # swap on
    params = ["-v", partition]
    run("swapon", params)

##
# total memory size
def mem_total():
    m = open("/proc/meminfo")
    for l in m:
        if l.startswith("MemTotal"):
            return int(l.split()[1]) / 1024
    return None

def eject_cdrom(mount_point=consts.source_dir):
    run("eject -m %s" % mount_point)

def text_is_valid(text):
    allowed_chars = ascii_letters + digits + '.' + '_' + '-'
    return len(text) == len(filter(lambda u: [x for x in allowed_chars if x == u], text))

def add_hostname(hostname = 'pardus'):
    hostname_file = os.path.join(consts.target_dir, 'etc/env.d/01hostname')
    hosts_file = os.path.join(consts.target_dir, 'etc/hosts')

    def getCont(x):
        return open(x).readlines()
    def getFp(x):
        return open(x, "w")

    hostname_fp, hosts_fp = getFp(hostname_file), getFp(hosts_file)
    hostname_contents = ""
    hosts_contents = ""
    if os.path.exists(hostname_file):
        hostname_contents = getCont(hostname_file)
    if os.path.exists(hosts_file):
        hosts_contents = getCont(hosts_file)

    if hostname_contents:
        for line in hostname_contents:
            if line.startswith('HOSTNAME'):
                line = 'HOSTNAME="%s"\n' % hostname
            hostname_fp.write(line)
        hostname_fp.close()
    else:
        hostname_fp.write('HOSTNAME="%s"\n' % hostname)

    if hosts_contents:
        for line in hosts_contents:
            if line.startswith('127.0.0.1'):
                line = '127.0.0.1\t\tlocalhost %s\n' % hostname
            hosts_fp.write(line)
        hosts_fp.close()
    else:
        hosts_fp.write('127.0.0.1\t\tlocalhost %s\n' % hostname)

def mount(source, target, fs, needs_mtab=False):
    params = ["-t", fs, source, target]
    if not needs_mtab:
        params.insert(0,"-n")
    run("mount",params)

def umount_(dir='/tmp/pcheck', params=''):
    param = [dir, params]
    run("umount",param)

def is_windows_boot(partition_path, file_system):
    m_dir = "/tmp/pcheck"
    if not os.path.isdir(m_dir):
        os.makedirs(m_dir)
    umount(m_dir)
    try:
        if file_system == "fat32":
            mount(partition_path, m_dir, "vfat")
        else:
            mount(partition_path, m_dir, file_system)
    except:
        return False

    exist = lambda f: os.path.exists(os.path.join(m_dir, f))

    if exist("boot.ini") or exist("command.com") or exist("bootmgr"):
        umount_(m_dir)
        return True
    else:
        umount_(m_dir)
        return False

def is_linux_boot(partition_path, file_system):
    import yali4.gui.context as ctx
    result = False
    m_dir = "/tmp/pcheck"
    if not os.path.isdir(m_dir):
        os.makedirs(m_dir)
    umount_(m_dir)

    ctx.debugger.log("Mounting %s to /tmp/pcheck" % partition_path)

    try:
        mount(partition_path, m_dir, file_system)
    except:
        ctx.debugger.log("Mount failed for %s " % partition_path)
        return False

    exist = lambda f: os.path.exists(os.path.join(m_dir,"boot/grub/", f))

    if exist("grub.conf") or exist("menu.lst"):
        menuLst = os.path.join(m_dir,"boot/grub/menu.lst")
        grubCnf = os.path.join(m_dir,"boot/grub/grub.conf")
        if os.path.islink(menuLst):
            ctx.debugger.log("grub.conf found on device %s" % partition_path)
            result = grubCnf
        else:
            ctx.debugger.log("menu.lst found on device %s" % partition_path)
            result = menuLst

    return result

def reboot():
    try:
        umount(consts.target_dir + "/home")
    except:
        pass
    umount(consts.target_dir)
    fastreboot()

# Shamelessly stolen from Anaconda :)
def execClear(command, argv, stdin = 0, stdout = 1, stderr = 2):
    import yali4.gui.context as ctx

    argv = list(argv)
    if isinstance(stdin, str):
        if os.access(stdin, os.R_OK):
            stdin = open(stdin)
        else:
            stdin = 0
    if isinstance(stdout, str):
        stdout = open(stdout, "w")
    if isinstance(stderr, str):
        stderr = open(stderr, "w")
    if stdout is not None and not isinstance(stdout, int):
        ctx.debugger.log("RUN : %s" %([command] + argv,))
        stdout.write("Running... %s\n" %([command] + argv,))

    p = os.pipe()
    childpid = os.fork()
    if not childpid:
        os.close(p[0])
        os.dup2(p[1], 1)
        os.dup2(stderr.fileno(), 2)
        os.dup2(stdin, 0)
        os.close(stdin)
        os.close(p[1])
        stderr.close()

        os.execvp(command, [command] + argv)
        os._exit(1)

    os.close(p[1])
    log = ''
    while 1:
        try:
            s = os.read(p[0], 1)
        except OSError, args:
            (num, msg) = args
            if (num != 4):
                raise IOError, args

        stdout.write(s)
        log+=s
        ctx.mainScreen.processEvents()

        if len(s) < 1:
            break

    try:
        ctx.debugger.log("OUT : %s" % log)
    except Exception, e:
        ctx.debugger.log("Debuger itself crashed yay :) %s" % e)

    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError, (num, msg):
        ctx.debugger.log("exception from waitpid: %s %s" %(num, msg))

    if status is None:
        return 0

    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)

    return 1


## Run an external program and capture standard out.
# @param command The command to run.
# @param argv A list of arguments.
# @param stdin The file descriptor to read stdin from.
# @param stderr The file descriptor to redirect stderr to.
# @param root The directory to chroot to before running command.
# @return The output of command from stdout.
def execWithCapture(command, argv, stdin = 0, stderr = 2, root ='/'):
    argv = list(argv)

    if isinstance(stdin, str):
        if os.access(stdin, os.R_OK):
            stdin = open(stdin)
        else:
            stdin = 0

    if isinstance(stderr, str):
        stderr = open(stderr, "w")

    try:
        pipe = subprocess.Popen([command] + argv, stdin = stdin,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                cwd=root)
    except OSError, ( errno, msg ):
        raise RuntimeError, "Error running " + command + ": " + msg

    rc = pipe.stdout.read()
    pipe.wait()
    return rc

import re
import string

# Based on RedHat's ZoneTab class
class TimeZoneEntry:
    def __init__(self, code=None, timeZone=None):
        self.code = code
        self.timeZone = timeZone

class TimeZoneList:
    def __init__(self, fromFile='/usr/share/zoneinfo/zone.tab'):
        self.entries = []
        self.readTimeZone(fromFile)

    def getEntries(self):
        return self.entries

    def readTimeZone(self, fn):
        f = open(fn, 'r')
        comment = re.compile("^#")
        while 1:
            line = f.readline()
            if not line:
                break
            if comment.search(line):
                continue
            fields = string.split(line, '\t')
            if len(fields) < 3:
                continue
            code = fields[0]
            timeZone = string.strip(fields[2])
            entry = TimeZoneEntry(code, timeZone)
            self.entries.append(entry)

# getShadow for passwd ..
import random
import hashlib

def getShadowed(passwd):
    des_salt = list('./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') 
    salt, magic = str(random.random())[-8:], '$1$'

    ctx = hashlib.new('md5', passwd)
    ctx.update(magic)
    ctx.update(salt)

    ctx1 = hashlib.new('md5', passwd)
    ctx1.update(salt)
    ctx1.update(passwd)

    final = ctx1.digest()

    for i in range(len(passwd), 0 , -16):
        if i > 16:
            ctx.update(final)
        else:
            ctx.update(final[:i])

    i = len(passwd)

    while i:
        if i & 1:
            ctx.update('\0')
        else:
            ctx.update(passwd[:1])
        i = i >> 1
    final = ctx.digest()

    for i in range(1000):
        ctx1 = hashlib.new('md5')
        if i & 1:
            ctx1.update(passwd)
        else:
            ctx1.update(final)
        if i % 3: ctx1.update(salt)
        if i % 7: ctx1.update(passwd)
        if i & 1:
            ctx1.update(final)
        else:
            ctx1.update(passwd)
        final = ctx1.digest()

    def _to64(v, n):
        r = ''
        while (n-1 >= 0):
            r = r + des_salt[v & 0x3F]
            v = v >> 6
            n = n - 1
        return r

    rv = magic + salt + '$'
    final = map(ord, final)
    l = (final[0] << 16) + (final[6] << 8) + final[12]
    rv = rv + _to64(l, 4)
    l = (final[1] << 16) + (final[7] << 8) + final[13]
    rv = rv + _to64(l, 4)
    l = (final[2] << 16) + (final[8] << 8) + final[14]
    rv = rv + _to64(l, 4)
    l = (final[3] << 16) + (final[9] << 8) + final[15]
    rv = rv + _to64(l, 4)
    l = (final[4] << 16) + (final[10] << 8) + final[5]
    rv = rv + _to64(l, 4)
    l = final[11]
    rv = rv + _to64(l, 2)

    return rv

