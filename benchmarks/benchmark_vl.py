#!/usr/bin/env python3
"""Serial VL demo timings + sampled process/system RAM; no VRAM exclusivity claim."""
import csv
import json
import os
from pathlib import Path
import sys
import threading
import time
from datetime import datetime

if len(sys.argv) != 3:
    raise SystemExit('Usage: benchmark_vl.py /path/to/image.png /path/to/results')
image=Path(sys.argv[1]).expanduser().resolve()
assert image.is_file(),image
out=Path(sys.argv[2])/('run-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True,exist_ok=True)
stop=threading.Event()
samples=[]
phase=['baseline']

def snap():
    d={}
    with open('/proc/meminfo') as f:
        for row in f:
            key,val=row.split(':',1)
            d[key]=int(val.split()[0])/1024
    with open('/proc/self/status') as f:
        rss=next((int(row.split()[1])/1024 for row in f if row.startswith('VmRSS:')),0)
    return {'time':round(time.monotonic(),3),'phase':phase[0],'rss_mib':round(rss,2),'mem_available_mib':round(d['MemAvailable'],2)}

def monitor():
    while not stop.is_set():
        samples.append(snap())
        stop.wait(0.5)

thread=threading.Thread(target=monitor,daemon=True)
thread.start()
try:
    import paddle
    from paddleocr import PaddleOCRVL
    baseline=snap()['mem_available_mib']
    phase[0]='initialize'; start=time.monotonic()
    pipeline=PaddleOCRVL(pipeline_version='v1.6', device='gpu:0',use_doc_orientation_classify=False,use_doc_unwarping=False)
    initialization=time.monotonic()-start
    timings=[]
    for i in range(3):
        phase[0]=f'inference-{i+1}'
        start=time.monotonic(); pages=0
        for item in pipeline.predict(str(image)):
            pages+=1
            if i==0:
                folder=out/'recognized';folder.mkdir(exist_ok=True)
                item.save_to_markdown(save_path=str(folder))
                item.save_to_json(save_path=str(folder))
        timings.append({'run':i+1,'seconds':round(time.monotonic()-start,3),'pages':pages})
        print(timings[-1],flush=True)
    phase[0]='finished';time.sleep(1)
finally:
    stop.set();thread.join(timeout=5)
if samples:
    with (out/'memory.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)
summary={'image':str(image),'engine':'paddle_dynamic','initialize_seconds':round(initialization,3),'runs':timings,'peak_rss_mib':max(x['rss_mib'] for x in samples),'minimum_mem_available_mib':min(x['mem_available_mib'] for x in samples),'baseline_mem_available_mib':baseline,'note':'Not exclusive GPU memory; sampling can miss peaks; other processes affect available memory.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print(json.dumps(summary,indent=2),flush=True)
