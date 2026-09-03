# اجرای Listener سریع بله در Termux

```bash
pkg update
pkg install python clang libxml2 libxslt
pip install pandas numpy openpyxl requests
cd ~/options-report
chmod +x run_termux_listener.sh
export BALE_BOT_TOKEN='توکن ربات'
./run_termux_listener.sh
```

برای روشن‌ماندن پس از خروج از صفحه:

```bash
termux-wake-lock
nohup ./run_termux_listener.sh >> termux_listener.log 2>&1 &
```

پیام «گزارش» گزارش تازه‌ی کل بازار با ۱۵ آپشن برتر را می‌فرستد. نام سهم، مانند «وبملت»، گزارش تازه‌ی همان سهم با ۵ آپشن برتر را می‌فرستد.
