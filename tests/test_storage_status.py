from __future__ import annotations

from tinyserver_collectors.storage_status import classify_targets, parse_mounts
from tinyserver_collectors.storage_status_framework import to_framework_snapshot


def test_parse_mounts_extracts_source_type_and_options() -> None:
    mounts = parse_mounts("/dev/sda1 / ext4 rw,relatime 0 0\n/dev/sdc2 /srv/storage ext4 rw,relatime 0 0\n")

    assert mounts["/"].source == "/dev/sda1"
    assert mounts["/"].fstype == "ext4"
    assert mounts["/srv/storage"].source == "/dev/sdc2"


def test_classify_targets_ok_warn_bad() -> None:
    assert classify_targets([
        {"exists": True, "mount_present": True, "readonly": False, "used_percent": 10.0},
        {"exists": True, "mount_present": True, "readonly": False, "used_percent": 20.0},
    ])[0] == "OK"

    assert classify_targets([
        {"exists": True, "mount_present": True, "readonly": False, "used_percent": 86.0},
    ])[0] == "WARN"

    assert classify_targets([
        {"exists": True, "mount_present": True, "readonly": False, "used_percent": 96.0},
    ])[0] == "BAD"

    assert classify_targets([
        {"exists": False, "mount_present": False, "readonly": None, "used_percent": None},
    ])[0] == "BAD"


def test_framework_snapshot_has_checks_and_numeric_metrics() -> None:
    snapshot = to_framework_snapshot(
        {
            "agent_id": "storage.status.ro",
            "collected_at": "2026-05-25T19:30:00+00:00",
            "state": "OK",
            "state_code": 0,
            "severity": "normal",
            "severity_code": 0,
            "freshness_code": 0,
            "operation_state_code": 6,
            "target_count": 2,
            "targets": [
                {
                    "path": "/",
                    "exists": True,
                    "mount_present": True,
                    "source": "/dev/mapper/root",
                    "fstype": "ext4",
                    "options": "rw,relatime",
                    "readonly": False,
                    "size_bytes": 1000,
                    "used_bytes": 250,
                    "free_bytes": 750,
                    "available_bytes": 700,
                    "used_percent": 25.0,
                },
                {
                    "path": "/srv/storage",
                    "exists": True,
                    "mount_present": True,
                    "source": "/dev/sdc2",
                    "fstype": "ext4",
                    "options": "rw,relatime",
                    "readonly": False,
                    "size_bytes": 2000,
                    "used_bytes": 100,
                    "free_bytes": 1900,
                    "available_bytes": 1800,
                    "used_percent": 5.0,
                },
            ],
        }
    )

    assert snapshot["agent_id"] == "storage.status.ro"
    assert snapshot["domain"] == "storage"
    assert snapshot["state"] == "OK"
    assert snapshot["severity"] == 0
    assert snapshot["capabilities"] == {"read_only": True, "actions": []}
    assert set(snapshot["checks"]) == {"storage_root_health", "storage_srv_storage_health"}
    assert snapshot["checks"]["storage_root_health"]["state"] == "OK"
    assert snapshot["metrics"]["storage_root_used_percent"] == 25.0
    assert snapshot["metrics"]["storage_srv_storage_used_percent"] == 5.0
    assert snapshot["metrics"]["storage_srv_storage_mount_present_value"] == 1


def test_framework_snapshot_marks_missing_target_bad() -> None:
    snapshot = to_framework_snapshot(
        {
            "collected_at": "2026-05-25T19:30:00+00:00",
            "state": "BAD",
            "severity_code": 4,
            "target_count": 1,
            "targets": [
                {
                    "path": "/srv/storage",
                    "exists": False,
                    "mount_present": False,
                    "readonly": None,
                    "used_percent": None,
                }
            ],
        }
    )

    assert snapshot["state"] == "BAD"
    assert snapshot["severity"] == 4
    check = snapshot["checks"]["storage_srv_storage_health"]
    assert check["state"] == "BAD"
    assert check["severity"] == 4
    assert snapshot["metrics"]["storage_srv_storage_exists_value"] == 0
    assert snapshot["metrics"]["storage_srv_storage_mount_present_value"] == 0
