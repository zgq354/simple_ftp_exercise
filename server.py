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

class Path():
  def __init__(self, base):
    self.base = base
    self.wd = '/'

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
  
  def get(self):
    return self.wd

  def getAbs(self):
    return self.base + self.wd


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
      pass
    elif cmd == 'LIST':
      if self.need_login():
        self.send_list()
      pass
    else:
      self.message(500, 'Syntax error, command unrecognized.')
  
  def send_list(self):
    s, addr = self.data_fd.accept()
    print('data: send to ', addr)
    result = os.popen('ls -al %s' % self.wd.getAbs()).read()
    # LF to CRLF
    lines = result.split('\n')
    self.message(150, 'start sending data')
    for line in lines:
      s.send((line + '\r\n').encode('utf-8'))
    self.data_fd.close()
    self.message(226, 'Transfer complete')

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

  def need_login(self):
    if not self.user:
      self.message(530, 'Log in with USER and PASS first.')
      return False
    return True

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
  t = Conn(sock, addr)
  counter.increase()
  t.start()
