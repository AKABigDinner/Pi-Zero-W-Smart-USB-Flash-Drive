// MONOX_DURATION_TOTAL_HOURS_V1: durations are not 24-hour clocks.
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


const assert = require('node:assert/strict');
for (const [value,expected] of [[148817,'41:20:17'],[0,'00:00:00'],[86399,'23:59:59'],[86400,'24:00:00'],['90061','25:01:01'],[360000,'100:00:00'],[-1,'--:--:--'],['bad','--:--:--'],[null,'--:--:--'],['','--:--:--']]) assert.equal(monoXDuration(value),expected);
console.log('10 total-hours duration cases passed');
