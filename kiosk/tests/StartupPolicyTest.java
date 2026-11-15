package com.huntsyea.frame;
public final class StartupPolicyTest {
 public static void main(String[] args) {
  long valid=1794700000000L;
  if(StartupPolicy.waiting(null,valid,true)==null)throw new AssertionError("Missing URL must be visible");
  if(StartupPolicy.waiting("https://example.invalid",valid,false)==null)throw new AssertionError("Offline must retry visibly");
  if(StartupPolicy.waiting("https://example.invalid",0,true)==null)throw new AssertionError("Reset clock must wait, never bypass TLS");
  if(StartupPolicy.waiting("https://example.invalid",valid,true)!=null)throw new AssertionError("Ready must load without splash delay");
  System.out.println("PASS HiveOS startup gates: URL, Wi-Fi, reset clock, ready");
 }
}
