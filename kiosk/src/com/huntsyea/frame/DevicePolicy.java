package com.huntsyea.frame;

import java.net.URI;

/** Pure URL policy, also exercised on the host JVM. No caller-controlled audience. */
public final class DevicePolicy {
  public static final String ORIGIN = "https://beestr0.duckdns.org:8789";
  public static final String PREFIX = "/__reminders-demo/";
  public static boolean trustedOrigin(String value) {
    if (!trustedResource(value)) return false;
    try {
      URI uri = new URI(value);
      return (uri.getPath().isEmpty() || "/".equals(uri.getPath())) && uri.getRawQuery() == null && uri.getRawFragment() == null;
    } catch (Exception rejected) { return false; }
  }
  public static boolean trustedResource(String value) {
    try {
      URI uri = new URI(value);
      if (!"https".equalsIgnoreCase(uri.getScheme()) || !"beestr0.duckdns.org".equalsIgnoreCase(uri.getHost())
          || uri.getPort() != 8789 || uri.getRawUserInfo() != null || uri.getPath() == null) return false;
      String path = uri.getPath();
      if (path.contains("\\")) return false;
      for (int i = 0; i < path.length(); i++) if (path.charAt(i) < 32) return false;
      for (String segment : path.split("/")) if (segment.equals(".") || segment.equals("..")) return false;
      return true;
    } catch (Exception rejected) { return false; }
  }
  public static boolean trustedPage(String value) {
    if (!trustedResource(value)) return false;
    try {
      URI uri = new URI(value);
      return uri.getPath().startsWith(PREFIX) && uri.getRawQuery() == null && uri.getRawFragment() == null;
    } catch (Exception rejected) { return false; }
  }
}
