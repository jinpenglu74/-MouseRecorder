from pathlib import Path
import hashlib
root=Path('.')
def rw(path, old, new):
    p=root/path
    s=p.read_text(encoding='utf-8')
    if old not in s: raise SystemExit(f'expected pattern missing: {path}')
    p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')
rw('src/fund_platform/api/routes_core.py','import httpx\n\nfrom fastapi','import httpx\nfrom fastapi')
rw('src/fund_platform/logging_runtime.py',"        with self._lock:\n            with self.path.open('a', encoding='utf-8') as stream:\n                stream.write(line)\n","        with self._lock, self.path.open('a', encoding='utf-8') as stream:\n            stream.write(line)\n")
p=root/'src/fund_platform/main.py'; s=p.read_text(encoding='utf-8'); s=s.replace('        logger = request.app.state.runtime_log\n','        runtime_log = request.app.state.runtime_log\n').replace('            logger.info("HTTP", f"{request.method} {request.url.path} 开始")','            runtime_log.info("HTTP", f"{request.method} {request.url.path} 开始")').replace('                logger.info("HTTP", f"{request.method} {request.url.path} -> {response.status_code}")','                runtime_log.info("HTTP", f"{request.method} {request.url.path} -> {response.status_code}")').replace('            logger.exception("HTTP", f"{request.method} {request.url.path} 未处理异常", error)','            runtime_log.exception("HTTP", f"{request.method} {request.url.path} 未处理异常", error)'); p.write_text(s,encoding='utf-8',newline='\n')
rw('src/fund_platform/model/calibration.py','from dataclasses import dataclass, replace\nimport math\n','import math\nfrom dataclasses import dataclass, replace\n')
p=root/'src/fund_platform/model/ensemble.py'; s=p.read_text(encoding='utf-8').replace('import math\n','').replace('from fund_platform.model.calibration import DEFAULTS, score_profile, select_profile','from fund_platform.model.calibration import score_profile, select_profile'); p.write_text(s,encoding='utf-8',newline='\n')
p=root/'tests/unit/test_daily_refresh.py'; s=p.read_text(encoding='utf-8').replace('    from datetime import date, timedelta\n    from fund_platform.data.nav_provider import NavPoint\n','    from datetime import timedelta\n\n    from fund_platform.data.nav_provider import NavPoint\n').replace('NavPoint(date.today() - timedelta(days=119-index), 1 + index * 0.001,','NavPoint(datetime.now(UTC).date() - timedelta(days=119-index), 1 + index * 0.001,'); p.write_text(s,encoding='utf-8',newline='\n')
rw('tests/unit/test_database_connections.py',"    with pytest.raises(RuntimeError, match='force rollback'):\n        with database.connect() as active:\n            connection = active\n            active.execute(\n                \"INSERT INTO search_history(token, used_at) VALUES (?, ?)\",\n                ('temporary', '2026-09-17T00:00:00+00:00'),\n            )\n            raise RuntimeError('force rollback')\n","    with pytest.raises(RuntimeError, match='force rollback'), database.connect() as active:\n        connection = active\n        active.execute(\n            \"INSERT INTO search_history(token, used_at) VALUES (?, ?)\",\n            ('temporary', '2026-09-17T00:00:00+00:00'),\n        )\n        raise RuntimeError('force rollback')\n")
p=root/'tests/unit/test_launcher_self_test.py'; s=p.read_text(encoding='utf-8').replace('import fund_platform.launcher as launcher','from fund_platform import launcher').replace(".encode('utf-8')",'.encode()'); p.write_text(s,encoding='utf-8',newline='\n')
p=root/'tests/unit/test_runtime_log.py'; s=p.read_text(encoding='utf-8').replace('    log = RuntimeLog(path, reset=True)','    runtime_log = RuntimeLog(path, reset=True)').replace('in log.read_text()','in runtime_log.read_text()').replace('    log = RuntimeLog(tmp_path / "runtime.log", reset=True)','    runtime_log = RuntimeLog(tmp_path / "runtime.log", reset=True)').replace('    log.info("TEST", "before-clear")','    runtime_log.info("TEST", "before-clear")').replace('in log.read_text()','in runtime_log.read_text()').replace('    log.clear()','    runtime_log.clear()').replace('    text = log.read_text()','    text = runtime_log.read_text()').replace('        runtime_log=log,','        runtime_log=runtime_log,').replace('    log = RuntimeLog(sandbox_path / "runtime.log", reset=True)','    runtime_log = RuntimeLog(sandbox_path / "runtime.log", reset=True)').replace('client = TestClient(create_app(sandbox_path / "runtime.db", seed_demo=True, runtime_log=log))','client = TestClient(\n        create_app(sandbox_path / "runtime.db", seed_demo=True, runtime_log=runtime_log)\n    )').replace('    before = log.read_text()','    before = runtime_log.read_text()').replace('    added = log.read_text()[len(before):]','    added = runtime_log.read_text()[len(before):]'); p.write_text(s,encoding='utf-8',newline='\n')
expected={
'src/fund_platform/api/routes_core.py':'d4bcaaf303d1cf0d01fe26e93f07f697359e93634375b8b3e7e4c16f14c3d770',
'src/fund_platform/logging_runtime.py':'a3d82a938dbd3cc518fbec5bcc331442dc6bf5268bcda726cd270fdc76b2abb3',
'src/fund_platform/main.py':'b60efe5ed7a43af62834af6740ad16b3170b215b2f324d602ebd2fea38b8f0a3',
'src/fund_platform/model/calibration.py':'ef5e0b191d1a35ffd0fa243895e27ca5c654751967b79bcaf770c4bc03b82574',
'src/fund_platform/model/ensemble.py':'aca8b94541f6ec72e92754035f35c8f4a582c8f2f36a66c6fd23b0e8cbe19136',
'tests/unit/test_daily_refresh.py':'ad1c61d85bb11bb5ce2dd65a77c41b8ea20db340f473ee4711dfd7a61f167320',
'tests/unit/test_database_connections.py':'af574a28850e26c80c43dcbb2fc283701cd3c9c62357184fd666c1716019dbce',
'tests/unit/test_launcher_self_test.py':'d53a775a288799fea660f057b3a28f8da2f5173631a653ad887f57b1f7ac7774',
'tests/unit/test_runtime_log.py':'bb338a579ca4afe7a327421714ef6d9e285478e00ae858e499355279f54de273'}
for name,want in expected.items():
    got=hashlib.sha256((root/name).read_bytes()).hexdigest()
    if got!=want: raise SystemExit(f'hash mismatch {name}: {got}')
