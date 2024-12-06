#!/usr/bin/env python3

import os
import sys

def mv(src_path, dst_path):
    # try the rename syscall
    try:
        os.rename(src_path, dst_path)
        return
    except OSError as exc:
        if exc.errno != 18:
            raise
        # OSError: [Errno 18] Invalid cross-device link

    def get_high_low(device):
        return (device & 0xff00) >> 8, device & 255

    def get_devid(device):
        high, low = get_high_low(device)
        return f"{high}:{low}"

    dst_dir = os.path.dirname(dst_path)
    assert os.path.exists(dst_dir)

    src_real = os.path.realpath(src_path)
    src_stat = os.stat(src_path)
    src_device = src_stat.st_dev
    src_devid = get_devid(src_stat.st_dev)
    src_inode = src_stat.st_ino
    print(f"src {src_devid} {src_inode} {src_real}")

    dst_dir_real = os.path.realpath(dst_dir)
    dst_dir_stat = os.stat(dst_dir)
    dst_dir_device = dst_dir_stat.st_dev
    dst_dir_devid = get_devid(dst_dir_stat.st_dev)
    dst_dir_inode = dst_dir_stat.st_ino
    print(f"dst_dir {dst_dir_devid} {dst_dir_inode} {dst_dir_real}")

    if src_device == dst_dir_device:
        print("src_device == dst_dir_device")
    else:
        print("src_device != dst_dir_device")

    # find bind mounts by parsing /proc/self/mountinfo
    # https://unix.stackexchange.com/questions/295525/how-is-findmnt-able-to-list-bind-mounts
    # https://github.com/cnamejj/PyProc

    # https://unix.stackexchange.com/a/346444/295986
    #import os.path
    import re
    from collections import namedtuple
    MountInfo = namedtuple('MountInfo', ['mountid', 'parentid', 'devid', 'root', 'mountpoint', 'mountoptions', 'extra', 'fstype', 'source', 'fsoptions'])
    mounts = []
    def unescape(string):
        return re.sub(r'\\([0-7]{3})', (lambda m: chr(int(m.group(1), 8))), string)
    dst_device_mountpoint = None
    dst_device_path = None
    with open('/proc/self/mountinfo', 'r') as f:
        for line in f:
            mid, pid, devid, root, mp, mopt, *tail = line.rstrip().split(' ')
            extra = []
            for item in tail:
                if item == '-':
                    break
                extra.append(item)
            fstype, src, fsopt = tail[len(extra)+1:]
            mid, pid = int(mid), int(pid)
            root, mp, src = unescape(root), unescape(mp), unescape(src)
            mount = MountInfo(mid, pid, devid, root, mp, mopt, extra, fstype, src, fsopt)
            #if devid != dst_dir_devid:
            if devid != src_devid:
                continue
            if root == "/":
                dst_device_mountpoint = mp
                continue
            mounts.append(mount)

    print("mounts:")
    for mount in mounts:
        print(f"  {mount.root} -> {mount.mountpoint}")

    # TODO handle chains of bind mounts

    if dst_device_mountpoint == "/":
        dst_device_mountpoint = ""

    def iter_realpaths(path):
        path = os.path.realpath(path)
        nonlocal mounts
        nonlocal dst_device_mountpoint
        for mount in mounts:
            mp = mount.mountpoint
            if path.startswith(mp):
                yield dst_device_mountpoint + mount.root + path[len(mp):]

    print(f"realpaths of src_path {src_path}")
    for path in iter_realpaths(src_path):
        print(f"  {path}")

    print(f"realpaths of dst_dir {dst_dir}")
    for path in iter_realpaths(dst_dir):
        print(f"  {path}")

    # search for the correct combination of realpaths
    for _src_path in iter_realpaths(src_path):
        for _dst_dir in iter_realpaths(dst_dir):
            _dst_path = _dst_dir + "/" + os.path.basename(dst_path)
            try:
                os.rename(_src_path, _dst_path)
                print(f"success: moved {_src_path!r} to {_dst_path!r}")
                return
            except OSError as exc:
                if exc.errno != 18:
                    raise
                # OSError: [Errno 18] Invalid cross-device link
                # continue searching

    raise Exception(f"failed to move {src_path!r} to {dst_path!r}")

if __name__ == "__main__":
    mv(sys.argv[1], sys.argv[2])
