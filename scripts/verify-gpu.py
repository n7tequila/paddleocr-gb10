#!/usr/bin/env python3
import platform
import paddle
print('Architecture:', platform.machine())
print('Paddle:', paddle.__version__)
print('CUDA compiled:', paddle.device.is_compiled_with_cuda())
assert platform.machine() == 'aarch64'
assert paddle.device.is_compiled_with_cuda()
paddle.set_device('gpu:0')
x = paddle.ones([64, 64])
y = paddle.matmul(x, x)
assert float(y[0, 0]) == 64.0
print('GPU matrix multiplication: PASS')
paddle.utils.run_check()
print('GPU verification: PASS')
