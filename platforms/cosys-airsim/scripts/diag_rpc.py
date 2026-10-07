# -*- coding: utf-8 -*-
"""诊断：为什么 ping 的响应永远不回来"""
from tornado import ioloop
import msgpackrpc

c = msgpackrpc.Client(msgpackrpc.Address('127.0.0.1', 41451), timeout=5)
sess_loop = c._loop._ioloop
print("A. session 的 ioloop 是主线程 current 吗:",
      ioloop.IOLoop.current() is sess_loop)

fut = c.send_request('ping', ())
print("B. 请求已发出，手工步进循环等响应（最多 8 秒）……")
import time
t0 = time.time()
while not fut._set_flag and time.time() - t0 < 8:
    sess_loop.start()   # 跑一会儿：有回调就会执行并 stop
print("C. 响应到了吗:", fut._set_flag, "| 结果:", fut._result, "| 错误:", fut._error)
if not fut._set_flag:
    print("D. 响应没回来 → 检查 IOStream 绑定的是哪个循环")
    print("   IOStream 们挂在:", [s for s in ioloop.IOLoop.current().handlers] if hasattr(ioloop.IOLoop.current(), 'handlers') else "(无法枚举)")
