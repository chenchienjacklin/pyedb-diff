from __future__ import annotations

import subprocess
from pathlib import Path
from importlib.resources import files


def main() -> int:
    workdir = Path.cwd()
    gitattributes = workdir / ".gitattributes"
    gitconfig = workdir / ".gitconfig"
    
    edb_diff_path = files("ansys.edb.diff.script").joinpath("edb_diff.sh")
    edb_diff_path = str(edb_diff_path).replace("\\", "/")
    gitattributes.write_text("*.def diff=edbdiff\n", encoding="utf-8")
    gitconfig.write_text("[diff \"edbdiff\"]\n    command=" + str(edb_diff_path) + "\n", encoding="utf-8")

    return subprocess.run(["git", "config", "--local", "--add", "include.path", gitconfig]).returncode


if __name__ == "__main__":
    raise SystemExit(main())