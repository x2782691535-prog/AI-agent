import os
import time
import mne
import numpy as np
import base64
from io import BytesIO
from PIL import ImageGrab
from scipy.spatial.distance import cosine
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, wait_exponential, stop_after_attempt

# =====================================================================
# 1. 网络与环境变量配置
# =====================================================================
# 本地 VPN 代理 (如果中转站在国内，甚至可以把这两行注释掉直连)
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # 关闭追踪防报错

# 加载 .env 文件中的 OPENAI_API_KEY 和 OPENAI_API_BASE
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")


# =====================================================================
# 2. 内隐感知：流式心智状态向量数据库 (全局滤波严谨版)
# =====================================================================
class StreamingBrainVectorDB:
    def __init__(self):
        self.memory = []
        self.gdf_path = r"E:\桌面\数据集\BCICIV_2a_gdf\originalData\A01T.gdf"

        print("[System] 正在挂载底层 EEG 数据流...")
        self.raw = mne.io.read_raw_gdf(self.gdf_path, preload=True, verbose='ERROR')
        events, self.event_id = mne.events_from_annotations(self.raw, verbose='ERROR')

        cue_tags = ['769', '770', '771', '772']
        valid_ids = [eid for desc, eid in self.event_id.items() if desc in cue_tags]
        self.mi_events = [e for e in events if e[2] in valid_ids]

        self.c3_idx = 7
        self.cz_idx = 9
        self.c4_idx = 11

        print("[System] 正在执行全局 CAR 空间滤波与 Mu 频段 (8-12Hz) 提取...")
        self.raw.load_data(verbose='ERROR')
        self.raw.set_eeg_reference('average', projection=False, verbose='ERROR')
        self.mu_continuous = self.raw.copy().filter(l_freq=8., h_freq=12., method='iir', verbose='ERROR')
        print("[System] 脑电信号纯化完毕，特征提取引擎就绪。")

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

        c3_base_var, cz_base_var, c4_base_var = (
            np.var(mu_base_data[self.c3_idx, :]), np.var(mu_base_data[self.cz_idx, :]),
            np.var(mu_base_data[self.c4_idx, :])
        )
        c3_task_var, cz_task_var, c4_task_var = (
            np.var(mu_task_data[self.c3_idx, :]), np.var(mu_task_data[self.cz_idx, :]),
            np.var(mu_task_data[self.c4_idx, :])
        )

        eps = 1e-10
        c3_erd = ((c3_task_var - c3_base_var) / (c3_base_var + eps)) * 100
        cz_erd = ((cz_task_var - cz_base_var) / (cz_base_var + eps)) * 100
        c4_erd = ((c4_task_var - c4_base_var) / (c4_base_var + eps)) * 100

        vector = np.array([c3_erd, cz_erd, c4_erd])

        return {
            "trial_id": trial_index,
            "label": label,
            "c3_erd": round(c3_erd, 2),
            "cz_erd": round(cz_erd, 2),
            "c4_erd": round(c4_erd, 2),
            "vector": vector
        }

    def search_and_memorize(self, current_state):
        past_memory = None
        if len(self.memory) > 0:
            similarities = []
            for past_record in self.memory:
                dist = cosine(current_state["vector"], past_record["vector"])
                similarities.append((dist, past_record))
            similarities.sort(key=lambda x: x[0])
            past_memory = similarities[0][1]

        self.memory.append(current_state)
        return past_memory


stream_db = StreamingBrainVectorDB()


# =====================================================================
# 3. 提供给 LLM 的主动分析 Tool
# =====================================================================
@tool
def perceive_and_remember(trial_index: int) -> dict:
    """系统回调：提取 3D 空间脑电特征 -> 检索生理记忆库"""
    print(f"\n[Daemon 内隐感知] ⚡ 捕获到 Trial {trial_index}，正在提取生理特征...")
    current_state = stream_db.process_live_trial(trial_index)
    if not current_state: return {"error": "数据解析失败"}
    print(
        f"   ├─ 空间特征: [C3: {current_state['c3_erd']}%, Cz: {current_state['cz_erd']}%, C4: {current_state['c4_erd']}%]")

    past_memory = stream_db.search_and_memorize(current_state)
    if past_memory:
        print(f"   ├─ NeuroRAG: 唤醒记忆 Trial {past_memory['trial_id']} (当时任务: {past_memory['label']})")
    else:
        print(f"   ├─ NeuroRAG: 记忆库为空，首次记录。")

    return {
        "current_state": {
            "c3_left_brain_erd": current_state["c3_erd"], "cz_central_brain_erd": current_state["cz_erd"],
            "c4_right_brain_erd": current_state["c4_erd"], "actual_task": current_state["label"]
        },
        "retrieved_memory": {
            "past_trial_id": past_memory["trial_id"], "past_task": past_memory["label"],
            "past_c3_erd": past_memory["c3_erd"], "past_cz_erd": past_memory["cz_erd"],
            "past_c4_erd": past_memory["c4_erd"]
        } if past_memory else "No past memory available."
    }


# =====================================================================
# 4. 外显感知：视觉屏幕捕获 (Vision 模块)
# =====================================================================
def get_screen_context():
    print("[Daemon 外显感知] 📸 正在捕获用户的视觉屏幕上下文...")
    try:
        screen = ImageGrab.grab()
        screen.thumbnail((512, 512))  # 极限压缩，防止代理断流
        buffered = BytesIO()
        screen.save(buffered, format="JPEG", quality=40)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        print(f"   ├─ 截图压缩完成，请求体积约为: {len(img_b64) / 1024:.2f} KB")
        return img_b64
    except Exception as e:
        print(f"[视觉模块报错]: {e}")
        return None


# =====================================================================
# 5. 多模态重试请求封装
# =====================================================================
@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def ask_neuro_agent_with_vision(agent_executor, trial_id, base64_image):
    if base64_image:
        input_content = [
            {"type": "text",
             "text": f"请作为守护进程，先调用工具分析我 Trial {trial_id} 的脑电 ERD 特征。同时，看这张我当前的电脑屏幕截图。结合我的脑波执行质量和屏幕内容，给我一个综合反馈。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    else:
        input_content = f"请调用工具分析 Trial {trial_id} 的脑波特征。"
    return agent_executor.invoke({"input": input_content})


# =====================================================================
# 6. 主程序与多模态 Agent 编排
# =====================================================================
def main():
    # 【修改点 2】：使用 ChatOpenAI，它会自动从 .env 读取 API_KEY 和 BASE_URL
    # 注意：这里的 model 名称填写你的中转站支持的模型名，通常原样写 gemini-2.5-flash 即可
    llm = ChatOpenAI(
        model="gpt-4o-all",
        temperature=0.2,
        max_retries=3,
        max_tokens=1000,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个搭载了 NeuroSkill 架构的顶级 AI 伴侣。
你拥有双重視角：内隐感知（脑电 ERD 数据）与外显感知（用户的电脑屏幕）。

分析步骤：
1. 【内隐脑波验证】：解读传入的 C3、Cz、C4 通道数据。依据 Motor Homunculus 理论（C3负值对侧对应右手，C4负值对侧对应左手，Cz负值对应双脚）。评判他当前脑波是否成功激活了目标区域？是否表现出了专注？
2. 【记忆对比】：简要对比你检索到的历史 Trial，指出他两次大脑状态的空间相似性。
3. 【外显视觉结合】：观察用户的屏幕画面，他在看什么（代码、游戏、文献）？
4. 【综合同理心反馈】：将脑波与屏幕结合。例如：“你现在的空间特征非常散漫，C3没有出现预期的负值。我看到你屏幕上打开了B站视频，是不是完全被视频分心了，忘记做运动想象了？”

回复要求：语气贴心、专业、像一个真正的真人 AI 助手。不要输出 JSON 数据。"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    tools = [perceive_and_remember]
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    print("=" * 75)
    print("🧠👁️ NeuroSkill 终极多模态守护进程 (中转加速版) 启动")
    print("=" * 75)

    mock_live_stream = [60, 61, 62]

    for trial_id in mock_live_stream:
        try:
            print(f"\n⏳ 时间推移... 受试者进入 Trial {trial_id}")
            screen_base64 = get_screen_context()
            print(f"当前使用的 Key: {api_key[:8]}...")  # 只打印前几位确认一下即可
            result = ask_neuro_agent_with_vision(agent_executor, trial_id, screen_base64)

            output_data = result["output"]
            clean_text = "".join(
                [item if isinstance(item, str) else item.get("text", "") for item in output_data]) if isinstance(
                output_data, list) else output_data

            print("\n🤖 AI 伴侣综合诊断反馈：")
            print(clean_text)
            print("-" * 75)

            # 使用中转站后额度通常很宽裕，休眠 10 秒防并发即可
            print("💤 (系统流式等待中，请随时准备切换你的屏幕画面...)")
            time.sleep(10)

        except Exception as e:
            print(f"\n❌ 网络或接口发生严重错误: {type(e).__name__}")
            if hasattr(e, 'last_attempt') and e.last_attempt is not None:
                print(f"🔍 真实底层报错原因: {e.last_attempt.exception()}")
            else:
                print(f"🔍 报错原因: {e}")


if __name__ == "__main__":
    main()
