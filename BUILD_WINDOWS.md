Building a Windows .exe for this project

Overview

This project is a Python script that reads PDF files and extracts MAWB and total information. To produce a Windows standalone executable (.exe) you should build it on Windows using PyInstaller. Cross-compiling from macOS to Windows is not reliable without extra tools (wine/cross-compilers) and is out of scope for this quick guide.

Prerequisites (Windows)
- Windows 10/11
- Python 3.8+ (matching the target environment)
- Git (optional)

Quick Steps (recommended)
1. Open PowerShell and navigate to the project directory (where `main.py` lives).
2. Allow script execution for this session (optional):

   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

3. Run the build script included here:

   ./build_exe.ps1 -ProjectDir . -Entry main.py -OutName cargo_parser

This script will:
- create a virtualenv in `.venv` (if not present)
- install requirements from `requirements.txt` (if present)
- install PyInstaller
- run PyInstaller --onefile to create a single exe

After successful run you'll find `cargo_parser.exe` in the `dist` folder.

Notes and troubleshooting
- If your project uses data files or non-Python assets, you may need to pass --add-data to PyInstaller.
- If the exe crashes on startup, run the exe from a console to see stderr output.
- If PyInstaller misses imports, add hidden imports via the `--hidden-import` flag.

Cross-building from macOS (alternative)
- You can use Docker with a Windows build image or use wine, but both are more complex than building on a Windows machine. For production builds, prefer an actual Windows runner (e.g., GitHub Actions windows-latest).

Using GitHub Actions to build from macOS (recommended)

If you are on macOS and want to produce a Windows .exe without a local Windows machine, use the included GitHub Actions workflow:

1. Commit and push your repository to GitHub on a branch (e.g. main).
2. Open the repository on GitHub, go to the "Actions" tab and run the "Build Windows EXE" workflow manually (Workflow -> Run workflow).
3. After the workflow completes successfully the Windows executable `cargo_parser.exe` will be available as an artifact named `cargo_parser-exe`.
4. Download the artifact from the workflow run details.

This approach uses a Windows runner in GitHub Actions and is the most reproducible and simple way to produce a Windows exe while working from macOS.

CI suggestion
- Use GitHub Actions `windows-latest` runner with a job step that runs the same PowerShell script. That’s the most reproducible approach.
