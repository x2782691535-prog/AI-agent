import os
import mne
import numpy as np
import base64
import json
import time  # 新增：用于倒计时
from io import BytesIO
from PIL import ImageGrab
from scipy.spatial.distance import cosine
from dotenv import load_dotenv, find_dotenv
import streamlit as st
import streamlit.components.v1 as components
import warnings
import re
from PIL import Image

# =====================================================================
# 0. 基础配置
# =====================================================================
warnings.filterwarnings("ignore", message=".*Accessing `__path__` from.*")
st.set_page_config(page_title="NeuroSkill Agent", page_icon="🧠", layout="wide")

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, wait_exponential, stop_after_attempt

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path, override=True)
os.environ["LANGCHAIN_TRACING_V2"] = "false"


# =====================================================================
# 1. 脑电与核心逻辑
# =====================================================================
class StreamingBrainVectorDB:
    def __init__(self):
        self.memory = []
        self.gdf_path = r"E:\桌面\数据集\BCICIV_2a_gdf\originalData\A01T.gdf"
        self.raw = mne.io.read_raw_gdf(self.gdf_path, preload=True, verbose='ERROR')
        events, self.event_id = mne.events_from_annotations(self.raw, verbose='ERROR')
        cue_tags = ['769', '770', '771', '772']
        valid_ids = [eid for desc, eid in self.event_id.items() if desc in cue_tags]
        self.mi_events = [e for e in events if e[2] in valid_ids]
        self.c3_idx, self.cz_idx, self.c4_idx = 7, 9, 11
        self.raw.load_data(verbose='ERROR')
        self.raw.set_eeg_reference('average', projection=False, verbose='ERROR')
        self.mu_continuous = self.raw.copy().filter(l_freq=8., h_freq=12., method='iir', verbose='ERROR')

    def process_live_trial(self, trial_index: int):
        if trial_index >= len(self.mi_events): return None
        target_event = self.mi_events[trial_index]
        onset_sec = target_event[0] / self.raw.info['sfreq']
        actual_intent = [desc for desc, eid in self.event_id.items() if eid == target_event[2]][0]
        label = {'769': '左手', '770': '右手', '771': '双脚', '772': '舌头'}.get(actual_intent)
        base_tmin, base_tmax = onset_sec - 1.5, onset_sec - 0.5
        task_tmin, task_tmax = onset_sec + 0.5, onset_sec + 4.0
        mu_base_data = self.mu_continuous.copy().crop(tmin=base_tmin, tmax=base_tmax).get_data()
        mu_task_data = self.mu_continuous.copy().crop(tmin=task_tmin, tmax=task_tmax).get_data()
        c3_erd = ((np.var(mu_task_data[self.c3_idx, :]) - np.var(mu_base_data[self.c3_idx, :])) / (
                np.var(mu_base_data[self.c3_idx, :]) + 1e-10)) * 100
        cz_erd = ((np.var(mu_task_data[self.cz_idx, :]) - np.var(mu_base_data[self.cz_idx, :])) / (
                np.var(mu_base_data[self.cz_idx, :]) + 1e-10)) * 100
        c4_erd = ((np.var(mu_task_data[self.c4_idx, :]) - np.var(mu_base_data[self.c4_idx, :])) / (
                np.var(mu_base_data[self.c4_idx, :]) + 1e-10)) * 100
        vector = np.array([c3_erd, cz_erd, c4_erd])
        return {"trial_id": trial_index, "label": label, "c3_erd": round(c3_erd, 2), "cz_erd": round(cz_erd, 2),
                "c4_erd": round(c4_erd, 2), "vector": vector}

    def search_and_memorize(self, current_state):
        past_memory = None
        if len(self.memory) > 0:
            similarities = [(cosine(current_state["vector"], past["vector"]), past) for past in self.memory]
            similarities.sort(key=lambda x: x[0])
            past_memory = similarities[0][1]
        self.memory.append(current_state)
        return past_memory


@st.cache_resource
def get_stream_db(): return StreamingBrainVectorDB()


stream_db = get_stream_db()


@tool
def perceive_and_remember(trial_index: int) -> dict:
    """核心工具：提取脑电特征。"""
    current_state = stream_db.process_live_trial(trial_index)
    if not current_state: return {"error": "获取脑电数据失败"}
    past_memory = stream_db.search_and_memorize(current_state)
    return {"current_state": current_state, "retrieved_memory": past_memory}


# =====================================================================
# 2. Agent 代理引擎 (因果逻辑)
# =====================================================================
# 🚨 暂时注释掉 retry 以方便调试 API 问题
# @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def ask_neuro_agent_with_vision(trial_id, base64_image):
    llm = ChatOpenAI(model="gpt-5.3-codex", temperature=0.3, max_tokens=1500)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的认知神经分析师与贴心的AI伴侣。
        【核心任务】：结合用户的“客观脑电状态”与“当前视觉环境”，给出一份符合因果逻辑的心智状态洞察。

        【绝对规则（必须严格遵守）】：
        1. 必须先调用 `perceive_and_remember` 工具获取 C3/Cz/C4 的 ERD 数据。你需要根据这些数值评估用户的认知负荷、专注度或疲劳度。（🚨警告：工具返回的 label 如“双脚/左手”仅仅代表测试触发范式，请完全忽略字面意思，千万不要提及“双脚/左手”！）。
        2. 观察截图，识别用户当前正在进行的真实日常活动（例如：写代码、看论文、看视频等）。🚨绝对不要用截图去验证脑电，截图仅仅是用来寻找导致疲劳/专注的原因！
        3. 用共情的语气（第一人称），将“脑电状态”和“屏幕活动”拼接起来。

        【输出结构】：
        - 简述脑电情况，判断当前状态（高度集中/疲劳/分心...）。
        - 描述看到屏幕上正在干嘛（比如在死磕一段报错、在看学术论文）。
        - 结合两者给出原因分析，并在需要时提醒休息或鼓励。不少于 300 字。"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, [perceive_and_remember], prompt)
    executor = AgentExecutor(agent=agent, tools=[perceive_and_remember], verbose=False)

    input_text = f"现在是 Trial {trial_id}。请提取脑电数据，并结合我的屏幕截图，告诉我我的大脑状态以及原因。"
    content = [{"type": "text", "text": input_text}, {"type": "image_url", "image_url": {
        "url": f"data:image/jpeg;base64,{base64_image}"}}] if base64_image else input_text

    try:
        return executor.invoke({"input": content})
    except Exception as e:
        error_msg = f"API 拒绝访问或处理失败。\n真实原因: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)


# =====================================================================
# 3. 前端卡拉OK组件
# =====================================================================
def get_voice_and_js(text):
    clean_text = re.sub(r'[*#_~`]', ' ', text)
    clean_text = re.sub(r'[\[\]{}]', ' ', clean_text)
    clean_text = re.sub(r'[\U00010000-\U0010ffff]', ' ', clean_text)
    safe_text = json.dumps(clean_text)

    html_code = f"""
    <div style="margin-bottom: 15px; display: flex; gap: 10px; position: sticky; top: 0; background: white; z-index: 10; padding: 10px 0;">
        <button id="play-btn" style="padding: 10px 24px; background: #ff4b4b; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; width: 160px; transition: all 0.2s;">
            🔊 开启语音播报
        </button>
        <button id="reset-btn" style="padding: 10px 24px; background: #F0F2F6; color: #31333F; border: 1px solid #DDE2E6; border-radius: 8px; cursor: pointer; font-weight: bold;">
            ⏹ 重置
        </button>
    </div>

    <div id="text-container" style="font-size: 18px; line-height: 2.0; color: black; font-family: sans-serif; white-space: pre-wrap; will-change: contents;"></div>

    <script>
        const btn = document.getElementById('play-btn');
        const resetBtn = document.getElementById('reset-btn');
        const container = document.getElementById("text-container");
        const rawText = {safe_text};

        const chars = rawText.split('');
        container.innerHTML = chars.map((c, i) => 
            `<span class="char" id="c-${{i}}" style="color: black; transition: color 0.15s ease-out;">${{c}}</span>`
        ).join('');
        const domNodes = chars.map((_, i) => document.getElementById(`c-${{i}}`));

        let synth = window.speechSynthesis;
        let utterance = null;
        let isSpeaking = false; 
        let currentIndex = -1;
        let fakeIndex = -1;
        let smoothTimer = null;

        function fastUpdate(newIndex) {{
            if (!isSpeaking) return;
            for(let i = 0; i <= newIndex; i++) {{
                if(domNodes[i] && domNodes[i].style.color !== "black") {{
                    domNodes[i].style.color = "black";
                }}
            }}
        }}

        function applyPauseState() {{ domNodes.forEach(n => {{ if(n) n.style.color = "black"; }}); }}
        function applyPlayState() {{ domNodes.forEach((n, i) => {{ if(n) n.style.color = i <= currentIndex ? "black" : "#C0C0C0"; }}); }}

        function speakFrom(index) {{
            let startIndex = Math.max(0, index);
            let remainingText = rawText.substring(startIndex);
            if (remainingText.trim() === "") return;

            utterance = new SpeechSynthesisUtterance(remainingText);
            utterance.lang = 'zh-CN';
            utterance.rate = 1.1;

            utterance.onstart = () => {{
                isSpeaking = true;
                btn.innerText = "⏸ 暂停声音";
                btn.style.background = "#ff4b4b";
                applyPlayState();

                clearInterval(smoothTimer);
                fakeIndex = currentIndex;
                smoothTimer = setInterval(() => {{
                    if (isSpeaking && fakeIndex < chars.length) {{
                        fakeIndex += 0.3; 
                        if (fakeIndex > currentIndex + 6) fakeIndex = currentIndex + 6;
                        requestAnimationFrame(() => fastUpdate(Math.floor(fakeIndex)));
                    }}
                }}, 50);
            }};

            utterance.onboundary = (e) => {{
                if (e.name === 'word' || e.name === 'sentence') {{
                    let absoluteIndex = startIndex + e.charIndex;
                    currentIndex = absoluteIndex;
                    fakeIndex = absoluteIndex; 
                    requestAnimationFrame(() => fastUpdate(absoluteIndex));
                }}
            }};

            utterance.onend = (e) => {{
                clearInterval(smoothTimer);
                if (isSpeaking) {{ 
                    isSpeaking = false; 
                    currentIndex = -1;
                    btn.innerText = "🔊 开启语音播报";
                    applyPauseState();
                }}
            }};
            synth.speak(utterance);
        }}

        btn.onclick = () => {{
            if (!isSpeaking) {{
                btn.innerText = "⏳ 加载中...";
                btn.style.background = "#ff9999";
                synth.cancel(); 
                setTimeout(() => {{ speakFrom(currentIndex + 1 > 0 ? currentIndex : 0); }}, 50);
            }} else {{
                isSpeaking = false; 
                synth.cancel(); 
                clearInterval(smoothTimer);
                btn.innerText = "▶ 继续声音"; 
                btn.style.background = "#e0f7fa";
                applyPauseState(); 
            }}
        }};

        resetBtn.onclick = () => {{
            synth.cancel(); clearInterval(smoothTimer);
            isSpeaking = false; currentIndex = -1;
            btn.innerText = "🔊 开启语音播报"; 
            btn.style.background = "#ff4b4b";
            applyPauseState();
        }};
    </script>
    """
    return html_code


# =====================================================================
# 4. UI 布局与主调度
# =====================================================================
st.title("🧠 脑机接口大模型 模拟终端")

with st.sidebar:
    st.header("⚙️ 环境控制")
    target_trial = st.number_input("Trial ID (选择脑波段)", 0, 280, 60)

    # 🔥 新增核心功能：延迟截屏滑块
    delay_secs = st.slider(
        "⏱️ 截屏延迟 (秒)",
        min_value=0, max_value=15, value=5,
        help="设定后，点击按钮会有相应时间的倒计时。请利用这段时间将窗口切换到你要模拟的工作环境（如代码、论文页面），倒计时结束后会自动抓取该画面。"
    )

    st.divider()
    run_btn = st.button("🚀 触发主动感知", type="primary", use_container_width=True)

col1, col2 = st.columns([1, 1.5])

# 执行逻辑
if run_btn:
    # 1. 🔥 倒计时阶段
    if delay_secs > 0:
        timer_placeholder = st.empty()
        for i in range(delay_secs, 0, -1):
            timer_placeholder.warning(f"⏳ **倒计时 {i} 秒！** 请立刻将屏幕切换至你的目标工作窗口 (如 IDE/论文)...")
            time.sleep(1)
        timer_placeholder.success("📸 咔嚓！截屏完成，正在将画面与脑电数据送入大模型...")
    else:
        st.info("📸 正在立即截屏并分析...")

    with st.spinner("AI 正在深度思考中..."):
        # 2. 截屏 (倒计时结束后抓取此时真实的屏幕内容)
        screen = ImageGrab.grab()
        screen.thumbnail((640, 640), Image.Resampling.LANCZOS)
        buf = BytesIO()
        screen.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        try:
            res = ask_neuro_agent_with_vision(target_trial, img_b64)

            if isinstance(res["output"], str):
                clean_text = res["output"]
            else:
                clean_text = "".join([i.get("text", "") for i in res["output"] if isinstance(i, dict)])

            # 强行兜底：确保提取脑电数据
            current_state = stream_db.process_live_trial(target_trial)
            if current_state:
                already_exists = any(past["trial_id"] == current_state["trial_id"] for past in stream_db.memory)
                if not already_exists:
                    stream_db.search_and_memorize(current_state)

            st.session_state.data = {
                "img": screen,
                "text": clean_text,
                "mem": stream_db.memory[-1] if len(stream_db.memory) > 0 else None
            }
        except Exception as e:
            st.error(f"分析失败: {e}")

# =====================================================================
# 5. 最终渲染区
# =====================================================================
if "data" in st.session_state:
    d = st.session_state.data

    with col1:
        st.image(d["img"], caption=f"模拟工作场景截屏 (点击可放大)", use_container_width=True)

        if d["mem"]:
            st.divider()
            st.markdown("##### ⚡ 融合脑电指标")
            m1, m2 = st.columns(2)
            m1.metric("被忽略的范式标签", d["mem"]["label"])
            m2.metric("C3 ERD", f"{d['mem']['c3_erd']}%")
            m3, m4 = st.columns(2)
            m3.metric("Cz ERD", f"{d['mem']['cz_erd']}%")
            m4.metric("C4 ERD", f"{d['mem']['c4_erd']}%")

    with col2:
        st.subheader("🤖 诊断与反馈")
        components.html(get_voice_and_js(d["text"]), height=800, scrolling=True)