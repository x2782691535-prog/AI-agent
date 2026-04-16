import streamlit as st
import requests
import pandas as pd
import json
import re
import os
import time
from datetime import datetime
import streamlit.components.v1 as components
import base64

st.set_page_config(page_title="E.C.H.O. 神经哨兵终端", page_icon="🧠", layout="wide")
API_BASE = "http://127.0.0.1:8000"
HISTORY_FILE = "echo_chat_history.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_history():
    data_to_save = {
        "chat_sessions": st.session_state.chat_sessions,
        "session_counter": st.session_state.session_counter,
        "current_session_id": st.session_state.current_session_id
    }
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)


if "app_initialized" not in st.session_state:
    saved_data = load_history()
    if saved_data:
        st.session_state.chat_sessions = saved_data["chat_sessions"]
        st.session_state.session_counter = saved_data["session_counter"]
        st.session_state.current_session_id = saved_data.get("current_session_id",
                                                             list(saved_data["chat_sessions"].keys())[-1])
    else:
        st.session_state.chat_sessions = {
            "session_1": {
                "title": "💬 初始认知检索",
                "messages": [{"role": "assistant",
                              "content": "你好！我是 E.C.H.O. 认知管家。你可以问我关于你过去的大脑状态，或者任何脑机接口相关的专业知识。"}]
            }
        }
        st.session_state.current_session_id = "session_1"
        st.session_state.session_counter = 1
        save_history()

    st.session_state.app_initialized = True
    st.session_state.editing_index = None
    st.session_state.active_page = "live"

if "last_metrics" not in st.session_state: st.session_state.last_metrics = None
if "history_data" not in st.session_state: st.session_state.history_data = []
if "last_event_ts" not in st.session_state: st.session_state.last_event_ts = 0
if "cached_event" not in st.session_state: st.session_state.cached_event = None

current_session = st.session_state.chat_sessions[st.session_state.current_session_id]


def switch_page(page_name):
    st.session_state.active_page = page_name
    st.session_state.editing_index = None


def delete_session(s_id):
    if s_id in st.session_state.chat_sessions:
        del st.session_state.chat_sessions[s_id]
        if st.session_state.current_session_id == s_id:
            if st.session_state.chat_sessions:
                st.session_state.current_session_id = list(st.session_state.chat_sessions.keys())[-1]
            else:
                st.session_state.session_counter += 1
                new_id = f"session_{st.session_state.session_counter}"
                st.session_state.chat_sessions[new_id] = {
                    "title": "💬 新对话",
                    "messages": [{"role": "assistant", "content": "你好！开启了新的认知检索会话。"}]
                }
                st.session_state.current_session_id = new_id
        save_history()


def delete_msg(msg_index):
    if 0 <= msg_index < len(current_session["messages"]):
        current_session["messages"].pop(msg_index)
        save_history()


def enable_edit(index):
    st.session_state.editing_index = index


def cancel_edit():
    st.session_state.editing_index = None


def submit_edit(index):
    new_text = st.session_state[f"edit_box_{index}"]
    if new_text.strip():
        st.session_state.chat_sessions[st.session_state.current_session_id]["messages"] = \
            st.session_state.chat_sessions[st.session_state.current_session_id]["messages"][:index]
        st.session_state.chat_sessions[st.session_state.current_session_id]["messages"].append(
            {"role": "user", "content": new_text}
        )
        save_history()
    st.session_state.editing_index = None


with st.sidebar:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] button { border: none !important; background: transparent; color: var(--text-color); text-align: left !important; }
        [data-testid="stSidebar"] button:hover { background-color: var(--secondary-background-color) !important; }
        button[title="删除此会话"] { color: #888 !important; padding: 0 !important; margin-top: 5px !important; }
        button[title="删除此会话"]:hover { color: #ff4b4b !important; }
        </style>
    """, unsafe_allow_html=True)

    st.header("🧭 系统导航")
    if st.button("📊 实时哨兵看板", use_container_width=True):
        switch_page("live")
    if st.button("💬 历史检索与知识库", use_container_width=True):
        switch_page("chat")

    st.divider()

    if st.button("📝 New chat", use_container_width=True, type="primary"):
        st.session_state.session_counter += 1
        new_id = f"session_{st.session_state.session_counter}"
        st.session_state.chat_sessions[new_id] = {
            "title": "💬 新对话",
            "messages": [{"role": "assistant", "content": "你好！开启了新的认知检索会话。"}]
        }
        st.session_state.current_session_id = new_id
        switch_page("chat")
        save_history()
        st.rerun()

    st.markdown(
        "<div style='margin-top: 15px; font-weight: bold; color: gray; font-size: 12px; padding-left: 10px;'>Recent Chats</div>",
        unsafe_allow_html=True)

    for s_id, s_data in reversed(list(st.session_state.chat_sessions.items())):
        col1, col2 = st.columns([5, 1])
        with col1:
            title = f"**{s_data['title']}**" if s_id == st.session_state.current_session_id else s_data['title']
            if st.button(title, key=f"btn_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                switch_page("chat")
                st.rerun()
        with col2:
            st.button("🗑️", key=f"del_session_{s_id}", help="删除此会话", on_click=delete_session, args=(s_id,))

    st.divider()
    st.markdown("<div style='font-size: 12px; color: gray;'>⚙️ 存储管理</div>", unsafe_allow_html=True)
    if st.button("🗑️ 清空后台向量大模型库", use_container_width=True):
        requests.post(f"{API_BASE}/clear_memory", timeout=5).json()
        st.success("向量记忆已清空")


def get_voice_and_js(text):
    clean_text = re.sub(r'[*#_~`]', ' ', text)
    clean_text = re.sub(r'[\[\]{}]', ' ', clean_text)
    clean_text = re.sub(r'[\U00010000-\U0010ffff]', ' ', clean_text)
    safe_text = json.dumps(clean_text)

    html_code = f"""
    <div style="margin-bottom: 15px; display: flex; gap: 10px; background: white; z-index: 10;">
        <button id="play-btn" style="padding: 10px 24px; background: #ff4b4b; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; transition: all 0.2s;">🔊 开启语音</button>
        <button id="reset-btn" style="padding: 10px 24px; background: #F0F2F6; color: #31333F; border: 1px solid #DDE2E6; border-radius: 8px; cursor: pointer; font-weight: bold;">⏹ 重置</button>
    </div>
    <div id="text-container" style="font-size: 16px; line-height: 1.8; color: black; font-family: sans-serif; white-space: pre-wrap;"></div>
    <script>
        const btn = document.getElementById('play-btn'); const resetBtn = document.getElementById('reset-btn');
        const container = document.getElementById("text-container"); const rawText = {safe_text};
        const chars = rawText.split('');
        container.innerHTML = chars.map((c, i) => `<span class="char" id="c-${{i}}" style="color: black; transition: color 0.15s ease-out;">${{c}}</span>`).join('');
        const domNodes = chars.map((_, i) => document.getElementById(`c-${{i}}`));
        let synth = window.speechSynthesis; let utterance = null; let isSpeaking = false; let currentIndex = -1; let fakeIndex = -1; let smoothTimer = null;
        function fastUpdate(newIndex) {{ if (!isSpeaking) return; for(let i = 0; i <= newIndex; i++) {{ if(domNodes[i]) domNodes[i].style.color = "black"; }} }}
        function applyPauseState() {{ domNodes.forEach(n => {{ if(n) n.style.color = "black"; }}); }}
        function applyPlayState() {{ domNodes.forEach((n, i) => {{ if(n) n.style.color = i <= currentIndex ? "black" : "#C0C0C0"; }}); }}
        function speakFrom(index) {{
            let startIndex = Math.max(0, index); let remainingText = rawText.substring(startIndex);
            if (remainingText.trim() === "") return;
            utterance = new SpeechSynthesisUtterance(remainingText); utterance.lang = 'zh-CN'; utterance.rate = 1.1;
            utterance.onstart = () => {{
                isSpeaking = true; btn.innerText = "⏸ 暂停声音"; btn.style.background = "#ff4b4b"; applyPlayState();
                clearInterval(smoothTimer); fakeIndex = currentIndex;
                smoothTimer = setInterval(() => {{
                    if (isSpeaking && fakeIndex < chars.length) {{ fakeIndex += 0.3; if (fakeIndex > currentIndex + 6) fakeIndex = currentIndex + 6; requestAnimationFrame(() => fastUpdate(Math.floor(fakeIndex))); }}
                }}, 50);
            }};
            utterance.onboundary = (e) => {{ if (e.name === 'word' || e.name === 'sentence') {{ currentIndex = startIndex + e.charIndex; fakeIndex = currentIndex; requestAnimationFrame(() => fastUpdate(currentIndex)); }} }};
            utterance.onend = () => {{ clearInterval(smoothTimer); if (isSpeaking) {{ isSpeaking = false; currentIndex = -1; btn.innerText = "🔊 开启语音"; applyPauseState(); }} }};
            synth.speak(utterance);
        }}
        btn.onclick = () => {{
            if (!isSpeaking) {{ btn.innerText = "⏳ 加载中..."; btn.style.background = "#ff9999"; synth.cancel(); setTimeout(() => {{ speakFrom(currentIndex + 1 > 0 ? currentIndex : 0); }}, 50); }} 
            else {{ isSpeaking = false; synth.cancel(); clearInterval(smoothTimer); btn.innerText = "▶ 继续声音"; btn.style.background = "#e0f7fa"; applyPauseState(); }}
        }};
        resetBtn.onclick = () => {{ synth.cancel(); clearInterval(smoothTimer); isSpeaking = false; currentIndex = -1; btn.innerText = "🔊 开启语音"; btn.style.background = "#ff4b4b"; applyPauseState(); }};
    </script>
    """
    return html_code


st.title("👁️‍🗨️ E.C.H.O. 认知监控与检索系统")

if st.session_state.active_page == "live":
    st.subheader("📊 实时哨兵看板")


    @st.fragment(run_every=1)
    def live_data_fragment():
        metrics, event = None, None
        proxies = {"http": None, "https": None}

        try:
            metrics = requests.get(f"{API_BASE}/metrics", timeout=1.0, proxies=proxies).json()
            st.session_state.last_metrics = metrics
        except Exception:
            metrics = st.session_state.last_metrics

        try:
            event = requests.get(f"{API_BASE}/event", timeout=1.0, proxies=proxies).json()
        except Exception:
            pass

        row1_left, row1_right = st.columns([2.5, 1])
        with row1_left:
            st.markdown("#### 📈 多维情绪分类概率预测模型")
            if metrics is not None and "fatigue_idx" in metrics:
                # 🌟 核心修复：五维情绪数据全面呈现！
                st.session_state.history_data.append({
                    "timestamp": datetime.now(),
                    "认知疲劳 (Fatigue)": metrics.get("fatigue_idx", 0),
                    "亢奋专注 (Focus)": metrics.get("focus_idx", 0),
                    "平和放松 (Calm)": metrics.get("calm_idx", 0),
                    "愉悦开心 (Happy)": metrics.get("happy_idx", 0),
                    "焦虑沮丧 (Distress)": metrics.get("distress_idx", 0)  # 🌟 加回去了！
                })
                if len(st.session_state.history_data) > 60: st.session_state.history_data.pop(0)
                df = pd.DataFrame(st.session_state.history_data).set_index("timestamp")

                # 色系：疲劳(红), 专注(蓝), 平和(绿), 开心(黄), 焦虑(紫)
                st.line_chart(df, color=["#f85149", "#58a6ff", "#3fb950", "#d29922", "#a371f7"])
            else:
                st.info("⏳ 脑电窗口信号缓冲中...")

        with row1_right:
            st.markdown("#### 🧬 生理特征 (PSD)")
            if metrics is not None:
                st.metric("Theta (困倦/压抑)", f"{metrics.get('theta', 0):.1f} μV²")
                st.metric("Alpha (放松)", f"{metrics.get('alpha', 0):.1f} μV²")
                st.metric("Beta (专注/活跃)", f"{metrics.get('beta', 0):.1f} μV²")
                st.success(f"🟢 MNE 引擎在线 | {datetime.now().strftime('%H:%M:%S')}")
            else:
                st.markdown("<p style='color:#f85149; font-size:12px;'>⚠️ 核心引擎数据流暂时中断</p>",
                            unsafe_allow_html=True)

        if event and event.get("timestamp", 0) > st.session_state.last_event_ts:
            st.session_state.cached_event = event
            st.session_state.last_event_ts = event.get("timestamp", 0)
            st.rerun()


    live_data_fragment()
    st.divider()

    st.markdown("#### 🛡️ AI 哨兵多模态诊断")
    if st.session_state.cached_event:
        ev = st.session_state.cached_event
        st.error(f"⚠️ **检测到稳态神经跃迁: {ev.get('state')}**")
        evt_col1, evt_col2 = st.columns([1, 1.5])
        with evt_col1:
            if ev.get("image_b64"):
                img_data = base64.b64decode(ev.get("image_b64"))
                st.image(img_data, caption="📸 触发报警时的桌面快照", use_container_width=True)
            else:
                st.warning("⚠️ 未捕捉到有效截图")
        with evt_col2:
            components.html(get_voice_and_js(ev.get('advice', '')), height=350, scrolling=True)
    else:
        st.success("🍵 哨兵目前处于静默守护状态，大脑波形平稳。")


elif st.session_state.active_page == "chat":
    st.subheader(current_session["title"])
    st.markdown(
        """
        <style>
        .gemini-container { max-width: 850px; margin: 0 auto; padding-bottom: 120px; }
        div[data-testid="stChatInput"] {
            position: fixed !important; bottom: 30px !important; left: 50% !important;
            transform: translateX(-50%) !important; width: 80% !important; max-width: 850px !important;
            background-color: var(--background-color) !important; border: 1px solid var(--secondary-background-color) !important;
            border-radius: 30px !important; box-shadow: 0 4px 15px rgba(0,0,0,0.08) !important; padding: 8px 15px !important; z-index: 9999 !important;
        }
        .stChatFloatingInputContainer { padding-bottom: 130px; }
        button[title="编辑并重发此消息"], button[title="删除此记录"] {
            border: none !important; background: transparent !important; box-shadow: none !important;
            padding: 0px 5px !important; color: transparent !important; transition: color 0.2s ease-in-out; height: 100%;
        }
        div[data-testid="column"]:hover button[title="编辑并重发此消息"], div[data-testid="column"]:hover button[title="删除此记录"] { color: #d3d3d3 !important; }
        button[title="编辑并重发此消息"]:hover { color: #58a6ff !important; }
        button[title="删除此记录"]:hover { color: #ff4b4b !important; }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown('<div class="gemini-container">', unsafe_allow_html=True)

    for i, msg in enumerate(current_session["messages"]):
        if msg["role"] == "user":
            if st.session_state.editing_index == i:
                st.text_area("编辑消息（确认后将清除此节点之后的记录并重新推演）", value=msg["content"],
                             key=f"edit_box_{i}", height=100)
                edit_col1, edit_col2, _ = st.columns([1, 1, 4])
                with edit_col1:
                    st.button("✅ 确认重发", key=f"submit_btn_{i}", on_click=submit_edit, args=(i,),
                              use_container_width=True)
                with edit_col2:
                    st.button("❌ 取消", key=f"cancel_btn_{i}", on_click=cancel_edit, use_container_width=True)
                st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
            else:
                usr_col1, usr_col2, usr_col3 = st.columns([15, 1, 1])
                with usr_col1:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 5px;">
                        <div style="background-color: var(--secondary-background-color); color: var(--text-color); 
                                    padding: 12px 20px; border-radius: 24px 4px 24px 24px; max-width: 80%; 
                                    line-height: 1.6; font-size: 16px;">
                            {msg["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with usr_col2:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    st.button("✏️", key=f"edit_{st.session_state.current_session_id}_{i}", help="编辑并重发此消息",
                              on_click=enable_edit, args=(i,))
                with usr_col3:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    st.button("🗑️", key=f"del_msg_u_{st.session_state.current_session_id}_{i}", help="删除此记录",
                              on_click=delete_msg, args=(i,))
        else:
            ai_col1, ai_col2, ai_col3 = st.columns([1, 14, 1])
            with ai_col1:
                st.markdown(
                    "<div style='font-size: 24px; text-align: center; color: #ffca28; padding-top: 2px;'>✨</div>",
                    unsafe_allow_html=True)
            with ai_col2:
                st.markdown(msg["content"])
            with ai_col3:
                if i > 0:
                    st.button("🗑️", key=f"del_msg_a_{st.session_state.current_session_id}_{i}", help="删除此记录",
                              on_click=delete_msg, args=(i,))
            st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

    if prompt := st.chat_input("问问 E.C.H.O. 你的大脑历史状态，或者 BCI 相关知识..."):
        if len(current_session["messages"]) <= 1:
            title_text = prompt[:12] + "..." if len(prompt) > 12 else prompt
            current_session["title"] = f"💬 {title_text}"

        current_session["messages"].append({"role": "user", "content": prompt})
        save_history()
        st.rerun()

    if len(current_session["messages"]) > 0 and current_session["messages"][-1]["role"] == "user":
        with st.spinner("🧠 正在检索神经记忆与知识库..."):
            try:
                proxies = {"http": None, "https": None}
                payload = {
                    "query": current_session["messages"][-1]["content"],
                    "history": current_session["messages"][:-1]
                }
                res = requests.post(f"{API_BASE}/chat", json=payload, timeout=60, proxies=proxies).json()
                answer = res.get("answer", "未能获取回答。")
            except Exception as e:
                answer = f"⚠️ 连接核心引擎失败: {str(e)}"

        current_session["messages"].append({"role": "assistant", "content": answer})
        save_history()
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)