#!/usr/bin/env python3
"""Short-lived local TLS/DNS/renewal monitor. No external notifications or secrets."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
from acme_common import ROOT, ACME, profile


def endpoint(cfg):
    context=ssl.create_default_context(cafile=str(ROOT/'frame-roots.pem'))
    raw=socket.create_connection((cfg['address'],8789),timeout=5)
    connection=http.client.HTTPConnection(cfg['hostname'],8789,timeout=5)
    try:
        connection.sock=context.wrap_socket(raw,server_hostname=cfg['hostname'])
        public=connection.sock.getpeercert(binary_form=True)
        connection.request('GET','/__proxy_health',headers={'Host':cfg['hostname']+':8789'})
        response=connection.getresponse();body=json.loads(response.read())
        if response.status!=200:raise ValueError('Endpoint health status')
        return public,body
    finally:connection.close();raw.close()


def evaluate(cfg, now=None):
    now=time.time() if now is None else now
    issues=[];result={'checkedAt':now,'issues':issues}
    for unit in ['pf1007l-proxy-https.service','pf1007l-proxy-https-firewall.service']:
        if subprocess.run(['systemctl','is-active','--quiet',unit]).returncode:
            issues.append('unit-inactive:'+unit)
    if subprocess.run(['nft','list','table','inet','pf1007l_proxy_tls'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        issues.append('tls-firewall-table-missing')
    try:
        addresses={item[4][0] for item in socket.getaddrinfo(cfg['hostname'],8789,type=socket.SOCK_STREAM)}
    except OSError:addresses=set()
    if addresses!={cfg['address']}:
        from run_acme import published_lan_address
        try:
            if published_lan_address(cfg):result['resolutionMode']='single-host-app-proxy; gateway filters private DNS'
            else:issues.append('published-dns-address-mismatch')
        except Exception:issues.append('public-dns-check-unavailable')
    try:
        bridge=http.client.HTTPConnection(cfg['address'],8790,timeout=4)
        try:
            bridge.request('CONNECT',cfg['hostname']+':8789',headers={'Host':cfg['hostname']+':8789'})
            response=bridge.getresponse();response.read()
            if response.status!=403:issues.append('bridge-local-identity-not-restricted')
        finally:bridge.close()
    except Exception:issues.append('kiosk-connect-bridge-unavailable')
    try:
        public,body=endpoint(cfg)
        result['proxy']={k:body[k] for k in ['uptimeSeconds','memory','upstreamErrors'] if k in body}
        expected=subprocess.check_output(['openssl','x509','-in',str(ROOT/'certificates/current/tls-chain'),'-outform','DER'],stderr=subprocess.DEVNULL)
        if hashlib.sha256(public).digest()!=hashlib.sha256(expected).digest():issues.append('certificate-not-activated')
        text=subprocess.check_output(['openssl','x509','-in',str(ROOT/'certificates/current/tls-chain'),'-enddate','-noout'],text=True)
        expiry=datetime.datetime.strptime(text.strip().split('=',1)[1],'%b %d %H:%M:%S %Y %Z').replace(tzinfo=datetime.timezone.utc).timestamp()
        result['certificateDaysRemaining']=round((expiry-now)/86400,2)
        if expiry-now<21*86400:issues.append('certificate-expiring-within-21-days')
    except ssl.SSLCertVerificationError:issues.append('https-certificate-validation-failed')
    except Exception:issues.append('https-health-or-certificate-failed')
    receipt=ACME/'run-status.json'
    try:
        renewal=json.loads(receipt.read_text());result['renewal']=renewal
        if not renewal.get('success'):issues.append('renewal-last-run-failed')
        if now-renewal['checkedAt']>36*3600:issues.append('renewal-check-overdue')
    except Exception:issues.append('renewal-status-unavailable')
    # Cloud availability is distinct from local health; do not restart a healthy
    # local proxy just because an external service or DNS is unavailable.
    try:
        request=urllib.request.Request('https://pf1007l-desk-dashboard.pages.dev/',method='HEAD',headers={'User-Agent':'Mozilla/5.0 PF1007L-monitor'})
        with urllib.request.urlopen(request,timeout=8) as response:
            if response.status!=200:issues.append('cloud-dashboard-unavailable')
    except Exception:issues.append('cloud-dashboard-unavailable')
    return result


def recover_local(result, previous, cfg):
    now=result['checkedAt'];issues=result['issues']
    status=subprocess.check_output(['systemctl','show','pf1007l-proxy-https.service','-p','ActiveState','--value'],text=True).strip()
    transport_failed='https-health-or-certificate-failed' in issues and status=='active'
    crashed=status=='failed'
    count=previous.get('consecutiveLocalFailures',0)+1 if transport_failed or crashed else 0
    result['consecutiveLocalFailures']=count
    result['lastRecoveryAt']=previous.get('lastRecoveryAt',0)
    if 'tls-firewall-table-missing' in issues:
        subprocess.run(['systemctl','stop','pf1007l-proxy-https.service'],check=False)
        result['failClosedGuardStop']=True
    elif count>=3 and now-result['lastRecoveryAt']>=1800 and not any('firewall' in issue for issue in issues):
        # Respect intentional stops and never attempt to fix Cloudflare/DNS/CA
        # failures by restarting unrelated services or falling back to HTTP.
        result['lastRecoveryAt']=now
        if crashed:
            subprocess.run(['systemctl','reset-failed','pf1007l-proxy-https.service'],check=False)
        attempt=subprocess.run(['systemctl','restart','pf1007l-proxy-https.service'],check=False)
        result['automaticRecoveryAttempted']=True
        if attempt.returncode==0:
            for _ in range(20):
                try:
                    endpoint(cfg);result['automaticRecoveryTransportRestored']=True;break
                except Exception:time.sleep(.5)
    return result


def main():
    os.umask(0o077)
    cfg=profile()
    path=ROOT/'monitor-status.json'
    try:previous=json.loads(path.read_text())
    except (OSError,ValueError):previous={}
    result=recover_local(evaluate(cfg),previous,cfg)
    temporary=path.with_suffix('.new');temporary.write_text(json.dumps(result,indent=2));temporary.chmod(0o600);temporary.replace(path)
    issues=result['issues']
    if issues:
        # Local durable alert, deliberately no external messaging integration.
        alert=ROOT/'last-alert.json';alert.write_text(json.dumps({'at':result['checkedAt'],'issues':issues},indent=2));alert.chmod(0o600)
        print('PF1007L_TLS_ALERT '+','.join(issues),file=sys.stderr)
        return 1
    print('PF1007L_TLS_HEALTHY daysRemaining='+str(result['certificateDaysRemaining']))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
