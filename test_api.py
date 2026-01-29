#!/usr/bin/env python3
"""ASR HTTP API 测试脚本"""

import requests
import json
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

def test_asr_with_url():
    """测试使用音频 URL 的 ASR 端点"""
    print("=" * 60)
    print("测试: ASR 端点（使用音频 URL）")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/asr"
    payload = {
        "audio_url": "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
    }
    
    try:
        print(f"发送请求到: {url}")
        print(f"音频 URL: {payload['audio_url']}")
        
        response = requests.post(url, json=payload, timeout=60)
        print(f"\n状态码: {response.status_code}")
        
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200 and result.get('success'):
            print(f"\n✅ ASR 识别文本: {result.get('transcribed_text')}")
            print(f"✅ Agent 执行: {result.get('agent_result', {}).get('success')}")
            return True
        else:
            print(f"\n❌ 测试失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始测试 ASR HTTP API...\n")
    
    success = test_asr_with_url()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
    print("=" * 60)
