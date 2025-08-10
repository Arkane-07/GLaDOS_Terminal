## GLaDOS-Terminal Setup Guide (Windows Focus)

This guide walks you from a clean Windows install to chatting with GLaDOS, plus (optional) packaging into a standalone `.exe`.

---
### 1. Install Prerequisites

1. Python:
   - Install Python 3.10–3.12 (3.10 recommended for widest PyTorch wheel support).
   - During installer: CHECK "Add Python to PATH".
2. (Optional) Git: https://git-scm.com/downloads
3. Visual C++ Build Tools (if missing): https://visualstudio.microsoft.com/visual-cpp-build-tools/
4. Ollama (local LLM runtime): https://ollama.ai — install and let it start the background service.

Verify in a new PowerShell window:
```
python --version
ollama --version
```

---
### 2. Install / Pull LLM Models with Ollama

Pick the models you want (examples):
```
ollama pull llama3.2:3b

```
List what you have:
```
ollama list
```

You can add/remove models any time. The app reads the installed list at startup (restart the app after changes).

---
### 3. Clone the Repository (or Download ZIP)

Using Git:
```
git clone https://github.com/Arkane-07/GLaDOS_Terminal.git
cd GLaDOS_Terminal
```
Or download the ZIP from GitHub and extract it, then open a PowerShell in that folder.

---
### 4. (Recommended) Create a Virtual Environment
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
If PowerShell blocks scripts, run (once):
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---
### 5. Install Python Dependencies

Base requirements:
```
pip install -r requirements.txt
```

Install PyTorch separately (choose CPU or CUDA per your GPU). Visit https://pytorch.org/get-started/locally/ or for CPU-only:
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Verify:
```
python -c "import torch, pygame, moderngl; print('Torch', torch.__version__)"
```

---
### 6. First Run
```
python Main.py
```
You’ll see a short boot period (approx 5s). After that:
* Press ` (backtick) or ~ to open the Model Selector.
* Use Up / Down and Enter to choose a model.
* Type your prompt; press Enter to send.

If no responses appear:
* Ensure Ollama service is running.
* Test: `curl http://localhost:11434/api/tags` (or `ollama list`).
* Check that the model you selected exists.

---
### 7. Hotkeys
| Key | Action |
|-----|--------|
| ` or ~ | Toggle model selector overlay |
| Up / Down | Navigate model selector OR scroll chat (when selector closed) |
| Enter | Select highlighted model (in selector) / submit text (when selector closed) |
| Esc | Close selector |
| Tab | Cycle through models sequentially |
| F1–F4 | Quick switch to first four models (if present) |
| F5 | Toggle TTS on/off |

TTS starts disabled by default; enable with F5 if you want synthesized voice (Tacotron2 + HiFi-GAN). Voice inference is heavier on CPU.

---
### 8. Troubleshooting
| Symptom | Fix |
|---------|-----|
| Backtick character appears in input when changing models | Already fixed: selector capture prevents insertion |
| No models listed | Ensure `ollama list` returns results; restart app after pulling |
| Long delay on first reply | Model warm-up + PyTorch JIT; subsequent replies are faster |
| High CPU usage | Disable TTS (F5) or use a smaller LLM (e.g., qwen3:0.6b) |
| Missing DLL (e.g., `VCRUNTIME`) | Install Microsoft Visual C++ Redistributable |
| Black window / crash on launch | Update GPU drivers; ensure moderngl can create a context |

Logs: Run with a console (omit `--windowed` in build) to see print statements.

---
### 9. Packaging a Windows Executable (.exe)

Already added a `resource_path` helper in `Main.py` so packaging works.

Install PyInstaller (if not already):
```
pip install pyinstaller
```

Create a folder-based build (recommended for large dependencies like PyTorch):
```
pyinstaller --noconfirm --windowed --onedir --name GLaDOS-Terminal ^
  --add-data "Fonts;Fonts" ^
  --add-data "Images;Images" ^
  --add-data "Sounds;Sounds" ^
  --add-data "Shaders;Shaders" ^
  --add-data "Scripts\\hifigan\\config.json;Scripts\\hifigan" ^
  Main.py
```

Result: `dist/GLaDOS-Terminal/GLaDOS-Terminal.exe` — distribute the entire folder.

Optional single-file build (slower startup, big exe):
```
pyinstaller --noconfirm --windowed --onefile --name GLaDOS-Terminal ^
  --add-data "Fonts;Fonts" ^
  --add-data "Images;Images" ^
  --add-data "Sounds;Sounds" ^
  --add-data "Shaders;Shaders" ^
  --add-data "Scripts\\hifigan\\config.json;Scripts\\hifigan" ^
  Main.py
```

Add an icon (convert `Images/Icon.png` to `Icon.ico`):
```
--icon Images\Icon.ico
```

If PyInstaller misses dynamic modules (rare):
```
--collect-all pygame --collect-all moderngl --collect-all numpy --collect-all torch
```

---
### 10. Updating Models or Ollama
1. Pull or remove models via `ollama pull <model>` / `ollama rm <model>`.
2. Restart the app to refresh the list.

---
### 11. Custom System Prompt
Edit `Settings.json` → `"SystemPrompt"` to adjust personality tone. Restart to apply.

---
### 12. Minimal Usage Flow (TL;DR)
```
ollama pull llama3.2:3b
git clone https://github.com/Arkane-07/GLaDOS_Terminal.git
cd GLaDOS_Terminal
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu   # or CUDA variant
python Main.py
```
Press `, pick model, type, Enter.

---
### 13. Support
Open an issue or ask in the repository if something breaks. Provide console output and steps.

Enjoy conversing with GLaDOS.
