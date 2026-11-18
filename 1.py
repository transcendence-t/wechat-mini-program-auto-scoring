import os
import sys
import time

import pyautogui


# --- 参数配置 ---
APP_NAME = "教师互评工具"
SCORE_VALUE = os.getenv("REVIEW_SCORE", "20")
INPUT_VALUE = SCORE_VALUE  # 兼容旧配置名
SCORE_COUNT = int(os.getenv("REVIEW_SCORE_COUNT", "5"))
MAX_ROUNDS = int(os.getenv("REVIEW_MAX_ROUNDS", "0"))  # 0 表示一直循环

TARGET_PERSON_IMAGE = "target_person.png"
INPUT_BOX_IMAGE = "input_box.png"
SUBMIT_BUTTON_IMAGE = "submit_button.png"
RESOURCE_FILES = (TARGET_PERSON_IMAGE, INPUT_BOX_IMAGE, SUBMIT_BUTTON_IMAGE)

SCROLL_STEP_LIST = -300  # 在人名列表滚动的幅度，负数代表向下滚
SCROLL_STEP_FORM = -800  # 找不到提交按钮时，在填表页向下滚动
MAX_SCROLL_ATTEMPTS = 5  # 在列表页找不到人时，最多尝试滚动的次数
CONFIDENCE = 0.85  # 图像识别精准度

AUTO_ACTIVATE_WINDOW = True
TARGET_WINDOW_TITLE = os.getenv("REVIEW_WINDOW_TITLE", "打分测评").strip()
WINDOW_TITLE_KEYWORDS = tuple(
    keyword for keyword in (TARGET_WINDOW_TITLE, "微信", "WeChat") if keyword
)
START_DELAY_SECONDS = 3
WINDOW_ACTIVATE_DELAY = 0.8
SCROLL_METHOD = os.getenv("REVIEW_SCROLL_METHOD", "auto").strip().lower()
DRAG_SCROLL_DISTANCE = int(os.getenv("REVIEW_DRAG_SCROLL_DISTANCE", "260"))

LOCATE_RETRY_ATTEMPTS = 5
LOCATE_RETRY_INTERVAL = 0.15
INPUT_INTERVAL = 0.02
CLICK_DELAY = 0.15
PAGE_LOAD_DELAY = 0.7
SUBMIT_RETRY_ATTEMPTS = 5

SCREEN_CENTER_X = 500
SCREEN_CENTER_Y = 500
WINDOW_SCROLL_Y_RATIO = 0.55

CURRENT_TARGET_WINDOW = None

pyautogui.FAILSAFE = True  # 把鼠标甩到左上角可强制停止
pyautogui.PAUSE = 0.05


def resource_path(filename):
    """兼容源码运行和 PyInstaller 打包后的资源路径。"""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


def missing_resources(resource_files=RESOURCE_FILES):
    """返回缺失的模板资源文件名。"""
    return [filename for filename in resource_files if not os.path.exists(resource_path(filename))]


def run_self_check():
    """检查 exe 内置资源，不执行自动化操作。"""
    missing = missing_resources()
    print(f"{APP_NAME} 自检")
    print(f"目标窗口标题：{TARGET_WINDOW_TITLE}")
    print(f"滚动模式：{SCROLL_METHOD}")
    if missing:
        print("资源缺失：" + "、".join(missing))
        return 1

    print("资源检查通过。")
    return 0


def choose_target_window(windows, title_keywords=WINDOW_TITLE_KEYWORDS):
    """从窗口列表中选择标题匹配的目标窗口。"""
    for keyword in title_keywords:
        keyword_lower = keyword.lower()
        for window in windows:
            title = getattr(window, "title", "") or ""
            if keyword_lower in title.lower():
                return window
    return None


def get_all_windows():
    """获取当前桌面窗口；失败时返回空列表，让用户手动切换。"""
    try:
        import pygetwindow

        return pygetwindow.getAllWindows()
    except Exception as exc:
        print(f"警告：无法读取窗口列表，将改为手动切换窗口。原因：{exc}")
        return []


def activate_window(window):
    """尽量把目标窗口恢复并置前。"""
    try:
        if getattr(window, "isMinimized", False):
            window.restore()
            time.sleep(0.2)
        window.activate()
        time.sleep(WINDOW_ACTIVATE_DELAY)
        return True
    except Exception as exc:
        print(f"警告：自动激活窗口失败，将改为手动切换。原因：{exc}")
        return False


def get_target_window():
    """返回缓存的目标窗口；没有缓存时重新查找。"""
    global CURRENT_TARGET_WINDOW
    if CURRENT_TARGET_WINDOW:
        return CURRENT_TARGET_WINDOW

    CURRENT_TARGET_WINDOW = choose_target_window(get_all_windows())
    return CURRENT_TARGET_WINDOW


def prepare_target_window():
    """启动前准备目标窗口，让脚本窗口可以放在后台。"""
    global CURRENT_TARGET_WINDOW
    if AUTO_ACTIVATE_WINDOW:
        window = choose_target_window(get_all_windows())
        if window:
            CURRENT_TARGET_WINDOW = window
            print(f"已找到目标窗口：{window.title}")
            if activate_window(window):
                return

    print(f"请在 {START_DELAY_SECONDS} 秒内切换到“{TARGET_WINDOW_TITLE or '微信小程序'}”窗口...")
    time.sleep(START_DELAY_SECONDS)


def window_scroll_point(window):
    """计算窗口内容区域内适合滚动的坐标。"""
    if not window:
        return SCREEN_CENTER_X, SCREEN_CENTER_Y

    left = getattr(window, "left", None)
    top = getattr(window, "top", None)
    width = getattr(window, "width", None)
    height = getattr(window, "height", None)
    if None in (left, top, width, height) or width <= 0 or height <= 0:
        return SCREEN_CENTER_X, SCREEN_CENTER_Y

    x = int(left + width * 0.5)
    y = int(top + height * WINDOW_SCROLL_Y_RATIO)
    return x, y


def drag_scroll(ui, x, y, amount, target_window=None):
    """用拖拽模拟小程序下滑/上滑。"""
    height = getattr(target_window, "height", 0) or 0
    distance = min(DRAG_SCROLL_DISTANCE, max(120, int(height * 0.35))) if height else DRAG_SCROLL_DISTANCE
    half_distance = int(distance / 2)

    if amount < 0:
        start_y = y + half_distance
        end_y = y - half_distance
    else:
        start_y = y - half_distance
        end_y = y + half_distance

    ui.moveTo(x, start_y)
    ui.dragTo(x, end_y, duration=0.25, button="left")


def scroll_method_for_attempt(attempt_index):
    """auto 模式下交替使用滚轮和拖拽，提高小程序滚动成功率。"""
    if SCROLL_METHOD == "auto":
        return "wheel" if attempt_index % 2 == 0 else "drag"
    return SCROLL_METHOD


def scroll_in_target_window(
    amount,
    target_window=None,
    ui=pyautogui,
    method=None,
    delay=0.5,
):
    """在目标窗口内容区域滚动，而不是使用固定屏幕坐标。"""
    window = target_window or get_target_window()
    x, y = window_scroll_point(window)
    selected_method = method or SCROLL_METHOD

    ui.moveTo(x, y)
    if selected_method == "drag":
        drag_scroll(ui, x, y, amount, window)
    elif selected_method == "pagedown":
        ui.press("pagedown" if amount < 0 else "pageup")
    else:
        ui.scroll(amount)

    time.sleep(delay)


def locate_all(image_path):
    """安全地查找屏幕上的全部模板匹配。"""
    try:
        return list(pyautogui.locateAllOnScreen(resource_path(image_path), confidence=CONFIDENCE))
    except Exception as exc:
        print(f"警告：识别 {image_path} 失败：{exc}")
        return []


def locate_one(image_path):
    """安全地查找屏幕上的单个模板匹配。"""
    try:
        return pyautogui.locateOnScreen(resource_path(image_path), confidence=CONFIDENCE)
    except Exception as exc:
        print(f"警告：识别 {image_path} 失败：{exc}")
        return None


def wait_for_image(image_path, attempts=LOCATE_RETRY_ATTEMPTS, interval=LOCATE_RETRY_INTERVAL):
    """等待某个图像出现，减少页面加载慢导致的误判。"""
    for attempt in range(1, attempts + 1):
        box = locate_one(image_path)
        if box:
            return box
        if attempt < attempts:
            time.sleep(interval)
    return None


def click_box(box):
    """点击识别出的矩形中心。"""
    x, y = pyautogui.center(box)
    pyautogui.click(x, y)
    time.sleep(CLICK_DELAY)


def clean_focused_input(ui=pyautogui, input_interval=INPUT_INTERVAL):
    """清空当前焦点所在输入框。"""
    ui.hotkey("ctrl", "a")
    time.sleep(input_interval)
    ui.press("backspace")
    time.sleep(input_interval)


def type_scores_by_tab(
    ui=pyautogui,
    score_value=SCORE_VALUE,
    score_count=SCORE_COUNT,
    input_interval=INPUT_INTERVAL,
):
    """按 Tab 顺序依次填写所有评分。"""
    for index in range(score_count):
        print(f"填写第 {index + 1}/{score_count} 个评分")
        clean_focused_input(ui, input_interval)
        ui.write(score_value)
        time.sleep(input_interval)

        if index < score_count - 1:
            ui.press("tab")
            time.sleep(input_interval)


def find_person_and_enter():
    """步骤 1：检测被评分人，如果检测不到则下滑，直到找到或超时。"""
    attempts = 0
    while attempts < MAX_SCROLL_ATTEMPTS:
        print(f"正在寻找被评分人... (尝试 {attempts + 1})")
        people = locate_all(TARGET_PERSON_IMAGE)

        if people:
            people.sort(key=lambda p: p.top)
            target = people[0]
            x, y = pyautogui.center(target)
            print(f"找到目标，坐标：{x},{y}，正在点击...")
            pyautogui.click(x, y)
            time.sleep(PAGE_LOAD_DELAY)
            return True

        print("当前屏幕未找到，正在向下滑动列表...")
        scroll_in_target_window(SCROLL_STEP_LIST, method=scroll_method_for_attempt(attempts))
        attempts += 1

    print("错误：已多次滚动仍未找到目标，可能已到底部。")
    return False


def fill_form_steps():
    """步骤 2：点击第一个评分框，然后用 Tab 依次填写。"""
    print(">>> 开始填写表单（Tab 顺序）")
    first_input = wait_for_image(INPUT_BOX_IMAGE)
    if not first_input:
        print("错误：未检测到第一个评分输入框，停止本轮任务。")
        return False

    click_box(first_input)
    type_scores_by_tab()
    return True


def submit_and_return():
    """步骤 3：提交并返回。找不到按钮时向下滚动后重试。"""
    for attempt in range(1, SUBMIT_RETRY_ATTEMPTS + 1):
        print(f"正在寻找【填写完毕】按钮... (尝试 {attempt})")
        btn = locate_one(SUBMIT_BUTTON_IMAGE)

        if btn:
            click_box(btn)
            print("已提交，等待返回...")
            time.sleep(PAGE_LOAD_DELAY)
            return True

        if attempt < SUBMIT_RETRY_ATTEMPTS:
            print("暂未找到提交按钮，向下滚动后重试...")
            scroll_in_target_window(SCROLL_STEP_FORM, method=scroll_method_for_attempt(attempt - 1))

    print("错误：找不到提交按钮！")
    return False


def should_continue(round_count):
    return MAX_ROUNDS <= 0 or round_count <= MAX_ROUNDS


def main():
    if "--check" in sys.argv:
        return run_self_check()

    print("程序启动中。脚本窗口可以放后台，但微信小程序窗口不能最小化。")
    prepare_target_window()

    round_count = 1
    while should_continue(round_count):
        print(f"\n--- 第 {round_count} 轮任务开始 ---")

        if not find_person_and_enter():
            break

        if not fill_form_steps():
            break

        if not submit_and_return():
            break

        round_count += 1
        time.sleep(0.5)

    print("任务结束。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
