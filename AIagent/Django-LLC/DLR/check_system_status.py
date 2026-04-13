#!/usr/bin/env python
"""
DLR + LangChain-Chatchat 系统状态检查脚本
检查所有服务是否正常运行
"""

import requests
import json
import time
import sys
from datetime import datetime

class SystemChecker:
    def __init__(self):
        self.dlr_url = "http://localhost:8000"
        self.chatchat_api_url = "http://localhost:7861"
        self.chatchat_ui_url = "http://localhost:8501"
        
    def print_header(self):
        """打印检查头部"""
        print("=" * 80)
        print("🔍 DLR + LangChain-Chatchat 系统状态检查")
        print("=" * 80)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def check_service(self, name, url, timeout=5):
        """检查单个服务状态"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print(f"✅ {name}: 运行正常")
                return True
            else:
                print(f"⚠️ {name}: 响应异常 (状态码: {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ {name}: 连接失败 (服务未启动)")
            return False
        except requests.exceptions.Timeout:
            print(f"⚠️ {name}: 响应超时")
            return False
        except Exception as e:
            print(f"❌ {name}: 检查失败 ({str(e)})")
            return False
    
    def check_dlr_health(self):
        """检查DLR健康状态"""
        try:
            response = requests.get(f"{self.dlr_url}/health/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ DLR健康检查: {data.get('status', 'unknown')}")
                
                # 显示详细信息
                if 'database' in data:
                    db_status = "✅" if data['database'] else "❌"
                    print(f"   {db_status} 数据库连接: {'正常' if data['database'] else '异常'}")
                
                if 'neo4j' in data:
                    neo4j_status = "✅" if data['neo4j'] else "❌"
                    print(f"   {neo4j_status} Neo4j连接: {'正常' if data['neo4j'] else '异常'}")
                
                return True
            else:
                print(f"⚠️ DLR健康检查: 响应异常 (状态码: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ DLR健康检查: 失败 ({str(e)})")
            return False
    
    def check_chatchat_api(self):
        """检查Chatchat API状态"""
        try:
            # 检查基本连接
            response = requests.get(f"{self.chatchat_api_url}/", timeout=10)
            if response.status_code == 200:
                print("✅ Chatchat API: 运行正常")
                
                # 检查模型列表
                try:
                    models_response = requests.get(f"{self.chatchat_api_url}/llm_model/list_running_models", timeout=10)
                    if models_response.status_code == 200:
                        models_data = models_response.json()
                        running_models = models_data.get('data', [])
                        if running_models:
                            print(f"   ✅ 运行中的模型: {', '.join(running_models)}")
                        else:
                            print("   ⚠️ 没有运行中的模型")
                    else:
                        print("   ⚠️ 无法获取模型列表")
                except:
                    print("   ⚠️ 模型状态检查失败")
                
                # 检查知识库列表
                try:
                    kb_response = requests.get(f"{self.chatchat_api_url}/knowledge_base/list_knowledge_bases", timeout=10)
                    if kb_response.status_code == 200:
                        kb_data = kb_response.json()
                        kb_list = kb_data.get('data', [])
                        if kb_list:
                            print(f"   ✅ 知识库数量: {len(kb_list)}")
                        else:
                            print("   ⚠️ 没有可用的知识库")
                    else:
                        print("   ⚠️ 无法获取知识库列表")
                except:
                    print("   ⚠️ 知识库状态检查失败")
                
                return True
            else:
                print(f"⚠️ Chatchat API: 响应异常 (状态码: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ Chatchat API: 检查失败 ({str(e)})")
            return False
    
    def check_integration(self):
        """检查DLR和Chatchat集成状态"""
        try:
            # 通过DLR调用Chatchat API
            response = requests.post(
                f"{self.dlr_url}/api/test_chatchat_connection/",
                json={"test": True},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ DLR-Chatchat集成: 连接正常")
                    return True
                else:
                    print(f"⚠️ DLR-Chatchat集成: {data.get('error', '未知错误')}")
                    return False
            else:
                print(f"⚠️ DLR-Chatchat集成: 测试失败 (状态码: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ DLR-Chatchat集成: 检查失败 ({str(e)})")
            return False
    
    def check_all_services(self):
        """检查所有服务"""
        print("🔍 检查基础服务连接...")
        
        services = [
            ("DLR主服务", self.dlr_url),
            ("Chatchat API", self.chatchat_api_url),
            ("Chatchat UI", self.chatchat_ui_url),
        ]
        
        results = {}
        for name, url in services:
            results[name] = self.check_service(name, url)
        
        print("\n🔍 检查详细状态...")
        
        # 详细检查
        if results.get("DLR主服务"):
            results["DLR健康检查"] = self.check_dlr_health()
        
        if results.get("Chatchat API"):
            results["Chatchat API详细"] = self.check_chatchat_api()
        
        # 集成检查
        if results.get("DLR主服务") and results.get("Chatchat API"):
            print("\n🔍 检查服务集成...")
            results["DLR-Chatchat集成"] = self.check_integration()
        
        return results
    
    def generate_report(self, results):
        """生成检查报告"""
        print("\n" + "=" * 80)
        print("📋 系统状态报告")
        print("=" * 80)
        
        total_checks = len(results)
        passed_checks = sum(1 for result in results.values() if result)
        
        print(f"📊 检查结果: {passed_checks}/{total_checks} 通过")
        
        if passed_checks == total_checks:
            print("🎉 所有服务运行正常！")
            status = "healthy"
        elif passed_checks >= total_checks * 0.7:
            print("⚠️ 大部分服务正常，但有一些问题需要关注")
            status = "warning"
        else:
            print("❌ 系统存在严重问题，需要检查")
            status = "error"
        
        print("\n📋 详细状态:")
        for service, result in results.items():
            status_icon = "✅" if result else "❌"
            print(f"   {status_icon} {service}")
        
        print("\n🔧 故障排除建议:")
        if not results.get("DLR主服务"):
            print("   - 检查DLR服务是否启动: python manage.py runserver 8000")
            print("   - 检查数据库连接配置")
        
        if not results.get("Chatchat API"):
            print("   - 检查Chatchat服务是否启动: python startup.py -a")
            print("   - 检查模型是否正确加载")
        
        if not results.get("DLR-Chatchat集成"):
            print("   - 检查CHATCHAT_API_BASE_URL配置")
            print("   - 确保两个服务都正常运行")
        
        print("\n🌐 访问地址:")
        print("   - DLR主界面: http://localhost:8000")
        print("   - Chatchat界面: http://localhost:8501")
        print("   - API文档: http://localhost:7861/docs")
        
        return status
    
    def run(self):
        """运行系统检查"""
        self.print_header()
        results = self.check_all_services()
        status = self.generate_report(results)
        
        print(f"\n🏁 检查完成 (状态: {status})")
        return status

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("DLR + LangChain-Chatchat 系统状态检查脚本")
        print()
        print("用法:")
        print("  python check_system_status.py")
        print()
        print("功能:")
        print("  - 检查DLR服务状态")
        print("  - 检查Chatchat服务状态")
        print("  - 检查服务集成状态")
        print("  - 生成详细报告")
        return
    
    try:
        checker = SystemChecker()
        status = checker.run()
        
        # 根据状态设置退出码
        if status == "healthy":
            sys.exit(0)
        elif status == "warning":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n🛑 检查被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 检查失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
