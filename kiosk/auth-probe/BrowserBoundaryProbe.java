package com.huntsyea.frame;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.util.Collections;
import java.util.concurrent.atomic.AtomicBoolean;
import org.json.JSONObject;

/** Invented cookie, separate UID, in-memory pages; never calls an auth/task endpoint. */
public final class BrowserBoundaryProbe {
  public static void start(Activity activity, JSONObject report, Runnable done) {
    WebView web=new WebView(activity);activity.setContentView(web);
    web.getSettings().setJavaScriptEnabled(true);
    AtomicBoolean finished=new AtomicBoolean(false);
    Handler handler=new Handler(Looper.getMainLooper());
    Runnable finish=() -> {
      if(finished.compareAndSet(false,true)){web.destroy();done.run();}
    };
    handler.postDelayed(finish,10000);
    try {
      if(!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER))throw new IllegalStateException();
      final boolean[] wrongOriginPage={false};
      web.setWebViewClient(new WebViewClient(){
        @Override public void onPageFinished(WebView view,String url){
          if(wrongOriginPage[0])web.evaluateJavascript("typeof PF1007LProbe === 'undefined'",value -> {
            put(report,"wrongOriginChannelAbsent","true".equals(value));finish.run();
          });
        }
      });
      WebViewCompat.addWebMessageListener(web,"PF1007LProbe",Collections.singleton(DevicePolicy.ORIGIN),
        (view,message,source,isMainFrame,reply) -> {
          if(!isMainFrame || !DevicePolicy.trustedOrigin(source.toString()))return;
          if("cookie-hidden".equals(message.getData())){
            put(report,"httpOnlyHiddenFromJS",true);reply.postMessage("ready");
          }else if("cookie-visible".equals(message.getData())){
            put(report,"httpOnlyHiddenFromJS",false);finish.run();
          }else if("reply-received".equals(message.getData())){
            put(report,"webMessageRoundTrip",true);
            wrongOriginPage[0]=true;
            web.loadDataWithBaseURL("https://unrelated.invalid/","<body>Origin rejection fixture</body>","text/html","UTF-8",null);
          }
        });
      CookieManager cookies=CookieManager.getInstance();
      cookies.setCookie(DevicePolicy.ORIGIN+DevicePolicy.PREFIX,
        "pf1007l-disposable=fixture; Path=/__reminders-demo/; Secure; HttpOnly; SameSite=Strict",accepted -> {
          put(report,"nativeCookieAccepted",accepted);
          String nativeCookies=cookies.getCookie(DevicePolicy.ORIGIN+DevicePolicy.PREFIX);
          put(report,"nativeCookiePresent",nativeCookies!=null && nativeCookies.contains("pf1007l-disposable=fixture"));
          web.loadDataWithBaseURL(DevicePolicy.ORIGIN+DevicePolicy.PREFIX,
            "<body>Disposable browser boundary fixture<script>PF1007LProbe.onmessage=function(e){if(e.data==='ready')PF1007LProbe.postMessage('reply-received')};PF1007LProbe.postMessage(document.cookie.indexOf('pf1007l-disposable=')<0?'cookie-hidden':'cookie-visible')</script></body>",
            "text/html","UTF-8",null);
        });
    }catch(Exception failure){put(report,"browserBoundaryError",failure.getClass().getSimpleName());finish.run();}
  }
  private static void put(JSONObject report,String name,Object value){try{report.put(name,value);}catch(Exception ignored){}}
}
