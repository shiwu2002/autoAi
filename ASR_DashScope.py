from http import HTTPStatus  # 从标准库导入HTTPStatus枚举，用于检查HTTP响应状态码（如200 OK）
from dashscope.audio.asr import Transcription  # 从DashScope的音频ASR模块导入Transcription类（用于提交/轮询转写任务）
import dashscope  # 导入DashScope SDK主包，用于配置API Key等
import os  # 导入操作系统接口模块，用于读取环境变量、文件路径等
import json  # 导入JSON模块，用于序列化输出结果（打印、日志等）


def transcribe(file_urls=None, file_paths=None):  # 定义转写函数，支持两种输入：公网URL列表或本地文件路径列表
    """
    使用达摩盘(DashScope) ASR服务进行转写

    支持两种输入：
    1) file_urls: 语音文件的公网URL列表（如OSS地址），例如 ["https://.../a.wav"]
    2) file_paths: 本地文件路径列表，例如 ["/path/to/audio.wav"]

    返回：
        dict: ASR识别结果或错误信息
    """
    # 配置API Key
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")  # 从环境变量读取DASHSCOPE_API_KEY并配置到SDK；若为空，则后续调用会失败

    try:  # 使用try捕获整个转写流程中的异常，保证函数返回统一结构
        # 优先使用URL方式（OSS服务等）
        if file_urls and isinstance(file_urls, list) and len(file_urls) > 0:  # 检查file_urls是否为非空列表
            task_response = Transcription.async_call(  # 通过异步接口提交ASR转写任务
                model="fun-asr-mtl",  # 指定ASR模型名称（多任务ASR模型）
                file_urls=file_urls  # 传入多个公网可访问的音频文件URL
            )
            transcribe_response = Transcription.wait(task=task_response.output.task_id)  # 使用任务ID轮询，等待转写完成并获取结果
            if transcribe_response.status_code == HTTPStatus.OK:  # 如果服务返回HTTP 200 OK，表示成功
                return {
                    "success": True,  # 标记成功
                    "output": transcribe_response.output  # 返回实际的ASR结果（通常包含每个音频的转写文本等）
                }
            else:  # 非200状态码，认为失败
                return {
                    "success": False,  # 标记失败
                    "error": f"ASR服务返回非OK状态: {transcribe_response.status_code}",  # 返回错误码信息
                    "details": getattr(transcribe_response, "message", None)  # 若响应中含有message字段则附带详细错误信息
                }

        # 其次使用本地文件路径方式
        if file_paths and isinstance(file_paths, list) and len(file_paths) > 0:  # 检查file_paths是否为非空列表
            # 验证所有文件是否存在
            for path in file_paths:
                if not os.path.exists(path):  # 检查文件是否存在
                    return {
                        "success": False,  # 失败标记
                        "error": f"文件不存在: {path}"  # 返回具体不存在的文件路径
                    }
            
            try:  # 尝试以本地文件路径方式调用SDK
                task_response = Transcription.async_call(  # 提交异步任务
                    model="paraformer-v2",  # 使用支持本地文件的模型
                    file_urls=file_paths  # DashScope SDK统一使用file_urls参数，本地文件也用此参数
                )
                transcribe_response = Transcription.wait(task=task_response.output.task_id)  # 轮询等待任务完成
                if transcribe_response.status_code == HTTPStatus.OK:  # 成功状态
                    return {
                        "success": True,  # 成功标记
                        "output": transcribe_response.output  # 返回ASR输出
                    }
                else:  # 非OK状态返回错误
                    return {
                        "success": False,  # 失败标记
                        "error": f"ASR服务返回非OK状态: {transcribe_response.status_code}",  # 状态码信息
                        "details": getattr(transcribe_response, "message", None)  # 错误详情（如果有）
                    }
            except Exception as e:  # 捕获调用本地文件方式可能出现的异常
                return {
                    "success": False,  # 失败标记
                    "error": "使用本地文件路径调用ASR失败",  # 错误提示
                    "details": str(e)  # 返回具体异常信息便于定位问题
                }

        # 两种输入均未提供
        return {
            "success": False,  # 失败标记
            "error": "必须提供file_urls或file_paths其中之一"  # 参数校验失败的提示信息
        }

    except Exception as e:  # 顶层异常捕获，防止未处理异常导致程序崩溃
        return {
            "success": False,  # 失败标记
            "error": "ASR转写过程中发生错误",  # 通用错误信息
            "details": str(e)  # 异常详情便于调试
        }


if __name__ == "__main__":  # 当该文件作为脚本直接运行时执行下面的示例代码
    """
    示例：使用URL或本地文件路径进行异步识别
    """
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")  # 再次从环境变量读取API Key，确保示例运行时已配置

    try:
        # 示例1: 使用OSS URL方式
        sample_urls = [  # 准备两个示例音频URL（DashScope官方示例资源）
            "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav",
            "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_male2.wav"
        ]
        print("=== 使用OSS URL方式 ===")
        result = transcribe(file_urls=sample_urls)  # 调用转写函数，采用URL方式
        print(json.dumps(result, indent=4, ensure_ascii=False))  # 格式化打印结果为JSON，保持中文不转义
        
        # 示例2: 使用本地文件路径方式（需要提供实际存在的本地文件）
        # local_files = ["/path/to/local/audio.wav"]
        # print("\n=== 使用本地文件路径方式 ===")
        # result = transcribe(file_paths=local_files)
        # print(json.dumps(result, indent=4, ensure_ascii=False))
        
    except Exception as e:  # 捕获示例运行时的异常（例如API Key未配置等）
        print(json.dumps({"success": False, "error": str(e)}, indent=4, ensure_ascii=False))  # 打印错误信息
