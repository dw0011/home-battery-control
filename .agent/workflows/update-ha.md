---
description: Automatically update the Home Assistant integration via HACS
---

This workflow automates the process of updating the House Battery Control integration via the HACS dashboard on a local Home Assistant instance.

If you are asked to execute this workflow, you should start the `browser_subagent` tool with the following task instructions:

```
CRITICAL INSTRUCTION: The Home Assistant server is on the local network and responds instantly. DO NOT use artificial wait or sleep commands. Execute actions as quickly as the DOM allows.

Execute the update-ha workflow:
1. Navigate to http://homeassistant.local:8123/hacs/repository/1162396285
5. Click "Redownload" from the dropdown.
6. Click "Download" on the confirmation popup.
7. Navigate to http://homeassistant.local:8123/config/dashboard
8. Click the Power/Restart icon in the top right corner.
9. Click "Restart Home Assistant" in the menu.
10. Click "Restart" on the final popup confirmation.
11. Return once the restart command has been successfully submitted.
```
