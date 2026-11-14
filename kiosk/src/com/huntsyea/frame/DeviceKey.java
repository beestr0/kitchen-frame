package com.huntsyea.frame;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyInfo;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.spec.ECGenParameterSpec;

/** Device-private signing handle. Only the public SPKI is exportable by this API. */
public final class DeviceKey {
  private final String alias;
  public DeviceKey(String alias) { this.alias = alias; }
  private synchronized KeyStore store() throws Exception {
    KeyStore store = KeyStore.getInstance("AndroidKeyStore");
    store.load(null);
    if (!store.containsAlias(alias)) {
      KeyPairGenerator generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore");
      generator.initialize(new KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
          .setAlgorithmParameterSpec(new ECGenParameterSpec("secp256r1"))
          .setDigests(KeyProperties.DIGEST_SHA256)
          .setUserAuthenticationRequired(false).build());
      generator.generateKeyPair();
    }
    return store;
  }
  public String publicKey() throws Exception {
    return Base64.encodeToString(store().getCertificate(alias).getPublicKey().getEncoded(), Base64.NO_WRAP);
  }
  public String identifier() throws Exception {
    byte[] digest = MessageDigest.getInstance("SHA-256").digest(store().getCertificate(alias).getPublicKey().getEncoded());
    StringBuilder text = new StringBuilder();
    for (byte value : digest) text.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
    return text.toString();
  }
  public boolean hardwareBacked() throws Exception {
    PrivateKey key = (PrivateKey) store().getKey(alias, null);
    KeyInfo info = KeyFactory.getInstance(key.getAlgorithm(), "AndroidKeyStore").getKeySpec(key, KeyInfo.class);
    return info.isInsideSecureHardware();
  }
  public String signSession(String origin, String device, String challenge, String nonce) throws Exception {
    if (!DevicePolicy.ORIGIN.equals(origin) || !identifier().equals(device)
        || !challenge.matches("[a-f0-9]{32}") || !nonce.matches("[a-f0-9]{64}")) {
      throw new SecurityException("Rejected device proof scope");
    }
    String message = "PF1007L-DEVICE-V1\n" + origin + "\nsession\n" + device + "\n" + challenge + "\n" + nonce;
    Signature signature = Signature.getInstance("SHA256withECDSA");
    signature.initSign((PrivateKey) store().getKey(alias, null));
    signature.update(message.getBytes(StandardCharsets.US_ASCII));
    return Base64.encodeToString(signature.sign(), Base64.NO_WRAP);
  }
}
