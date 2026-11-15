package com.huntsyea.frame;

/** Pure startup gates; never changes Android time, network or TLS policy. */
final class StartupPolicy {
  static final long MIN_CLOCK_MS = 1672531200000L; // 2023-01-01; catches this frame's reset clock.
  static String waiting(String url, long now, boolean connected) {
    if (url == null) return "Dashboard address needs setup.";
    if (!connected) return "Waiting for Wi-Fi. Retrying automatically…";
    if (now < MIN_CLOCK_MS) return "Waiting for date and time to synchronize. Retrying securely…";
    return null;
  }
}
