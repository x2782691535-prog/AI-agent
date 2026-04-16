import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet
import threading
import sys

# 全局状态，默认 0 为中性白噪音
current_mode = '0'


def eeg_streamer():
    # 创建一个 8 通道、250Hz 采样率的虚拟 EEG 流
    info = StreamInfo('MockEEG', 'EEG', 8, 250, 'float32', 'mock_uid_12345')
    outlet = StreamOutlet(info)
    fs = 250.0
    print("📡 LSL 虚拟脑电通道已开启。正在广播 'MockEEG' 数据流...")

    t = 0.0
    while True:
        signal_val = 0.0

        # ==========================================================
        # 🧠 适配 MNE 机器学习分类器的复合波形合成
        # ==========================================================
        if current_mode == '1':
            # 💤 疲劳 (Fatigue): 纯 Theta 波 (6Hz)
            signal_val = np.sin(2 * np.pi * 6 * t) * 5.0

        elif current_mode == '2':
            # 🍵 平和 (Calm): 纯 Alpha 波 (10Hz)
            signal_val = np.sin(2 * np.pi * 10 * t) * 5.0

        elif current_mode == '3':
            # ⚡ 兴奋 (Focus): 纯 Beta 波 (20Hz)
            signal_val = np.sin(2 * np.pi * 20 * t) * 5.0

        elif current_mode == '4':
            # 😊 开心 (Happy): Alpha (放松) + Beta (活跃) 的完美混合！
            signal_val = (np.sin(2 * np.pi * 10 * t) * 3.5) + (np.sin(2 * np.pi * 20 * t) * 3.5)

        elif current_mode == '5':
            # 🌧️ 沮丧/焦虑 (Distress): Theta (压抑) + Beta (活跃) 的混合！
            signal_val = (np.sin(2 * np.pi * 6 * t) * 3.5) + (np.sin(2 * np.pi * 20 * t) * 3.5)

        else:
            # 🌫️ 恢复日常中性 (Neutral): 没有主导频率
            signal_val = 0.0

        # 加入白噪音模拟真实脑电的粗糙感
        noise = np.random.normal(0, 0.5)
        sample = [signal_val + noise] * 8
        outlet.push_sample(sample)

        t += 1.0 / fs
        time.sleep(1.0 / fs)


def keyboard_listener():
    global current_mode
    print("\n🎮 [控制台指引] 请输入数字切换大脑状态 (按回车确认):")
    print("  [0] - 恢复日常 (消除主导状态，清除模型记忆)")
    print("  [1] - 触发: 认知疲劳 (Theta 主导)")
    print("  [2] - 触发: 深度平和 (Alpha 主导)")
    print("  [3] - 触发: 高度专注 (Beta 主导)")
    print("  [4] - 触发: 愉悦开心 (Alpha + Beta 双频共振) 🌟")
    print("  [5] - 触发: 焦虑沮丧 (Theta + Beta 认知冲突) 🌧️")
    print("--------------------------------------------------")

    while True:
        cmd = sys.stdin.readline().strip()
        if cmd in ['0', '1', '2', '3', '4', '5']:
            current_mode = cmd
            print(f"🔄 脑波频率已切换至模式: [{cmd}]。请保持 3 秒以上以触发模型检验...")


if __name__ == '__main__':
    threading.Thread(target=eeg_streamer, daemon=True).start()
    keyboard_listener()