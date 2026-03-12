import os

from openbciganglionui.app import main


if __name__ == "__main__":
    os.environ.setdefault("OPENBCI_BACKEND", "mock")
    main()
