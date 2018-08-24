#!/usr/bin/python3
import socket
import threading
import os

# temporary user list
users = [
  {
    'name': 'admin',
    'passwd': 'password',
    'path': '/'
  },
  {
    'name': 'user2',
    'passwd': 'password',
    'path': '/home'
  },
  {
    'name': 'anonymous',
    'passwd': 'anon@localhost',
    'path': '/'
  }
]

# 带锁的计数器
class Counter():
  def __init__(self):
    self.connect_count = 0
    self.counter_lock = threading.Lock()

  def increase(self):
    self.counter_lock.acquire()
    try:
      self.connect_count += 1
    finally:
      self.counter_lock.release()
    print("count: %d connections" % self.connect_count)

  def decrease(self):
    self.counter_lock.acquire()
    try:
      self.connect_count -= 1
    finally:
      self.counter_lock.release()
    print("count: %d connections" % self.connect_count)

counter = Counter()

# 处理路径的类
class Path():
  def __init__(self, base):
    self.base = base
    self.wd = '/'

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
    print('wd:', self.wd)
  
  # 获得相对路径
  def get(self):
    return self.wd

  # 获取绝对路径
  def getAbs(self):
    return self.base + self.wd

# FTP 连接处理类
class Conn(threading.Thread):
  def __init__(self, fd, addr):
    threading.Thread.__init__(self)
    self.fd = fd
    self.addr = addr
    self.data_fd = False
    self.running = True
    self.user = False
    self.username = False
    self.passwd = False
    self.wd = Path(os.getcwd())
    self.mode = 'I'

  # FTP 命令处理
  def pocess_command(self, cmd, args):
    cmd = cmd.upper()
    # print(cmd, args)
    if cmd == 'USER':
      self.username = args
      if self.user:
        self.user = False
        self.message(331, 'Previous account information was flushed, send password.')
      else:
        self.message(331, 'Username ok, send password.')
    elif cmd == 'PASS':
      self.passwd = args
      self.login()
    elif cmd == "TYPE":
      self.mode = args
      self.message(200, "ok")  
    elif cmd == 'PWD':
      if self.need_login():
        self.message(257, "\"%s\" is the current directory." % self.wd.wd)
    elif cmd == 'CWD':
      if self.need_login():
        self.wd.cwd(args)
        self.message(250, "\"%s\" is the current directory." % self.wd.wd)
    elif cmd == 'PASV':
      if self.need_login():
        self.init_datafd()
    elif cmd == 'LIST':
      if self.need_login():
        self.send_list()
    elif cmd == 'MKD':
      if self.need_login():
        path = Path(os.getcwd())
        path.cwd(self.wd.wd)
        path.cwd(args)
        os.makedirs(path.getAbs(), exist_ok=True)
        self.message(257, "\"%s\" directory created" % path.wd)
    elif cmd == 'RMD':
      if self.need_login():
        path = Path(os.getcwd())
        path.cwd(self.wd.wd)
        path.cwd(args)
        os.rmdir(path.getAbs())
        self.message(250, "\"%s\" directory removed" % path.wd)
    elif cmd == 'RETR':
      if self.need_login():
        self.send_file(args)
    elif cmd == 'STOR':
      if self.need_login():
        self.upload_file(args)
    elif cmd == 'DELE':
      if self.need_login():
        path = Path(os.getcwd())
        path.cwd(self.wd.wd)
        path.cwd(args)
        os.remove(path.getAbs())
        self.message(250, 'file removed')
    else:
      self.message(500, 'Syntax error, command unrecognized.')

  # 上传文件
  def upload_file(self, file_path):
    path = Path(os.getcwd())
    path.cwd(self.wd.wd)
    path.cwd(file_path)
    file = path.getAbs()
    s, addr = self.data_fd.accept()
    print('data: receive from ', addr)
    self.message(150, 'start receiving data')
    with open(file, 'wb') as f:
      while self.running:
        data = s.recv(2048)
        if len(data) == 0:
          break
        f.write(data)
    # 传完即关闭连接
    self.data_fd.close()
    self.message(226, 'Transfer complete')

  # 发送文件
  def send_file(self, file_path):
    path = Path(os.getcwd())
    path.cwd(self.wd.wd)
    path.cwd(file_path)
    file = path.getAbs()
    if not os.path.isfile(file):
      self.message(550, "failed")  
      return
    s, addr = self.data_fd.accept()
    print('data: send to ', addr)
    self.message(150, 'start sending data')
    with open(file, 'rb') as f:
      while self.running:
        data = f.read(2048)
        if len(data) == 0:
          break  
        s.send(data)
    # 传完即关闭连接
    self.data_fd.close()
    self.message(226, 'Transfer complete')

  # 列出文件夹
  def send_list(self):
    s, addr = self.data_fd.accept()
    print('data: send to ', addr)
    # 调用 ls 命令获得
    result = os.popen('ls -al %s' % self.wd.getAbs()).read()
    self.message(150, 'start sending data')
    # 把默认的 LF 转换为 CRLF
    lines = result.split('\n')
    lines.append('')
    s.send('\r\n'.join(lines).encode('utf-8'))
    # 传完即关闭连接
    self.data_fd.close()
    self.message(226, 'Transfer complete')

  # 初始化数据连接
  def init_datafd(self):
    try:
      self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.data_fd.bind(('0.0.0.0', 0))
      self.data_fd.listen()
      ip, port = self.data_fd.getsockname()
      addr = ','.join(ip.split('.')) + ',' + str(port >> 8) + ',' + str(port & 255)
      self.message(227, "Entering Passive Mode (%s)." % addr)
    except:
      self.message(500, 'Failed create data socket')

  # 检查是否登录
  def need_login(self):
    if not self.user:
      self.message(530, 'Log in with USER and PASS first.')
      return False
    return True

  # 登录
  def login(self):
    if not self.username:
      self.message(503, 'Login with USER first.')
    else:
      # search user
      user = ''
      for u in users:
        if u['name'] == self.username:
          user = u
          break
      if not user or user['passwd'] != self.passwd:
        self.username = self.passwd = False
        self.message(530, 'Authentication failed.')
      else:
        # success
        self.user = user
        self.wd.cwd(user['path'])
        print('login:', self.user)
        self.message(230, 'Login successful.')
        pass

  # 返回消息
  def message(self, code, data):
    print('reply:', code, data)
    self.fd.send(("%d %s\r\n" % (code, data)).encode('utf-8'))

  def run(self):
    # welcome message
    self.message(220, 'gqftpd service ready')
    raw = ''
    while self.running:
      recv = self.fd.recv(2048)
      if not recv:
        break
      if len(recv) == 0 :
        break
      raw += recv.decode('utf-8')
      if raw[-2:] != '\r\n':
        continue
      print('client:', raw[:-2])
      # 解析 FTP 命令
      raw = raw[:-2]
      command = raw.split(' ')[0]
      args = raw[(len(command) + 1):]
      raw = ''
      # process ftp command
      self.pocess_command(command, args)
    print('conn: Close connection')
    counter.decrease()
    self.running = False
    self.fd.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 22333))
s.listen()

print('Waiting for connect...')
while True:
  # 接受连接
  sock, addr = s.accept()
  # 初始化对应的工作线程
  t = Conn(sock, addr)
  t.start()
  # 计数器加一
  counter.increase()
