"""
贪吃蛇 AI 控制器 v3 — BFS + 安全验证 + 死循环探测 + 随机探索
目标: 分数 > 100，30x20 棋盘
"""
import sys
import os
import random
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snake import SnakeLogic, Direction, COLS, ROWS


def bfs(start, target, blocked):
    """BFS 返回最短路径（方向列表）。"""
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


def reachable_count(start, blocked):
    """从 start 可达的空格数（含 start）。"""
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


def simulate_path(game, path):
    """模拟走完 path 后的蛇身（蛇可能吃到食物也可能没吃到）。"""
    snake = list(game.snake)
    snake_set = set(snake)
    head = snake[0]
    food_pos = game.food

    for step in path:
        new_head = (head[0] + step.dx, head[1] + step.dy)
        if new_head == food_pos:
            snake.insert(0, new_head)
            snake_set.add(new_head)
            # 吃完食物后无法模拟新食物，蛇只是变长了
            food_pos = (-1, -1)
        else:
            tail = snake.pop()
            snake_set.discard(tail)
            snake.insert(0, new_head)
            snake_set.add(new_head)
        head = new_head
    return snake, snake_set


def is_path_safe(game, path):
    """走完 path 后蛇是否安全（能从新头走到新尾）。"""
    snake, snake_set = simulate_path(game, path)
    head = snake[0]
    tail = snake[-1]
    body_blocked = snake_set - {head, tail}
    # 从 head 能否走到 tail（下一步 tail 会移开）
    area = reachable_count(head, body_blocked)
    return area >= len(snake) - 1


def best_direction(game, deadlock_counter):
    head = game.head
    food = game.food
    body = game.snake_set

    # ---- 1. 安全路径到食物 ----
    path = bfs(head, food, body)
    if path and is_path_safe(game, path):
        return path[0], 0

    # ---- 2. 死循环探测：走最远方向探索 ----
    if deadlock_counter > 200:
        # 随机挑一个安全方向打破循环
        safe_dirs = []
        for d in Direction:
            if d == game.direction.opposite():
                continue
            nx, ny = head[0] + d.dx, head[1] + d.dy
            nxt = (nx, ny)
            if 0 <= nx < COLS and 0 <= ny < ROWS and nxt not in body:
                sim_snake = list(game.snake)
                sim_snake_set = body.copy()
                tail = sim_snake.pop()
                sim_snake_set.discard(tail)
                sim_snake.insert(0, nxt)
                sim_snake_set.add(nxt)
                if reachable_count(nxt, sim_snake_set - {nxt}) >= len(sim_snake):
                    safe_dirs.append(d)
        if safe_dirs:
            chosen = random.choice(safe_dirs)
            return chosen, 0
        deadlock_counter = 0

    # ---- 3. 尾随策略 ----
    tail = game.snake[-1]
    blocked_for_tail = body.copy()
    blocked_for_tail.discard(tail)
    path_to_tail = bfs(head, tail, blocked_for_tail)
    if path_to_tail:
        return path_to_tail[0], deadlock_counter + 1

    # ---- 4. 最安全方向 ----
    best_d = None
    best_score = -9999
    for d in Direction:
        if d == game.direction.opposite():
            continue
        nx, ny = head[0] + d.dx, head[1] + d.dy
        nxt = (nx, ny)
        if not (0 <= nx < COLS and 0 <= ny < ROWS) or nxt in body:
            continue
        sim_snake = list(game.snake)
        sim_snake_set = body.copy()
        tail_pos = sim_snake.pop()
        sim_snake_set.discard(tail_pos)
        sim_snake.insert(0, nxt)
        sim_snake_set.add(nxt)

        # 评分：可达面积 + 到食物的距离惩罚
        area = reachable_count(nxt, sim_snake_set - {nxt})
        if area < len(sim_snake):
            continue
        dist = abs(nx - food[0]) + abs(ny - food[1])
        score = area * 10 - dist
        if score > best_score:
            best_score = score
            best_d = d

    # ---- 5. 兜底 ----
    if best_d is None:
        for d in Direction:
            if d == game.direction.opposite():
                continue
            nx, ny = head[0] + d.dx, head[1] + d.dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in body:
                return d, deadlock_counter + 1
    return best_d, deadlock_counter + (0 if best_d else 1)


def run_ai(target=100, max_steps=200000):
    game = SnakeLogic()
    steps = 0
    deadlock = 0

    while game.score < target and steps < max_steps:
        d, deadlock = best_direction(game, deadlock)
        if d is None:
            print(f"  STUCK  | score={game.score}, len={len(game.snake)}, steps={steps}")
            break
        game.set_direction(d)
        result = game.move()
        steps += 1

        if result == "death":
            print(f"  DIED   | score={game.score}, len={len(game.snake)}, steps={steps}")
            break
        if result == "win":
            print(f"  WIN!   | score={game.score}, steps={steps}")
            break

        if steps % 500 == 0:
            print(f"  LIVE   | score={game.score}, len={len(game.snake)}, steps={steps}")

    ok = game.score >= target
    print(f"  RESULT | score={game.score}, len={len(game.snake)}, steps={steps}")
    return ok, game.score


if __name__ == "__main__":
    print("Snake AI v3 - BFS + safety + deadlock-break + explore\n")
    success, score = run_ai(100)
    print(f"\n{'[OK] Hit target' if success else '[FAIL] Below target'} - final score: {score}")
    sys.exit(0 if success else 1)
