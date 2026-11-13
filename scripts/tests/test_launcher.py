"""Exercise the Windows launcher chain without building/stopping real containers."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows cmd → PowerShell → Git Bash wrapper")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def launcher(tmp_path):
    for name in ("run.cmd", "run.ps1", "run.sh"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    stubs = {
        "docker": '[[ "$1" == info ]] && exit 0\nprintf "%s\\n" "$@" > "$LAUNCHER_LOG"\nexit "${LAUNCHER_EXIT:-0}"\n',
        "curl": "exit 0\n",
        "uname": "printf 'Linux\\n'\n",
        "xdg-open": "exit 0\n",
    }
    for name, script in stubs.items():
        (binaries / name).write_text("#!/usr/bin/env bash\n" + script, encoding="utf-8", newline="\n")
    log = tmp_path / "docker-args.txt"

    def run(command, *, enabled=False, docker_exit=0):
        (tmp_path / ".env").write_text(
            "EASYTV_PUBLIC_HOST=127.0.0.1\nEASYTV_HOST_DISCOVERY=off\nEASYTV_NETWORK=bridge\n"
            f"EASYTV_AI={'on' if enabled else 'off'}\n", encoding="utf-8", newline="\n",
        )
        env = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
               "LAUNCHER_LOG": log.as_posix(), "LAUNCHER_EXIT": str(docker_exit)}
        result = subprocess.run([os.environ["COMSPEC"], "/d", "/c", "run.cmd", command],
                                cwd=tmp_path, env=env, capture_output=True, encoding="utf-8",
                                errors="replace", timeout=20)
        return result, log.read_text().splitlines() if log.exists() else []

    return run


@pytest.mark.parametrize(("command", "enabled", "with_ai"), [
    ("ai", False, True), ("up", True, True), ("up", False, False),
])
def test_windows_command_selects_compose_files_and_builds(launcher, command, enabled, with_ai):
    result, arguments = launcher(command, enabled=enabled)
    assert result.returncode == 0, result.stderr
    expected = ["compose", "-f", "docker-compose.yml"]
    if with_ai:
        expected += ["-f", "docker-compose.ai.yml"]
    assert arguments == expected + ["up", "-d", "--build"]


def test_windows_help_includes_ai_command(launcher):
    result, arguments = launcher("help")
    assert result.returncode == 0, result.stderr
    assert "./run.sh ai" in result.stdout
    assert not arguments


def test_windows_launcher_preserves_build_failure(launcher):
    result, arguments = launcher("ai", docker_exit=23)
    assert result.returncode == 23, result.stderr
    assert arguments[-3:] == ["up", "-d", "--build"]
