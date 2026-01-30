# AutoAI - AI驱动的手机自动化框架

AutoAI 是一个基于AI驱动的自动化代理系统，专注于通过自然语言指令实现对移动设备（如手机）的操作控制。项目结合大模型能力与设备交互技术，实现智能化任务执行。

## 功能特点

- 基于文本指令控制手机设备完成指定任务
- 屏幕截图获取与视觉理解（结合Pillow和OpenAI API）
- ADB设备连接与操作封装（点击、输入、滑动等）
- 多语言支持（中文/英文提示词配置）
- 可扩展的动作处理器设计
- 支持 OpenAI 和 DashScope 模型作为后端推理引擎
- 提供 HTTP 接口服务

## 技术架构

- **后端**: Python 标准库 + 自定义模块
- **模型接口**: OpenAI >=2.9.0, DashScope SDK
- **图像处理**: Pillow >=12.0.0
- **设备通信**: ADB (adb/* 模块封装)
- **部署可选**: sglang>=0.5.6.post1 或 vllm>=0.12.0

## 系统要求

- Python ≥3.8
- ADB 工具链（Android Debug Bridge）
- Android设备通过USB调试连接到电脑

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/autoAi.git
cd autoAi
```

### 2. 安装依赖

安装项目依赖：

#### 使用 setup.py

```bash
pip install -e .
```

### 3. 配置

编辑 [phone_agent/config/config.json](file:///Volumes/data/python/autoAi/phone_agent/config/config.json) 文件以配置项目参数：

```json
{
    "agent": {
        "max_steps": 100,
        "lang": "cn"
    },
    "http": {
        "host": "127.0.0.1",
        "port": 8080
    }
}
```

### 4. 连接设备

确保你的Android设备已启用USB调试，并通过USB连接到计算机。

### 5. 运行项目

#### 启动HTTP接口服务

```bash
python http_interface.py
```

服务将在 `http://127.0.0.1:8080` 上启动，提供以下端点：

- `POST /task` - 直接发送任务
- `GET /task/<task_description>` - 通过URL发送任务
- `POST /asr` - 发送音频进行ASR + 代理处理

示例请求：
```bash
# 发送任务
curl -X POST http://127.0.0.1:8080/task -H 'Content-Type: application/json' -d '{"task":"打开计算器"}'

# 通过URL发送任务
curl http://127.0.0.1:8080/task/打开计算器
```

#### 运行基本示例

```bash
python examples/basic_usage.py
```

#### 运行思考示例

```bash
python examples/demo_thinking.py
```

## 配置说明

### 配置文件位置

- 主配置文件: [phone_agent/config/config.json](file:///Volumes/data/python/autoAi/phone_agent/config/config.json)
- 应用配置: [phone_agent/config/apps.py](file:///Volumes/data/python/autoAi/phone_agent/config/apps.py)
- 提示词配置: [phone_agent/config/prompts_en.py](file:///Volumes/data/python/autoAi/phone_agent/config/prompts_en.py) 和 [prompts_zh.py](file:///Volumes/data/python/autoAi/phone_agent/config/prompts_zh.py)

### 模型配置

项目支持多种模型提供商，需要在环境变量或配置文件中设置API密钥：

- **OpenAI**: 设置 `OPENAI_API_KEY` 环境变量
- **DashScope**: 设置 `DASHSCOPE_API_KEY` 环境变量

## 项目结构

```
autoAi/
├── phone_agent/           # 核心代码
│   ├── actions/          # 动作处理器
│   ├── adb/             # ADB设备控制
│   ├── config/          # 配置文件
│   ├── model/           # 模型客户端
│   └── agent.py         # 主代理类
├── examples/            # 示例代码
├── scripts/             # 脚本文件
├── http_interface.py    # HTTP接口服务
├── main.py              # 主入口
├── setup.py             # 安装配置
├── requirements.txt     # 依赖列表
├── install.sh           # Linux/macOS安装脚本
├── install.bat          # Windows安装脚本
└── README.md           # 本文件
```

## 已知问题

- Transformers 版本可能存在依赖冲突（文档中明确说明可忽略）
- 当前仅支持单设备连接（未提供多设备管理机制）
- 模型客户端错误处理机制未详述

## 贡献

欢迎提交Issue和Pull Request来帮助改进项目。

## 许可证

Apache License 2.0