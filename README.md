## Eero Device Tracker for Home Assistant

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

Adds device tracking support for [Eero Mesh WiFi routers](https://eero.com/) to [Home Assistant](https://www.home-assistant.io/).

This project is based on [@343max's eero-client project](https://github.com/343max/eero-client) -- many thanks to him or this project probably wouldn't exist. Thanks to [@rsnodgrass](https://github.com/rsnodgrass) for the structural improvements. This code has no warranties, and please submit any pull requests you might have to improve upon it.

## Setup Process

1. Install using [HACS](https://github.com/hacs/integration) or manually copy the files
2. Run the eero_tracker_instantiate.py script to setup credentials (creates an eero.session in /config)
3. Add eero_tracker to your configuration.yaml
4. Restart Home Assistant

Now let's get on with installin' this thing!

## Step 1: Installation

### Option A: Installation with Home Assistant Community Store (HACS)

For easy updates whenever a new version is released, use the [Home Assistant Community Store (HACS)](https://github.com/hacs/integration) and add the following Integration in the Settings tab:

```
jrlucier/eero_tracker
```

Then go to the Integration tab, search for "Eero Tracker", and click install.

### Option B: Manual Installation

Copy the scripts!

SSH into your device. Download the zip file from the releases section and uncompress it in your configuration directory (e.g. `~/.homeassistant` or `/config`):

```
cd ~/.homeassistant/
wget https://github.com/jrlucier/eero_tracker/releases/download/1.0.9/eero_tracker-1.0.9.zip
unzip eero_tracker-1.0.9.zip
```

## Step 2: Generate Credentials for Connecting to Your Eeros

#### Why do I need to run a script in my config directory?

Eero doesn't have a traditional user/password login setup, so we need to use your phone's SMS or your email address to create an authenticated session token (`eero.session`). To do that, you'll need to SSH into your device running Home Assistant to run an interactive script that allows that to occur.

#### Note for Hass.io users

If you're running [Hass.io](https://www.home-assistant.io/hassio/), be aware that the official SSH server will not allow you to run python files (so I'm told, and which we require), so use the Secure Shell community add-on. Your configuration directory will be stored under `/config` instead of `~/.homeassistant/`.

An alternative method would be to run `eero_tracker_instantiate.py` on another machine, and then manually copy over the `eero.session` file to the config directory on the Home Assistant host.

#### Running the Script

The scripts in this project rely on the "requests" package, so install it if it's not already installed:

```
python3 -m pip install requests
```

We need to get an authenticated session created with Eero's servers. So to do that, you'll need to go to your configuration directory (eg: `cd ~/.homeassistant`), and run the `eero_tracker_instantiate.py` file:

```
python3 eero_tracker_instantiate.py
```

This will prompt you for your phone number (no dashes), and then it will send you an SMS text with a code you will need to put in. You may also use an email address instead. Once done, it will create an `eero.session` file in your configuration directory.  Subsequent calls to this python file will dump the list of connected wireless devices, their mac addresses, and hostnames for easier reference.  You technically shouldn't need `eero_tracker_instantiate.py` after the creation of the `eero.session` file, but I keep it around for quick mac address referencing.

#### Manual Installation Permissions

If you aren't running [Hass.io](https://www.home-assistant.io/hassio/) (whose default SSH user is root), and have Home Assistant configured differently, then check the permissions on the files. `chown` the files to the same permissions as your other HA configuration files (`ls -al` to check yours in your configuration directory). Mine are owned by `homeassistant:nogroup`:

```bash
sudo chown homeassistant:nogroup eero.session
sudo chown homeassistant:nogroup eero_tracker_instantiate.py 
sudo chown -R homeassistant:nogroup custom_components/
```

## Step 3: Add Tracker to Home Assistant's Configuration

Now that that installation and authentication are done, all that is left is to add the [device_tracker](https://www.home-assistant.io/integrations/device_tracker/) to your `configuration.yaml`.

The minimum required configuration:

```yaml
device_tracker:
  - platform: eero_tracker
```

Example including optional configuration:

```yaml
device_tracker:
  - platform: eero_tracker

    # optional eero_tracker settings:
    only_macs: "11:22:33:44:55:66,22:22:22:22:22:22"
    only_networks:
      - 30120

    # standard device_tracker options
    consider_home: 300     # default: 180
    interval_seconds: 30   # default: 25
    only_wireless: True    # default: True
```

#### Config Keys

| Key                | Default | Description |
|--------------------|---------|-------------|
| `only_macs`        | none    | comma separated list of MAC addresses that reduces the devices monitored to a smaller set. |
| `interval_seconds` | 180     | **must** be 25 seconds or greater to avoid DDoS of eero's servers. |
| `only_networks`    | none    | YAML list of network identifiers to search for devices (only useful if you have multiple eero locations under a single eero email address, for instance at work or a second home). Turn on HA debug logging to determine the network ids for your eeros |
| `only_wireless`    | True    | only track wireless devices if set to true (normally hardwired devices are not useful for tracking)

For additional device tracker configuration options, see the [HA device_tracker docs](https://www.home-assistant.io/integrations/device_tracker/).

## Step 4: Restart and Test

You should see wireless devices populate using each device's nicknames, where possible, as the device name.

**NOTE: This does not populate any devices that are not wirelessly connected to your eero.**

## Support

If you are experiencing any issues, first check the [community support discussion thread](https://community.home-assistant.io/t/eero-support/21153) to see if anyone else has solved your issue previously. You can also discuss the issue you are having there. If you feel it is a bug, please [create an github Issue with the details](https://github.com/jrlucier/eero_tracker/issues).

#### Not Yet Implemented

The following features are not yet implemented (no plans currently for adding). If you are interested in contributing code, please submit a patch.

- support for family profiles (pause/unpause switch) and assigning to Home Assistant "person" entities
- support for rebooting the eero network
- eero connection status and most recent upload/download speed test results
- config_flow to allow all configuration through the Home Assistant UI (including eero.session setup)

## See Also

* [Eero Tracker community discussion forum](https://community.home-assistant.io/t/eero-support/21153)
* [Eero Mesh WiFi routers](https://eero.com/) (official site)
* [Eero Python Client (343max/eero-client)](https://github.com/343max/eero-client)
* [Eero API endpoint examples](https://github.com/yepher/eeroMonitor)
