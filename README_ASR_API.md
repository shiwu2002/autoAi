# ASR HTTP API 使用文档

## 概述

实现了语音识别（ASR）+ Agent 处理的完整 HTTP 接口。前端发送音频数据，系统自动进行语音识别并调用 Agent 执行任务。

## 快速开始

### 1. 启动服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置必要的环境变量
export DASHSCOPE_API_KEY="your_api_key"

# 启动 HTTP 服务器（默认端口 8080）
python http_interface.py
```

### 2. API 端点

#### 端点 1: POST /task - 直接发送文本任务
```bash
curl -X POST http://localhost:8080/task \
  -H "Content-Type: application/json" \
  -d '{"task":"打开计算器"}'
```

#### 端点 2: GET /task/<任务描述> - 通过 URL 发送任务
```bash
curl http://localhost:8080/task/打开计算器
```

#### 端点 3: POST /asr - 发送音频进行识别并执行任务 ⭐

**使用音频 URL 方式：**
```bash
curl -X POST http://localhost:8080/asr \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
  }'
```

**使用 Base64 编码方式：**
```bash
# 先将音频文件转为 base64
BASE64_DATA=$(base64 -i audio.wav)

# 发送请求
curl -X POST http://localhost:8080/asr \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_base64\": \"$BASE64_DATA\",
    \"audio_format\": \"wav\"
  }"
```

### 3. 响应格式

**成功响应示例：**
```json
{
  "success": true,
  "transcribed_text": "打开计算器",
  "agent_result": {
    "success": true,
    "message": "任务执行成功"
  }
}
```

**错误响应示例：**
```json
{
  "error": "ASR转写失败",
  "details": "具体错误信息"
}
```

## 环境变量配置

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| DASHSCOPE_API_KEY | 阿里云 DashScope API 密钥 | - | ✅ |
| PHONE_AGENT_BASE_URL | Agent 模型服务地址 | http://localhost:8000/v1 | ❌ |
| PHONE_AGENT_MODEL | 模型名称 | autoglm-phone-9b | ❌ |
| HTTP_INTERFACE_HOST | 服务器监听地址 | localhost | ❌ |
| HTTP_INTERFACE_PORT | 服务器监听端口 | 8080 | ❌ |

## 支持的音频格式

- WAV
- MP3
- M4A
- FLAC
- 其他 DashScope ASR 支持的格式

## 前端集成示例

### JavaScript/Fetch API

```javascript
// 方式 1: 使用音频 URL
async function sendAudioURL(audioUrl) {
  const response = await fetch('http://localhost:8080/asr', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      audio_url: audioUrl
    })
  });
  
  const result = await response.json();
  console.log('识别结果:', result.transcribed_text);
  console.log('Agent 执行结果:', result.agent_result);
}

// 方式 2: 使用录音数据（Base64）
async function sendAudioData(audioBlob) {
  // 将 Blob 转为 Base64
  const reader = new FileReader();
  reader.readAsDataURL(audioBlob);
  reader.onloadend = async () => {
    const base64Data = reader.result.split(',')[1];
    
    const response = await fetch('http://localhost:8080/asr', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        audio_base64: base64Data,
        audio_format: 'wav'
      })
    });
    
    const result = await response.json();
    console.log('识别结果:', result.transcribed_text);
  };
}
```

### Python 示例

```python
import requests
import base64

# 方式 1: 使用音频 URL
def send_audio_url(audio_url):
    response = requests.post(
        'http://localhost:8080/asr',
        json={'audio_url': audio_url}
    )
    return response.json()

# 方式 2: 使用本地音频文件
def send_audio_file(audio_path):
    with open(audio_path, 'rb') as f:
        audio_data = base64.b64encode(f.read()).decode('utf-8')
    
    response = requests.post(
        'http://localhost:8080/asr',
        json={
            'audio_base64': audio_data,
            'audio_format': 'wav'
        }
    )
    return response.json()

# 使用示例
result = send_audio_url('https://example.com/audio.wav')
print(f"识别文本: {result['transcribed_text']}")
```

## 错误处理

常见错误码：

- `400 Bad Request`: 请求参数错误（缺少音频数据或格式错误）
- `413 Payload Too Large`: 音频文件过大（超过 10MB）
- `500 Internal Server Error`: 服务器内部错误（ASR 或 Agent 执行失败）

## 性能优化建议

1. **音频格式**: 优先使用 WAV 或 FLAC 格式以获得最佳识别效果
2. **音频质量**: 采样率建议 16kHz 或更高，单声道即可
3. **文件大小**: 控制在 10MB 以内，建议 1-2MB
4. **网络传输**: 大文件建议先上传到 OSS 再使用 URL 方式

## 故障排查

### 问题 1: ASR 识别失败
- 检查 `DASHSCOPE_API_KEY` 是否正确配置
- 确认音频格式是否支持
- 查看服务器日志获取详细错误信息

### 问题 2: Agent 执行失败
- 确认 Phone Agent 模型服务是否正常运行
- 检查 ADB 连接是否正常
- 查看日志中的详细错误堆栈

### 问题 3: 跨域问题
- 设置 `CORS_ALLOW_ORIGIN` 环境变量
- 或在前端配置代理

## 技术栈

- Python 3.x
- DashScope ASR (阿里云语音识别)
- Phone Agent (手机操作代理)
- HTTP Server (Python 标准库)

## 许可证

请参考项目根目录的 LICENSE 文件。
