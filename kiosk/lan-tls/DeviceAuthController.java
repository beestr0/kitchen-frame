package com.huntsyea.frame;

import android.app.Activity;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import androidx.webkit.WebMessageCompat;
import androidx.webkit.JavaScriptReplyProxy;
import java.util.Collections;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import org.json.JSONObject;

/** Opt-in only. Never signs JS-provided text and never returns secrets/proofs to JS. */
final class DeviceAuthController {
  private static final ExecutorService WORKER = Executors.newSingleThreadExecutor();
  private static final AtomicBoolean ACTIVE = new AtomicBoolean(false);
  private static final DeviceKey KEY = new DeviceKey("pf1007l-device-v1");
  static boolean isSupported() { return WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER); }
  static boolean attach(Activity activity, WebView web) {
    if (!isSupported()) return false;
    web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    web.getSettings().setAllowFileAccess(false);
    web.getSettings().setAllowContentAccess(false);
    WebViewCompat.addWebMessageListener(web, "FrameDeviceAuth", Collections.singleton(DevicePolicy.ORIGIN),
        (view, message, sourceOrigin, isMainFrame, reply) -> {
          if (!isMainFrame || !DevicePolicy.trustedOrigin(sourceOrigin.toString())
              || !DevicePolicy.trustedPage(view.getUrl()) || message.getType() != WebMessageCompat.TYPE_STRING || !"renew".equals(message.getData())) {
            return;
          }
          if (!ACTIVE.compareAndSet(false, true)) return;
          WORKER.execute(() -> {
            try {
              String device = KEY.identifier();
              JSONObject challenge = DeviceTransport.post("device/challenge", new JSONObject().put("device", device)).body;
              String identifier = challenge.getString("id"), nonce = challenge.getString("nonce");
              String audience = challenge.getString("audience");
              String expected = "PF1007L-DEVICE-V1\n" + DevicePolicy.ORIGIN + "\nsession\n" + device + "\n" + identifier + "\n" + nonce;
              if (!device.equals(challenge.getString("device")) || !"session".equals(challenge.getString("purpose"))
                  || !expected.equals(challenge.getString("message"))) throw new SecurityException("Proof scope rejected");
              String signature = KEY.signSession(audience, device, identifier, nonce);
              final String cookie = DeviceTransport.post("device/prove", new JSONObject().put("device", device).put("challenge", identifier).put("signature", signature)).cookie;
              if (cookie == null) throw new SecurityException("Session cookie missing");
              activity.runOnUiThread(() -> {
                if (!DevicePolicy.trustedPage(web.getUrl())) { ACTIVE.set(false); return; }
                CookieManager.getInstance().setCookie(DevicePolicy.ORIGIN + DevicePolicy.PREFIX, cookie, accepted -> {
                  CookieManager.getInstance().flush();
                  ACTIVE.set(false);
                  safeReply(web, reply, accepted ? "ready" : "unavailable");
                });
              });
            } catch (Exception rejected) {
              ACTIVE.set(false);
              activity.runOnUiThread(() -> safeReply(web, reply, "unavailable"));
            }
          });
        });
    return true;
  }
  private static void safeReply(WebView web, JavaScriptReplyProxy reply, String value) {
    try { if (DevicePolicy.trustedPage(web.getUrl())) reply.postMessage(value); }
    catch (RuntimeException navigatedAway) { /* No secrets/logging and no app crash. */ }
  }
}
