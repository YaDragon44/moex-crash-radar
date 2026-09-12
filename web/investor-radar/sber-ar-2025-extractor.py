#!/usr/bin/env python3
import json, os, re, ssl, subprocess, sys, urllib.request
from pathlib import Path
from urllib.parse import urlparse

URL = os.environ.get('SBER_AR_URL','https://www.sberbank.com/common/img/uploaded/_new_site/com/gosa2026/sber-ar-2025-ru.pdf')
OUT = Path(os.environ.get('OUT_DIR','artifacts/r1.8.43'))
OUT.mkdir(parents=True, exist_ok=True)
pdf = OUT/'sber-ar-2025-ru.pdf'
txt = OUT/'sber-ar-2025-ru.txt'
result_path = OUT/'sber-ar-2025-extraction.json'

ALLOWED_HOST='www.sberbank.com'
parsed=urlparse(URL)
if parsed.scheme!='https' or parsed.hostname!=ALLOWED_HOST:
    raise SystemExit('Refusing non-official Sber annual-report URL')

req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 InvestorRadar/1.8.43'})
transport='TLS_VERIFIED'
transport_error=None
try:
    with urllib.request.urlopen(req,timeout=60) as r:
        final=urlparse(r.geturl())
        if final.hostname!=ALLOWED_HOST: raise RuntimeError('redirect outside official Sber host')
        body=r.read()
except Exception as e:
    transport_error=str(e)
    if 'CERTIFICATE_VERIFY_FAILED' not in transport_error:
        result={'status':'DOWNLOAD_FAILED','sourceUrl':URL,'error':transport_error,'commonBvpsEligible':False,'valuationStatus':'PARTIAL'}
        result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))
        sys.exit(2)
    # Russian PKI may not be trusted by the GitHub-hosted runner. We only use
    # this path for document location/extraction, never to promote valuation
    # evidence to VERIFIED. Host is pinned and redirects outside it are blocked.
    transport='TLS_UNVERIFIED_PINNED_OFFICIAL_HOST'
    ctx=ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req,timeout=60,context=ctx) as r:
            final=urlparse(r.geturl())
            if final.hostname!=ALLOWED_HOST: raise RuntimeError('redirect outside official Sber host')
            body=r.read()
    except Exception as e2:
        result={'status':'DOWNLOAD_FAILED','sourceUrl':URL,'error':str(e2),'verifiedTlsError':transport_error,'transportTrust':transport,'commonBvpsEligible':False,'valuationStatus':'PARTIAL'}
        result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))
        sys.exit(2)

if not body.startswith(b'%PDF'):
    result={'status':'NOT_PDF','sourceUrl':URL,'bytes':len(body),'transportTrust':transport,'commonBvpsEligible':False,'valuationStatus':'PARTIAL'}
    result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    sys.exit(3)
pdf.write_bytes(body)

try:
    subprocess.run(['pdftotext','-layout',str(pdf),str(txt)],check=True,timeout=120)
except Exception as e:
    result={'status':'TEXT_EXTRACTION_FAILED','sourceUrl':URL,'error':str(e),'transportTrust':transport,'commonBvpsEligible':False,'valuationStatus':'PARTIAL'}
    result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    sys.exit(4)

lines=txt.read_text(encoding='utf-8',errors='replace').splitlines()
patterns={
 'attributable_equity_to_shareholders':[r'капитал.{0,80}акционер',r'принадлеж.{0,80}акционер',r'equity.{0,80}shareholder'],
 'attributable_common_equity':[r'обыкновенн.{0,80}капитал',r'капитал.{0,80}обыкновенн',r'common.{0,80}equity'],
 'treasury_common_shares':[r'собственн.{0,40}акци',r'выкупленн.{0,40}акци',r'treasury.{0,40}share'],
 'common_shares_outstanding':[r'обыкновенн.{0,60}акци',r'акци.{0,60}в обращ',r'common.{0,60}shares'],
 'preferred_share_current_rights':[r'привилегированн.{0,80}акци',r'preferred.{0,80}share']
}

def contexts(regexes,limit=20):
    out=[]
    for i,line in enumerate(lines):
        low=line.lower()
        if any(re.search(p,low,re.I) for p in regexes):
            a=max(0,i-2); b=min(len(lines),i+3)
            out.append({'line':i+1,'context':'\n'.join(lines[a:b]).strip()})
            if len(out)>=limit: break
    return out

hits={k:contexts(v) for k,v in patterns.items()}
found={k:bool(v) for k,v in hits.items()}
result={
 'status':'EXTRACTED_PRIMARY_DOCUMENT',
 'sourceUrl':URL,
 'transportTrust':transport,
 'verifiedTlsError':transport_error,
 'documentBytes':len(body),
 'textLines':len(lines),
 'targetsFound':found,
 'hits':hits,
 'commonBvpsEligible':False,
 'valuationStatus':'PARTIAL',
 'rule':'Keyword/context extraction is locator evidence only. If transportTrust is TLS_UNVERIFIED_PINNED_OFFICIAL_HOST, content must be independently corroborated before any field becomes VERIFIED. No value is promoted to VERIFIED without exact accounting meaning, share-class basis, unit and period validation.'
}
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'transportTrust':transport,'targetsFound':found,'textLines':len(lines)},ensure_ascii=False))
