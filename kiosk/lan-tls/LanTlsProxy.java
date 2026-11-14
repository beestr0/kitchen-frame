package com.huntsyea.frame;

import android.app.Activity;
import android.util.Log;
import androidx.webkit.ProxyConfig;
import androidx.webkit.ProxyController;
import androidx.webkit.WebViewFeature;

/** Single-host per-process CONNECT proxy; never changes Android/network CA settings. */
final class LanTlsProxy {
  static void install(Activity activity, Runnable ready) {
    if (!WebViewFeature.isFeatureSupported(WebViewFeature.PROXY_OVERRIDE)
        || !WebViewFeature.isFeatureSupported(WebViewFeature.PROXY_OVERRIDE_REVERSE_BYPASS)) {
      Log.e("FrameKiosk", "Required app-only proxy feature unavailable; no security override applied");
      ready.run();
      return;
    }
    ProxyConfig config = new ProxyConfig.Builder()
        .addProxyRule("http://10.157.1.115:8790", ProxyConfig.MATCH_HTTPS)
        .addBypassRule("beestr0.duckdns.org")
        .setReverseBypassEnabled(true)
        .build();
    ProxyController.getInstance().setProxyOverride(config,
        command -> activity.runOnUiThread(command), () -> {
          Log.i("FrameKiosk", "Single-host application proxy ready; normal TLS verification retained");
          ready.run();
        });
  }
}
