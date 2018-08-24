#!/usr/bin/python3
import socket
import re

class FTPSession(object):
  def __init__(self):
    self.c_socket = False
    self.working_directory = False
    self.c_type = 'A'

  # 获得工作目录
  def get_wd(self):
    self.send('PWD', '')
    code, text = self.get_result()
    if code == 257:
      self.working_directory = self.parse_path(text)
  
  # 打印工作目录
  def pwd(self):
    self.get_wd()
    print(self.working_directory)

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
  def send(self, command, args):
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
    addr_match = re.match(r'(\(.*\))', string)
    ip = ''
    port = 0
    if addr_match:
      try:
        arr = addr_match.group(1)[1:-1].split(',')
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

class CommandHandler():
  def __init__(self):
    self.handler = {}
    self.session = False
    # 开始注册命令处理函数
    self.register('connect', self.c_connect)
    self.register('conn', self.c_connect)
    self.register('close', self.c_close)
    self.register('type', self.c_type)
    self.register('pwd', self.c_pwd)
    self.register('exit', self.c_exit)
    self.register('echo', print)
    self.register('cat', lambda a: print(r"flag{1t's_a_b1ackd00r}") if a == 'flag.txt' else False)

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
  def c_exit(self):
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
        com = input('%s ' % ('-' if self.session else '>'))
      except EOFError:
        exit()
      command = com.split(' ')[0]
      args = com[(len(command) + 1):]
      # 解析命令
      self.exec_command(command, args)

# 命令解析器
handler = CommandHandler()
handler.start()
