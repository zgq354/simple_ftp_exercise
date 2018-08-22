#!/usr/bin/python3
import socket
import threading

class Conn(threading.Thread):
  def __init__(self, fd):
    threading.Thread.__init__(self)
    self.fd = fd
    self.running = True
  
  def message(self, code, data):
    self.fd.send(("%s %s\r\n" % (code, data)).encode('utf-8'))

  def run(self):
    self.message('220', 'gqftpd service ready')
    while self.running:
      recv = self.fd.recv(2048)
      if not recv:
        self.fd.close()
        break
      self.fd.send(recv)
      print(recv)


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 2233))
s.listen()

print('Waiting for connect...')
while True:
  # 接受连接
  sock, addr = s.accept()
  t = Conn(sock)
  t.start()
