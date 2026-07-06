import os

# Keep Qt WebEngine/Chromium third-party map warnings from flooding the terminal.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-logging --log-level=3")
os.environ.setdefault("QT_LOGGING_RULES", "qt.webenginecontext.debug=false;qt.webenginecontext.info=false;js.warning=false;js.info=false;qt.fonts.warning=false")

from stanky_market.app import main

if __name__ == "__main__":
    main()
