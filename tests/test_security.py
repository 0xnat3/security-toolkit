import os

import pytest

from app.security import TargetNotAllowed, check_scan_ip, resolve_scan_directory


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "192.168.1.20"])
def test_loopback_and_private_allowed(ip):
    check_scan_ip(ip, allow_public=False)


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1"])
def test_public_blocked_by_default(ip):
    with pytest.raises(TargetNotAllowed):
        check_scan_ip(ip, allow_public=False)


def test_public_allowed_when_enabled():
    check_scan_ip("8.8.8.8", allow_public=True)


@pytest.mark.parametrize("ip", ["169.254.169.254", "0.0.0.0", "224.0.0.1", "255.255.255.255"])
def test_dangerous_addresses_always_blocked(ip):
    with pytest.raises(TargetNotAllowed):
        check_scan_ip(ip, allow_public=True)


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "files"
    (r / "data").mkdir(parents=True)
    return r


@pytest.fixture
def sec_app(make_app, root):
    return make_app(INTEGRITY_ROOTS=(str(root),))


def test_relative_path_resolves_inside_root(sec_app, root):
    with sec_app.app_context():
        assert resolve_scan_directory("data") == os.path.realpath(root / "data")


def test_parent_directory_rejected(sec_app):
    with sec_app.app_context(), pytest.raises(TargetNotAllowed):
        resolve_scan_directory("..")


def test_absolute_path_outside_root_rejected(sec_app, tmp_path):
    with sec_app.app_context(), pytest.raises(TargetNotAllowed):
        resolve_scan_directory(str(tmp_path))


def test_sibling_with_same_prefix_rejected(sec_app, tmp_path):
    evil = tmp_path / "files-evil"  # shares the "files" prefix with the real root
    evil.mkdir()
    with sec_app.app_context(), pytest.raises(TargetNotAllowed):
        resolve_scan_directory(str(evil))


def test_missing_directory_rejected(sec_app):
    with sec_app.app_context(), pytest.raises(ValueError) as exc:
        resolve_scan_directory("nope")
    assert not isinstance(exc.value, TargetNotAllowed)