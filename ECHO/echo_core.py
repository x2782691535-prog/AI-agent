from dotenv import load_dotenv

load_dotenv(override=True)

import time
import queue
import threading
import base64
from io import BytesIO
from datetime import datetime
import numpy as np
from scipy import signal
from pylsl import StreamInlet, resolve_byprop
import chromadb
from PIL import ImageGrab, Image
import mne

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn

# ==========================================
# FastAPI 实例初始化
# ==========================================
app = FastAPI(title="E.C.H.O. Neural API")

# ==========================================
# 向量数据库与大模型初始化 (Memory & LLM Core)
# ==========================================
# 初始化 ChromaDB 本地持久化客户端，用于存储多模态的神经记忆
chroma_client = chromadb.PersistentClient(path="./echo_memory_db")
# EEG 向量集合：以余弦相似度空间存储脑电特征，用于潜意识状态的相似性检索
eeg_collection = chroma_client.get_or_create_collection(name="eeg_memory", metadata={"hnsw:space": "cosine"})
# 文本集合：存储结合了时间、状态、屏幕视觉推断的综合文字记忆
text_collection = chroma_client.get_or_create_collection(name="text_memory", metadata={"hnsw:space": "cosine"})

# 初始化大语言模型，作为认知中枢
llm = ChatOpenAI(
    model="gpt-5.3-codex",
    temperature=0.1,  # 较低的温度以保证状态归因分析的稳定性与逻辑严密性
    frequency_penalty=1.0,
    presence_penalty=1.0
)


class NeuralState:
    """
    神经状态容器 (Thread-Safe)

    作为高速实时 EEG 数据流（后台线程）与异步 Web API（前端请求）之间的数据桥梁。
    使用 threading.Lock 确保在多线程环境下的读写原子性和数据一致性。
    """

    def __init__(self):
        # 存储最新的脑波频带能量与推断的心理指标
        self.latest_metrics = {
            "theta": 0.0, "alpha": 0.0, "beta": 0.0,
            "fatigue_idx": 0.0, "focus_idx": 0.0, "calm_idx": 0.0, "happy_idx": 0.0, "distress_idx": 0.0
        }
        # 存储最近发生的大脑状态跃迁事件及其 AI 建议
        self.latest_event = None

        # 定义读写锁
        self.metrics_lock = threading.Lock()
        self.event_lock = threading.Lock()

    def update_metrics(self, theta, alpha, beta, fatigue_idx, focus_idx, calm_idx, happy_idx, distress_idx):
        """线程安全地更新底层脑电节律及认知指标数据。"""
        with self.metrics_lock:
            self.latest_metrics = {
                "theta": theta, "alpha": alpha, "beta": beta,
                "fatigue_idx": fatigue_idx, "focus_idx": focus_idx,
                "calm_idx": calm_idx, "happy_idx": happy_idx, "distress_idx": distress_idx,
                "timestamp": time.time()
            }

    def set_event(self, state, advice, vector, image_b64=None):
        """线程安全地更新大脑状态跃迁事件。"""
        with self.event_lock:
            self.latest_event = {"state": state, "advice": advice, "vector": vector, "image_b64": image_b64,
                                 "timestamp": time.time()}


state_container = NeuralState()


@app.get("/metrics")
def get_metrics():
    """API 端点：获取当前实时的脑电指标。"""
    with state_container.metrics_lock:
        return state_container.latest_metrics


@app.get("/event")
def get_event():
    """API 端点：获取最近一次的大脑状态事件。"""
    with state_container.event_lock:
        return state_container.latest_event


class ChatRequest(BaseModel):
    """聊天请求的 Pydantic 数据模型"""
    query: str
    history: list = []


@app.post("/chat")
def chat_with_echo(request: ChatRequest):
    """
    E.C.H.O 认知管家交互接口 (RAG 核心层)

    该接口负责接收用户对话，并通过检索 ChromaDB 提取用户最近的大脑状态序列，
    将其作为上下文提示注入给大语言模型，从而实现具有时间感知和“读心”能力的回复。
    """
    try:
        context_str = "无相关历史记录。"

        if text_collection.count() > 0:
            # 直接提取出数据库里的所有记忆碎片
            all_records = text_collection.get()
            if all_records and all_records['metadatas'] and all_records['documents']:
                # 把元数据(包含时间戳)和文本内容打包成列表
                memories = list(zip(all_records['metadatas'], all_records['documents']))

                # 按照 timestamp 倒序排列（最近发生的排在最前面）
                memories.sort(key=lambda x: x[0]['timestamp'], reverse=True)

                # 强制抽取最近的 10 次大状态跃迁，让 AI 拥有完整的近期“记忆胶卷”
                recent_10 = memories[:10]

                # 再把顺序反转回来，让文本按照从旧到新的真实时间线排列，方便大模型阅读上下文演变
                recent_10.reverse()

                contexts = [m[1] for m in recent_10]
                context_str = "\n\n---\n\n".join(contexts)

        # 构建 System Prompt，实施人设并注入神经检索上下文
        messages = [
            SystemMessage(content=f"""你是 E.C.H.O. 认知管家与贴心伴侣。
【系统为你提取的最近 10 次大脑状态跃迁时间线】:
{context_str}

【最高交互准则】:
1. 你现在的脑海中拥有一条按时间排序的完整记忆流。绝对不要再说“找不到记录”！
2. 当用户询问“上一次XX状态是什么时候”或“我今天经历了哪些状态”时，仔细查阅上方的时间线并主动串联起来回答。
3. 必须包含【具体时间】和【持续多长时间】（如果仍显示“状态持续中”，则明确告知用户此刻依然处于该状态）。
4. 结合记忆里的【AI分析】告诉TA当时可能在做什么，语气自然温暖，充满同理心。""")
        ]

        # 挂载历史对话记录（仅保留最近 4 条以优化上下文窗口）
        for msg in request.history[-4:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=request.query))

        # 调用 LLM 生成回复
        response = llm.invoke(messages)
        return {"answer": response.content}
    except Exception as e:
        return {"answer": f"抱歉，我的神经检索中枢遇到了一点问题：{str(e)}"}


@app.post("/clear_memory")
def clear_memory():
    """API 端点：清除所有存储在向量数据库中的脑电及文本记忆。"""
    global eeg_collection, text_collection
    try:
        chroma_client.delete_collection(name="eeg_memory")
        chroma_client.delete_collection(name="text_memory")
        eeg_collection = chroma_client.create_collection(name="eeg_memory", metadata={"hnsw:space": "cosine"})
        text_collection = chroma_client.create_collection(name="text_memory", metadata={"hnsw:space": "cosine"})
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class EEGFeatureExtractor:
    """
    脑电信号频域特征提取器

    使用 Welch 方法将时域信号转换为功率谱密度（PSD），从而提取经典的脑波频带能量。
    当前支持的频带：Theta (4-8 Hz), Alpha (8-13 Hz), Beta (13-30 Hz)。
    """

    def __init__(self, fs=250.0):
        self.fs = fs  # 采样率 (Sampling Frequency)
        mne.set_log_level('WARNING')

    def extract_features(self, data_chunk):
        """
        对传入的数据块进行傅里叶变换及能量积分。

        参数:
            data_chunk (np.ndarray): 形状为 (n_samples, n_channels) 的时域 EEG 矩阵。

        返回:
            tuple: (特征向量数组[Theta, Alpha, Beta], Theta能量, Alpha能量, Beta能量)
        """
        data_mne = data_chunk.T  # 转换形状为 (n_channels, n_samples) 以适配 mne
        n_fft = min(int(self.fs * 2), data_chunk.shape[0])

        # 使用 Welch 方法计算 PSD
        psds, freqs = mne.time_frequency.psd_array_welch(
            data_mne, sfreq=self.fs, fmin=1.0, fmax=50.0,
            n_fft=n_fft, verbose=False
        )

        psd_mean = np.mean(psds, axis=0)  # 在所有通道上取平均
        bands = {'Theta': (4.0, 8.0), 'Alpha': (8.0, 13.0), 'Beta': (13.0, 30.0)}
        band_powers = {}

        # 在指定频带内进行数值积分，并除以带宽以获取平均功率
        for band_name, (f_low, f_high) in bands.items():
            idx = np.logical_and(freqs >= f_low, freqs < f_high)
            power = np.trapezoid(psd_mean[idx], freqs[idx])
            bandwidth = f_high - f_low
            band_powers[band_name] = float(power / bandwidth)

        feature_vector = np.array([band_powers['Theta'], band_powers['Alpha'], band_powers['Beta']])
        return feature_vector, band_powers['Theta'], band_powers['Alpha'], band_powers['Beta']


class EmotionClassifier:
    """
    启发式脑波状态分类器

    基于不同频带相对能量的阈值规则，将脑电特征映射为六种预定义的认知或情绪状态。
    注：这属于专家系统规则引擎，依赖绝对的占比与硬编码阈值进行推理。
    """

    def __init__(self):
        self.model_loaded = False
        self.labels = ['calm', 'happy', 'distress', 'fatigue', 'focus', 'neutral']

    def predict_proba(self, feature_vector):
        """
        计算各认知状态的倾向性概率，并选出最可能的状态。

        返回:
            tuple: (置信度最高的状态标签, 包含各个状态概率的字典)
        """
        theta, alpha, beta = feature_vector[0], feature_vector[1], feature_vector[2]
        total = theta + alpha + beta + 1e-6
        # 计算相对功率
        p_theta, p_alpha, p_beta = theta / total, alpha / total, beta / total
        w_beta = 3.5  # Beta 波的放大权重（补偿高频衰减特性）

        # 定义启发式评分规则
        probs = {
            'calm': p_alpha if p_alpha > 0.5 else 0.0,
            'fatigue': p_theta if p_theta > 0.5 else 0.0,
            'focus': (p_beta * w_beta) if p_beta > 0.2 else 0.0,
            'happy': (p_alpha * (p_beta * w_beta) * 2.0) if (p_alpha > 0.3 and p_beta > 0.15) else 0.0,
            'distress': (p_theta * (p_beta * w_beta) * 2.0) if (p_theta > 0.3 and p_beta > 0.15) else 0.0,
        }

        max_label = max(probs, key=probs.get)
        max_prob = probs[max_label]

        # 设定静息态(neutral)的准入阈值
        if max_prob < 0.4:
            return 'neutral', probs

        # 抑制非主要标签以凸显主导状态
        for k in probs:
            if k != max_label:
                probs[k] *= 0.2
            else:
                probs[k] = min(probs[k], 1.0)

        return max_label, probs


class ECHOInterventionEngine(threading.Thread):
    """
    E.C.H.O 干预引擎 (后台服务)

    负责处理由 EEGSentinel 产生的状态事件。当检测到大脑状态发生持续跃迁时：
    1. 捕捉当前屏幕画面（提供客观上下文）。
    2. 从 ChromaDB 检索过往相似的 EEG 记忆。
    3. 将【脑波状态 + 屏幕画面 + 检索上下文】打包提交给多模态大模型，以生成环境推断或温柔建议。
    4. 将新事件录入向量数据库，形成记忆闭环。
    """

    def __init__(self, event_queue):
        super().__init__(daemon=True)
        self.event_queue = event_queue

    def capture_screen(self):
        """捕捉屏幕并进行降采样、Base64 编码，为大模型提供视觉上下文。"""
        try:
            screen = ImageGrab.grab(all_screens=True)
            screen.thumbnail((768, 768), Image.Resampling.NEAREST)
            buf = BytesIO()
            screen.save(buf, format="JPEG", quality=50)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    def run(self):
        while True:
            event_data = self.event_queue.get()

            if event_data['action'] == 'start':
                # --- 状态开始的处理逻辑 ---
                eeg_vector = event_data['eeg_vector']
                current_state = event_data['state']
                evt_id = event_data['evt_id']
                start_time = event_data['start_time']

                image_b64 = self.capture_screen()

                # 先在前端立刻展示状态，表明 AI 正在分析中
                state_container.set_event(
                    state=f"{current_state} (AI 归因中...)",
                    advice="⏳ 发现稳态改变，正在提取多模态上下文...",
                    vector=eeg_vector,
                    image_b64=image_b64
                )

                past_context = "无相似记忆"
                if eeg_collection.count() > 0:
                    # 检索数据库中历史的、拥有类似底层脑波特征的记录
                    results = eeg_collection.query(query_embeddings=[eeg_vector], n_results=1)
                    if results['distances'] and len(results['distances'][0]) > 0 and results['distances'][0][0] < 0.2:
                        past_context = results['metadatas'][0][0].get('context', '无相似记忆')

                try:
                    # 使用大模型执行多模态推理
                    messages = [SystemMessage(
                        content="结合脑波状态、屏幕截图及历史记忆，判断用户当前在做什么，并给出极其简短（150字内）的温柔建议或归因分析。")]
                    user_content = [{"type": "text",
                                     "text": f"【当前状态】: {current_state}\n【历史记忆】: {past_context}\n为何我的大脑处于这个状态？我该怎么做？"}]
                    if image_b64:
                        user_content.append(
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
                    messages.append(HumanMessage(content=user_content))
                    advice = llm.invoke(messages).content
                except Exception as e:
                    advice = f"🚨 大模型推理崩溃：{str(e)}"

                # 更新前端展示包含 AI 建议的最终结果
                state_container.set_event(current_state, advice, eeg_vector, image_b64)

                # 将当前事件结构化，并写入 ChromaDB 构成长期记忆
                start_str = datetime.fromtimestamp(start_time).strftime("%Y年%m月%d日 %H时%M分%S秒")
                memory_text = f"【状态】: {current_state}\n【开始时间】: {start_str}\n【当时AI分析/环境推断】: {advice}\n【结束时间】: [状态持续中...]"

                eeg_collection.add(embeddings=[eeg_vector],
                                   metadatas=[{"context": memory_text, "timestamp": start_time}], ids=[evt_id])
                text_collection.add(documents=[memory_text],
                                    metadatas=[{"context": memory_text, "timestamp": start_time}], ids=[evt_id])

            elif event_data['action'] == 'end':
                # --- 状态结束的处理逻辑，补全数据库中缺失的“结束时间” ---
                evt_id = event_data['evt_id']
                end_time = event_data['end_time']
                start_time = event_data['start_time']

                duration_sec = int(end_time - start_time)
                mins, secs = divmod(duration_sec, 60)
                dur_str = f"{mins}分{secs}秒" if mins > 0 else f"{secs}秒"
                end_str = datetime.fromtimestamp(end_time).strftime("%Y年%m月%d日 %H时%M分%S秒")

                try:
                    res = text_collection.get(ids=[evt_id])
                    if res and res['documents'] and len(res['documents']) > 0:
                        old_doc = res['documents'][0]
                        old_meta = res['metadatas'][0]

                        # 修改之前预留的 "[状态持续中...]" 占位符
                        new_doc = old_doc.replace("【结束时间】: [状态持续中...]",
                                                  f"【结束时间】: {end_str}\n【持续总时长】: {dur_str}")
                        old_meta['context'] = new_doc

                        text_collection.update(ids=[evt_id], documents=[new_doc], metadatas=[old_meta])
                        eeg_collection.update(ids=[evt_id], metadatas=[old_meta])
                except Exception as e:
                    print(f"更新记忆闭环失败: {e}")

            self.event_queue.task_done()


class EEGSentinel:
    """
    脑电监视器 (核心调度引擎)

    1. 连接并维持 Lab Streaming Layer (LSL) 数据流。
    2. 采用滑动窗口 (Sliding Window) 接收并缓存连续脑电数据。
    3. 调用特征提取器与分类器进行实时分析。
    4. 运用状态机逻辑（防抖和持续性检测），在发现实质性稳态变化时，派发事件给干预引擎。
    """

    def __init__(self):
        self.fs = 250.0
        self.extractor = EEGFeatureExtractor(fs=self.fs)
        self.classifier = EmotionClassifier()

        self.inlet = self._connect_lsl()
        self.intervention_queue = queue.Queue()
        self.agent_thread = ECHOInterventionEngine(self.intervention_queue)
        self.agent_thread.start()

        self.window_size = int(self.fs * 4)  # 4秒的滑动窗口长度
        self.buffer = np.zeros((0, self.inlet.channel_count))

        # 状态机防抖控制变量
        self.current_sustained_state = None
        self.state_first_seen_time = 0
        self.last_reported_state = None
        self.SUSTAIN_SECONDS = 3.0  # 判定为有效状态变化前，状态必须持续的时间（阈值）

        self.active_evt_id = None
        self.active_start_time = None

    def _connect_lsl(self):
        """寻找并连接局域网内的 LSL 脑电数据流。"""
        streams = resolve_byprop('type', 'EEG', timeout=5.0)
        if not streams: raise RuntimeError("LSL EEG Stream not found.")
        return StreamInlet(streams[0])

    def run_realtime_loop(self):
        """主数据处理循环：持续从 LSL 拉取数据，更新缓冲池，并触发分析管线。"""
        while True:
            chunk, timestamps = self.inlet.pull_chunk(timeout=0.1, max_samples=int(self.fs))
            if timestamps:
                chunk_np = np.array(chunk)
                self.buffer = np.vstack((self.buffer, chunk_np))

                # 维持滑动窗口的最大容量，丢弃过期数据
                if len(self.buffer) > self.window_size: self.buffer = self.buffer[-self.window_size:]

                # 只有当缓冲区填满时才进行频谱分析
                if len(self.buffer) == self.window_size:
                    feature_vector, theta, alpha, beta = self.extractor.extract_features(self.buffer)
                    predicted_label, probs = self.classifier.predict_proba(feature_vector)

                    # 无论状态是否发生跃迁，实时更新前端的仪表盘指标
                    state_container.update_metrics(
                        theta, alpha, beta,
                        probs.get('fatigue', 0) * 100,
                        probs.get('focus', 0) * 100,
                        probs.get('calm', 0) * 100,
                        probs.get('happy', 0) * 100,
                        probs.get('distress', 0) * 100
                    )

                    # --- 状态机防抖逻辑 ---
                    if predicted_label == 'neutral':
                        # 若回到静息态，并且存在一个正在进行中的事件，则闭合该事件
                        if self.active_evt_id is not None:
                            self.intervention_queue.put({
                                'action': 'end', 'evt_id': self.active_evt_id,
                                'start_time': self.active_start_time, 'end_time': time.time()
                            })
                            self.active_evt_id = None
                            self.last_reported_state = None
                        self.current_sustained_state = None

                    elif predicted_label != self.current_sustained_state:
                        # 发现新的异于当前的标签，开启计时器
                        self.current_sustained_state = predicted_label
                        self.state_first_seen_time = time.time()

                    else:
                        # 当前预测状态延续
                        sustained_time = time.time() - self.state_first_seen_time

                        # 当状态持续超过阈值，且并非已报告的旧状态时，认定为真正的神经跃迁
                        if sustained_time >= self.SUSTAIN_SECONDS and self.current_sustained_state != self.last_reported_state:

                            # 如果此时有其他的活跃事件，强行闭合
                            if self.active_evt_id is not None:
                                self.intervention_queue.put({
                                    'action': 'end', 'evt_id': self.active_evt_id,
                                    'start_time': self.active_start_time, 'end_time': time.time()
                                })

                            self.last_reported_state = self.current_sustained_state

                            label = ""
                            if predicted_label == 'happy':
                                label = 'Joyful_Happy (愉悦/开心/积极)'
                            elif predicted_label == 'fatigue':
                                label = 'Cognitive_Fatigue (认知疲劳/犯困)'
                            elif predicted_label == 'focus':
                                label = 'Hyperactive_Focus (亢奋/高度紧张/专注)'
                            elif predicted_label == 'calm':
                                label = 'Peaceful_Calm (平和/深度放松/发呆)'
                            elif predicted_label == 'distress':
                                label = 'Emotional_Distress (焦虑/沮丧/冲突)'

                            if label != "":
                                # 生成唯一的事件 ID
                                evt_id = f"evt_{int(time.time())}"
                                self.active_evt_id = evt_id
                                self.active_start_time = time.time()

                                # 提交给后台的大语言模型引擎进行情境分析
                                self.intervention_queue.put({
                                    'action': 'start', 'evt_id': evt_id,
                                    'start_time': self.active_start_time,
                                    'state': label, 'eeg_vector': feature_vector.tolist()
                                })

            time.sleep(0.01)


def run_service():
    """程序入口：启动后台的 EEG 数据线程，并使用 Uvicorn 运行 Web 服务器。"""
    sentinel = EEGSentinel()
    threading.Thread(target=sentinel.run_realtime_loop, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    run_service()