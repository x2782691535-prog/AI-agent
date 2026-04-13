import os
import httpx
from dotenv import load_dotenv, find_dotenv

# 1. 加载密钥
load_dotenv(find_dotenv())
api_key = os.getenv("GOOGLE_API_KEY")

print(f"✅ 已读取 API Key (尾号: {api_key[-4:] if api_key else 'None'})")

# 2. 设置你的 VPN 代理 (如果你的代理不是 7890，请修改这里)
proxies = "http://127.0.0.1:7897"

# 3. 直接调用 Google 最底层的 REST API 查询模型列表
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print("正在通过代理直连 Google 服务器查询模型 (请稍候)...")

try:
    # 强制走代理，verify=False 防止某些 VPN 劫持证书导致报错
    with httpx.Client(proxy=proxies, verify=False) as client:
        response = client.get(url, timeout=15)

        if response.status_code == 200:
            print("\n🎉 连接成功！您的 API Key 可以使用以下模型：")
            models = response.json().get('models', [])

            valid_models = []
            for m in models:
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    # 过滤掉前缀 'models/'，只保留模型名字
                    model_name = m['name'].replace('models/', '')
                    valid_models.append(model_name)
                    print(f"- {model_name}")

            print("-" * 40)
            print("👉 接下来该怎么做？")
            if valid_models:
                print(f"请在你的 LangChain 代码中，随便挑选上面列表里的一个名字填入。")
                print(f"例如: model = ChatGoogleGenerativeAI(model=\"{valid_models[0]}\")")

        else:
            print(f"❌ 查询失败！Google 拒绝了请求。状态码: {response.status_code}")
            print(f"返回信息: {response.text}")
            print("这通常意味着你的 API Key 无效，或者被 Google 封禁了。")

except Exception as e:
    print(f"❌ 代理连接失败: {e}")
    print("请确认你的 VPN 软件是否已开启，并且 HTTP 代理端口确实是 7890。")