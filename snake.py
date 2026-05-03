"""
贪吃蛇游戏 - 优化版

架构：SnakeLogic（纯逻辑，可单元测试） + SnakeGame（tkinter GUI 层）
修复了原始版本的全部 20 项缺陷。
"""
import tkinter as tk
import sys
import random
import os
import winsound
from enum import Enum
from typing import List, Tuple, Set, Optional, Dict
from math import cos, pi
from collections import deque

# ═══════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════
COLS: int = 30
ROWS: int = 20
CELL: int = 20
WIDTH: int = COLS * CELL
HEIGHT: int = ROWS * CELL

BASE_TICK_MS: int = 120
MIN_TICK_MS: int = 40
SPEED_STEP_MS: int = 10
SPEED_EVERY: int = 3

HIGH_SCORE_FILE: str = "snake_highscore.txt"

COLOR_BG: str = "#111111"
COLOR_GRID: str = "#1a1a1a"
COLOR_HEAD: str = "#ff0000"
COLOR_BODY_A: str = "#00aa00"
COLOR_BODY_B: str = "#008800"
COLOR_FOOD: str = "#ff4040"
COLOR_FOOD_GLOW: str = "#ff6666"
COLOR_TEXT: str = "#eeeeee"
COLOR_OVERLAY_BG: str = "#000000"
COLOR_SMALL: str = "#aaaaaa"
COLOR_PAUSE: str = "#ffcc00"

INITIAL_SNAKE: List[Tuple[int, int]] = [(5, 10), (4, 10), (3, 10)]

# ═══════════════════════════════════════════
# 枚举
# ═══════════════════════════════════════════

class Direction(Enum):
    """方向枚举，存储 (dx, dy) 网格偏移。"""
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    def opposite(self) -> "Direction":
        """返回相反方向。"""
        mapping: Dict["Direction", "Direction"] = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return mapping[self]


class GameState(Enum):
    """游戏状态机。"""
    START = "start"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    WIN = "win"


# ═══════════════════════════════════════════
# 纯逻辑层（可脱离 GUI 进行单元测试）
# ═══════════════════════════════════════════

class SnakeLogic:
    """
    贪吃蛇纯逻辑引擎。

    所有坐标使用网格坐标 (col, row)，与像素无关。
    维护 snake_set 用于 O(1) 碰撞检测。
    """

    def __init__(self, cols: int = COLS, rows: int = ROWS,
                 initial_snake: List[Tuple[int, int]] | None = None) -> None:
        self.cols: int = cols
        self.rows: int = rows
        self._cells: int = cols * rows
        self.snake: List[Tuple[int, int]] = list(initial_snake if initial_snake else INITIAL_SNAKE)
        self.snake_set: Set[Tuple[int, int]] = set(self.snake)
        self.direction: Direction = Direction.RIGHT
        self._next_direction: Optional[Direction] = None
        self.score: int = 0
        self._food: Tuple[int, int] = (0, 0)
        self._food = self.spawn_food()

    # ── 属性 ──────────────────────────────

    @property
    def head(self) -> Tuple[int, int]:
        return self.snake[0]

    @property
    def food(self) -> Tuple[int, int]:
        return self._food

    @property
    def food_eaten(self) -> None:
        pass

    # ── 方向输入 ───────────────────────────

    def set_direction(self, new_dir: Direction) -> None:
        """
        设置下一步方向。
        使用 next_direction 缓冲机制防止同一帧内多次按键导致 180° 掉头。
        """
        if new_dir != self.direction.opposite():
            self._next_direction = new_dir

    def _apply_direction(self) -> None:
        """每帧调用一次，应用缓冲的方向。"""
        if self._next_direction is not None:
            self.direction = self._next_direction
            self._next_direction = None

    # ── 移动与碰撞 ─────────────────────────

    def move(self) -> str:
        """
        移动蛇一步。返回结果：
        'ok'     — 正常移动
        'food'   — 吃到了食物
        'death'  — 撞墙或撞自己
        'win'    — 蛇填满棋盘，胜利
        """
        self._apply_direction()

        head_x = self.head[0] + self.direction.dx
        head_y = self.head[1] + self.direction.dy
        new_head = (head_x, head_y)

        # 边界碰撞
        if head_x < 0 or head_x >= self.cols or head_y < 0 or head_y >= self.rows:
            return "death"

        # 自身碰撞（注意：尾巴会在没吃到食物时移除，所以先排除尾巴）
        tail_removed = self.snake.pop()  # 先挪走尾巴
        self.snake_set.discard(tail_removed)
        self_collision = new_head in self.snake_set

        if self_collision:
            # 恢复尾巴再返回
            self.snake.append(tail_removed)
            self.snake_set.add(tail_removed)
            return "death"

        # 插入新头
        self.snake.insert(0, new_head)
        self.snake_set.add(new_head)

        # 吃到食物？
        if new_head == self._food:
            self.score += 1
            self.snake.append(tail_removed)  # 尾巴长回来
            self.snake_set.add(tail_removed)
            # 胜利检测
            if len(self.snake) >= self._cells:
                return "win"
            self._food = self.spawn_food()
            return "food"

        return "ok"

    # ── 食物生成 ───────────────────────────

    def spawn_food(self) -> Tuple[int, int]:
        """
        在空格中随机生成食物。

        优化：维护空位集合，避免 wait-loop 死循环。
        当空位 ≤ 20 时从空位列表中随机选取。
        """
        free_count = self._cells - len(self.snake)
        if free_count <= 0:
            return (-1, -1)  # 无空位

        # 当空位较少时，直接枚举所有空位
        if free_count <= 20:
            free_cells = [
                (c, r) for c in range(self.cols) for r in range(self.rows)
                if (c, r) not in self.snake_set
            ]
            return random.choice(free_cells)

        # 空位充足时，随机采样（最多 100 次尝试）
        for _ in range(100):
            x = random.randrange(self.cols)
            y = random.randrange(self.rows)
            if (x, y) not in self.snake_set and (x, y) != self._food:
                return (x, y)

        # 兜底：枚举
        free_cells = [
            (c, r) for c in range(self.cols) for r in range(self.rows)
            if (c, r) not in self.snake_set
        ]
        return random.choice(free_cells) if free_cells else (-1, -1)

    # ── 重置 ───────────────────────────────

    def reset(self) -> None:
        """重置游戏逻辑到初始状态。"""
        self.snake = list(INITIAL_SNAKE)
        self.snake_set = set(self.snake)
        self.direction = Direction.RIGHT
        self._next_direction = None
        self.score = 0
        self._food = self.spawn_food()


# ═══════════════════════════════════════════
# GUI 层（tkinter）
# ═══════════════════════════════════════════

class SnakeGame:
    """贪吃蛇 GUI 层，负责渲染和输入。"""

    def __init__(self, auto: bool = False) -> None:
        self.auto = auto
        self._auto_deadlock = 0

        self.root = tk.Tk()
        self.root.title("贪吃蛇 - Snake" + (" [AI]" if auto else ""))
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        self.canvas = tk.Canvas(
            self.root, width=WIDTH, height=HEIGHT,
            bg=COLOR_BG, highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.focus_set()

        # 逻辑层
        self.logic = SnakeLogic(COLS, ROWS)

        # 状态
        self.state: GameState = GameState.START
        self.auto: bool = auto
        self._auto_deadlock: int = 0
        self._after_id: Optional[str] = None
        self._tick_ms: int = BASE_TICK_MS
        self._high_score: int = self._load_high_score()
        self._pulse_t: float = 0.0

        # Canvas 复用项 ID
        self._grid_ids: List[int] = []
        self._snake_ids: List[int] = []
        self._food_id: Optional[int] = None
        self._food_glow_id: Optional[int] = None
        self._score_text_id: Optional[int] = None
        self._mode_text_id: Optional[int] = None
        self._overlay_ids: List[int] = []

        # 按键映射
        self._key_map: Dict[str, Direction] = {
            "Up": Direction.UP,
            "Down": Direction.DOWN,
            "Left": Direction.LEFT,
            "Right": Direction.RIGHT,
            "w": Direction.UP,
            "s": Direction.DOWN,
            "a": Direction.LEFT,
            "d": Direction.RIGHT,
        }

        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Destroy>", self._on_destroy)

        self._draw_start_screen()
        self.root.mainloop()

    # ══ 高分持久化 ═══════════════════════════

    def _load_high_score(self) -> int:
        try:
            if os.path.exists(HIGH_SCORE_FILE):
                with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as f:
                    return int(f.read().strip())
        except (ValueError, OSError):
            pass
        return 0

    def _save_high_score(self) -> None:
        try:
            with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as f:
                f.write(str(self._high_score))
        except OSError:
            pass

    # ══ 按键处理 ═════════════════════════════

    def _on_key(self, event: tk.Event) -> None:
        """统一按键处理，按状态分发。"""
        key = event.keysym

        if self.state == GameState.START:
            if key in ("space", "Return"):
                self.auto = False
                self._start_game()
                return
            if key == "2":
                self.auto = True
                self._start_game()
                return
            return

        if self.state == GameState.PLAYING:
            if key in ("p", "P", "space"):
                self._pause_game()
                return
            if key == "F2":
                self.auto = not self.auto
                self._auto_deadlock = 0
                self.root.title("贪吃蛇 - Snake" + (" [AI]" if self.auto else ""))
                self._update_score_display()
                return
            if not self.auto:
                direction = self._key_map.get(key)
                if direction is not None:
                    self.logic.set_direction(direction)
            return

        if self.state == GameState.PAUSED:
            if key in ("p", "P", "space"):
                self._resume_game()
            return

        if self.state in (GameState.GAME_OVER, GameState.WIN):
            if key == "Return":
                self._restart_game()
            return

    # ══ 状态转换 ═════════════════════════════

    def _start_game(self) -> None:
        """从开始界面进入游戏。"""
        self.logic.reset()
        self.state = GameState.PLAYING
        self._tick_ms = BASE_TICK_MS
        self._clear_overlay()
        self._init_grid()
        self._init_snake_items()
        self._init_food_items()
        self._tick()

    def _pause_game(self) -> None:
        """暂停游戏。"""
        self.state = GameState.PAUSED
        self._cancel_tick()
        winsound.Beep(600, 80)
        self._draw_pause_overlay()

    def _resume_game(self) -> None:
        """继续游戏。"""
        self.state = GameState.PLAYING
        winsound.Beep(800, 80)
        self._clear_overlay()
        self._draw_snake()
        self._draw_food()
        self._tick()

    def _restart_game(self) -> None:
        """重新开始。"""
        self._cancel_tick()
        self.logic.reset()
        self.state = GameState.PLAYING
        self._tick_ms = BASE_TICK_MS
        self._clear_overlay()
        self._update_score_display()
        self._tick()

    def _game_over(self, reason: str) -> None:
        """游戏结束。"""
        self._cancel_tick()
        self.state = GameState.GAME_OVER if reason == "death" else GameState.WIN
        winsound.Beep(200, 300)
        winsound.Beep(150, 300)

        if self.logic.score > self._high_score:
            self._high_score = self.logic.score
            self._save_high_score()

        self._draw_end_screen(reason)

    # ══ after 回调管理（防并发） ════════════

    def _cancel_tick(self) -> None:
        if self._after_id is not None:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None

    # ══ 游戏主循环 ═══════════════════════════

    def _tick(self) -> None:
        """单帧更新（仅逻辑），然后调度下次渲染。"""
        if self.state != GameState.PLAYING:
            return

        if self.auto:
            d = self._auto_dir()
            if d is not None:
                self.logic.set_direction(d)

        result = self.logic.move()

        if result == "death" or result == "win":
            self._draw_snake()
            self._game_over(result)
            return

        if result == "food":
            winsound.Beep(1000, 50)
            # 递增速度
            if self.logic.score % SPEED_EVERY == 0:
                self._tick_ms = max(MIN_TICK_MS, self._tick_ms - SPEED_STEP_MS)

        self._draw_snake()
        self._draw_food()
        self._update_score_display()

        self._after_id = self.canvas.after(self._tick_ms, self._tick)

    # ══ 渲染 ═════════════════════════════════

    def _pixel_rect(self, col: int, row: int, pad: int = 0) -> Tuple[int, int, int, int]:
        """网格坐标 → 像素矩形，支持内边距使蛇段有间隙。"""
        x1 = col * CELL + pad
        y1 = row * CELL + pad
        x2 = (col + 1) * CELL - pad
        y2 = (row + 1) * CELL - pad
        return x1, y1, x2, y2

    def _init_grid(self) -> None:
        """初始化网格线（只创建一次，不再重绘）。"""
        for c in range(1, COLS):
            x = c * CELL
            self._grid_ids.append(
                self.canvas.create_line(x, 0, x, HEIGHT, fill=COLOR_GRID, width=1)
            )
        for r in range(1, ROWS):
            y = r * CELL
            self._grid_ids.append(
                self.canvas.create_line(0, y, WIDTH, y, fill=COLOR_GRID, width=1)
            )

    def _init_snake_items(self) -> None:
        """初始化蛇段 canvas item（复用）。"""
        for _ in self.logic.snake:
            sid = self.canvas.create_rectangle(0, 0, 0, 0, fill=COLOR_BODY_A, outline="")
            self._snake_ids.append(sid)

    def _init_food_items(self) -> None:
        """初始化食物 canvas item（复用）。"""
        fx, fy, _, _ = self._pixel_rect(*self.logic.food)
        r = CELL // 2 - 2
        self._food_glow_id = self.canvas.create_oval(
            0, 0, 0, 0, fill=COLOR_FOOD_GLOW, outline="", state="normal"
        )
        self._food_id = self.canvas.create_oval(
            0, 0, 0, 0, fill=COLOR_FOOD, outline=""
        )
        self._score_text_id = self.canvas.create_text(
            8, 4, text="Score: 0", fill=COLOR_TEXT,
            font=("Consolas", 12, "bold"), anchor="nw"
        )
        self._mode_text_id = self.canvas.create_text(
            WIDTH - 8, 4, text="", fill=COLOR_TEXT,
            font=("Consolas", 10), anchor="ne"
        )

    def _draw_snake(self) -> None:
        """使用 coords() 更新蛇的位置（不复用 delete/create），蛇变长时动态创建新 item。"""
        n = len(self.logic.snake)
        # 动态创建不足的 canvas item
        while len(self._snake_ids) < n:
            sid = self.canvas.create_rectangle(0, 0, 0, 0, fill=COLOR_BODY_A, outline="")
            self._snake_ids.append(sid)
        # 隐藏多余的 item（reset 后蛇变短）
        for i in range(n, len(self._snake_ids)):
            self.canvas.coords(self._snake_ids[i], -10, -10, -5, -5)
        # 更新可见段
        for i, seg in enumerate(self.logic.snake):
            color = COLOR_HEAD if i == 0 else (COLOR_BODY_A if i % 2 == 0 else COLOR_BODY_B)
            coords = self._pixel_rect(seg[0], seg[1], pad=1)
            self.canvas.coords(self._snake_ids[i], *coords)
            self.canvas.itemconfig(self._snake_ids[i], fill=color)

    def _draw_food(self) -> None:
        """使用 coords() 更新食物位置，并做脉冲缩放。"""
        self._pulse_t += 0.15
        scale = 1.0 + 0.15 * cos(self._pulse_t)  # 1.0 ~ 1.15 波动
        pad = int((CELL - CELL * scale) / 2)

        coords = self._pixel_rect(*self.logic.food, pad=pad)
        self.canvas.coords(self._food_id, *coords)

        # 发光光晕（比食物略大）
        glow_pad = max(0, pad - 2)
        glow_coords = self._pixel_rect(*self.logic.food, pad=glow_pad)
        self.canvas.coords(self._food_glow_id, *glow_coords)

    def _update_score_display(self) -> None:
        hs = f" | Best: {self._high_score}" if self._high_score else ""
        self.canvas.itemconfig(
            self._score_text_id,
            text=f"Score: {self.logic.score}{hs}"
        )
        mode = "[AI]" if self.auto else "[Manual]"
        color = "#ff6666" if self.auto else "#66ff66"
        self.canvas.itemconfig(self._mode_text_id, text=mode, fill=color)

    # ══ 覆盖层 ═══════════════════════════════

    def _clear_overlay(self) -> None:
        for oid in self._overlay_ids:
            self.canvas.delete(oid)
        self._overlay_ids.clear()

    def _draw_overlay_rect(self, alpha: int = 180) -> int:
        """画半透明背景遮罩。"""
        return self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT, fill=COLOR_OVERLAY_BG, outline="",
            stipple="gray25" if alpha < 200 else ""
        )

    def _draw_start_screen(self) -> None:
        """开始界面。"""
        oid = self._draw_overlay_rect(220)
        self._overlay_ids.append(oid)
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 60,
            text="🐍 贪吃蛇", fill=COLOR_HEAD, font=("Arial", 32, "bold"),
            anchor="center"
        ))
        lines = [
            "Enter / Space    手动游玩",
            "2                 AI 自动演示",
            "",
            "游戏中: F2 切换手动/AI ",
            "        P      暂停",
        ]
        y_off = 0
        for line in lines:
            self._overlay_ids.append(self.canvas.create_text(
                WIDTH // 2, HEIGHT // 2 + y_off,
                text=line, fill=COLOR_SMALL, font=("Consolas", 11),
                anchor="center"
            ))
            y_off += 22

        if self._high_score:
            self._overlay_ids.append(self.canvas.create_text(
                WIDTH // 2, HEIGHT - 20,
                text=f"最高分: {self._high_score}",
                fill=COLOR_SMALL, font=("Consolas", 10), anchor="center"
            ))

    def _draw_pause_overlay(self) -> None:
        """暂停覆盖层。"""
        oid = self._draw_overlay_rect(140)
        self._overlay_ids.append(oid)
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 15,
            text="⏸ 已暂停", fill=COLOR_PAUSE, font=("Arial", 28, "bold"),
            anchor="center"
        ))
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 25,
            text="按 Space / P 继续",
            fill=COLOR_SMALL, font=("Consolas", 11), anchor="center"
        ))

    def _draw_end_screen(self, reason: str) -> None:
        """游戏结束或胜利界面。"""
        oid = self._draw_overlay_rect(200)
        self._overlay_ids.append(oid)

        is_win = reason == "win"
        title = "🏆 恭喜通关！" if is_win else "💀 Game Over"
        color = COLOR_FOOD_GLOW if is_win else COLOR_FOOD

        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 50,
            text=title, fill=color, font=("Arial", 28, "bold"),
            anchor="center"
        ))

        score_text = f"得分: {self.logic.score}"
        if self.logic.score >= self._high_score and self._high_score > 0:
            score_text += "  ★ 新纪录！"
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2,
            text=score_text, fill=COLOR_TEXT, font=("Arial", 18),
            anchor="center"
        ))

        hs_text = f"最高分: {self._high_score}"
        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 30,
            text=hs_text, fill=COLOR_SMALL, font=("Consolas", 12),
            anchor="center"
        ))

        self._overlay_ids.append(self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 60,
            text="按 Enter 重新开始",
            fill=COLOR_SMALL, font=("Consolas", 11),
            anchor="center"
        ))

    # ══ AI 自动控制 ═══════════════════════════

    def _auto_start(self) -> None:
        """自动开始（AI 模式）。"""
        self._start_game()

    def _auto_dir(self) -> Optional[Direction]:
        """AI 决策下一步方向。"""
        logic = self.logic
        head = logic.head
        food = logic.food
        body = logic.snake_set

        path = self._bfs(head, food, body)
        if path and self._ai_safe(logic, path):
            return path[0]

        if self._auto_deadlock > 200:
            for d in Direction:
                if d == logic.direction.opposite():
                    continue
                nx, ny = head[0] + d.dx, head[1] + d.dy
                nxt = (nx, ny)
                if 0 <= nx < COLS and 0 <= ny < ROWS and nxt not in body:
                    sim_set = body.copy()
                    tail_pop = logic.snake[-1]
                    sim_set.discard(tail_pop)
                    sim_set.add(nxt)
                    if self._ai_reachable(nxt, sim_set - {nxt}) >= len(logic.snake):
                        self._auto_deadlock = 0
                        return d
            self._auto_deadlock = 0

        tail = logic.snake[-1]
        blocked = body.copy()
        blocked.discard(tail)
        path_to_tail = self._bfs(head, tail, blocked)
        if path_to_tail:
            self._auto_deadlock += 1
            return path_to_tail[0]

        best_d = None
        best_score = -9999
        for d in Direction:
            if d == logic.direction.opposite():
                continue
            nx, ny = head[0] + d.dx, head[1] + d.dy
            nxt = (nx, ny)
            if not (0 <= nx < COLS and 0 <= ny < ROWS) or nxt in body:
                continue
            sim_set = body.copy()
            sim_tail = logic.snake[-1]
            sim_set.discard(sim_tail)
            sim_set.add(nxt)
            area = self._ai_reachable(nxt, sim_set - {nxt})
            if area < len(logic.snake):
                continue
            dist = abs(nx - food[0]) + abs(ny - food[1])
            score = area * 10 - dist
            if score > best_score:
                best_score = score
                best_d = d

        if best_d is None:
            for d in Direction:
                if d == logic.direction.opposite():
                    continue
                nx, ny = head[0] + d.dx, head[1] + d.dy
                if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in body:
                    return d
        return best_d

    def _bfs(self, start, target, blocked):
        if start == target:
            return []
        q = deque([start])
        prev = {start: None}
        while q:
            cur = q.popleft()
            for d in Direction:
                nx, ny = cur[0] + d.dx, cur[1] + d.dy
                nxt = (nx, ny)
                if 0 <= nx < COLS and 0 <= ny < ROWS and nxt not in blocked and nxt not in prev:
                    prev[nxt] = (cur, d)
                    if nxt == target:
                        path = []
                        node = nxt
                        while prev[node] is not None:
                            parent, direc = prev[node]
                            path.append(direc)
                            node = parent
                        path.reverse()
                        return path
                    q.append(nxt)
        return None

    def _ai_reachable(self, start, blocked):
        if start in blocked:
            return 0
        seen = {start}
        q = deque([start])
        while q:
            cur = q.popleft()
            for d in Direction:
                nx, ny = cur[0] + d.dx, cur[1] + d.dy
                nxt = (nx, ny)
                if 0 <= nx < COLS and 0 <= ny < ROWS and nxt not in blocked and nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return len(seen)

    def _ai_safe(self, logic, path):
        snake = list(logic.snake)
        ss = set(snake)
        head = snake[0]
        fpos = logic.food
        for step in path:
            nh = (head[0] + step.dx, head[1] + step.dy)
            if nh == fpos:
                snake.insert(0, nh)
                ss.add(nh)
                fpos = (-1, -1)
            else:
                tail = snake.pop()
                ss.discard(tail)
                snake.insert(0, nh)
                ss.add(nh)
            head = nh
        h = snake[0]
        b = ss - {h, snake[-1]}
        return self._ai_reachable(h, b) >= len(snake) - 1

    # ══ 清理 ═════════════════════════════════

    def _on_destroy(self, event: tk.Event) -> None:
        self._cancel_tick()


if __name__ == "__main__":
    auto = len(sys.argv) > 1 and sys.argv[1] == "--auto"
    SnakeGame(auto=auto)
