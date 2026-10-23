# Raspberry Pi image release plan

Deliverable: compressed flashable `.img.xz`, source/build recipe, SHA256 checksums and release notes. An ISO is not the intended SD-card image format. **No downloadable continuation image exists yet.**

Before building:

1. Record the exact Pi model, OS release/architecture, USB gadget setup, camera stack and deployed service configuration. Export only the relevant configuration, not credentials or private logs.
2. Select a supported Raspberry Pi OS baseline that works on that hardware; pin its source version and checksums. Evaluate pi-gen or an equivalent reproducible build recipe.
3. Integrate USB Share sources, explicit configuration templates, camera, and a reviewed bridge installer. Preserve upstream and dependency license notices. Review historical privileged web controls and default-account assumptions before presenting the image as release-ready.
4. Provide first-boot user/network setup. Generate unique SSH host keys and machine identity on first boot. Do not bake in Wi-Fi passwords, user SSH keys, reusable default passwords, personal print jobs or logs.
5. Keep experimental printer firmware optional and separate. Never auto-flash it from the Pi image.
6. Test a freshly flashed spare SD card: boot, network onboarding, SMB, USB enumeration, camera, status, idle reboot recovery, delayed handshake and a complete small print with pause/resume.
7. Build versioned artifacts and checksums in a controlled workflow, then publish a candidate release with exact supported hardware and known limitations. Promote it only after clean-install tests pass.

The historical automatic tagging workflow is now manual-only so a documentation push cannot accidentally label an untested image release.
