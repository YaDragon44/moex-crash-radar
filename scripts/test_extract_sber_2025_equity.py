#!/usr/bin/env python3
import importlib.util
from pathlib import Path

MODULE=Path(__file__).with_name('extract_sber_2025_equity.py')
spec=importlib.util.spec_from_file_location('extractor', MODULE)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

assert 'attributable_equity' in m.PATTERNS
assert 'treasury_shares' in m.PATTERNS
assert 'shares_outstanding' in m.PATTERNS
assert 'preferred_shares' in m.PATTERNS
assert 'liquidation_rights' in m.PATTERNS

samples={
 'attributable_equity':'Капитал, принадлежащий акционерам Банка',
 'treasury_shares':'Собственные акции, выкупленные у акционеров',
 'shares_outstanding':'обыкновенные акции в обращении',
 'ordinary_shares':'обыкновенные акции',
 'preferred_shares':'привилегированные акции',
 'liquidation_rights':'ликвидационная стоимость привилегированной акции',
}
import re
for cat,text in samples.items():
    assert any(re.search(p,text,re.I) for p in m.PATTERNS[cat]), (cat,text)
print('R1.8.42 extractor boundary tests: PASS')
