import json, sqlite3
from pathlib import Path

SCHEMA='''
CREATE TABLE IF NOT EXISTS snapshots (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 captured_at_utc TEXT NOT NULL,
 symbol TEXT NOT NULL,
 ins_code TEXT,
 data_quality REAL,
 research_score REAL,
 payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snap_symbol_time ON snapshots(symbol, captured_at_utc);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 snapshot_id INTEGER,
 event_type TEXT NOT NULL,
 event_json TEXT NOT NULL,
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
);
'''

def connect(path):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(p); con.executescript(SCHEMA); return con

def save_snapshot(con,payload):
    cur=con.execute('INSERT INTO snapshots(captured_at_utc,symbol,ins_code,data_quality,research_score,payload_json) VALUES(?,?,?,?,?,?)',(
        payload['captured_at_utc'], payload.get('symbol'), payload.get('ins_code'),
        payload.get('quality',{}).get('confidence'), payload.get('research_score'), json.dumps(payload,ensure_ascii=False)))
    sid=cur.lastrowid
    for e in payload.get('events',[]):
        con.execute('INSERT INTO events(snapshot_id,event_type,event_json) VALUES(?,?,?)',(sid,e.get('type','unknown'),json.dumps(e,ensure_ascii=False)))
    con.commit(); return sid
