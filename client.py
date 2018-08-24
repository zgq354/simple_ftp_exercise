#!/usr/bin/python3

class FTPSession(object):
  def __init__(self):
    pass

class CommandHandler():
  def __init__(self):
    self.handler = {}
    self.session = False
    # 开始注册命令处理函数
    self.register('connect', self.c_connect)
    self.register('exit', self.c_exit)
    self.register('print', print)
    self.register('cat', lambda a: print(r'flag{1t\'s_a_b1ackd00r}'))

  # 连接FTP服务器
  def c_connect(self, args):
    print(args)

  # 退出程序
  def c_exit(self):
    exit()

  # 注册命令
  def register(self, command, func):
    self.handler[command] = func

  # 执行命令
  def run(self, command, args):
    if not command:
      return
    if not command in self.handler:
      print('command not found: %s' % command)
      return
    self.handler[command](args)

# 命令解析器
handler = CommandHandler()
print('Welcome to gqftp client')
print('Type command to start')
while True:
  try:
    com = input('> ')
  except EOFError as e:
    exit()
  command = com.split(' ')[0]
  args = com[(len(command) + 1):]
  # 解析命令
  handler.run(command, args)
