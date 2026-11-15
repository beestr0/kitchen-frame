package com.huntsyea.frame;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.Calendar;

/** Small native first-paint/error overlay: no images, network assets or animation loop. */
final class HiveStartup extends FrameLayout {
  private final TextView status;
  private final LinearLayout actions;
  private final int foreground;
  HiveStartup(Context context, String preference, Runnable retry, Runnable settings) {
    super(context);
    int hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
    boolean dark = "dark".equals(preference) || (!"light".equals(preference) && (hour < 7 || hour >= 19));
    foreground = Color.rgb(dark ? 238 : 28, dark ? 239 : 30, dark ? 242 : 34);
    setBackgroundColor(dark ? Color.rgb(20,21,24) : Color.rgb(247,247,249));
    LinearLayout center = new LinearLayout(context); center.setOrientation(LinearLayout.VERTICAL);center.setGravity(Gravity.CENTER);
    FrameLayout.LayoutParams layout = new FrameLayout.LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.MATCH_PARENT);
    addView(center,layout);
    View mark = new View(context) {
      final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
      @Override protected void onDraw(Canvas canvas) {
        canvas.save();canvas.scale(getWidth()/80f,getHeight()/80f);
        paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.6f);paint.setColor(foreground);
        paint.setStrokeCap(Paint.Cap.ROUND);paint.setStrokeJoin(Paint.Join.ROUND);
        // Original fine-line bee: paired wings, striped abdomen and antennae.
        Path path = new Path();
        path.moveTo(37,37);path.cubicTo(9,35,12,8,27,17);path.cubicTo(36,22,36,31,37,37);
        path.moveTo(43,37);path.cubicTo(71,35,68,8,53,17);path.cubicTo(44,22,44,31,43,37);
        path.moveTo(31,43);path.cubicTo(28,59,34,66,40,71);path.cubicTo(46,66,52,59,49,43);
        path.moveTo(31,50);path.quadTo(40,54,49,50);
        path.moveTo(32,58);path.quadTo(40,62,48,58);
        path.moveTo(35,28);path.quadTo(30,20,26,22);
        path.moveTo(45,28);path.quadTo(50,20,54,22);
        path.moveTo(31,46);path.lineTo(24,51);path.lineTo(22,57);
        path.moveTo(49,46);path.lineTo(56,51);path.lineTo(58,57);
        canvas.drawPath(path,paint);
        canvas.drawOval(31,27,49,45,paint);
        canvas.restore();
      }
    };
    center.addView(mark,new LinearLayout.LayoutParams(80,80));
    TextView name = text(context,"HiveOS",34);name.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));name.setPadding(0,14,0,0);center.addView(name);
    TextView subtitle=text(context,"get shit done.",18);subtitle.setPadding(0,8,0,0);center.addView(subtitle);
    status=text(context,"Connecting securely…",15);status.setPadding(32,24,32,12);center.addView(status);
    actions=new LinearLayout(context);actions.setGravity(Gravity.CENTER);
    Button again=new Button(context);again.setText("Retry");again.setOnClickListener(v->retry.run());actions.addView(again);
    Button options=new Button(context);options.setText("Android settings");options.setOnClickListener(v->settings.run());actions.addView(options);
    actions.setVisibility(GONE);center.addView(actions);
    setClickable(true);
  }
  private TextView text(Context context,String value,int size){TextView t=new TextView(context);t.setText(value);t.setTextColor(foreground);t.setTextSize(size);t.setGravity(Gravity.CENTER);return t;}
  void problem(String message) { animate().cancel();setAlpha(1f);setVisibility(VISIBLE);status.setText(message);actions.setVisibility(VISIBLE); }
  void ready() { if(getVisibility()==VISIBLE)animate().alpha(0f).setDuration(160).withEndAction(()->setVisibility(GONE)).start(); }
}
