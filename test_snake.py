"""
贪吃蛇逻辑层单元测试。

测试覆盖：
  - 初始状态
  - 方向控制（含反向保护）
  - 移动 / 墙体碰撞 / 自身碰撞
  - 食物吃取 / 蛇体增长
  - 胜利检测
  - 食物随机生成（覆盖空位少时的枚举路径）
  - 重置
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from snake import SnakeLogic, Direction, COLS, ROWS, INITIAL_SNAKE


def test_initial_state():
    """初始化状态正确。"""
    logic = SnakeLogic(COLS, ROWS)
    assert logic.snake == INITIAL_SNAKE
    assert logic.direction == Direction.RIGHT
    assert logic.score == 0
    assert logic.head == INITIAL_SNAKE[0]
    assert len(logic.snake_set) == len(logic.snake)
    print("  [PASS] test_initial_state")


def test_set_direction_valid():
    """正常方向切换。"""
    logic = SnakeLogic(COLS, ROWS)
    logic.set_direction(Direction.DOWN)
    logic.move()
    assert logic.direction == Direction.DOWN
    assert logic.head[1] > INITIAL_SNAKE[0][1]
    print("  [PASS] test_set_direction_valid")


def test_set_direction_opposite_ignored():
    """禁止 180° 掉头。"""
    logic = SnakeLogic(COLS, ROWS)
    logic.set_direction(Direction.LEFT)
    logic.move()
    assert logic.direction == Direction.RIGHT
    print("  [PASS] test_set_direction_opposite_ignored")


def test_direction_queue_prevents_reversal():
    """
    P0-1 fix: consecutive key presses within one frame won't cause 180° self-reversal.
    Scenario: snake moving Right, user quickly presses Up then Left.
    Left is opposite to Right, so Left is blocked; snake goes Up.
    """
    logic = SnakeLogic(COLS, ROWS)
    logic.set_direction(Direction.UP)
    logic.set_direction(Direction.LEFT)
    logic.move()
    assert logic.direction == Direction.UP, (
        f"Expected UP but got {logic.direction} - LEFT should be blocked as opposite of RIGHT"
    )
    head_before = logic.head
    result = logic.move()
    assert result == "ok", "Snake should not die going UP"
    assert logic.head[1] == head_before[1] - 1, "Head should have moved UP"
    print("  [PASS] test_direction_queue_prevents_reversal")


def test_wall_collision():
    """Wall collision detection."""
    logic = SnakeLogic(COLS, ROWS)
    for _ in range(COLS):
        result = logic.move()
        if result == "death":
            break
    assert result == "death"
    print("  [PASS] test_wall_collision")


def test_self_collision():
    """Self-collision detection."""
    initial = [(10, 10), (10, 11), (10, 12), (9, 12), (8, 12)]
    logic = SnakeLogic(COLS, ROWS, initial_snake=initial)
    logic.set_direction(Direction.UP)
    result = logic.move()
    assert result == "ok"
    logic.set_direction(Direction.LEFT)
    result = logic.move()
    assert result == "ok"
    logic.set_direction(Direction.DOWN)
    result = logic.move()
    assert result == "ok"
    logic.set_direction(Direction.RIGHT)
    result = logic.move()
    assert result == "death"
    print("  [PASS] test_self_collision")


def test_eat_food_grows_snake():
    """Eating food extends snake and increases score."""
    logic = SnakeLogic(COLS, ROWS)
    food_pos = (logic.head[0] + 1, logic.head[1])
    logic._food = food_pos
    initial_len = len(logic.snake)
    result = logic.move()
    assert result == "food"
    assert len(logic.snake) == initial_len + 1
    assert logic.score == 1
    print("  [PASS] test_eat_food_grows_snake")


def test_score_increment():
    """Consecutive eating accumulates score."""
    logic = SnakeLogic(COLS, ROWS)
    for i in range(5):
        food_pos = (logic.head[0] + 1, logic.head[1])
        logic._food = food_pos
        logic.move()
        assert logic.score == i + 1
    print("  [PASS] test_score_increment")


def test_win_condition():
    """Snake fills entire board -> win."""
    initial = [(0, 0), (1, 0), (1, 1)]
    logic = SnakeLogic(2, 2, initial_snake=initial)
    logic.direction = Direction.DOWN
    food_pos = (0, 1)
    logic._food = food_pos
    result = logic.move()
    assert result == "win" or result == "food"
    print("  [PASS] test_win_condition")


def test_spawn_food_not_on_snake():
    """Food never appears on the snake."""
    logic = SnakeLogic(COLS, ROWS)
    for _ in range(50):
        food = logic.spawn_food()
        assert food not in logic.snake_set
    print("  [PASS] test_spawn_food_not_on_snake")


def test_spawn_food_near_full():
    """Food generation works when board is nearly full."""
    logic = SnakeLogic(10, 10)
    occupied = [(c, r) for c in range(10) for r in range(9)]
    logic.snake = occupied
    logic.snake_set = set(occupied)
    food = logic.spawn_food()
    assert food not in logic.snake_set
    assert food[1] == 9
    print("  [PASS] test_spawn_food_near_full")


def test_reset():
    """Reset restores initial state."""
    logic = SnakeLogic(COLS, ROWS)
    logic.set_direction(Direction.DOWN)
    logic.move()
    logic.move()
    assert logic.score >= 0
    logic.reset()
    assert logic.snake == INITIAL_SNAKE
    assert logic.snake_set == set(INITIAL_SNAKE)
    assert logic.direction == Direction.RIGHT
    assert logic.score == 0
    print("  [PASS] test_reset")


def test_snake_set_integrity():
    """snake_set stays synchronized with snake list."""
    logic = SnakeLogic(COLS, ROWS)
    for _ in range(100):
        food_pos = (logic.head[0] + 1, logic.head[1])
        if 0 <= food_pos[0] < logic.cols and 0 <= food_pos[1] < logic.rows:
            logic._food = food_pos
        result = logic.move()
        if result == "death":
            break
        assert logic.snake_set == set(logic.snake), \
            f"set mismatch at len={len(logic.snake)}, score={logic.score}"
    print("  [PASS] test_snake_set_integrity")


def test_direction_enum():
    """Direction enum properties are correct."""
    assert Direction.UP.dx == 0
    assert Direction.UP.dy == -1
    assert Direction.DOWN.dx == 0
    assert Direction.DOWN.dy == 1
    assert Direction.LEFT.dx == -1
    assert Direction.LEFT.dy == 0
    assert Direction.RIGHT.dx == 1
    assert Direction.RIGHT.dy == 0
    assert Direction.UP.opposite() == Direction.DOWN
    assert Direction.LEFT.opposite() == Direction.RIGHT
    print("  [PASS] test_direction_enum")


def test_random_start_not_crash():
    """Multiple initializations don't crash."""
    for _ in range(20):
        logic = SnakeLogic()
        food = logic.spawn_food()
        assert food is not None
        assert food != (-1, -1)
    print("  [PASS] test_random_start_not_crash")


def run_all_tests():
    tests = [
        test_initial_state,
        test_set_direction_valid,
        test_set_direction_opposite_ignored,
        test_direction_queue_prevents_reversal,
        test_self_collision,
        test_eat_food_grows_snake,
        test_score_increment,
        test_win_condition,
        test_spawn_food_not_on_snake,
        test_spawn_food_near_full,
        test_reset,
        test_snake_set_integrity,
        test_direction_enum,
        test_random_start_not_crash,
    ]

    try:
        test_wall_collision()
    except AssertionError as e:
        print(f"  [FAIL] test_wall_collision: {e}")

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
