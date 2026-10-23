# Validation matrix

| Check | Evidence | Status |
|---|---|---|
| Original firmware USB recovery, Wi-Fi active | User-observed UDC configured and files returned after Pi-only reboot | Reported pass |
| Experimental v1 USB recovery | Failed equivalent reboot comparison | Regression; superseded |
| Retry v2 control flow | Immediate/absent/delayed peer simulation with synthetic timing and mocked UART | Passed within simulation limits |
| Retry v2 Pi reboot recovery | User reported configured and files visible | Reported pass; limited trials |
| Retry v2 delayed handshake >=60 seconds | User reported connection and files returned | Reported pass |
| Real-print status and camera | Live webpage/API/widget observations | Observed working |
| v2 pause/resume and print completion | Not yet confirmed | Pending |
| Web duration: 24h, 41h, 100h and invalid values | JavaScript test cases | Passed locally |
| Existing-page patch: backup and idempotency | Local fixture tests | Passed locally |
| Web patch on owner's Pi | Installer reported success and backup path; owner acknowledged result | Installed; visual value confirmation not separately recorded |
| Windows vertical overlay and live video | Window inspected against active print | Observed working |
| Clean SD image and first-boot setup | No image build yet | Pending |
| Annotated physical wiring | Photos/pins not yet verified for publication | Pending |

This is not a broad compatibility or long-term reliability claim. Failed trials remain documented so readers can understand why the design changed.
