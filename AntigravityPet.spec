# -*- mode: python ; coding: utf-8 -*-

starter_datas = [
    ('logo.png', '.'),
    ('icon.ico', '.'),
    ('pets/.catalog_cache.json', 'pets'),
    ('pets/desk-otter--zihualiu1997', 'pets/desk-otter--zihualiu1997'),
    ('pets/codenono--dq02', 'pets/codenono--dq02'),
    ('pets/codex-orb--legeling', 'pets/codex-orb--legeling'),
    ('pets/chud-codex--jorge-cuevas90003', 'pets/chud-codex--jorge-cuevas90003'),
    ('pets/ai-pulse--wxy', 'pets/ai-pulse--wxy'),
    ('pets/diandian--lllucasxu', 'pets/diandian--lllucasxu'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=starter_datas,
    hiddenimports=[
        'win32gui', 'win32con', 'win32api', 'win32process',
        'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageChops',
        'psutil', 'websockets', 'asyncio'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'numpy', 'tkinter', 'unittest'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AntigravityPet',
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
    version='version_info.txt',
    icon=['icon.ico'],
)
