#!/usr/bin/python3
import socket
import re
import os

class FTPSession(object):
  def __init__(self):
    self.c_socket = False
    self.working_directory = False
    self.local_wd = Path(os.getcwd())
    self.data_fd = False
    self.c_type = 'A'

  # 删除文件
  def delete(self, file):
    self.send('DELE', file)
    self.get_result()

  # 上传文件
  def stor(self, file):
    p = Path(self.local_wd.wd)
    p.cwd(file)
    if not os.path.exists(p.wd):
      self.log('File %s not exist.' % p.wd, 3)
      return
    # PASV 获得请求端口
    self.send('PASV')
    code, text = self.get_result()
    if code == 227:
      host, port = self.parse_addr(text)
      try:
        self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_fd.connect((host, port))
        self.send('STOR', file)
        code = self.get_result()[0]
        if code == 150:
          with open(p.wd, 'rb') as f:
            while True:
              data = f.read(2048)
              if not data:
                break
              self.data_fd.send(data)
          # 传完即关闭连接
          self.data_fd.close()
          self.get_result()
          self.log('File %s uploaded' % file, 2)
      except Exception as e:
        self.log(e, 3)

  # 返回文件
  def retr(self, file):
    # PASV 获得请求端口
    self.send('PASV')
    code, text = self.get_result()
    if code == 227:
      host, port = self.parse_addr(text)
      try:
        self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_fd.connect((host, port))
        self.send('RETR', file)
        code = self.get_result()[0]
        if code == 150:
          p = Path(self.local_wd.wd)
          p.cwd(file)
          print(p.wd)
          with open(p.wd, 'wb') as f:
            while True:
              data = self.data_fd.recv(2048)
              if not data:
                break
              f.write(data)
          # 传完即关闭连接
          self.data_fd.close()
          self.get_result()
          self.log('File %s saved to %s' % (file, self.local_wd.wd), 2)
      except Exception as e:
        self.log(e, 3)

  # 设置本地工作目录
  def lcd(self, path):
    if not path:
      path = os.getcwd()
    p = Path(os.getcwd())
    p.cwd(self.local_wd.wd)
    p.cwd(path)
    if not os.path.isdir(p.getAbs()):
      self.log('No such directory', 3)
    else:
      self.local_wd.cwd(path)
      self.log('Local directory now %s' % self.local_wd.wd, 2)

  # 删除文件夹
  def rmdir(self, dirname):
    self.send('RMD', dirname)
    self.get_result()

  # 创建文件夹
  def mkdir(self, dirname):
    self.send('MKD', dirname)
    self.get_result()

  # 列出目录
  def ls(self):
    # PASV 获得请求端口
    self.send('PASV')
    code, text = self.get_result()
    if code == 227:
      host, port = self.parse_addr(text)
      try:
        self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_fd.connect((host, port))
        self.send('LIST')
        code = self.get_result()[0]
        if code == 150:
          raw = ''
          while True:
            recv = self.data_fd.recv(2048)
            if not recv:
              break
            raw += recv.decode('utf-8')
          self.data_fd.close()
          self.get_result()
          print(raw, end='')
      except Exception as e:
        self.log(e, 3)

  # 获得工作目录
  def get_wd(self):
    self.send('PWD')
    code, text = self.get_result()
    if code == 257:
      self.working_directory = Path(self.parse_path(text), os.getcwd())
  
  # 打印工作目录
  def pwd(self):
    self.get_wd()
    print(self.working_directory.wd)

  # 切換工作目錄
  def cd(self, new_dir):
    path = Path(self.working_directory.wd)
    path.cwd(new_dir)
    # path.wd
    self.send('CWD', path.wd)
    code, text = self.get_result()
    if code == 250:
      self.working_directory.cwd(self.parse_path(text))
    elif code == 431:
      self.log("No such directory", 3)

  # 传输模式设定
  def mode(self, mode):
    mode = mode.upper()
    mode = 'A' if mode == 'A' else 'I'
    self.log('TYPE %s' % mode)
    self.send('TYPE', mode)
    self.get_result()[0]
    # 传输模式
    self.c_type = mode

  # 登录
  def login(self, user, passwd, addr, port):
    # 初始化连接
    success = self.init_ctrl_connection(addr, port)[0]
    if not success:
      self.log('Failed connecting to server', 4)
      return
    self.log('Successfully connecting to %s:%s' % (addr, port))
    self.log('USER %s' % user)
    self.send('USER', user)
    code = self.get_result()[0]
    if code == 331:
      self.log('PASS ****')
      self.send('PASS', passwd)
      code = self.get_result()[0]
      # 登录成功
      if code == 230:
        self.log('Login successful', 2)
        # 获取工作目录
        self.get_wd()
        return True
    # 登录失败
    self.log('Authentication failed.')
    return False

  # 友好的 LOG
  def log(self, text, ty=1):
    t = {
      1: 'x',
      2: '+',
      3: '-',
      4: 'i',
    }
    print("[%s] %s" % (t[ty], text))

  # 发送命令
  def send(self, command, args = ''):
    self.c_socket.send(("%s %s\r\n" % (command, args)).encode('utf-8'))

  # 初始化连接
  def init_ctrl_connection(self, addr, port):
    try:
      if not self.c_socket:
        self.c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.c_socket.connect((addr, int(port)))
        code, text = self.get_result()
        if code != 220:
          self.c_socket = False
          return False, ''
        return True, text
    except Exception:
      self.c_socket = False
      return False, ''
  
  # 关闭连接
  def close(self):
    self.c_socket.close()
    self.c_socket = False
    self.log('Current FTP session closed', 4)

  # 等待回应
  def get_result(self):
    raw = ''
    while True:
      recv = self.c_socket.recv(1024)
      if not recv:
        break
      if len(recv) == 0 :
        break
      raw += recv.decode('utf-8')
      if raw[-2:] == "\r\n":
        break
    return self.parse_result(raw)

  # 解析消息代码和消息体
  def parse_result(self, string):
    code = int(string[:3])
    text = string[4:-2]
    self.log(str(code) + ' ' + text, 4)
    return code, text

  # 解析消息中的IP地址
  def parse_addr(self, string):
    # print(string)
    addr_match = re.findall(r'(\(.*\))', string)[0]
    # print(addr_match)
    ip = ''
    port = 0
    if addr_match:
      try:
        arr = addr_match[1:-1].split(',')
        ip = '.'.join(arr[:4])
        port = (int(arr[4]) << 8) + int(arr[5])
      finally:
        return ip, port
    return
  
  # 解析返回中的地址
  def parse_path(self, string):
    match = re.match(r'(".*")', string)
    if match:
      return match.group(1)[1:-1]
    return ''

# 处理路径的类
class Path():
  def __init__(self, wd = '/', base = ''):
    self.base = base
    self.wd = wd

  # 切换工作目录
  def cwd(self, new_wd):
    if new_wd[:1] == '/':
      self.wd = new_wd
    elif new_wd[:2] == './':
      self.wd += new_wd[2:]
    elif new_wd[:2] == '..':
      if self.wd[-1:] == '/':
        self.wd = self.wd[:-1]
      self.wd = '/'.join(self.wd.split('/')[:-1])
      new_wd = new_wd[2:]
      if new_wd[:1] != '/':
        new_wd = '/' + new_wd
      self.wd += new_wd
    else:
      if (self.wd[-1] == '/' and new_wd[:1] == '/'):
        self.wd += new_wd[1:]
      elif (self.wd[-1] != '/' and new_wd[:1] != '/'):
        self.wd += '/' + new_wd
      else:
        self.wd += new_wd
    # print('wd:', self.wd)
  
  # 获得相对路径
  def get(self):
    return self.wd

  # 获取绝对路径
  def getAbs(self):
    return self.base + self.wd


class CommandHandler():
  def __init__(self):
    self.handler = {}
    self.session = False
    # 注册命令处理函数
    self.register('connect', self.c_connect)
    self.register('conn', self.c_connect)
    self.register('close', self.c_close)
    self.register('type', self.c_type)
    self.register('pwd', self.c_pwd)
    self.register('cd', self.c_cd)
    self.register('ls', self.c_ls)
    self.register('mkdir', self.c_mkdir)
    self.register('rmdir', self.c_rmdir)
    self.register('lcd', self.c_lcd)
    self.register('get', self.c_get)
    self.register('put', self.c_put)
    self.register('delete', self.c_delete)
    self.register('exit', self.c_exit)
    self.register('echo', print)
    self.register('cat', lambda a: print(r"flag{1t's_a_b1ackd00r}") if a == 'flag.txt' else False)

  # 下载文件
  def c_get(self, args):
    if self.need_login():
      self.session.retr(args)

  # 上传文件
  def c_put(self, args):
    if self.need_login():
      self.session.stor(args)

  # 删除文件
  def c_delete(self, args):
    if self.need_login():
      self.session.delete(args)

  # 创建文件夹
  def c_lcd(self, args):
    if self.need_login():
      self.session.lcd(args)

  # 创建文件夹
  def c_mkdir(self, args):
    if self.need_login():
      self.session.mkdir(args)

  # 删除文件夹
  def c_rmdir(self, args):
    if self.need_login():
      self.session.rmdir(args)

  # 列出文件
  def c_ls(self, args):
    if self.need_login():
      self.session.ls()

  # 切換工作目錄
  def c_cd(self, args):
    if self.need_login():
      self.session.cd(args)

  # 打印工作目录
  def c_pwd(self, args):
    if self.need_login():
      self.session.pwd()

  # 模式，二进制还是ASCII
  def c_type(self, args):
    if self.need_login():
      self.session.mode(args)

  # 连接FTP服务器
  def c_connect(self, args):
    # print(args)
    args = "ftp://admin:password@127.0.0.1:22333"
    matchObj = re.match(r'ftp://(.+?):(.*?)@(.*):(\d+)', args)
    if not matchObj:
      print('[-] URL not valid.')
      return
    user, passwd, addr, port = matchObj.groups()
    if self.session:
      print('[-] Current session exists!')
    # 新建会话
    self.session = FTPSession()
    self.session.login(user, passwd, addr, port)

  # 关闭连接
  def c_close(self, args):
    if self.need_login():
      self.session.close()
      self.session = False

  # 退出程序
  def c_exit(self, args):
    exit()

  # 需要登录
  def need_login(self):
    if not self.session:
      print('[-] Session not found, login first')
      return False
    return True

  # 注册命令
  def register(self, command, func):
    self.handler[command] = func

  # 执行命令
  def exec_command(self, command, args):
    if not command:
      return
    if not command in self.handler:
      print('command not found: %s' % command)
      return
    self.handler[command](args)
  
  # 开始
  def start(self):
    print('Welcome to gqftp client')
    print('Type command to start')
    while True:
      try:
        com = input('gqftp%s ' % (':%s$' % self.session.working_directory.wd if self.session else '>'))
      except EOFError:
        exit()
      command = com.split(' ')[0]
      args = com[(len(command) + 1):]
      # 解析命令
      self.exec_command(command, args)

# 命令解析器
handler = CommandHandler()
handler.start()
