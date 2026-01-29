#!/usr/bin/env python3  # 指定解释器为Python3，允许脚本在类Unix系统中直接执行

"""
HTTP Interface for Phone Agent - Exposes an HTTP API to send tasks to the phone agent.

Usage:
    python http_interface.py [--host HOST] [--port PORT]

The server will expose an endpoint at http://HOST:PORT/task where you can POST JSON data:
{
    "task": "your task description"
}

Example:
    curl -X POST http://localhost:5000/task \\
         -H "Content-Type: application/json" \\
         -d '{"task": "open calculator app"}'
         
Or using path parameters:
    curl -X GET http://localhost:5000/task/open%20calculator%20app
"""
# 顶部文档字符串：说明脚本用途、使用方法和示例命令

import argparse  # 命令行参数解析模块
import json  # 处理JSON序列化/反序列化
import base64  # 处理二进制与Base64编码转换（用于音频数据）
import logging  # 日志记录模块
import os  # 操作系统相关功能，如环境变量、路径处理
import sys  # Python解释器相关功能，如路径操作
import urllib.parse  # URL解码
from http.server import BaseHTTPRequestHandler, HTTPServer  # 简易HTTP服务器及请求处理基类
from urllib.parse import parse_qs, urlparse  # URL解析（解析路径、查询参数等）

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 将当前脚本所在目录加入sys.path，以便导入同项目内模块

# 导入必要的模块
from phone_agent import PhoneAgent  # 导入PhoneAgent核心类，用于执行任务
from phone_agent.model import ModelConfig  # 导入模型配置类，配置模型相关参数
from phone_agent.agent import AgentConfig  # 导入代理配置类，配置代理行为（如最大步骤等）
# 导入ASR转写函数
from ASR_DashScope import transcribe as asr_transcribe  # 导入ASR转写函数，并重命名为asr_transcribe

# 配置日志记录
logging.basicConfig(level=logging.INFO)  # 设置日志级别为INFO
logger = logging.getLogger(__name__)  # 获取以当前模块名为标识的日志记录器

def load_config():
    """Load configuration from config file."""
    # 从配置文件加载配置，返回字典；解析失败或不存在时返回空字典
    config_path = os.path.join(os.path.dirname(__file__), 'phone_agent', 'config', 'config.json')  # 构造配置文件路径
    if os.path.exists(config_path):  # 检查配置文件是否存在
        try:
            with open(config_path, 'r', encoding='utf-8') as f:  # 打开配置文件，使用UTF-8编码
                return json.load(f)  # 解析JSON并返回
        except json.JSONDecodeError as e:  # JSON解析错误
            logger.error(f"Failed to parse config file: {e}")  # 记录错误日志
            return {}  # 返回空配置
        except Exception as e:  # 其他文件读取错误
            logger.error(f"Failed to load config file: {e}")  # 记录错误日志
            return {}  # 返回空配置
    return {}  # 如果文件不存在，返回空配置

class TaskHandler(BaseHTTPRequestHandler):
    """处理任务请求的HTTP请求处理器"""
    # 继承BaseHTTPRequestHandler，实现自定义请求处理逻辑
    
    # 类变量存储agent实例
    agent = None  # 用于缓存PhoneAgent单例，避免每次请求都初始化
    agent_config = None  # 缓存AgentConfig实例
    model_config = None  # 缓存ModelConfig实例
    
    def _send_response(self, code, data):
        """发送带有JSON数据的HTTP响应
        
        Args:
            code (int): HTTP状态码
            data (dict): 要返回的JSON数据
        """
        self.send_response(code)  # 写入状态码
        self.send_header('Content-type', 'application/json')  # 设置响应内容类型为JSON
        self.send_header('Access-Control-Allow-Origin', os.environ.get('CORS_ALLOW_ORIGIN', '*'))  # 允许跨域访问来源（默认*）
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')  # 允许的HTTP方法
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')  # 允许的请求头
        self.end_headers()  # 结束头部写入
        self.wfile.write(json.dumps(data).encode())  # 将数据序列化为JSON并写回响应体
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self._send_response(200, {})  # 返回200，空体，用于跨域预检
    
    def do_GET(self):
        """处理GET请求以执行任务"""
        parsed_path = urlparse(self.path)  # 解析请求路径（包含路径与查询参数）
        
        # 检查路径是否以 /task 开头
        if parsed_path.path.startswith('/task'):
            # 解析查询参数
            query_params = parse_qs(parsed_path.query)
            
            # 首先尝试从查询参数获取任务
            task = None
            if 'task' in query_params and query_params['task']:
                task = query_params['task'][0]  # parse_qs返回的是列表，取第一个元素
            
            # 如果查询参数中没有任务，则尝试从路径中获取
            if not task and parsed_path.path.startswith('/task/'):
                # 提取任务描述
                task_encoded = parsed_path.path[len('/task/'):]  # 获取 /task/ 后面的部分
                if task_encoded:
                    # URL解码任务描述
                    task = urllib.parse.unquote(task_encoded)
            
            # 如果仍然没有任务，则返回错误
            if not task:
                self._send_response(400, {'error': 'Missing task parameter. Please provide task in query string or path.'})
                return
            
            logger.info(f"Received task via GET: {task}")
            
            try:
                # 初始化agent（如果尚未初始化）
                if TaskHandler.agent is None:
                    logger.info("Initializing PhoneAgent...")
                    
                    # 创建模型配置，直接从环境变量读取，不依赖配置文件
                    TaskHandler.model_config = ModelConfig(
                        base_url=os.getenv("PHONE_AGENT_BASE_URL", "http://localhost:8000/v1"),
                        model_name=os.getenv("PHONE_AGENT_MODEL", "autoglm-phone-9b"),
                        api_key=os.getenv("PHONE_AGENT_API_KEY", "EMPTY")
                    )
                    
                    # 创建代理配置，直接从环境变量读取
                    TaskHandler.agent_config = AgentConfig(
                        max_steps=int(os.getenv("PHONE_AGENT_MAX_STEPS", "100")),
                        lang=os.getenv("PHONE_AGENT_LANG", "cn")
                    )
                    
                    # 创建PhoneAgent实例
                    TaskHandler.agent = PhoneAgent(TaskHandler.model_config, TaskHandler.agent_config)
                    logger.info("PhoneAgent initialized successfully.")
                
                # 执行任务
                result = self._execute_task(task)
                
                # 发送简化版的成功响应
                if result.get('success'):
                    self._send_response(200, {'result': 'Task executed successfully', 'details': result.get('message', '')})
                else:
                    self._send_response(500, {'error': 'Task execution failed', 'details': result.get('message', '')})
            
            except Exception as e:
                logger.error(f"Error executing task: {str(e)}", exc_info=True)
                self._send_response(500, {'error': 'Internal server error', 'details': str(e)})
        else:
            self._send_response(404, {'error': 'Endpoint not found'})
    
    def do_POST(self):
        """处理POST请求以执行任务"""
        parsed_path = urlparse(self.path)  # 解析请求路径（包含路径与查询参数）
        
        if parsed_path.path == '/task':  # 如果是任务执行接口
            # 限制请求体大小，防止过大请求导致内存问题
            content_length = int(self.headers.get('Content-Length', 0))  # 从请求头读取内容长度
            if content_length > 1024 * 1024:  # 限制为1MB
                self._send_response(413, {'error': 'Request entity too large'})  # 返回413错误
                return  # 终止处理
            
            # 读取POST主体
            post_data = self.rfile.read(content_length)  # 从输入流读取指定长度的请求体
            
            try:
                # 解析JSON数据
                task_data = json.loads(post_data.decode('utf-8'))  # 将字节解码为字符串并解析为JSON
                
                # 提取任务
                task = task_data.get('task')  # 获取'task'字段
                if not task:  # 如果缺少task字段
                    self._send_response(400, {'error': 'Missing "task" field in request'})  # 返回400错误
                    return  # 终止处理
                
                logger.info(f"Received task via POST: {task}")  # 记录收到的任务
                
                # 初始化agent（如果尚未初始化）
                if TaskHandler.agent is None:  # 检查是否已初始化
                    logger.info("Initializing PhoneAgent...")  # 日志：开始初始化
                    
                    # 创建模型配置，直接从环境变量读取，不依赖配置文件
                    TaskHandler.model_config = ModelConfig(
                        base_url=os.getenv("PHONE_AGENT_BASE_URL", "http://localhost:8000/v1"),  # 模型服务基础URL
                        model_name=os.getenv("PHONE_AGENT_MODEL", "autoglm-phone-9b"),  # 模型名
                        api_key=os.getenv("PHONE_AGENT_API_KEY", "EMPTY")  # API密钥（默认EMPTY）
                    )
                    
                    # 创建代理配置，直接从环境变量读取
                    TaskHandler.agent_config = AgentConfig(
                        max_steps=int(os.getenv("PHONE_AGENT_MAX_STEPS", "100")),  # 最大执行步骤（字符串需转int）
                        lang=os.getenv("PHONE_AGENT_LANG", "cn")  # 语言代码（cn/其他）
                    )
                    
                    # 创建PhoneAgent实例
                    TaskHandler.agent = PhoneAgent(TaskHandler.model_config, TaskHandler.agent_config)  # 用模型配置和代理配置实例化PhoneAgent
                    logger.info("PhoneAgent initialized successfully.")  # 日志：初始化完成
                
                # 执行任务
                result = self._execute_task(task)  # 调用内部方法执行任务，返回结果字典
                
                # 发送简化版的成功响应
                if result.get('success'):  # 如果成功
                    self._send_response(200, {'result': 'Task executed successfully', 'details': result.get('message', '')})  # 返回200以及详情
                else:  # 如果失败
                    self._send_response(500, {'error': 'Task execution failed', 'details': result.get('message', '')})  # 返回500错误和失败详情
                
            except json.JSONDecodeError:  # JSON解析错误
                self._send_response(400, {'error': 'Invalid JSON in request'})  # 返回400错误
            except Exception as e:  # 其他运行时错误
                logger.error(f"Error executing task: {str(e)}", exc_info=True)  # 记录异常堆栈
                self._send_response(500, {'error': 'Internal server error', 'details': str(e)})  # 返回500错误与异常信息
        elif parsed_path.path == '/asr':  # 语音识别+agent调用端点
            # 限制请求体大小（音频文件可能较大，设置为10MB）
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 10 * 1024 * 1024:  # 限制为10MB
                self._send_response(413, {'error': 'Request entity too large. Max 10MB allowed.'})
                return
            
            # 读取POST主体
            post_data = self.rfile.read(content_length)
            
            try:
                # 解析JSON数据
                data = json.loads(post_data.decode('utf-8'))
                
                # 支持两种输入方式：
                # 1. audio_url: 音频文件的公网URL
                # 2. audio_base64: Base64编码的音频数据
                audio_url = data.get('audio_url')
                audio_base64 = data.get('audio_base64')
                audio_format = data.get('audio_format', 'wav')  # 默认wav格式
                
                if not audio_url and not audio_base64:
                    self._send_response(400, {'error': 'Missing audio_url or audio_base64 field'})
                    return
                
                logger.info("Received ASR request")
                
                # 处理音频并调用ASR
                asr_result = None
                
                if audio_url:
                    # 使用URL方式调用ASR
                    logger.info(f"Processing audio from URL: {audio_url}")
                    asr_result = asr_transcribe(file_urls=[audio_url])
                
                elif audio_base64:
                    # 使用Base64数据方式
                    logger.info("Processing audio from base64 data")
                    
                    # 解码Base64数据
                    try:
                        audio_data = base64.b64decode(audio_base64)
                    except Exception as e:
                        self._send_response(400, {'error': f'Invalid base64 data: {str(e)}'})
                        return
                    
                    # 保存为临时文件
                    import tempfile
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_format}')
                    temp_file_path = temp_file.name
                    try:
                        temp_file.write(audio_data)
                        temp_file.close()
                        
                        # 使用本地文件路径调用ASR
                        asr_result = asr_transcribe(file_paths=[temp_file_path])
                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                
                # 检查ASR结果
                if not asr_result or not asr_result.get('success'):
                    error_msg = asr_result.get('error', 'ASR转写失败') if asr_result else 'ASR转写失败'
                    error_details = asr_result.get('details', '') if asr_result else ''
                    self._send_response(500, {
                        'error': error_msg,
                        'details': error_details
                    })
                    return
                
                # 提取转写文本
                asr_output = asr_result.get('output', {})
                
                # DashScope ASR返回的结果结构可能是：
                # {
                #   "results": [
                #     {
                #       "transcription_url": "...",
                #       "transcription": {
                #         "sentences": [{"text": "识别的文本"}]
                #       }
                #     }
                #   ]
                # }
                transcribed_text = ""
                
                # 尝试提取文本
                if hasattr(asr_output, 'results') and asr_output.results:
                    for result in asr_output.results:
                        if hasattr(result, 'transcription') and result.transcription:
                            transcription = result.transcription
                            if hasattr(transcription, 'sentences') and transcription.sentences:
                                for sentence in transcription.sentences:
                                    if hasattr(sentence, 'text'):
                                        transcribed_text += sentence.text + " "
                
                # 如果为字典类型，尝试另一种解析方式
                if isinstance(asr_output, dict):
                    results = asr_output.get('results', [])
                    for result in results:
                        transcription = result.get('transcription', {})
                        sentences = transcription.get('sentences', [])
                        for sentence in sentences:
                            transcribed_text += sentence.get('text', '') + " "
                
                transcribed_text = transcribed_text.strip()
                
                if not transcribed_text:
                    self._send_response(500, {
                        'error': 'ASR返回结果为空或无法解析',
                        'asr_output': str(asr_output)
                    })
                    return
                
                logger.info(f"ASR transcription: {transcribed_text}")
                
                # 初始化agent（如果尚未初始化）
                if TaskHandler.agent is None:
                    logger.info("Initializing PhoneAgent...")
                    
                    TaskHandler.model_config = ModelConfig(
                        base_url=os.getenv("PHONE_AGENT_BASE_URL", "http://localhost:8000/v1"),
                        model_name=os.getenv("PHONE_AGENT_MODEL", "autoglm-phone-9b"),
                        api_key=os.getenv("PHONE_AGENT_API_KEY", "EMPTY")
                    )
                    
                    TaskHandler.agent_config = AgentConfig(
                        max_steps=int(os.getenv("PHONE_AGENT_MAX_STEPS", "100")),
                        lang=os.getenv("PHONE_AGENT_LANG", "cn")
                    )
                    
                    TaskHandler.agent = PhoneAgent(TaskHandler.model_config, TaskHandler.agent_config)
                    logger.info("PhoneAgent initialized successfully.")
                
                # 使用转写的文本作为任务调用agent
                agent_result = self._execute_task(transcribed_text)
                
                # 返回完整结果
                response = {
                    'success': True,
                    'transcribed_text': transcribed_text,
                    'agent_result': agent_result
                }
                
                self._send_response(200, response)
                
            except json.JSONDecodeError:
                self._send_response(400, {'error': 'Invalid JSON in request'})
            except Exception as e:
                logger.error(f"Error processing ASR request: {str(e)}", exc_info=True)
                self._send_response(500, {'error': 'Internal server error', 'details': str(e)})
        else:
            self._send_response(404, {'error': 'Endpoint not found'})  # 未匹配到路径，返回404
    
    def _execute_task(self, task):
        """直接调用PhoneAgent执行任务
        
        Args:
            task (str): 要执行的任务描述
            
        Returns:
            dict: 任务执行结果
        """
        try:
            # 直接执行任务
            logger.info(f"Executing task directly: {task}")  # 日志：开始执行任务
            result_message = TaskHandler.agent.run(task)  # 调用PhoneAgent的run方法执行任务，返回消息
            logger.info(f"Task execution completed: {task}")  # 日志：任务执行完成
            
            # 返回结果
            return {
                'message': result_message,  # 执行结果信息（可能是字符串或结构化文本）
                'success': True  # 标记成功
            }
        except Exception as e:
            logger.error(f"Failed to execute task: {task}, error: {str(e)}", exc_info=True)  # 记录错误与堆栈
            return {
                'error': f'Failed to execute task: {str(e)}',  # 返回错误信息
                'success': False  # 标记失败
            }

def parse_args():
    # 加载配置文件
    config = load_config()  # 调用load_config获取配置字典
    
    # 获取HTTP相关配置，默认为空字典
    http_config = config.get('http', {})  # 从配置字典中取'http'子配置
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="HTTP Interface for Phone Agent")  # 初始化参数解析器，带描述
    parser.add_argument(
        "--host",  # 定义--host参数
        type=str,  # 参数类型为字符串
        default=os.getenv("HTTP_INTERFACE_HOST", http_config.get("host", "localhost")),  # 默认值优先从环境变量，其次配置文件，最后'localhost'
        help="Host to bind the HTTP server to"  # 帮助文本
    )
    parser.add_argument(
        "--port",  # 定义--port参数
        type=int,  # 参数类型为整数
        default=int(os.getenv("HTTP_INTERFACE_PORT", str(http_config.get("port", 8080)))),  # 默认值优先环境变量，其次配置文件，最后8080
        help="Port to bind the HTTP server to"  # 帮助文本
    )
    return parser.parse_args()  # 解析并返回命令行参数对象

def main():
    """主入口函数"""
    args = parse_args()  # 解析命令行参数，获取host和port
    
    # 创建HTTP服务器
    server_address = (args.host, args.port)  # 绑定的地址与端口
    httpd = HTTPServer(server_address, TaskHandler)  # 创建HTTPServer实例，指定请求处理类TaskHandler
    
    print(f"Starting HTTP server on {args.host}:{args.port}")  # 控制台输出服务器启动信息
    print(f"\nAvailable endpoints:")
    print(f"  1. POST to http://{args.host}:{args.port}/task - Send task directly")
    print(f"     Example: curl -X POST http://{args.host}:{args.port}/task -H 'Content-Type: application/json' -d '{{\"task\":\"打开计算器\"}}'")
    print(f"\n  2. GET to http://{args.host}:{args.port}/task/<task_description> - Send task via URL")
    print(f"     Example: curl http://{args.host}:{args.port}/task/打开计算器")
    print(f"\n  3. POST to http://{args.host}:{args.port}/asr - Send audio for ASR + agent")
    print(f"     Example with URL:")
    print(f"       curl -X POST http://{args.host}:{args.port}/asr -H 'Content-Type: application/json' -d '{{\"audio_url\":\"https://example.com/audio.wav\"}}'")
    print(f"     Example with base64:")
    print(f"       curl -X POST http://{args.host}:{args.port}/asr -H 'Content-Type: application/json' -d '{{\"audio_base64\":\"<base64_data>\",\"audio_format\":\"wav\"}}'")
    print()
    
    try:
        # 开始服务请求
        httpd.serve_forever()  # 启动服务器循环，阻塞式处理请求
    except KeyboardInterrupt:  # 捕获Ctrl+C中断
        print("\nShutting down server...")  # 打印关闭提示
        httpd.shutdown()  # 优雅关闭服务器
        print("Server stopped.")  # 打印停止提示

if __name__ == "__main__":  # 仅当脚本作为主程序运行时执行main
    main()  # 调用主函数，启动HTTP服务
