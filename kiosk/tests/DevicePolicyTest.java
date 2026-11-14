package com.huntsyea.frame;

public final class DevicePolicyTest {
  public static void main(String[] args) {
    String origin=DevicePolicy.ORIGIN;
    String[] denied={"http://beestr0.duckdns.org:8789/__reminders-demo/", "https://beestr0.duckdns.org/__reminders-demo/",
      "https://beestr0.duckdns.org:8790/__reminders-demo/", "https://unrelated.example:8789/__reminders-demo/",
      "https://user@beestr0.duckdns.org:8789/__reminders-demo/", origin+"/", origin+"/__reminders-demo/../api/",
      origin+"/__reminders-demo/%2e%2e/api/", origin+"/__reminders-demo/?key=value", origin+"/__reminders-demo/#fragment",
      origin+"/__reminders-demo/%00", "file:///__reminders-demo/", "javascript:alert(1)",null};
    for(String value:denied) if(DevicePolicy.trustedPage(value))throw new AssertionError("Unexpected trusted page");
    if(!DevicePolicy.trustedPage(origin+"/__reminders-demo/"))throw new AssertionError("Trusted demo rejected");
    if(!DevicePolicy.trustedResource(origin+"/api/weather"))throw new AssertionError("Same-origin weather rejected");
    if(DevicePolicy.trustedResource("content://example/"))throw new AssertionError("Content URL allowed");
    if(!DevicePolicy.trustedOrigin(origin) || !DevicePolicy.trustedOrigin(origin+"/"))throw new AssertionError("Origin rejected");
    if(DevicePolicy.trustedOrigin(origin+"/__reminders-demo/"))throw new AssertionError("Origin path allowed");
    if(DevicePolicy.trustedOrigin(origin+"/?other"))throw new AssertionError("Origin query allowed");
    System.out.println("PASS native URL policy: "+(denied.length+7)+" cases");
  }
}
