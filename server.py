#!/usr/bin/python3
import socket
import threading

# temporary user list
users = [
  {
    'name': 'admin',
    'passwd': 'password',
    'path': '/home'
  },
  {
    'name': 'user2',
    'passwd': 'password',
    'path': '/home'
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
    print("%d connections" % self.connect_count)

  def decrease(self):
    self.counter_lock.acquire()
    try:
      self.connect_count -= 1
    finally:
      self.counter_lock.release()
    print("%d connections" % self.connect_count)

counter = Counter()

class Conn(threading.Thread):
  def __init__(self, fd):
    threading.Thread.__init__(self)
    self.fd = fd
    self.running = True
    self.user = False
    self.username = False
    self.passwd = False

  def pocess_command(self, command, args):
    command = command.upper()
    if command == 'USER':
      self.username = args
      if self.user:
        self.user = False
        self.message(331, 'Previous account information was flushed, send password.')
      else:
        self.message(331, 'Username ok, send password.')
    elif command == 'PASS':
      self.passwd = args
      self.login()
    else:
      self.message(500, 'Syntax error, command unrecognized.')

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
        print(self.user)
        self.message(230, 'Login successful.')
        pass

  def message(self, code, data):
    self.fd.send(("%d %s\r\n" % (code, data)).encode('utf-8'))

  def run(self):
    # welcome message
    self.message(220, 'gqftpd service ready')
    raw = ''
    while self.running:
      recv = self.fd.recv(2048)
      print(recv)
      if not recv:
        break
      if len(recv) == 0 :
        break
      raw += recv.decode('utf-8')
      if raw[-2:] != '\r\n':
        continue
      command = raw.split(' ')[0]
      args = raw[(len(command) + 1):-2]
      raw = ''
      # process ftp command
      self.pocess_command(command, args)
    print('Close connection')
    counter.decrease()
    self.running = False
    self.fd.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 2233))
s.listen()

print('Waiting for connect...')
while True:
  # 接受连接
  sock, addr = s.accept()
  t = Conn(sock)
  counter.increase()
  t.start()
