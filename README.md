# Mazda 6e Cloud for Home Assistant based on Changan Deepal Cloud (https://github.com/danperks/ha-deepal)

<p align="center">
  <img src="icon.png" alt="Mazda 6e logo" width="160">
</p>

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

Custom Home Assistant integration for the Mazda 6e cloud API.

This adaptation uses the Mazda 6e `cma-app-gw` endpoints for device-authorized cloud telemetry. It is currently **read-only** because Mazda remote-command endpoints have not been verified.

## Important Warnings

- Use this integration at your own risk.
- This is an unofficial integration and is not endorsed by Changan or Deepal.
- Remote commands can affect the vehicle. Make sure it is safe before using controls such as locks, windows, boot, climate, lights, or horn.
- This integration cannot be used to drive the car. It does not implement the BLE/digital key path required for drive authorization.
- Authorizing a Home Assistant device can affect sessions in the official Mazda app. Use a distinct device ID if you run more than one client.

## Supported Vehicle

- Mazda 6e: cloud telemetry and a manual refresh button.

## Current Features

- Mazda encrypted-email/password login and email device verification through Home Assistant.
- Native Home Assistant reauthentication/repair flow when the cloud session is invalidated.
- Vehicle telemetry sensors and binary sensors.
- Vehicle image URL sensor from the Mazda vehicle metadata.
- Manual refresh button.

Remote climate, charging, locks, windows, boot, lights, and horn controls are intentionally not exposed in this release.

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add this fork's repository URL as an **Integration** repository.
5. Install **Mazda 6e Cloud** from HACS.
6. Restart Home Assistant.

### Manual

1. Copy `custom_components/mazda6e_cloud` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

[![Open your Home Assistant instance and start setting up Mazda 6e Cloud.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=mazda6e_cloud)

You can also configure it manually from **Settings -> Devices & services -> Add integration**, then search for **Mazda 6e Cloud**.

During setup, enter the email address and password used by the official Mazda app (!! USE A SEPARATE ACCOUNT !!), then enter the device verification code sent by email. The integration encrypts credentials with Mazda's embedded app public key before sending them and does not store them after setup.

## Notes

- The integration polls Mazda cloud status every minute. The diagnostic refresh button requests another cloud poll.
- If the account is used elsewhere, Home Assistant may need reauthentication.

## Development Status

This is early reverse-engineering work. Expect breaking changes, incomplete model support, and occasional cloud API/session issues.
