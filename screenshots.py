"""
Screenshot capture script for the Snake game.
Uses Windows API for accurate client-area capture (no title bar, no DPI issues).
Ref: SCREENSHOT_GUIDE.md
"""
import ctypes
import os
import time
import tkinter as tk
from ctypes import wintypes

from PIL import ImageGrab

# Disable DPI scaling
ctypes.windll.user32.SetProcessDPIAware()

# Import game constants
from snake import (
    COLS, ROWS, CELL, WIDTH, HEIGHT,
    COLOR_BG, COLOR_GRID, COLOR_HEAD, COLOR_BODY_A, COLOR_BODY_B,
    COLOR_FOOD, COLOR_FOOD_GLOW, COLOR_TEXT, COLOR_OVERLAY_BG,
    COLOR_SMALL, COLOR_PAUSE,
)


def get_client_rect(hwnd):
    rect = wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, rect.right, rect.bottom


def grab_window(root):
    hwnd = ctypes.windll.user32.FindWindowW(None, root.title())
    if not hwnd:
        hwnd = int(root.frame(), 16)
    x, y, w, h = get_client_rect(hwnd)
    return ImageGrab.grab(bbox=(x, y, x + w, y + h))


class ScreenshotGame:
    """Minimal game window for screenshots — no game loop, just rendering."""

    def __init__(self, title="贪吃蛇 - Snake"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        self.canvas = tk.Canvas(
            self.root, width=WIDTH, height=HEIGHT,
            bg=COLOR_BG, highlightthickness=0
        )
        self.canvas.pack()

        self._overlay_ids = []
        self._snake_ids = []
        self._food_id = None
        self._food_glow_id = None
        self._score_text_id = None
        self._mode_text_id = None

        # Draw grid once
        for c in range(1, COLS):
            x = c * CELL
            self.canvas.create_line(x, 0, x, HEIGHT, fill=COLOR_GRID, width=1)
        for r in range(1, ROWS):
            y = r * CELL
            self.canvas.create_line(0, y, WIDTH, y, fill=COLOR_GRID, width=1)

    def _pixel_rect(self, col, row, pad=0):
        x1 = col * CELL + pad
        y1 = row * CELL + pad
        x2 = (col + 1) * CELL - pad
        y2 = (row + 1) * CELL - pad
        return x1, y1, x2, y2

    def _draw_overlay_rect(self, alpha=180):
        return self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT, fill=COLOR_OVERLAY_BG, outline="",
            stipple="gray25" if alpha < 200 else ""
        )

    def _clear_overlay(self):
        for oid in self._overlay_ids:
            self.canvas.delete(oid)
        self._overlay_ids.clear()

    # ── Start screen ──────────────────────

    def draw_start_screen(self, high_score=0):
        self._clear_overlay()
        self._overlay_ids.append(self._draw_overlay_rect(220))
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 60,
            text="\U0001f40d \u8d2a\u5403\u86c7", fill=COLOR_HEAD,
            font=("Arial", 32, "bold"), anchor="center"
        ))
        lines = [
            "Enter / Space    \u624b\u52a8\u6e38\u73a9",
            "2                AI \u81ea\u52a8\u6f14\u793a",
            "",
            "\u6e38\u620f\u4e2d: F2 \u5207\u6362\u624b\u52a8/AI",
            "        P      \u6682\u505c",
        ]
        y_off = 0
        for line in lines:
            self._overlay_ids.append(self.canvas.create_text(
                WIDTH // 2, HEIGHT // 2 + y_off,
                text=line, fill=COLOR_SMALL, font=("Consolas", 11),
                anchor="center"
            ))
            y_off += 22
        if high_score:
            self._overlay_ids.append(self.canvas.create_text(
                WIDTH // 2, HEIGHT - 20,
                text=f"\u6700\u9ad8\u5206: {high_score}",
                fill=COLOR_SMALL, font=("Consolas", 10), anchor="center"
            ))

    # ── Game state helpers ────────────────

    def _clear_snake(self):
        for sid in self._snake_ids:
            self.canvas.delete(sid)
        self._snake_ids.clear()

    def _clear_food(self):
        if self._food_id:
            self.canvas.delete(self._food_id)
            self._food_id = None
        if self._food_glow_id:
            self.canvas.delete(self._food_glow_id)
            self._food_glow_id = None

    def draw_snake(self, segments, style="manual"):
        """segments: list of (col, row) tuples."""
        self._clear_snake()
        for i, seg in enumerate(segments):
            color = COLOR_HEAD if i == 0 else (COLOR_BODY_A if i % 2 == 0 else COLOR_BODY_B)
            coords = self._pixel_rect(seg[0], seg[1], pad=1)
            sid = self.canvas.create_rectangle(*coords, fill=color, outline="")
            self._snake_ids.append(sid)

    def draw_food(self, food_pos, pulse_scale=1.0):
        self._clear_food()
        scale = pulse_scale
        pad = int((CELL - CELL * scale) / 2)

        coords = self._pixel_rect(*food_pos, pad=pad)
        self._food_id = self.canvas.create_oval(*coords, fill=COLOR_FOOD, outline="")

        glow_pad = max(0, pad - 2)
        glow_coords = self._pixel_rect(*food_pos, pad=glow_pad)
        self._food_glow_id = self.canvas.create_oval(
            *glow_coords, fill=COLOR_FOOD_GLOW, outline=""
        )

    def draw_game_ui(self, score, high_score=0, ai=False):
        """Score text and mode indicator."""
        self._clear_score_texts()
        hs = f" | Best: {high_score}" if high_score else ""
        self._score_text_id = self.canvas.create_text(
            8, 4, text=f"Score: {score}{hs}", fill=COLOR_TEXT,
            font=("Consolas", 12, "bold"), anchor="nw"
        )
        mode = "[AI]" if ai else "[Manual]"
        color = "#ff6666" if ai else "#66ff66"
        self._mode_text_id = self.canvas.create_text(
            WIDTH - 8, 4, text=mode, fill=color,
            font=("Consolas", 10), anchor="ne"
        )

    def _clear_score_texts(self):
        if self._score_text_id:
            self.canvas.delete(self._score_text_id)
            self._score_text_id = None
        if self._mode_text_id:
            self.canvas.delete(self._mode_text_id)
            self._mode_text_id = None

    def draw_pause_overlay(self):
        self._clear_overlay()
        self._overlay_ids.append(self._draw_overlay_rect(140))
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 15,
            text="\u23f8 \u5df2\u6682\u505c", fill=COLOR_PAUSE,
            font=("Arial", 28, "bold"), anchor="center"
        ))
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 25,
            text="\u6309 Space / P \u7ee7\u7eed",
            fill=COLOR_SMALL, font=("Consolas", 11), anchor="center"
        ))

    def draw_gameover_overlay(self, score, high_score, is_win=False):
        self._clear_overlay()
        self._overlay_ids.append(self._draw_overlay_rect(200))
        title = "\U0001f3c6 \u606d\u559c\u901a\u5173\uff01" if is_win else "\U0001f480 Game Over"
        color = COLOR_FOOD_GLOW if is_win else COLOR_FOOD
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 50,
            text=title, fill=color, font=("Arial", 28, "bold"), anchor="center"
        ))
        score_text = f"\u5f97\u5206: {score}"
        if score >= high_score and high_score > 0:
            score_text += "  \u2605 \u65b0\u7eaa\u5f55\uff01"
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2,
            text=score_text, fill=COLOR_TEXT, font=("Arial", 18), anchor="center"
        ))
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 30,
            text=f"\u6700\u9ad8\u5206: {high_score}",
            fill=COLOR_SMALL, font=("Consolas", 12), anchor="center"
        ))
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 60,
            text="\u6309 Enter \u91cd\u65b0\u5f00\u59cb",
            fill=COLOR_SMALL, font=("Consolas", 11), anchor="center"
        ))

    # ── Capture ───────────────────────────

    def capture(self, filename):
        self.root.attributes('-topmost', True)
        for _ in range(10):
            self.root.update()
        self.root.update_idletasks()
        time.sleep(0.5)
        self.root.lift()
        self.root.update()
        time.sleep(0.3)
        img = grab_window(self.root)
        # Ensure output dir
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        img.save(filename)
        print(f"[OK] {filename}")

    def destroy(self):
        self.root.destroy()


# ═══════════════════════════════════════════
# Generate all screenshots
# ═══════════════════════════════════════════

def main():
    out_dir = "screenshots"
    os.makedirs(out_dir, exist_ok=True)

    INITIAL_SNAKE = [(5, 10), (4, 10), (3, 10)]
    SAMPLE_SNAKE_LONG = [
        (15, 10), (14, 10), (13, 10), (12, 10), (11, 10),
        (10, 10), (9, 10), (8, 10), (7, 10), (6, 10),
        (5, 10)
    ]
    FOOD_POS = (20, 5)

    # 1. Start screen
    print("Capturing start screen...")
    app = ScreenshotGame("贪吃蛇 - Snake")
    app.draw_start_screen(high_score=42)
    app.capture(os.path.join(out_dir, "screenshot_start.png"))
    app.destroy()
    time.sleep(0.3)

    # 2. Manual play
    print("Capturing manual play...")
    app = ScreenshotGame("贪吃蛇 - Snake")
    app.draw_snake(SAMPLE_SNAKE_LONG, style="manual")
    app.draw_food(FOOD_POS)
    app.draw_game_ui(score=8, ai=False)
    app.capture(os.path.join(out_dir, "screenshot_manual.png"))
    app.destroy()
    time.sleep(0.3)

    # 3. AI auto-play
    print("Capturing AI play...")
    app = ScreenshotGame("贪吃蛇 - Snake [AI]")
    app.draw_snake(SAMPLE_SNAKE_LONG, style="ai")
    app.draw_food(FOOD_POS)
    app.draw_game_ui(score=15, ai=True)
    app.capture(os.path.join(out_dir, "screenshot_ai.png"))
    app.destroy()
    time.sleep(0.3)

    # 4. Pause screen
    print("Capturing pause screen...")
    app = ScreenshotGame("贪吃蛇 - Snake")
    app.draw_snake(SAMPLE_SNAKE_LONG, style="manual")
    app.draw_food(FOOD_POS)
    app.draw_game_ui(score=12, ai=False)
    app.draw_pause_overlay()
    app.capture(os.path.join(out_dir, "screenshot_pause.png"))
    app.destroy()
    time.sleep(0.3)

    # 5. Game Over screen
    print("Capturing game over screen...")
    app = ScreenshotGame("贪吃蛇 - Snake")
    app.draw_snake(SAMPLE_SNAKE_LONG, style="manual")
    app.draw_food(FOOD_POS)
    app.draw_game_ui(score=24, high_score=42, ai=False)
    app.draw_gameover_overlay(score=24, high_score=42, is_win=False)
    app.capture(os.path.join(out_dir, "screenshot_gameover.png"))
    app.destroy()
    time.sleep(0.3)

    print(f"\nDone! Screenshots saved to '{out_dir}/'")
    for f in os.listdir(out_dir):
        size = os.path.getsize(os.path.join(out_dir, f))
        print(f"  {f}  ({size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
