#!/data/data/com.termux/files/usr/bin/bash
if ! pgrep -x crond >/dev/null; then
  crond
  echo "$(date) crond restarted" >> ~/OptimusAI_V41_LIVE/output/crond_watchdog.log
fi
if ! pgrep -f "bale_listener" >/dev/null; then
  cd ~/OptimusAI_V41_LIVE
  nohup python3.14 bale_listener.py >> output/bale_listener.log 2>&1 &
  echo "$(date) listener restarted" >> ~/OptimusAI_V41_LIVE/output/crond_watchdog.log
fi
