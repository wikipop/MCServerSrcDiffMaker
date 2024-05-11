# MC server src diff maker

This project is based on the work of [DecompilerMC](https://github.com/hube12/DecompilerMC) and is up to date with this commit [
3a8aa87](https://github.com/hube12/DecompilerMC/commit/3a8aa87d01065fbd7fdc8422f19a0fa379740635)

---
**What is this for?**

This tool generates git-like diff of two minecraft versions src.\
Primary usage is to check what Mojang has changed between two versions in terms of server architecture.

---
**Important Note**

This project requires any of the JetBrains IDE to compare the decompiled versions.

You need an internet connection to download the mappings, you can ofc put them in the respective folder if you have them physically

We support Windows and **probably** MacOS and linux

You need a java runtime inside your path (Java 8 for older versions, Java 11+ for newer versions)

CFR decompilation is approximately 60s and fernflower takes roughly 200s, please give it time

You can run it directly with python 3.11+ with `python3 main.py`

You can find the jar and the version manifest in the `./versions/` directory

The code will then be inside the folder called `./src/<name_version(option_hash)>/<side>`

The `./tmp/` directory can be removed without impact

---
**Usage**

```
usage: main.py [-h] [--ide-location [IDE_LOCATION]] [--re-download] [--no-compare] [--fern-flower] version [compare]

Decompile and Compare two Minecraft versions

positional arguments:
  version               Minecraft Version 1
  compare               Minecraft Version 2 (Default Latest Snapshot)

options:
  -h, --help            show this help message and exit
  --ide-location [IDE_LOCATION], -l [IDE_LOCATION]
                        Provide JetBrains IDE location or PATH name
  --re-download, -rd    Force re-download
  --no-compare, -nc     Skip comparing the decompiled versions
  --fern-flower, -ff    Use FernFlower Decompiler instead of CFR
```
If no -l argument is provided, script will try to use `idea64.exe` from path.

Examples

Compare 1.17.1 server src to the latest snapshot\
```python3 main.py -l "C:\Program Files\Jetbrains\apps\IDEA-U\ch-0\241.15989.150\bin\idea64.exe" 1.17.1```

Compare 1.17.1 server src to the latest snapshot\
```python3 main.py -l "C:\Program Files\Jetbrains\apps\IDEA-U\ch-0\241.15989.150\bin\idea64.exe" 1.17.1 snap```

Compare 1.17.1 server src to the latest full release\
```python3 main.py -l "C:\Program Files\Jetbrains\apps\IDEA-U\ch-0\241.15989.150\bin\idea64.exe" 1.17.1 latest```

Compare 1.17.1 server src to 1.17.2\
```python3 main.py -l "C:\Program Files\Jetbrains\apps\IDEA-U\ch-0\241.15989.150\bin\idea64.exe" 1.17.1 1.17.2```

Compare 1.17.1 server src to 1.17.2 using FernFlower\
```python3 main.py -l "C:\Program Files\Jetbrains\apps\IDEA-U\ch-0\241.15989.150\bin\idea64.exe" -ff 1.17.1 1.17.2```

---

You can probably use it as executable by creating a standalone executable with pyinstaller, although I haven't fully tested it yet.

```bash
pip install pyinstaller
pyinstaller main.py --distpath build --onefile
```
