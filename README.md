👁️‍🗨️ E.C.H.O. Neural Sentinel
(Cognitive Monitoring & Retrieval System / 认知监控与检索系统)

E.C.H.O. (Empathic Cognitive & Heuristic Observer) 是一个全息脑机接口（BCI）智能伴侣终端。它通过实时解析 LSL (Lab Streaming Layer) 脑电数据流，结合屏幕视觉上下文与多模态大模型，实现对人类大脑认知负荷与底层情绪状态的秒级监控、自动归因分析与长级记忆检索。

✨ 核心特性 (Core Features)
🧠 1. 医疗级脑电信号处理引擎
MNE-Python 内核：废弃粗糙的绝对比值法，采用 MNE 内置的 Welch 方法计算高精度功率谱密度 (PSD)。

频段能量均值化 (Power Density Normalization)：自动补偿 Beta 频段宽带劣势，提取纯粹的相对频段能量 (Theta/Alpha/Beta) 作为特征向量。

Valence-Arousal 多维情感矩阵：内置机器学习分类器（可无缝接入真实 SVM/DGCNN 模型），并结合频段协同权重（Weight Bias），精准输出五维情绪概率：

💤 Cognitive_Fatigue (认知疲劳 / Theta 主导)

🍵 Peaceful_Calm (深度平和 / Alpha 主导)

⚡ Hyperactive_Focus (高度专注 / Beta 主导)

😊 Joyful_Happy (愉悦开心 / Alpha+Beta 双频共振)

🌧️ Emotional_Distress (焦虑沮丧 / Theta+Beta 认知冲突)

🛡️ 2. 工业级状态机与防抖路由
边缘触发机制 (Edge-Triggered)：只在状态真正发生“跃迁”时触发拦截，彻底杜绝电平触发导致的无脑刷屏。

物理时钟驻留验证 (Wall-clock Debounce)：基于真实物理时间的 3.0 秒滑动窗口，完美过滤眨眼 (EOG) 与咬牙 (EMG) 导致的瞬时高频伪迹干扰。

生命周期闭环追踪：从状态切入（Start）到状态退出（End），系统自动闭环记录并结算状态“持续总时长”。

🔍 3. 全息多模态记忆检索 (RAG)
瞬间快照归因：在状态突变的瞬间，系统自动抓取当前电脑屏幕上下文 (Bilinear 压缩极速释放 GIL)，交由多模态大语言模型进行原因推断。

ChromaDB 向量/时序双库流：告别传统的纯语义匹配。AI 能够按照真实时间线提取最近 N 次的神经状态起伏记录，精确回答“我上一次开心是什么时候？持续了多久？当时在干嘛？”。

🎨 4. 高容错可视化中控台 (Streamlit)
五维光谱实时看板：异步并发图表渲染，即使大模型后台满载推演，前端数据流也绝不卡顿、绝不断流。

Gemini 式时空回溯对话：特有的“隐形编辑笔 (Ghost Edit)”功能。用户修改历史提问后，系统将自动斩断当前时间线，遗忘后续对话，带着全新的记忆重新推演。

📂 工程目录结构 (Architecture)
Plaintext
E.C.H.O./
├── run.py                       # 🚀 全局一键启动与进程编排脚本 (Graceful Shutdown)
├── echo_core.py                 # 🧠 核心引擎 (FastAPI + MNE DSP + ML Classifier + ChromaDB)
├── echo_app.py                  # 👁️ 可视化终端 (Streamlit Frontend)
├── virtual_eeg_producer.py      # 📡 LSL 虚拟脑电发生器 (支持多频段复合状态生成)
├── echo_memory_db/              # 🗄️ ChromaDB 向量数据库持久化目录 (自动生成)
└── echo_chat_history.json       # 📝 前端对话树状态持久化文件 (自动生成)
🚀 极速启动 (Quick Start)
1. 环境依赖安装
请确保已安装 Python 3.9+，并在终端中执行：

Bash
pip install fastapi uvicorn streamlit requests pandas numpy scipy pylsl chromadb Pillow langchain-openai mne
2. 配置大模型 API
在项目根目录创建 .env 文件，填入您的大模型配置（兼容 OpenAI 格式）：

代码段
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=your_api_base_url_here
3. 一键拉起系统
在终端中直接运行编排脚本，它会自动启动发生器、核心引擎与前端 UI：

Bash
python run.py
🎮 模拟器测试指南 (Simulation Guide)
在启动 run.py 后，当前的终端窗口即变为“大脑神经控制器”。
您可以输入以下数字并按回车，实时向系统注入极其逼真的混合脑波特征，观察 E.C.H.O. 的响应：

[0] - 恢复日常噪音：消除主导频率，用于测试状态结束与时长结算。

[1] - 认知疲劳：注入 6Hz 高幅 Theta 波。

[2] - 深度平和：注入 10Hz 高幅 Alpha 波。

[3] - 高度专注：注入 20Hz 高幅 Beta 波。

[4] - 愉悦开心：注入 10Hz + 20Hz 双频共振信号（测试复合模型分类）。

[5] - 焦虑沮丧：注入 6Hz + 20Hz 冲突信号。

测试 Tip：在任意状态下快速切回 0 并瞬间切回原状态，可完美测试系统的“抗眨眼伪迹防抖”功能（前端图表会有明显跌落，但 AI 监控报警不会被欺骗）。

🔬 学术扩展 (For Researchers)
本系统已为接入真实医疗级 BCI 模型留出标准化接口。
如需使用基于真实数据集（如 SEED / DEAP）训练的模型，只需在 echo_core.py 中定位到 EmotionClassifier 类：

引入您的 .pkl 或 .h5 模型文件。

替换 predict_proba 方法中的模拟推断逻辑，即可实现从 Demo 到真实医疗辅助诊断终端的无缝升级。