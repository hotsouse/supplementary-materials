"""Compare two complete numeric output directories after independent executions."""
from pathlib import Path
import argparse,hashlib,json
import pandas as pd

def main():
    p=argparse.ArgumentParser();p.add_argument('reference',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--save',type=Path,required=True);a=p.parse_args()
    rows=[]
    for f in sorted((a.reference/'tables').glob('*.csv')):
        other=a.candidate/'tables'/f.name
        row={'file':f.name,'exists':other.exists(),'byte_identical':False,'numerically_equal':False}
        if other.exists():
            row['byte_identical']=hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256(other.read_bytes()).digest()
            try:
                pd.testing.assert_frame_equal(pd.read_csv(f),pd.read_csv(other),check_exact=False,rtol=1e-12,atol=1e-10)
                row['numerically_equal']=True
            except (AssertionError,pd.errors.EmptyDataError) as e:
                if row['byte_identical']:row['numerically_equal']=True
                else:row['difference']=str(e)[:500]
        rows.append(row)
    result={'all_tables_equal':all(r['numerically_equal'] for r in rows),'n_tables':len(rows),
        'byte_identical_count':sum(r['byte_identical'] for r in rows),'tolerance':{'rtol':1e-12,'atol':1e-10},'tables':rows}
    a.save.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='tables'}))
    if not result['all_tables_equal']:raise SystemExit(1)

if __name__=='__main__':main()
