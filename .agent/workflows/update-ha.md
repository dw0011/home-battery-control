---
description: Automatically update the Home Assistant integration via HACS
---

This workflow automates the process of updating the House Battery Control integration via the HACS dashboard on a local Home Assistant instance.

If you are asked to execute this workflow, you should start the `browser_subagent` tool with the following task instructions:

```
Execute the update-ha workflow:
1. Navigate to http://homeassistant.local:8123/hacs/dashboard
2. Search for "home battery" in the UI search bar
3. Click the 3 dots (overflow menu) on the "House Battery Control" card
4. Click "Redownload"
5. Click "Download" on the popup
6. Navigate to Settings
7. Click "Restart Required" (or navigate to system restart depending on the HA version UI)
8. Click "Submit" on the popup to execute the restart
```
