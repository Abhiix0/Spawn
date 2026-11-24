"""Windows handle-relative inspection I/O. Imported only on Windows."""

from __future__ import annotations

import ctypes as ct
import errno
import msvcrt
import os
import stat
from contextlib import contextmanager
from ctypes import wintypes as wt
from dataclasses import dataclass
from pathlib import Path

_REPARSE = 0x400
_DIRECTORY = 0x10
_SHARE_READ_WRITE = 3  # No share-delete while an ancestor is in use.
_READ_ACCESS = 0x00100081  # SYNCHRONIZE | FILE_READ_ATTRIBUTES | FILE_READ_DATA


class _UnicodeString(ct.Structure):
    _fields_ = [
        ("length", wt.USHORT),
        ("maximum_length", wt.USHORT),
        ("buffer", wt.LPWSTR),
    ]


class _ObjectAttributes(ct.Structure):
    _fields_ = [
        ("size", wt.ULONG),
        ("root", wt.HANDLE),
        ("name", ct.POINTER(_UnicodeString)),
        ("flags", wt.ULONG),
        ("security_descriptor", wt.LPVOID),
        ("security_quality_of_service", wt.LPVOID),
    ]


class _IoStatusBlock(ct.Structure):
    _fields_ = [("status", wt.LPVOID), ("information", ct.c_size_t)]


class _DirectoryInfo(ct.Structure):
    # FILE_FULL_DIR_INFO up to the start of its variable-length name.
    _fields_ = [
        ("next_offset", wt.DWORD),
        ("index", wt.DWORD),
        ("times_and_sizes", ct.c_int64 * 6),
        ("attributes", wt.DWORD),
        ("name_bytes", wt.DWORD),
        ("ea_size", wt.DWORD),
        ("name", wt.WCHAR * 1),
    ]


_kernel = ct.WinDLL("kernel32", use_last_error=True)
_nt = ct.WinDLL("ntdll")
_create = _kernel.CreateFileW
_create.argtypes = [
    wt.LPCWSTR,
    wt.DWORD,
    wt.DWORD,
    wt.LPVOID,
    wt.DWORD,
    wt.DWORD,
    wt.HANDLE,
]
_create.restype = wt.HANDLE
_close = _kernel.CloseHandle
_close.argtypes = [wt.HANDLE]
_close.restype = wt.BOOL
_info = _kernel.GetFileInformationByHandleEx
_info.argtypes = [wt.HANDLE, ct.c_int, wt.LPVOID, wt.DWORD]
_info.restype = wt.BOOL
_open = _nt.NtCreateFile
_open.argtypes = [
    ct.POINTER(wt.HANDLE),
    wt.DWORD,
    ct.POINTER(_ObjectAttributes),
    ct.POINTER(_IoStatusBlock),
    wt.LPVOID,
    wt.ULONG,
    wt.ULONG,
    wt.ULONG,
    wt.ULONG,
    wt.LPVOID,
    wt.ULONG,
]
_open.restype = wt.LONG
_status_to_error = _nt.RtlNtStatusToDosError
_status_to_error.argtypes = [wt.LONG]
_status_to_error.restype = wt.ULONG


def _child(parent, name: str, *, directory: bool):
    if not name or name in (".", "..") or any(c in name for c in "\\/:\0"):
        raise OSError(errno.EINVAL, "Invalid repository path component")
    size = len(name.encode("utf-16-le", errors="surrogatepass"))
    buffer = ct.create_unicode_buffer(name, size // 2 + 1)
    relative = _UnicodeString(size, size + 2, ct.cast(buffer, wt.LPWSTR))
    attrs = _ObjectAttributes(
        ct.sizeof(_ObjectAttributes), parent, ct.pointer(relative), 0x40, None, None
    )
    handle = wt.HANDLE()
    # FILE_OPEN_REPARSE_POINT affects the last component. Pass exactly one
    # component per call and reject the opened reparse point before using it.
    options = 0x00200020 | (0x1 if directory else 0x40)
    status = _open(
        ct.byref(handle),
        _READ_ACCESS,
        ct.byref(attrs),
        ct.byref(_IoStatusBlock()),
        None,
        0,
        _SHARE_READ_WRITE,
        1,
        options,
        None,
        0,
    )
    if status < 0:
        error = _status_to_error(status)
        if error in (1920, 4390, 4392, 4393, 4394):
            raise OSError(errno.ELOOP, "Repository link was not followed")
        raise ct.WinError(error)
    attributes = (wt.DWORD * 2)()
    try:
        if not _info(handle, 9, ct.byref(attributes), ct.sizeof(attributes)):
            raise ct.WinError(ct.get_last_error())
        if attributes[0] & _REPARSE:
            raise OSError(errno.ELOOP, "Repository link was not followed")
    except BaseException:
        _close(handle)
        raise
    return handle


@contextmanager
def _directory(root: Path, parts: tuple[str, ...]):
    # A local drive root has no unchecked ancestor. Reject other namespaces
    # if they cannot be anchored using the same guarantees.
    anchor = root.anchor
    if len(anchor) != 3 or anchor[1:] != ":\\":
        raise OSError(errno.EACCES, "Cannot anchor this repository filesystem")
    volume = _create(
        "\\\\?\\" + anchor,
        _READ_ACCESS,
        _SHARE_READ_WRITE,
        None,
        3,  # OPEN_EXISTING
        0x02200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
        None,
    )
    if volume == wt.HANDLE(-1).value:
        raise ct.WinError(ct.get_last_error())
    handles = [volume]
    try:
        for name in (*root.parts[1:], *parts):
            handles.append(_child(handles[-1], name, directory=True))
        yield handles[-1]
    finally:
        for handle in reversed(handles):
            _close(handle)


@contextmanager
def open_file(root: Path, parts: tuple[str, ...]):
    with _directory(root, parts[:-1]) as parent:
        handle = _child(parent, parts[-1], directory=False)
        try:
            fd = msvcrt.open_osfhandle(handle.value, os.O_RDONLY | os.O_BINARY)
        except BaseException:
            _close(handle)
            raise
        with os.fdopen(fd, "rb") as stream:
            yield stream


def check_directory(root: Path) -> None:
    with _directory(root, ()):
        pass


@dataclass(frozen=True)
class _Entry:
    name: str
    st_mode: int

    def stat(self, *, follow_symlinks: bool):
        assert not follow_symlinks
        return self


def list_directory(root: Path, parts: tuple[str, ...]):
    with _directory(root, parts) as directory:
        buffer = ct.create_string_buffer(64 * 1024)
        result = []
        while _info(directory, 14, buffer, ct.sizeof(buffer)):  # FileFullDirectoryInfo
            offset = 0
            while True:
                entry = _DirectoryInfo.from_buffer(buffer, offset)
                name = ct.wstring_at(
                    ct.addressof(buffer) + offset + _DirectoryInfo.name.offset,
                    entry.name_bytes // 2,
                )
                if name not in (".", ".."):
                    if entry.attributes & _REPARSE:
                        mode = stat.S_IFLNK
                    else:
                        mode = (
                            stat.S_IFDIR
                            if entry.attributes & _DIRECTORY
                            else stat.S_IFREG
                        )
                    result.append(_Entry(name, mode))
                if not entry.next_offset:
                    break
                offset += entry.next_offset
        error = ct.get_last_error()
        if error != 18:  # ERROR_NO_MORE_FILES
            raise ct.WinError(error)
    return sorted(result, key=lambda entry: entry.name)
