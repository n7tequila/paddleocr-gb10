"""Run inside the existing image with --gpus all; tiny CUDA computation only."""
import json
import platform
import ctypes
import paddle

assert platform.machine() == "aarch64", platform.machine()
assert paddle.is_compiled_with_cuda(), "CUDA-disabled Paddle build"
paddle.set_device("gpu:0")
name = paddle.device.cuda.get_device_name(0)
capability = paddle.device.cuda.get_device_capability(0)
assert tuple(capability) == (12, 1), capability
x = paddle.ones([8, 8], dtype="float32")
y = paddle.matmul(x, x)
assert float(y[0, 0]) == 8.0 and float(y.sum()) == 512.0
runtime = ctypes.c_int()
result = ctypes.CDLL("libcudart.so.13").cudaRuntimeGetVersion(ctypes.byref(runtime))
assert result == 0, f"cudaRuntimeGetVersion returned {result}"
cuda_runtime = f"{runtime.value // 1000}.{(runtime.value % 1000) // 10}"
print(json.dumps({"gpu": name, "compute_capability": capability,
                  "cuda_build": paddle.version.cuda(), "cuda_runtime": cuda_runtime,
                  "matrix_sum": float(y.sum())}))
