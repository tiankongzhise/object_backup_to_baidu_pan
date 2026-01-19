from pathlib import Path
import os
import re
import time
from dotenv import load_dotenv
import hashlib
from pprint import pprint
from .openapi_client.api import fileupload_api
from . import openapi_client
from datetime import datetime
from .utils import extract_date_and_password_from_path
from .oauth import oauthtoken_refreshtoken

load_dotenv()

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒


def _is_network_error(exception: Exception) -> bool:
    """判断是否是网络连接异常或超时

    Args:
        exception: 异常对象

    Returns:
        bool: 是否是网络异常
    """
    exception_str = str(exception).lower()

    # 网络连接相关关键词
    network_keywords = [
        'connection',
        'timeout',
        'timed out',
        'network',
        'socket',
        'econnreset',
        'econnrefused',
        'enetunreach',
        'ehostunreach',
        'etimedout',
        'temporary failure',
        'name or service not known',
        'no route to host',
        'connection refused',
        'connection reset',
        'connection closed',
        'ssl',
        'tls',
        'handshake',
    ]

    # 检查异常消息是否包含网络关键词
    for keyword in network_keywords:
        if keyword in exception_str:
            return True

    # 检查异常类型
    exception_type = type(exception).__name__
    network_types = [
        'ConnectionError',
        'TimeoutError',
        'OSError',
        'BrokenPipeError',
        'ConnectionResetError',
        'ConnectionAbortedError',
        'ConnectionRefusedError',
        'ConnectionRefusedError',
    ]

    # 检查是否是 requests 相关的网络异常
    if 'requests' in exception_type.lower() or hasattr(exception, 'request'):
        if hasattr(exception, 'response') and exception.response is not None:
            status_code = exception.response.status_code
            # 5xx 服务器错误通常是临时性的网络问题
            if 500 <= status_code < 600:
                return True
            # 408 Request Timeout
            if status_code == 408:
                return True
            # 429 Too Many Requests (可能是临时性的)
            if status_code == 429:
                return True

    # 检查 urllib3 相关异常
    if 'urllib3' in exception_type.lower():
        return True

    # 检查 openapi_client 异常的状态码
    if isinstance(exception, openapi_client.ApiException):
        if exception.status >= 500:
            return True
        if exception.status == 408:
            return True

    return False


class UploadService:
    def __init__(self, file_path:str|Path = '',chunk_size: int = 20*1024*1024, rtype: int = 1,env_path:str|Path ='upload.env',temp_dir:str|Path|None = None):
        self.file_path = Path(file_path)
        self.remote_path:str = None # type: ignore
        self.chunk_size:int = chunk_size
        self.rtype:int = rtype
        self.size:int = None # type: ignore
        self.block_list_jsonstr:str = None # type: ignore
        self.block_list:list[str] = None # type: ignore
        self.upload_id:str = None # type: ignore
        self.temp_dir = temp_dir
        self.tmp_list:list[Path] = None # type: ignore
        oauthtoken_refreshtoken()
        self.load_env(env_path)


    def load_env(self,env_path:str|Path ='upload.env'):
        if not Path(env_path).exists():
            raise FileNotFoundError(f"env file:{env_path} not found,can not access")
        load_dotenv(env_path)

    def _set_remote_path(self):
        """设置远程路径，格式遵循PRD规范:
        {百度云盘指定目录}/YYYYMMDD/{源文件夹名}/解压密码_{password}/{文件名}.zip
        """
        # 从本地ZIP路径提取日期和密码
        date, password = extract_date_and_password_from_path(self.file_path.absolute().as_posix())
        date = date or datetime.now().strftime("%Y%m%d")

        if not password:
            print(f"upload info Password is missing, please check your file path:{self.file_path}, use unknown instead")
            password = "unknown"

        # 从本地路径提取源文件夹名
        # 本地路径格式: {compress_dir}/YYYYMMDD/{源文件夹名}/解压密码_{password}/{文件名}.zip
        path_parts = self.file_path.parent.parts
        source_folder_name = None
        for index, part in enumerate(reversed(path_parts)):
            # 跳过日期和压缩根目录，找到源文件夹名
            if re.match(r'^\d{8}$', part):
                if index +1 <= len(path_parts):
                    source_folder_name = path_parts[index + 1]
                    break

        if not source_folder_name:
            source_folder_name = "unknown"

        # 构建远程路径: /item_backup/YYYYMMDD/{源文件夹名}/解压密码_{password}/{文件名}.zip
        self.remote_path = f"/item_backup/{date}/{source_folder_name}/解压密码_{password}/{self.file_path.name}"

    def _split_file(self):
        '''
        分片文件，设置self.tmp_list为分片文件列表，并且返回self.tmp_list
        '''
        import shutil

        # 检查文件是否存在
        if not Path(self.file_path).exists():
            raise FileNotFoundError(f"file_path:{self.file_path} not exists")


        # 如果文件大小小于等于块大小，则直接返回文件路径,无需分块
        if self.file_path.stat().st_size <= self.chunk_size:
            self.tmp_list = [self.file_path]
            return self.tmp_list

        # 确保临时目录存在
        if not self.temp_dir:
            self.temp_dir = self.file_path.parent / f"temp_{self.file_path.name}"
        self.temp_dir = Path(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # 清空临时目录，确保没有残留文件
        shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        
        # 4. 初始化存储分块文件路径的列表和分块计数器
        paths:list[Path] = []
        partnum = 0
        
        # 5. 以二进制读模式打开源文件
        with open(self.file_path, 'rb') as inputfile:
            # 6. 从源文件路径中提取文件名（不包含目录）
            file_name = self.file_path.name
            
            # 7. 循环读取源文件，直到文件结束
            while True:
                # 8. 读取指定大小的数据块
                chunk = inputfile.read(self.chunk_size)
                
                # 9. 如果读取到的数据为空，说明已到文件末尾，退出循环
                if not chunk:
                    break
                
                # 10. 构建分块文件的完整路径，使用路径拼接运算符 `/`
                filename = self.temp_dir / f'{file_name}.part{partnum:04d}'
                
                # 11. 将分块文件路径（Path对象）添加到列表中
                paths.append(filename)
                
                # 12. 以二进制写模式创建并打开分块文件，写入数据块
                with open(filename, 'wb') as fileobj:
                    fileobj.write(chunk)
                
                # 13. 分块计数器加1，为下一个分块文件准备
                partnum += 1
        
        # 14. 返回所有分块文件的路径列表
        self.tmp_list = paths
        return self.tmp_list


    def _calculate_md5(self,data):
        """
        计算数据的MD5值
        :param data: 数据
        :return: MD5值
        """
        md5_hash = hashlib.md5()
        md5_hash.update(data)
        return md5_hash.hexdigest().lower()

    def _create_block_list(self):
        import json
        block_list = []
        self._split_file()
        for file_path in self.tmp_list:
            with open(file_path, 'rb') as f:
                md5 = self._calculate_md5(f.read())
                block_list.append(md5)
        return json.dumps(block_list)
    

    def precreate(self):
        """
        precreate - 创建文件上传前的预创建信息，带网络异常重试
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"file_path:{self.file_path} not exists!")
        if not self.file_path.is_file():
            raise ValueError(f"file_path:{self.file_path} is not a file,folder is not supported")
        self._set_remote_path()

        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                # Enter a context with an instance of the API client
                with openapi_client.ApiClient() as api_client:
                    # Create an instance of the API class
                    api_instance = fileupload_api.FileuploadApi(api_client)
                    access_token = os.getenv("BAIDU_PAN_ACCESS_TOKEN")  # str |
                    path = self.remote_path  # str | 对于一般的第三方软件应用，路径以 "/apps/your-app-name/" 开头。对于小度等硬件应用，路径一般 "/来自：小度设备/" 开头。对于定制化配置的硬件应用，根据配置情况进行填写。
                    isdir = 0  # int | isdir
                    self.size = self.file_path.stat().st_size  # int | size
                    autoinit = 1  # int | autoinit
                    self.block_list_jsonstr = self._create_block_list() # str | 由MD5字符串组成的list
                    rtype = self.rtype  # int | rtype (optional)
                    # example passing only required values which don't have defaults set
                    # and optional values
                    api_response = api_instance.xpanfileprecreate(
                        access_token, path, isdir, self.size, autoinit, self.block_list_jsonstr, rtype=rtype)
                    print(api_response)
                    self.upload_id = api_response['uploadid']
                    self.block_list = api_response['block_list']
                    return self
            except Exception as e:
                last_exception = e
                # 检查是否是网络异常
                if _is_network_error(e):
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (attempt + 1)  # 指数退避
                        print(f"[precreate] 网络异常: {e}, {attempt + 1}/{MAX_RETRIES} 次尝试, {delay}秒后重试")
                        time.sleep(delay)
                        continue
                # 非网络异常或重试用尽，直接抛出
                print(f"[precreate] 错误: {e}")
                raise

        # 理论上不会到达这里，但为了安全
        if last_exception:
            raise last_exception
    
    def _get_file(self, partseq):
        try:
            file = open(self.tmp_list[partseq], 'rb')
            return file
        except Exception as e:
            print(f"Exception when open file:{e}")
            exit(-1)

    def upload(self):
        """
        upload - 上传文件分片，带网络异常重试
        """
        last_exception = None
        for partseq in self.block_list:
            path = self.remote_path  # str |
            uploadid = self.upload_id  # str |
            type = "tmpfile"  # str |
            file = self._get_file(partseq)  # file_type | 要进行传送的本地文件分片

            for attempt in range(MAX_RETRIES):
                try:
                    # Enter a context with an instance of the API client
                    with openapi_client.ApiClient() as api_client:
                        # Create an instance of the API class
                        api_instance = fileupload_api.FileuploadApi(api_client)
                        access_token = os.getenv("BAIDU_PAN_ACCESS_TOKEN")  # str |
                        api_response = api_instance.pcssuperfile2(
                            access_token, str(partseq), path, uploadid, type, file=file)
                        pprint(api_response)
                        break  # 成功，跳出重试循环
                except Exception as e:
                    last_exception = e
                    # 检查是否是网络异常
                    if _is_network_error(e):
                        if attempt < MAX_RETRIES - 1:
                            delay = RETRY_DELAY * (attempt + 1)  # 指数退避
                            print(f"[upload] 分片 {partseq} 网络异常: {e}, {attempt + 1}/{MAX_RETRIES} 次尝试, {delay}秒后重试")
                            time.sleep(delay)
                            continue
                    # 非网络异常或重试用尽，直接抛出
                    print(f"[upload] 分片 {partseq} 错误: {e}")
                    raise
            # 确保文件关闭
            try:
                file.close()
            except Exception:
                pass

        print("upload done")
        return self

    def create(self):
        """
        create - 创建文件（完成上传流程），带网络异常重试
        """
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                # Enter a context with an instance of the API client
                with openapi_client.ApiClient() as api_client:
                    # Create an instance of the API class
                    api_instance = fileupload_api.FileuploadApi(api_client)
                    access_token = os.getenv("BAIDU_PAN_ACCESS_TOKEN")  # str |
                    path = self.remote_path  # str | 与precreate的path值保持一致
                    isdir = 0  # int | isdir
                    size = self.size # int | 与precreate的size值保持一致
                    uploadid = self.upload_id  # str | precreate返回的uploadid
                    block_list = self.block_list_jsonstr  # str | 与precreate的block_list值保持一致
                    rtype = self.rtype  # int | rtype (optional)

                    # example passing only required values which don't have defaults set
                    # and optional values
                    api_response = api_instance.xpanfilecreate(
                        access_token, path, isdir, size, uploadid, block_list, rtype=rtype)
                    pprint(api_response)
                    return api_response
            except Exception as e:
                last_exception = e
                # 检查是否是网络异常
                if _is_network_error(e):
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (attempt + 1)  # 指数退避
                        print(f"[create] 网络异常: {e}, {attempt + 1}/{MAX_RETRIES} 次尝试, {delay}秒后重试")
                        time.sleep(delay)
                        continue
                # 非网络异常或重试用尽，直接抛出
                print(f"[create] 错误: {e}")
                raise

        # 理论上不会到达这里，但为了安全
        if last_exception:
            raise last_exception
    def _clean_tmp(self):
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir)

    def upload_file(self,file_path:str|Path,chunk_size: int = 20*1024*1024, rtype: int = 1,temp_dir:str|Path|None = None):
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size
        self.rtype = rtype
        self.temp_dir = temp_dir
        self.precreate()
        self.upload()
        result = self.create()
        self._clean_tmp()
        return result
        
    def __del__(self):
        import shutil
        if self.temp_dir:
            temp_dir = Path(self.temp_dir)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)



if __name__ == "__main__":
    params = {
        'file_path':r'd:\压缩测试\20260115\解压密码_H_x123456789\normal_folder.zip',
        'chunk_size': 20*1024*1024,
        'rtype': 1
    }
    upload_service = UploadService(**params)
    upload_service.precreate().upload().create()
