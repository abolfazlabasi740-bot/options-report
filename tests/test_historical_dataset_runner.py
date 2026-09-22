import pandas as pd
from historical_dataset_runner import run_file

def test_runner_records_sha_and_unresolved_sheet(tmp_path):
    p=tmp_path/"sample.xlsx"
    pd.DataFrame([{"نماد":"X","حجم معاملات":100,"ارزش معاملات":1000}]).to_excel(p,index=False)
    result=run_file(p,top_n=1)
    assert result["sha256"]
    assert result["sheets"][0]["sheet"]=="Sheet1"
    assert result["sheets"][0]["status"]=="UNRESOLVED"
