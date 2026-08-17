from __future__ import annotations

import os
import platform
import re
import subprocess
from typing import Callable


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


def _run(cmd, default: str = "", timeout: int = 3) -> str:
    try:
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() or default
    except Exception:
        return default


def _read_os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    for path in ("/etc/os-release", "/usr/lib/os-release", "/etc/openwrt_release"):
        content = _read_file(path)
        if content:
            for line in content.splitlines():
                if "=" in line:
                    key, _, value = line.partition("=")
                    data[key] = value.strip('"')
            break
    return data


def get_os() -> str:
    system = platform.system()
    if system == "Linux":
        osrel = _read_os_release()
        if "PRETTY_NAME" in osrel:
            name = osrel["PRETTY_NAME"]
        elif "NAME" in osrel:
            name = osrel["NAME"]
            if "VERSION_ID" in osrel:
                name += " " + osrel["VERSION_ID"]
        else:
            name = "Linux"

        arch = platform.machine()
        if os.path.exists("/etc/arch-release"):
            name = "Arch Linux"
        elif os.path.exists("/etc/debian_version"):
            name = "Debian " + _read_file("/etc/debian_version")

        if arch and arch not in name:
            name = f"{name} {arch}"
        return name
    if system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    return system


def get_host() -> str:
    system = platform.system()
    if system == "Linux":
        board_vendor = _read_file("/sys/devices/virtual/dmi/id/board_vendor")
        board_name = _read_file("/sys/devices/virtual/dmi/id/board_name")
        if board_vendor and board_name:
            return f"{board_vendor} {board_name}"
        product_name = _read_file("/sys/devices/virtual/dmi/id/product_name")
        if product_name:
            return product_name
    return ""


def get_kernel() -> str:
    return platform.release()


def get_uptime() -> str:
    if platform.system() == "Linux" and os.path.exists("/proc/uptime"):
        try:
            seconds = int(float(_read_file("/proc/uptime").split()[0]))
        except (ValueError, IndexError):
            return ""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        parts = []
        if days:
            parts.append(f"{days} days")
        if hours:
            parts.append(f"{hours} hours")
        if minutes:
            parts.append(f"{minutes} mins")
        return ", ".join(parts) if parts else f"{seconds} seconds"
    return ""


def get_packages() -> str:
    managers: list[str] = []

    pkg_checks = [
        ("pacman -Qq --color never", "pacman"),
        ("dpkg-query -f '.\n' -W", "dpkg"),
        ("rpm -qa", "rpm"),
        ("xbps-query -l", "xbps"),
        ("apk info", "apk"),
    ]

    for cmd, name in pkg_checks:
        out = _run(cmd)
        if out:
            count = len(out.splitlines())
            if count > 0:
                managers.append(f"{count} ({name})")

    flatpak = _run("flatpak list")
    if flatpak:
        count = max(0, len(flatpak.splitlines()) - 1)
        if count > 0:
            managers.append(f"{count} (flatpak)")

    snap = _run("snap list")
    if snap:
        count = max(0, len(snap.splitlines()) - 1)
        if count > 0:
            managers.append(f"{count} (snap)")

    return ", ".join(managers) if managers else ""


def get_shell() -> str:
    shell = os.environ.get("SHELL", "")
    if not shell:
        return ""
    name = os.path.basename(shell)
    if name == "bash":
        ver = os.environ.get("BASH_VERSION", "")
        if ver:
            return f"bash {ver.split()[0]}"
    elif name == "zsh":
        ver = os.environ.get("ZSH_VERSION", "")
        if ver:
            return f"zsh {ver}"
    elif name == "fish":
        ver = os.environ.get("FISH_VERSION", "")
        if ver:
            return f"fish {ver}"
    return name


def get_resolution() -> str:
    if platform.system() != "Linux":
        return ""
    xrandr = _run("xrandr")
    if not xrandr:
        return ""
    for line in xrandr.splitlines():
        if " connected " in line:
            parts = line.split()
            for part in parts:
                if "+" in part and "x" in part:
                    return part.split("+")[0]
    return ""


def get_de() -> str:
    return os.environ.get("XDG_CURRENT_DESKTOP", "") or os.environ.get("DESKTOP_SESSION", "")


def get_wm() -> str:
    wm = os.environ.get("XDG_CURRENT_DESKTOP", "") or os.environ.get("DESKTOP_SESSION", "")
    if wm:
        return wm
    wmctrl = _run(["wmctrl", "-m"])
    if wmctrl:
        for line in wmctrl.splitlines():
            if line.startswith("Name:"):
                return line.split(":", 1)[1].strip()
    return ""


def get_wm_theme() -> str:
    return _run(
        ["gsettings", "get", "org.gnome.desktop.wm.preferences", "theme"]
    ).strip("'")


def get_theme() -> str:
    return _run(
        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
    ).strip("'")


def get_icons() -> str:
    return _run(
        ["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"]
    ).strip("'")


def get_terminal() -> str:
    term = os.environ.get("TERMINAL", "") or os.environ.get("TERM_PROGRAM", "")
    if not term and platform.system() == "Linux":
        parent = _run(["ps", "-p", str(os.getppid()), "-o", "comm="])
        if parent:
            term = os.path.basename(parent)
    return term


def get_terminal_font() -> str:
    kitty = _run(["kitty", "@", "get-font-name"])
    if kitty:
        return kitty

    alacritty_yml = os.path.expanduser("~/.config/alacritty/alacritty.yml")
    if os.path.exists(alacritty_yml):
        content = _read_file(alacritty_yml)
        match = re.search(r"family:\s*[\"']?([^\"'\s]+)", content)
        if match:
            return match.group(1)

    return ""


def get_cpu() -> str:
    if platform.system() == "Linux":
        cpuinfo = _read_file("/proc/cpuinfo")
        if cpuinfo:
            for line in cpuinfo.splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
            for line in cpuinfo.splitlines():
                if line.startswith("Processor"):
                    return line.split(":", 1)[1].strip()
    if platform.system() == "Darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    return ""


def get_gpu() -> str:
    if platform.system() == "Linux":
        lspci = _run("lspci | grep -i 'vga\\|3d\\|display'")
        if lspci:
            lines = []
            for line in lspci.splitlines():
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    lines.append(parts[1])
            return " / ".join(lines) if lines else lspci
    return ""


def get_memory() -> str:
    if platform.system() == "Linux":
        meminfo = _read_file("/proc/meminfo")
        if meminfo:
            total = available = 0
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    available = int(line.split()[1]) * 1024

            if total > 0:
                def fmt(b: float) -> str:
                    for unit in ["B", "KiB", "MiB", "GiB"]:
                        if abs(b) < 1024.0:
                            return f"{b:.1f}{unit}"
                        b /= 1024.0
                    return f"{b:.1f}TiB"

                return f"{fmt(available)} / {fmt(total)}"
    return ""


_FIELDS: list[tuple[str, Callable[[], str]]] = [
    ("OS", get_os),
    ("Host", get_host),
    ("Kernel", get_kernel),
    ("Uptime", get_uptime),
    ("Packages", get_packages),
    ("Shell", get_shell),
    ("Resolution", get_resolution),
    ("DE", get_de),
    ("WM", get_wm),
    ("WM Theme", get_wm_theme),
    ("Theme", get_theme),
    ("Icons", get_icons),
    ("Terminal", get_terminal),
    ("Terminal Font", get_terminal_font),
    ("CPU", get_cpu),
    ("GPU", get_gpu),
    ("Memory", get_memory),
]


def generate() -> str:
    user = os.environ.get("USER", "")
    hostname = os.uname().nodename
    title = f"{user}@{hostname}"

    lines = [
        title,
        "-" * len(title),
    ]

    for label, func in _FIELDS:
        value = func()
        if value:
            lines.append(f"{label}: {value}")

    return "\n".join(lines)
