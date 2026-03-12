# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


project_root = Path.cwd()
src_root = project_root / "src"
entry_script = project_root / "packaging" / "app_entry.py"
icon_path = src_root / "openbciganglionui" / "assets" / "app_icon.ico"

datas = []
binaries = []
hiddenimports = []

for package_name in ("qfluentwidgets", "qframelesswindow"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

datas += collect_data_files("brainflow")
binaries += collect_dynamic_libs("brainflow")
hiddenimports += collect_submodules("brainflow")


a = Analysis(
    [str(entry_script)],
    pathex=[str(project_root), str(src_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenBCIGanglionUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OpenBCIGanglionUI",
)
