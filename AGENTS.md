# AGENTS.md

## Project

A Classic Snake game (贪吃蛇) with manual and AI auto-play modes. Windows-only, pure Python stdlib (tkinter + winsound). No pip dependencies.

## Architecture

```
snake.py          GUI app + game logic (entrypoint)
  SnakeLogic       pure logic engine, grid-coordinate based, fully testable
  SnakeGame        tkinter GUI, rendering, input, AI inline methods
snake_ai.py       Standalone AI runner (no GUI), imports SnakeLogic from snake.py
test_snake.py     14 unit tests against SnakeLogic only (no test framework)
```

`snake.py` uses grid coordinates `(col, row)` internally; `_pixel_rect()` converts to canvas pixels. Snake head is always red (`#ff0000`).

## Commands

```powershell
# Run the game (GUI)
python snake.py              # interactive start screen
python snake.py --auto       # launch in AI mode

# Run unit tests
python test_snake.py

# Run AI benchmark (no GUI)
python snake_ai.py           # target: score > 100, ~2-3k steps

# Build standalone EXE
pyinstaller --onefile --windowed --name "贪吃蛇" snake.py
# Output: dist/贪吃蛇.exe (~10.9 MB)
```

## Game modes

| Trigger | Mode |
|---------|------|
| Enter / Space on start screen | Manual play |
| Key `2` on start screen | AI auto-demo |
| `F2` during gameplay | Toggle AI on/off |
| `P` during gameplay | Pause/resume |

Arrow keys and WASD both work for manual control.

## Testing

Tests are pure logic (`SnakeLogic` class only, no GUI). Run with plain `python test_snake.py`. No pytest installed. All 14 tests should pass before any logic change.

## Gotchas

- **Windows GBK encoding**: avoid Unicode characters (✓, ✗, →) in print/log output. Use ASCII-safe markers like `[PASS]` / `[FAIL]`.
- **No pygame**: Python 3.14 has no pygame wheel available. Stay with tkinter.
- **snake_ai.py imports snake.py**: these two import each other if you add `import snake_ai` inside `snake.py`. Keep them independent — `snake.py` has its own inline AI methods (`_auto_dir`, `_bfs`, `_ai_safe`, `_ai_reachable`) so the GUI AI mode works without importing `snake_ai.py`.
- **winsound** is Windows-only. No cross-platform sound support.
- **PyInstaller + Chinese filename**: PowerShell may garble the output name. Build with ASCII name then rename via Python `os.rename()`.
- **High score file**: `snake_highscore.txt` is created/read in the working directory. The EXE will create it alongside itself on first run.
