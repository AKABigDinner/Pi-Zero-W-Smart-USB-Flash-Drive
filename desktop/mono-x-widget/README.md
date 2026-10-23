# Windows camera/status widget

Install Python 3 with Tk support, then `py -m pip install Pillow`. Launch `Start_MonoX_Widget.cmd`, or run `py mono_x_widget.py --host YOUR_PI_HOST`.

Default host is 3dprinter.local. The window shows MJPEG camera video with a small vertical translucent status panel. Right-click for always-on-top and borderless mode. Double-click toggles borderless mode; Escape restores the normal window. Ctrl+O toggles status and Ctrl+T toggles always-on-top. Window geometry is saved on close. Close before editing settings.json.

The widget reads the existing HTTP status endpoint every five seconds and the port-8080 MJPEG feed. It sends no printer controls. Stale status and camera frames are labeled; connections retry automatically. Remaining time preserves hours beyond 24. Resin is the job estimate, not measured vat contents. This is a source release, not a standalone EXE.
