# UART and USB recovery journey

This account separates observations from hypotheses. It summarizes development on one original Photon Mono X.

The starting printer showed **main firmware V3.5.4 and UI_V1.2**. The original Wi-Fi module was removed, with a three-wire route through the center of the chassis, out an existing bottom hole and toward the rear. See [the firmware and hardware guide](FIRMWARE_AND_HARDWARE.md) before treating this as a reproducible modification.

1. Static analysis identified ARM Thumb code in the main STM32 firmware and traced the boot discovery, UART baud configuration and runtime retry state machine. FPGA files were left unchanged.
2. A first experimental startup replacement bypassed the bounded discovery routine. Wi-Fi communication could work, but USB failed the Pi-only reboot recovery comparison. The precise cause was not proven.
3. A fair baseline was established using the original firmware with Wi-Fi active. USB recovered after a Pi-only reboot and files returned.
4. Retry v2 restored the original startup sequence and changed seven bytes at three instruction sites. Both probe phases use 460800 and exhausted discovery enables the stock runtime retry path. This does not prove a physical module was detected and does not guarantee every future failure can recover.
5. Synthetic control-flow tests covered immediate, absent, second-phase and delayed peers. UART setup/transmit and timing were mocked; these were not USB or full hardware simulations.
6. Hardware observations reported USB configured/files visible after a Pi-only reboot on v2, and successful delayed connection after waiting at least 60 seconds. Full-print pause/resume/completion validation remains pending.
7. During a subsequent real print, webpage status and the camera were observed live. A 24-hour time-display error was traced to JavaScript clock formatting and corrected separately, without rebooting the Pi or changing printer firmware.

Main original SHA256: `86496c6500a29775bd46347b9ae3072c16efdccd219f5c57a2722cc43dd554c1`.
Retry v2 SHA256: `647712723c46af7e77aca4a08c9eae6826795ecc72fdd358c7d38315d230f3c6`; size 303492 bytes.

No firmware binary is added here. Current live bridge configuration and scripts must be captured, sanitized and compared before a reproducible bridge installer is claimed. Historical development copies are not assumed to equal the deployed service.
