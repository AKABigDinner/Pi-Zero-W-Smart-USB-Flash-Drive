"""Patch only the Mono X webpage duration display; no services restarted."""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

OLD = 'new Date(obj.seconds_remaining * 1000).toISOString().substr(11, 8)'
NEW = 'monoXDuration(obj.seconds_remaining)'
MARKER = '        function getPrinterStatus() {'
HELPER = '''        // MONOX_DURATION_TOTAL_HOURS_V1: durations are not 24-hour clocks.
        function monoXDuration(value) {
            if (value === null || value === undefined || String(value).trim() === '') return '--:--:--';
            var seconds = Number(value);
            if (!Number.isFinite(seconds) || seconds < 0) return '--:--:--';
            seconds = Math.floor(seconds);
            var hours = Math.floor(seconds / 3600);
            var minutes = Math.floor((seconds % 3600) / 60);
            var remainder = seconds % 60;
            return String(hours).padStart(2, '0') + ':' +
                   String(minutes).padStart(2, '0') + ':' +
                   String(remainder).padStart(2, '0');
        }

'''


def patched(source):
    if 'MONOX_DURATION_TOTAL_HOURS_V1' in source:
        if OLD in source or source.count(NEW) != 1 or source.count('function monoXDuration(') != 1:
            raise ValueError('Partial or unexpected prior patch; no files changed.')
        return source
    if source.count(OLD) != 1 or source.count(MARKER) != 1:
        raise ValueError('Unexpected webpage version; no files changed.')
    return source.replace(OLD, NEW, 1).replace(MARKER, HELPER + MARKER, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=Path('/home/pi/usb_share/html_root/anycubic_mono.php'))
    parser.add_argument('--check', action='store_true', help='Validate without writing')
    args = parser.parse_args()
    target = args.file.resolve(strict=True)
    original = target.read_bytes()
    source = original.decode('utf-8')
    output = patched(source)
    if output == source:
        print('Total-hours fix is already installed. Nothing changed.')
        return
    if args.check:
        print('Compatible webpage: one formatter replacement and one helper insertion. No files changed.')
        return
    info = target.stat()
    fd, temp_name = tempfile.mkstemp(prefix='.mono-time-', suffix='.php', dir=target.parent)
    temporary = Path(temp_name)
    backup = target.with_name(target.name + '.before-total-hours-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(output.encode('utf-8'))
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temporary, info.st_mode)
        if hasattr(os, 'chown'):
            os.chown(temporary, info.st_uid, info.st_gid)
        php = shutil.which('php')
        if php:
            subprocess.run([php, '-l', str(temporary)], check=True, capture_output=True)
        if target.read_bytes() != original:
            raise RuntimeError('Webpage changed during patch preparation. Nothing installed.')
        shutil.copy2(target, backup)
        if hasattr(os, 'chown'):
            os.chown(backup, info.st_uid, info.st_gid)
        os.replace(temporary, target)
        print('Installed total-hours display fix:', target)
        print('Backup:', backup)
        print('Refresh the webpage. No reboot or service restart is needed.')
        print('Rollback: sudo cp --preserve=all ' + str(backup) + ' ' + str(target))
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    main()
