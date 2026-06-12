"""
recycle_servo.py - 智慧資源回收箱 SG90 控制 API
適用：Raspberry Pi 5 + 三顆 SG90（分類轉盤 + 兩片閘門）

轉盤布局：
    左2    左1   idle   右1    右2
     0°    45°   90°   135°   180°
   OTHER  METAL       PAPER  PLASTIC
              (預設位置)

執行：
    sudo python3 recycle_servo.py

使用：
    from recycle_servo import RecycleBin, Category

    bin = RecycleBin()
    try:
        bin.dispose(Category.PLASTIC)
    finally:
        bin.cleanup()
"""
import os
import time
from enum import IntEnum


# ============ 硬體設定 ============
# 分類轉盤
TURNTABLE_CHIP = '/sys/class/pwm/pwmchip2'
TURNTABLE_CH = 0  # GPIO 17

# 閘門 A (左片)
GATE_A_CHIP = '/sys/class/pwm/pwmchip0'
GATE_A_CH = 2  # GPIO 18

# 閘門 B (右片)
GATE_B_CHIP = '/sys/class/pwm/pwmchip0'
GATE_B_CH = 3  # GPIO 19


# ============ 角度校正（依實機調整）============
class Category(IntEnum):
    """4 種回收分類"""
    PLASTIC = 0    # 塑膠
    PAPER = 1      # 紙類
    METAL = 2      # 金屬
    OTHER = 3      # 其他

# 轉盤角度（依實機調整）
# 預設 idle 在中間 (90°)，兩類在左 (0°, 45°)，兩類在右 (135°, 180°)
TURNTABLE_IDLE = 90  # 預設停留位置（中間）

TURNTABLE_ANGLES = {
    Category.OTHER:   0,    # 最左
    Category.METAL:   45,   # 左
    Category.PAPER:   135,  # 右
    Category.PLASTIC: 180,  # 最右
}

# 閘門角度（依機構調整）
GATE_CLOSED_A = 110   # A 片關閉角度
GATE_OPEN_A = 20      # A 片開啟角度（往左翻）
GATE_CLOSED_B = 40   # B 片關閉角度
GATE_OPEN_B = 130    # B 片開啟角度（往右翻）

# 時序
ROTATE_DELAY = 3.0   # 轉盤轉動等待時間
DROP_DURATION = 1.5  # 物品掉落時間


# ============ 底層工具 ============
def _write(path, value):
    """寫入 sysfs 檔案"""
    with open(path, 'w') as f:
        f.write(str(value))


def _angle_to_pulse_ns(angle):
    """角度轉換為 pulse width (奈秒)"""
    angle = max(0, min(180, angle))
    return int(500000 + (angle / 180.0) * 2000000)


def _setup_pwm(chip, channel, initial_angle):
    """
    初始化一個 PWM channel，啟用前先設好初始角度
    避免馬達在 enable 瞬間亂跑

    Args:
        chip: pwmchip 路徑
        channel: channel 編號
        initial_angle: 啟動時要保持的角度 (0-180)
    """
    pwm_path = f"{chip}/pwm{channel}"

    # 如果還沒 export 就 export
    if not os.path.exists(pwm_path):
        try:
            _write(f"{chip}/export", channel)
            time.sleep(0.2)
        except OSError:
            pass

    if not os.path.exists(pwm_path):
        raise RuntimeError(
            f"PWM 初始化失敗: {pwm_path}\n"
            f"檢查 config.txt 是否正確設定 PWM overlay"
        )

    # 設定週期 20ms = 50Hz
    _write(f"{pwm_path}/period", 20000000)

    # 關鍵：在 enable 之前先設好 duty_cycle
    # 這樣 PWM 一啟用就是正確位置，馬達不會亂跑
    _write(f"{pwm_path}/duty_cycle", _angle_to_pulse_ns(initial_angle))

    # 啟用 PWM 輸出
    _write(f"{pwm_path}/enable", 1)

    return pwm_path


def _set_angle(pwm_path, angle):
    """設定 PWM channel 對應的角度 (0-180 度)"""
    _write(f"{pwm_path}/duty_cycle", _angle_to_pulse_ns(angle))


# ============ 主類別 ============
class RecycleBin:
    """智慧回收箱控制器"""

    def __init__(self):
        print("[初始化] 設定 PWM...")

        # 三顆馬達啟動時就在安全位置，避免一通電就亂轉
        self.turntable = _setup_pwm(
            TURNTABLE_CHIP, TURNTABLE_CH,
            initial_angle=TURNTABLE_IDLE
        )
        self.gate_a = _setup_pwm(
            GATE_A_CHIP, GATE_A_CH,
            initial_angle=GATE_CLOSED_A
        )
        self.gate_b = _setup_pwm(
            GATE_B_CHIP, GATE_B_CH,
            initial_angle=GATE_CLOSED_B
        )
        self.current_category = None

        time.sleep(0.5)
        print("[初始化] 完成")

    # ---- 閘門控制 ----
    def close_gate(self):
        """關閉閘門（支撐物品）"""
        _set_angle(self.gate_a, GATE_CLOSED_A)
        _set_angle(self.gate_b, GATE_CLOSED_B)

    def open_gate(self):
        """開啟閘門（讓物品掉落）"""
        _set_angle(self.gate_a, GATE_OPEN_A)
        _set_angle(self.gate_b, GATE_OPEN_B)

    # ---- 轉盤控制 ----
    def rotate_to(self, category: Category):
        """轉盤轉到指定分類位置"""
        angle = TURNTABLE_ANGLES[category]
        _set_angle(self.turntable, angle)
        self.current_category = category
        time.sleep(ROTATE_DELAY)

    def rotate_to_idle(self):
        """轉盤回到中間 idle 位置"""
        _set_angle(self.turntable, TURNTABLE_IDLE)
        self.current_category = None
        time.sleep(ROTATE_DELAY)

    # ---- 完整流程 ----
    def dispose(self, category: Category, return_to_idle: bool = True):
        """
        完整投放流程：
        1. 轉盤轉到目標分類
        2. 開啟閘門讓物品掉落
        3. 等待物品落下
        4. 關閉閘門
        5. 轉盤回到 idle（可選）

        Args:
            category: 目標分類
            return_to_idle: 是否在投放後回到中間位置，預設 True
        """
        print(f"[投放] 分類: {category.name}")

        print("  → 轉動分類盤")
        self.rotate_to(category)

        print("  → 開啟閘門")
        self.open_gate()
        time.sleep(DROP_DURATION)

        print("  → 關閉閘門")
        self.close_gate()
        time.sleep(0.5)

        if return_to_idle:
            print("  → 轉盤回到中間")
            self.rotate_to_idle()

        print("[投放] 完成\n")

    def cleanup(self):
        """
        釋放資源前先回到安全位置
        注意：PWM 保持啟用，避免 pwm-gpio 在 disable 時馬達亂跑
        """
        try:
            self.close_gate()
            self.rotate_to_idle()
            time.sleep(0.5)
            print("[清理] 完成（PWM 保持啟用維持位置）")
        except Exception as e:
            print(f"[清理] 警告: {e}")


# ============ 互動模式 ============
if __name__ == "__main__":
    print("分類對應：")
    for cat in Category:
        print(f"  {cat.value} → {cat.name}")
    print("  q → 離開\n")

    bin = RecycleBin()
    try:
        while True:
            raw = input("輸入分類編號：").strip()
            if raw.lower() == 'q':
                break
            if not raw.isdigit():
                print("請輸入數字或 q 離開")
                continue
            num = int(raw)
            if num not in [cat.value for cat in Category]:
                print(f"無效編號，請輸入 {[cat.value for cat in Category]} 其中之一")
                continue
            bin.dispose(Category(num))
    finally:
        bin.cleanup()