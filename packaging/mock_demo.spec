from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files


project_root = Path.cwd()
src_root = project_root / "src"
app_root = src_root / "openbciganglionui"
icon_path = app_root / "assets" / "app_icon.ico"

qfw_datas, qfw_binaries, qfw_hiddenimports = collect_all("qfluentwidgets")
app_datas = collect_data_files(
    "openbciganglionui",
    includes=["assets/*"],
)

datas = qfw_datas + app_datas
binaries = qfw_binaries
hiddenimports = qfw_hiddenimports


a = Analysis(
    [str(project_root / "packaging" / "mock_demo_entry.py")],
    pathex=[str(src_root)],
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
    name="OpenBCIGanglionUI-MockDemo",
    icon=str(icon_path),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OpenBCIGanglionUI-MockDemo",
)
