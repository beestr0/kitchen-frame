package com.huntsyea.frame;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import javax.net.ssl.HttpsURLConnection;
import org.json.JSONObject;

/** Fixed-audience native HTTPS. Never changes trust, hostname verification or system DNS. */
public final class DeviceTransport {
  public static final class Response {
    public final JSONObject body;
    public final String cookie;
    public final String cipher;
    Response(JSONObject body, String cookie, String cipher) { this.body=body; this.cookie=cookie; this.cipher=cipher; }
  }
  public static Response post(String route, JSONObject body) throws Exception {
    if (!route.equals("device/challenge") && !route.equals("device/prove")) throw new SecurityException("Route rejected");
    return request(DevicePolicy.PREFIX + route, body);
  }
  public static Response health() throws Exception { return request("/__proxy_health", null); }
  private static Response request(String path, JSONObject value) throws Exception {
    URL url = new URL(DevicePolicy.ORIGIN + path);
    Proxy proxy = new Proxy(Proxy.Type.HTTP, new InetSocketAddress("10.157.1.115", 8790));
    HttpsURLConnection connection = (HttpsURLConnection) url.openConnection(proxy);
    try {
    connection.setInstanceFollowRedirects(false);
    connection.setConnectTimeout(8000); connection.setReadTimeout(8000);
    connection.setRequestProperty("Origin", DevicePolicy.ORIGIN);
    if (value != null) {
      byte[] data = value.toString().getBytes(StandardCharsets.UTF_8);
      if (data.length > 2048) throw new SecurityException("Request too large");
      connection.setRequestMethod("POST"); connection.setDoOutput(true);
      connection.setRequestProperty("Content-Type", "application/json");
      connection.setFixedLengthStreamingMode(data.length);
      try (java.io.OutputStream output = connection.getOutputStream()) { output.write(data); }
    }
      if (connection.getResponseCode() != 200) throw new SecurityException("Device authorization unavailable");
      String cookie = null;
      for (Map.Entry<String,List<String>> entry : connection.getHeaderFields().entrySet()) {
        if (entry.getKey() != null && entry.getKey().equalsIgnoreCase("Set-Cookie")) {
          for (String candidate : entry.getValue()) {
            if (candidate.matches("pf1007l-device=[a-f0-9]{64}; Path=/__reminders-demo/; Secure; HttpOnly; SameSite=Strict; Max-Age=900")) cookie=candidate;
          }
        }
      }
      ByteArrayOutputStream bytes = new ByteArrayOutputStream();
      try (InputStream input = connection.getInputStream()) {
        byte[] buffer = new byte[1024]; int count;
        while ((count=input.read(buffer)) != -1) { bytes.write(buffer,0,count); if(bytes.size()>16384) throw new SecurityException("Response too large"); }
      }
      return new Response(new JSONObject(new String(bytes.toByteArray(),StandardCharsets.UTF_8)), cookie, connection.getCipherSuite());
    } finally { connection.disconnect(); }
  }
}
