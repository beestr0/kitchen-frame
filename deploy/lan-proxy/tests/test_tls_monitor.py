import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tls'))
import monitor

class RecoveryPolicyTests(unittest.TestCase):
    def exercise(self,issues,status='active',previous=None):
        value={'checkedAt':10000,'issues':issues}
        with patch.object(monitor.subprocess,'check_output',return_value=status),patch.object(monitor.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run,patch.object(monitor,'endpoint',return_value=(b'public',{})):
            result=monitor.recover_local(value,previous or {},{})
            return result,[c.args[0] for c in run.call_args_list]
    def test_cloud_outage_does_not_restart_any_service(self):
        result,calls=self.exercise(['cloud-dashboard-unavailable'],previous={'consecutiveLocalFailures':2})
        self.assertEqual(calls,[]);self.assertEqual(result['consecutiveLocalFailures'],0)
    def test_intentional_stop_is_respected(self):
        _,calls=self.exercise(['unit-inactive:pf1007l-proxy-https.service'],'inactive',{'consecutiveLocalFailures':5})
        self.assertEqual(calls,[])
    def test_certificate_failure_does_not_trigger_blind_restart(self):
        _,calls=self.exercise(['https-certificate-validation-failed'],previous={'consecutiveLocalFailures':3})
        self.assertEqual(calls,[])
    def test_hung_proxy_restarts_only_own_unit_after_three_failures(self):
        result,calls=self.exercise(['https-health-or-certificate-failed'],previous={'consecutiveLocalFailures':2})
        self.assertEqual(calls,[['systemctl','restart','pf1007l-proxy-https.service']]);self.assertTrue(result['automaticRecoveryTransportRestored'])
    def test_missing_guard_stops_only_https_fail_closed(self):
        _,calls=self.exercise(['tls-firewall-table-missing'],previous={'consecutiveLocalFailures':5})
        self.assertEqual(calls,[['systemctl','stop','pf1007l-proxy-https.service']])
    def test_recovery_is_rate_limited(self):
        _,calls=self.exercise(['https-health-or-certificate-failed'],previous={'consecutiveLocalFailures':2,'lastRecoveryAt':9500})
        self.assertEqual(calls,[])

class DiagnosticFilterTests(unittest.TestCase):
    def test_only_literal_pong_crosses_diagnostic_channel(self):
        source=(Path(__file__).resolve().parents[3]/'scripts/pf1007l-lan-proxy.mjs').read_text()
        function=source[source.index('function pongOnly('):source.index("server.on('upgrade',")]
        code=function+'''
const forwarded=[];let closed=false;
const filter=pongOnly(b=>forwarded.push(b.toString('hex')),()=>closed=true);
const frame=t=>Buffer.concat([Buffer.from([129,Buffer.byteLength(t)]),Buffer.from(t)]);
const personal=frame(JSON.stringify({messages:[{title:'invented private fixture'}]}));
const pong=frame('pong');const all=Buffer.concat([personal,pong]);
for(let i=0;i<all.length;i+=3)filter(all.subarray(i,i+3));
console.log(JSON.stringify({forwarded,expected:pong.toString('hex'),closed}));
'''
        result=json.loads(subprocess.check_output(['node','-e',code],text=True))
        self.assertEqual(result['forwarded'],[result['expected']]);self.assertFalse(result['closed'])

if __name__=='__main__':unittest.main()
