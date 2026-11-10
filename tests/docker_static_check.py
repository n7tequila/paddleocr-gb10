from pathlib import Path
import ast
import subprocess
r=Path(__file__).resolve().parents[1]
sh_files=list((r/'docker').glob('*.sh'))
for p in sh_files:
    subprocess.run(['bash','-n',str(p)], check=True)
for p in (r/'docker').glob('*.py'):
    ast.parse(p.read_text(),filename=str(p))
compose=(r/'docker/compose.yaml').read_text()
assert 'gpus: all' in compose
healthcheck=compose.split('    healthcheck:', 1)[1].split('    # Deliberately', 1)[0]
assert 'urllib.request.urlopen' in healthcheck
assert 'http://127.0.0.1:8080/health' in healthcheck
assert 'response.status == 200' in healthcheck
assert '/layout-parsing' not in healthcheck
for setting in ('interval: 30s', 'timeout: 10s', 'retries: 3', 'start_period: 120s'):
    assert setting in healthcheck, setting
assert '127.0.0.1' in (r/'docker/.env.example').read_text()
assert 'paddlex --serve' in (r/'docker/entrypoint.sh').read_text()
assert 'FastAPI' not in (r/'docker/entrypoint.sh').read_text()
assert '/layout-parsing' in (r/'docker/test-official-api.py').read_text()
dockerfile=(r/'docker/Dockerfile').read_text()
builder=(r/'docker/build-image.sh').read_text()
for name in ('requirements-verified.txt', 'fix-cusparselt-wheel-tag.py', 'entrypoint.sh'):
    assert f'COPY docker/{name}' in dockerfile
    assert f'"$REPO/docker/{name}"' in builder
assert 'PIP_CONSTRAINT=/opt/requirements-verified.txt' in dockerfile
pins=(r/'docker/requirements-verified.txt').read_text()
for pin in ('numpy==2.3.5', 'paddleocr==3.7.0', 'paddlex==3.7.2',
            'nvidia-cusparselt-cu13==0.8.1', 'protobuf==7.36.1'):
    assert pin in pins.splitlines(), pin
print('PASS:', len(sh_files), 'shell files, Python syntax, official-serving configuration')
