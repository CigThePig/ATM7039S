#!/usr/bin/env python3
"""Compare immediate-parent resources by numeric base, never assert chip equivalence."""
import argparse
import json
from pathlib import Path
import research as r

def compare(left,right):
 result=[]
 for a in left['ranges']:
  if a['size'] is None:continue
  for b in right['ranges']:
   if b['size'] is None or a['address']!=b['address']:continue
   result.append(dict(base=hex(a['address']),left_path=a['path'],right_path=b['path'],left_size=a['size'],right_size=b['size'],left_irq=a['interrupts_raw'],right_irq=b['interrupts_raw'],irq_cells_equal=a['interrupts_raw']==b['interrupts_raw'],confidence='inferred',conclusion='matching numeric resource; compatibility unverified',translation='caller must establish identity CPU bus mappings'))
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('left',type=Path);p.add_argument('right',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 r.save(a.output,compare(json.loads(a.left.read_text()),json.loads(a.right.read_text())))
