# -*- mode: python -*-

block_cipher = None


plist_opts = dict(
    NSHighResolutionCapable=True,
    CFBundleDocumentTypes=[
	dict(
	    CFBundleTypeName="MUF File",
	    CFBundleTypeRole="Viewer",
	    LSHandlerRank="Alternate",
	    CFBundleTypeMIMETypes=["text/x-muf", "application/x-muf"],
	    LSItemContentTypes=["org.fuzzball.muf"],
	    CFBundleTypeExtensions=["muf"],
	),
	dict(
	    CFBundleTypeName="MUV File",
	    CFBundleTypeRole="Viewer",
	    LSHandlerRank="Alternate",
	    CFBundleTypeMIMETypes=["text/x-muv", "application/x-muv"],
	    LSItemContentTypes=["com.belfry.muv"],
	    CFBundleTypeExtensions=["muv"],
	),
    ],
)


a = Analysis(['kickstart.py'],
             pathex=[],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='MufSim',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='icons/MufSim.ico')
app = BUNDLE(exe,
             name='MufSim.app',
             icon='icons/MufSim.icns',
	     info_plist=plist_opts,
             bundle_identifier='com.belfry.mufsimulator')
