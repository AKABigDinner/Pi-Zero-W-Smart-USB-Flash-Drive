"""Read-only Mono X camera monitor. Requires Python 3 + Pillow."""
from __future__ import annotations
import argparse
import io
import json
import logging
import queue
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULTS = dict(host='3dprinter.local', camera_port=8080, status_interval=5,
                geometry='720x405', always_on_top=True, overlay_opacity=155)


def duration(value):
    try:
        seconds = max(0, int(float(value)))
        return f'{seconds // 3600}:{seconds % 3600 // 60:02}:{seconds % 60:02}'
    except (ValueError, TypeError, OverflowError):
        return '--:--:--'


def progress(value):
    try:
        return max(0, min(100, float(str(value).strip().rstrip('%'))))
    except (ValueError, TypeError):
        return None


def request(url, timeout=8):
    # Local LAN traffic goes directly to the Pi, without system HTTP proxies.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(urllib.request.Request(url, headers={'User-Agent': 'MonoX-Desktop-Widget/1.0'}), timeout=timeout)


def jpeg_frames(response, stopped):
    """Incremental MJPEG reader with bounded buffering, independent of boundary names."""
    buffer = bytearray()
    read = getattr(response, 'read1', response.read)
    while not stopped.is_set():
        chunk = read(16384)
        if not chunk:
            raise ConnectionError('Camera stream ended')
        buffer.extend(chunk)
        while True:
            start = buffer.find(b'\xff\xd8')
            if start < 0:
                buffer[:] = buffer[-1:]
                break
            if start:
                del buffer[:start]
            end = buffer.find(b'\xff\xd9', 2)
            if end < 0:
                break
            yield bytes(buffer[:end + 2])
            del buffer[:end + 2]
        if len(buffer) > 12 * 1024 * 1024:
            raise ValueError('Camera frame exceeds buffer limit')


class Monitor:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.stop = threading.Event()
        self.frames, self.status_updates = queue.Queue(maxsize=1), queue.Queue(maxsize=1)
        self.frame = None
        self.status = {}
        self.last_frame = self.last_status = 0
        self.camera_message = 'Connecting to camera...'
        self.status_error = ''
        self.overlay = True
        self.compact = False
        self.dirty = True
        self.photo = None
        self.drag_start = None
        self.topmost = tk.BooleanVar(value=config['always_on_top'])
        root.title('Mono-X Camera Widget')
        root.configure(bg='#10151b')
        try:
            root.geometry(config['geometry'])
        except tk.TclError:
            root.geometry('720x405')
        root.minsize(360, 220)
        root.attributes('-topmost', self.topmost.get())
        self.canvas = tk.Canvas(root, bg='#10151b', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor='nw')
        self.canvas.bind('<Configure>', lambda event: self.mark_dirty())
        self.canvas.bind('<Button-3>', self.menu)
        self.canvas.bind('<Double-Button-1>', lambda event: self.toggle_compact())
        self.canvas.bind('<Button-1>', self.begin_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        root.bind('<Escape>', lambda event: self.normal_window())
        root.bind('<Control-o>', lambda event: self.toggle_overlay())
        root.bind('<Control-t>', lambda event: self.toggle_topmost())
        root.protocol('WM_DELETE_WINDOW', self.close)
        threading.Thread(target=self.camera_worker, daemon=True).start()
        threading.Thread(target=self.status_worker, daemon=True).start()
        root.after(50, self.tick)

    @staticmethod
    def latest(channel, item):
        try:
            channel.get_nowait()
        except queue.Empty:
            pass
        try:
            channel.put_nowait(item)
        except queue.Full:
            pass

    def camera_worker(self):
        url = f"http://{self.config['host']}:{self.config['camera_port']}/?action=stream"
        while not self.stop.is_set():
            try:
                with request(url) as response:
                    last_decode = 0
                    for blob in jpeg_frames(response, self.stop):
                        now = time.monotonic()
                        if now - last_decode < .10:  # at most 10 rendered FPS
                            continue
                        with Image.open(io.BytesIO(blob)) as im:
                            frame = im.convert('RGB')
                        self.latest(self.frames, (frame, now, ''))
                        last_decode = now
                if self.stop.is_set():
                    return
            except Exception as exc:
                logging.warning('Camera: %s', exc)
                self.latest(self.frames, (None, 0, 'Camera offline — reconnecting'))
                self.stop.wait(3)

    def status_worker(self):
        url = f"http://{self.config['host']}/includes/util_anycubic.php?a=printer_status"
        while not self.stop.is_set():
            try:
                with request(url) as response:
                    data = json.loads(response.read(1024 * 1024))
                if not isinstance(data, dict) or 'printer_status' not in data:
                    raise ValueError('Unexpected printer status response')
                self.latest(self.status_updates, (data, time.monotonic(), ''))
            except Exception as exc:
                logging.warning('Status: %s', exc)
                self.latest(self.status_updates, (None, 0, 'Status unavailable — retrying'))
            self.stop.wait(max(2.5, self.config['status_interval']))

    def mark_dirty(self):
        self.dirty = True

    def tick(self):
        if self.stop.is_set():
            return
        try:
            frame, stamp, message = self.frames.get_nowait()
            if frame is not None:
                self.frame, self.last_frame = frame, stamp
            self.camera_message = message
            self.dirty = True
        except queue.Empty:
            pass
        try:
            data, stamp, error = self.status_updates.get_nowait()
            if data is not None:
                # Paused API replies may omit job fields. Retain the last known
                # details only while paused, and label them instead of resetting.
                if data.get('printer_status') == 'Paused':
                    prior = self.status.copy()
                    prior.update({k: v for k, v in data.items() if v not in ('', None)})
                    data = prior
                self.status, self.last_status = data, stamp
            self.status_error = error
            self.dirty = True
        except queue.Empty:
            pass
        now = time.monotonic()
        if int(now) != getattr(self, 'last_tick_second', 0):
            self.dirty = True
            self.last_tick_second = int(now)
        if self.dirty:
            self.render()
            self.dirty = False
        self.root.after(100, self.tick)

    @staticmethod
    def font(size, bold=False):
        name = 'segoeuib.ttf' if bold else 'segoeui.ttf'
        try:
            return ImageFont.truetype('C:/Windows/Fonts/' + name, size)
        except OSError:
            return ImageFont.load_default()

    def render(self):
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        if w < 10 or h < 10:
            return
        base = Image.new('RGBA', (w, h), '#10151b')
        if self.frame is not None:
            video = ImageOps.contain(self.frame, (w, h), Image.Resampling.BILINEAR)
            base.paste(video, ((w-video.width)//2, (h-video.height)//2))
        else:
            ImageDraw.Draw(base).text((20, h//2), self.camera_message, font=self.font(18), fill='white')
        layer = Image.new('RGBA', base.size)
        d = ImageDraw.Draw(layer)
        if self.overlay:
            scale = min(1.0, max(.72, (h-20)/300))
            pad = int(10*scale)
            small, regular, title = self.font(int(11*scale)), self.font(int(13*scale)), self.font(int(15*scale), True)
            pw = min(w-20, int(182*scale))
            x, y = 10, 10
            panel_h = int(292*scale)
            d.rounded_rectangle((x,y,x+pw,y+panel_h), radius=9, fill=(8,15,23,int(self.config['overlay_opacity'])))
            state = str(self.status.get('printer_status') or 'Connecting...')
            stale = bool(self.status_error) or (self.last_status and time.monotonic()-self.last_status > 15)
            color = '#ffc665' if stale or state.lower() == 'paused' else '#9cdf70'
            d.text((x+pad,y+pad), 'MONO X', font=title, fill='white')
            label = 'STATUS OFFLINE' if stale else state.upper()
            d.text((x+pad,y+int(31*scale)), label, font=small, fill=color)
            job = str(self.status.get('print_job_name') or 'No active filename')
            while d.textlength(job, font=regular) > pw-2*pad and len(job)>5:
                job = job[:-5] + '…'
            d.text((x+pad,y+int(52*scale)), job, font=regular, fill='white')
            value = progress(self.status.get('percent_complete'))
            text = f'{value:g}%' if value is not None else '--%'
            by = y+int(77*scale)
            d.text((x+pad,by), text, font=title, fill=color)
            bx = x+pad
            bar_y = by+int(25*scale)
            d.rounded_rectangle((bx,bar_y,x+pw-pad,bar_y+5), radius=2, fill=(255,255,255,45))
            if value:
                d.rounded_rectangle((bx,bar_y,bx+(pw-2*pad)*value/100,bar_y+5), radius=2, fill=color)
            values = [('Layers', self.status.get('layers_complete') or '—'),
                      ('Remaining', duration(self.status.get('seconds_remaining'))),
                      ('Resin', self.status.get('resin_required') or '—')]
            for i,(key,val) in enumerate(values):
                yy = y+int((121+48*i)*scale)
                d.text((x+pad,yy),key,font=small,fill='#c4d1de')
                d.text((x+pad,yy+int(16*scale)),str(val),font=regular,fill='white')
            age = int(time.monotonic()-self.last_status) if self.last_status else None
            footer = f'Updated {age}s ago' if age is not None else 'Waiting for status'
            if stale:
                footer = f'Offline · last seen {age}s ago' if age is not None else 'Status offline · retrying'
            d.text((x+pad,y+int(269*scale)),footer,font=small,fill='#ffc665' if stale else '#b7c7d7')
        if self.frame is not None and (self.camera_message or time.monotonic()-self.last_frame > 10):
            d.rectangle((0,h-30,w,h),fill=(20,15,10,210))
            d.text((12,h-25),'Camera offline · showing last frame · reconnecting',font=self.font(13),fill='#ffc665')
        self.photo = ImageTk.PhotoImage(Image.alpha_composite(base, layer).convert('RGB'))
        self.canvas.itemconfigure(self.image_item, image=self.photo)

    def toggle_topmost(self):
        self.topmost.set(not self.topmost.get())
        self.root.attributes('-topmost', self.topmost.get())

    def toggle_overlay(self):
        self.overlay = not self.overlay
        self.mark_dirty()

    def toggle_compact(self):
        self.compact = not self.compact
        self.root.overrideredirect(self.compact)

    def normal_window(self):
        self.compact = False
        self.root.overrideredirect(False)

    def begin_drag(self, event):
        self.drag_start = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def drag(self, event):
        if self.compact and self.drag_start:
            x,y,rx,ry = self.drag_start
            self.root.geometry(f'+{rx+event.x_root-x}+{ry+event.y_root-y}')

    def menu(self, event):
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_checkbutton(label='Always on top', variable=self.topmost,
                             command=lambda: self.root.attributes('-topmost',self.topmost.get()))
        menu.add_command(label='Hide status' if self.overlay else 'Show status',command=self.toggle_overlay)
        menu.add_command(label='Normal window' if self.compact else 'Borderless widget',command=self.toggle_compact)
        menu.add_separator()
        menu.add_command(label='Open printer webpage',command=lambda: webbrowser.open(f"http://{self.config['host']}/anycubic_mono.php"))
        menu.add_command(label='Close',command=self.close)
        try:
            menu.tk_popup(event.x_root,event.y_root)
        finally:
            menu.grab_release()

    def close(self):
        self.stop.set()
        saved = dict(self.config, geometry=self.root.geometry(), always_on_top=self.topmost.get())
        try:
            (HERE/'settings.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
        except OSError:
            logging.exception('Unable to save window settings')
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host')
    args = parser.parse_args()
    config = DEFAULTS.copy()
    try:
        config.update(json.loads((HERE/'settings.json').read_text(encoding='utf-8')))
    except (OSError, ValueError):
        pass
    if args.host:
        config['host'] = args.host
    logging.basicConfig(filename=HERE/'widget.log',level=logging.WARNING,
                        format='%(asctime)s %(message)s')
    root = tk.Tk()
    Monitor(root,config)
    root.mainloop()


if __name__ == '__main__':
    main()
