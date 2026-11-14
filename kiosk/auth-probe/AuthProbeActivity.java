package com.huntsyea.frame;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import android.util.Base64;
import java.io.File;
import java.io.FileOutputStream;
import java.security.KeyFactory;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** Separate application UID and key alias; never enrolls or updates the working kiosk. */
public final class AuthProbeActivity extends Activity {
  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    TextView view=new TextView(this);view.setText("Disposable Keystore/TLS check. Working kiosk is unchanged.");setContentView(view);
    // Initialize only this disposable UID's WebView, without loading any page.
    if (getIntent().getBooleanExtra("checkWebView",false)) new android.webkit.WebView(this).destroy();
    new Thread(() -> {
      JSONObject result=new JSONObject();
      try {
        DeviceKey key=new DeviceKey("pf1007l-disposable-auth-probe");
        String identifier=key.identifier(), challenge="11111111111111111111111111111111";
        String nonce="2222222222222222222222222222222222222222222222222222222222222222";
        String proof=key.signSession(DevicePolicy.ORIGIN,identifier,challenge,nonce);
        String message="PF1007L-DEVICE-V1\n"+DevicePolicy.ORIGIN+"\nsession\n"+identifier+"\n"+challenge+"\n"+nonce;
        Signature verifier=Signature.getInstance("SHA256withECDSA");
        verifier.initVerify(KeyFactory.getInstance("EC").generatePublic(new X509EncodedKeySpec(Base64.decode(key.publicKey(),Base64.DEFAULT))));
        verifier.update(message.getBytes(StandardCharsets.US_ASCII));
        result.put("signatureVerified",verifier.verify(Base64.decode(proof,Base64.DEFAULT)));
        result.put("publicKey",key.publicKey()); result.put("device",identifier);
        result.put("signature",proof); result.put("message",message);
        result.put("hardwareBacked",key.hardwareBacked()); result.put("sdk",android.os.Build.VERSION.SDK_INT);
        if (getIntent().getBooleanExtra("checkWebView",false)) {
          try {
            Class<?> feature=Class.forName("androidx.webkit.WebViewFeature");
            result.put("webMessageListener",feature.getMethod("isFeatureSupported",String.class).invoke(null,"WEB_MESSAGE_LISTENER"));
          }catch(Exception unavailable){result.put("webMessageListener",false);}
        }
        boolean wrongAudienceDenied=false;
        try {key.signSession("https://unrelated.example",identifier,challenge,nonce);}catch(SecurityException expected){wrongAudienceDenied=true;}
        result.put("wrongAudienceDenied",wrongAudienceDenied);
        try {result.put("nativeTLSValidated",DeviceTransport.health().cipher);}
        catch(Exception unavailable){result.put("nativeTLSValidated",false);result.put("tlsError",unavailable.getClass().getSimpleName());}
      }catch(Exception failure){try{result.put("error",failure.getClass().getSimpleName());}catch(Exception ignored){}}
      runOnUiThread(() -> {
        Runnable persist=() -> {
          try {
            File output=new File(getExternalFilesDir(null),"result.json");
            try(FileOutputStream stream=new FileOutputStream(output)){stream.write(result.toString().getBytes(StandardCharsets.UTF_8));}
          }catch(Exception ignored){}
          finish();
        };
        if(getIntent().getBooleanExtra("checkWebView",false)){
          try {
            Class.forName("com.huntsyea.frame.BrowserBoundaryProbe").getMethod("start",Activity.class,JSONObject.class,Runnable.class).invoke(null,this,result,persist);
          }catch(Exception unavailable){try{result.put("browserBoundaryError",unavailable.getClass().getSimpleName());}catch(Exception ignored){}persist.run();}
        }else persist.run();
      });
    },"disposable-keystore-probe").start();
  }
}
