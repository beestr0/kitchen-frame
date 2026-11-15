package com.huntsyea.frame;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Starts only our activity after boot; does not register or replace Android HOME. */
public final class BootReceiver extends BroadcastReceiver {
  @Override public void onReceive(Context context, Intent intent) {
    if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction()) ||
        !context.getSharedPreferences("kiosk",Context.MODE_PRIVATE).getBoolean("autostart",true)) return;
    context.startActivity(new Intent(context,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP));
  }
}
