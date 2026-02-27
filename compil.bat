pyinstaller --noconfirm --windowed --uac-admin ^
    --distpath="../build" ^
    --workpath="../build/temp" ^
    --icon=static/icon.png ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "vgamepad/win/vigem/client/x64/ViGEmClient.dll;vgamepad/win/vigem/client/x64" ^
    --hidden-import=pythonnet ^
    --hidden-import=clr ^
    --hidden-import=webview ^
    --hidden-import=webview.platforms.edgechromium ^
    --hidden-import=webview.platforms.winforms ^
    --collect-all pythonnet ^
    --collect-all clr_loader ^
    --collect-all webview ^
    --collect-all pynput ^
    --collect-all flask ^
    main.py