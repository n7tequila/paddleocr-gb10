#!/usr/bin/env python3
"""Single-process, non-daemon PaddleOCR-VL-1.6 inference smoke test."""
import argparse
import json
from pathlib import Path
import time
from paddleocr import PaddleOCRVL

p = argparse.ArgumentParser()
p.add_argument('input', help='Local PNG/JPG/PDF path')
p.add_argument('--output', default='outputs/vl16')
a = p.parse_args()
src = Path(a.input).expanduser().resolve()
if not src.is_file():
    p.error(f'file not found: {src}')
out = Path(a.output)
out.mkdir(parents=True, exist_ok=True)
t0 = time.perf_counter()
pipe = PaddleOCRVL(pipeline_version='v1.6', device='gpu:0', use_doc_orientation_classify=False, use_doc_unwarping=False)
init = time.perf_counter() - t0
t1 = time.perf_counter()
count = 0
for result in pipe.predict(str(src)):
    result.save_to_json(save_path=str(out))
    result.save_to_markdown(save_path=str(out))
    count += 1
summary = dict(init_s=round(init, 3), predict_and_save_s=round(time.perf_counter()-t1, 3), pages=count, output=str(out))
print(json.dumps(summary, ensure_ascii=False, indent=2))
