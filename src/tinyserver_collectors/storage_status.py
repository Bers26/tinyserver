"""Read-only storage.status.ro collector helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

STATE_CODES = {"OK": 0, "WARN": 1, "BAD": 2, "UNKNOWN": 3, "STALE": 4, "ERROR": 5, "DISABLED": 6}
SEVERITY_CODES = {"normal": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown_or_error": 5}
FRESHNESS_CODES = {"fresh": 0, "aging": 1, "stale": 2, "expired": 3, "unknown": 4}
OPERATION_STATE_CODES = {"idle": 0, "queued": 1, "running": 2, "slow": 3, "timed_out": 4, "failed": 5, "completed": 6, "unknown": 7}

# Explicit targets are still supported for tests and future pinning, but the
# runtime default is dynamic mount discovery so adding a disk does not require a
# code change.
DEFAULT_TARGETS: tuple[str, ...] = ()

LOCAL_PERSISTENT_FSTYPES = {
    "btrfs",
    "exfat",
    "ext2",
    "ext3",
    "ext4",
    "f2fs",
    "ntfs",
    "vfat",
    "xfs",
    "zfs",
}

EXCLUDED_FSTYPES = {
    "autofs",
    "binfmt_misc",
    "bpf",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devpts",
    "devtmpfs",
    "efivarfs",
    "fusectl",
    "hugetlbfs",
    "mqueue",
    "nsfs",
    "overlay",
    "proc",
    "pstore",
    "securityfs",
    "squashfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}

EXCLUDED_MOUNT_PREFIXES = (
    "/dev",
    "/proc",
    "/run",
    "/snap",
    "/sys",
    "/tmp",
    "/var/lib/containers",
    "/var/lib/docker",
)

PREFERRED_MOUNT_PREFIXES = (
    "/",
    "/data",
    "/home",
    "/media",
    "/mnt",
    "/srv",
)


@dataclass(frozen=True)
class MountInfo:
    mountpoint: str
    source: str
    fstype: str
    options: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _decode_proc_mount_field(value: str) -> str:
    return value.replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\")


def parse_mounts(text: str) -> dict[str, MountInfo]:
    mounts: dict[str, MountInfo] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        source, mountpoint, fstype, options = parts[:4]
        mountpoint = _decode_proc_mount_field(mountpoint)
        mounts[mountpoint] = MountInfo(
            mountpoint=mountpoint,
            source=_decode_proc_mount_field(source),
            fstype=fstype,
            options=options,
        )
    return mounts


def read_mounts(path: str | Path = "/proc/mounts") -> dict[str, MountInfo]:
    try:
        return parse_mounts(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}


def is_relevant_mount(info: MountInfo) -> bool:
    mountpoint = info.mountpoint
    if not mountpoint.startswith("/"):
        return False
    if mountpoint != "/" and any(mountpoint == prefix or mountpoint.startswith(prefix + "/") for prefix in EXCLUDED_MOUNT_PREFIXES):
        return False
    if info.fstype in EXCLUDED_FSTYPES:
        return False
    if mountpoint == "/":
        return True
    if info.fstype not in LOCAL_PERSISTENT_FSTYPES and not info.source.startswith("/dev/"):
        return False
    return any(mountpoint == prefix or mountpoint.startswith(prefix + "/") for prefix in PREFERRED_MOUNT_PREFIXES)


def discover_targets(mounts: Mapping[str, MountInfo]) -> list[str]:
    targets = sorted(info.mountpoint for info in mounts.values() if is_relevant_mount(info))
    if "/" in mounts and "/" not in targets:
        targets.insert(0, "/")
    return sorted(set(targets), key=lambda item: (item != "/", item))


def collect_path(path: str, *, mounts: Mapping[str, MountInfo] | None = None) -> dict[str, Any]:
    mount_data = mounts if mounts is not None else read_mounts()
    info = mount_data.get(path)
    exists = Path(path).exists()
    result: dict[str, Any] = {
        "path": path,
        "exists": exists,
        "mount_present": info is not None,
        "source": info.source if info else None,
        "fstype": info.fstype if info else None,
        "options": info.options if info else None,
        "readonly": None,
        "size_bytes": None,
        "used_bytes": None,
        "free_bytes": None,
        "available_bytes": None,
        "used_percent": None,
    }
    if info is not None:
        result["readonly"] = "ro" in {part.strip() for part in info.options.split(",")}
    if not exists:
        return result
    try:
        stats = os.statvfs(path)
    except OSError:
        return result
    size = stats.f_frsize * stats.f_blocks
    free = stats.f_frsize * stats.f_bfree
    available = stats.f_frsize * stats.f_bavail
    used = size - free
    used_percent = None if size <= 0 else round((used / size) * 100, 3)
    result.update(
        {
            "size_bytes": size,
            "used_bytes": used,
            "free_bytes": free,
            "available_bytes": available,
            "used_percent": used_percent,
        }
    )
    return result


def classify_targets(targets: Iterable[Mapping[str, Any]]) -> tuple[str, int, str, int]:
    worst_state = "OK"
    worst_severity = "normal"
    seen = False
    for target in targets:
        seen = True
        exists = target.get("exists") is True
        mounted = target.get("mount_present") is True
        used_percent = target.get("used_percent")
        readonly = target.get("readonly") is True
        if not exists or not mounted:
            return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
        if readonly:
            worst_state = "WARN"
            worst_severity = "degraded"
        if isinstance(used_percent, (int, float)):
            if used_percent >= 95:
                return "BAD", STATE_CODES["BAD"], "critical", SEVERITY_CODES["critical"]
            if used_percent >= 85 and worst_state != "BAD":
                worst_state = "WARN"
                worst_severity = "degraded"
            elif used_percent >= 75 and worst_state == "OK":
                worst_state = "WARN"
                worst_severity = "warning"
        else:
            worst_state = "UNKNOWN"
            worst_severity = "unknown_or_error"
    if not seen:
        return "UNKNOWN", STATE_CODES["UNKNOWN"], "unknown_or_error", SEVERITY_CODES["unknown_or_error"]
    return worst_state, STATE_CODES[worst_state], worst_severity, SEVERITY_CODES[worst_severity]


def collect_storage_status(targets: Iterable[str] | None = None, *, mounts_path: str | Path = "/proc/mounts") -> dict[str, Any]:
    mounts = read_mounts(mounts_path)
    selected_targets = list(targets) if targets is not None else discover_targets(mounts)
    target_list = [collect_path(path, mounts=mounts) for path in selected_targets]
    state, state_code, severity, severity_code = classify_targets(target_list)
    return {
        "agent_id": "storage.status.ro",
        "collected_at": utc_now_iso(),
        "targets": target_list,
        "target_count": len(target_list),
        "state": state,
        "state_code": state_code,
        "severity": severity,
        "severity_code": severity_code,
        "freshness": "fresh",
        "freshness_code": FRESHNESS_CODES["fresh"],
        "operation_state": "completed",
        "operation_state_code": OPERATION_STATE_CODES["completed"],
    }
