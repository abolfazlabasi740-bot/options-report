#!/usr/bin/env python3
import argparse, json, logging
from pathlib import Path
from engine import Analyzer
from db import connect, save_snapshot
from report import render

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('symbols',nargs='*'); ap.add_argument('--file',default=None); ap.add_argument('--json',action='store_true'); args=ap.parse_args()
    syms=list(args.symbols)
    if args.file: syms += [x.strip() for x in Path(args.file).read_text(encoding='utf-8').splitlines() if x.strip() and not x.startswith('#')]
    if not syms: ap.error('symbol or --file required')
    cfg=json.loads(Path('config.json').read_text(encoding='utf-8')); analyzer=Analyzer(cfg); con=connect(cfg['snapshot_db'])
    for s in syms:
        try:
            p=analyzer.analyze(s); sid=save_snapshot(con,p)
            out=Path('reports')/f'{s}_{p["captured_at_utc"].replace(":","-")}.txt'; out.parent.mkdir(exist_ok=True); out.write_text(render(p),encoding='utf-8')
            print(json.dumps({'symbol':s,'snapshot_id':sid,'research_score':p['research_score'],'report':str(out)},ensure_ascii=False) if args.json else render(p))
        except Exception as e:
            logging.exception('failed %s',s); print(f'[{s}] ERROR: {e}')
if __name__=='__main__': main()
