"""Bounded local HTTP read benchmark. No research or business state is changed."""
import argparse
import concurrent.futures
import json
import platform
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def sample(base: str) -> dict:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(base.rstrip('/') + '/api/bootstrap', timeout=15) as response:
            body = response.read()
            return {'latency_ms': (time.perf_counter()-start)*1000, 'status': response.status, 'bytes': len(body)}
    except Exception as error:
        return {'latency_ms': (time.perf_counter()-start)*1000, 'status': 0, 'error': type(error).__name__}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',default='http://127.0.0.1:8001')
    parser.add_argument('--output',default='reports/performance-readonly.json')
    args=parser.parse_args()
    groups=[]
    for concurrency in (10,25,50):
        sample(args.base)
        started=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            samples=list(pool.map(lambda _:sample(args.base),range(concurrency*3)))
        values=sorted(s['latency_ms'] for s in samples)
        quantile=lambda p:values[min(len(values)-1,int((len(values)-1)*p))]
        groups.append({'concurrency':concurrency,'requests':len(samples),'wall_seconds':time.perf_counter()-started,
                       'p50_ms':statistics.median(values),'p95_ms':quantile(.95),'p99_ms':quantile(.99),
                       'error_rate':sum(s['status']!=200 for s in samples)/len(samples),'samples':samples})
    report={'recorded_at':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
            'base_url':args.base,'endpoint':'GET /api/bootstrap','cohort':'Local synthetic demonstration database',
            'method':'Three requests per worker; 10/25/50 worker pools; warm-up read; HTTP wall time includes DB and JSON. Other project workloads active.',
            'model_calls':0,'db_only_latency':'unavailable: no separate instrumentation','production_capacity':'unavailable: short local read sample only','groups':groups}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in g.items() if k!='samples'} for g in groups],indent=2))


if __name__=='__main__':
    main()
