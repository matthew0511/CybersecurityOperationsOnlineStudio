"""PyInstaller entrypoint; includes an opt-in, synthetic GUI smoke-test mode.

`--self-test` deliberately never opens the user's real vault.
"""
from __future__ import annotations
import sys

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from cyberstudio.windows_smoke import main as smoke_main
        args = [arg for arg in sys.argv[1:] if arg != "--self-test"]
        raise SystemExit(smoke_main(args))
    from cyberstudio.app import main
    raise SystemExit(main())
