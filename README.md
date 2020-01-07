## Eero Device Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

Adds device tracking support for [Eero Mesh WiFi routers](https://eero.com/) to Home Assistant (HA, HASSIO, HASS OS). This project is based on [@343max's eero-client project](https://github.com/343max/eero-client) -- many thanks to him or this project probably wouldn't exist. Thanks to [@rsnodgrass](https://github.com/rsnodgrass) for the structural improvements. This code has no warranties, and please submit any pull requests you might have to improve upon it.

## Setup Steps

1. Install using HACS or manually
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

Then go to the Integration tab and search for "Eero Tracker" and click install.

### Option B: Manual Installation

Copy the scripts!

SSH into your device. Now we need to download the zip file from the releases section, and uncompress it in your configuration directory (mine is `~/.homeassistant`):
```
cd ~/.homeassistant/
wget https://github.com/jrlucier/eero_tracker/releases/download/1.0.4/eero_tracker-1.0.4.zip
unzip eero_tracker-1.0.4.zip
```

## Step 2: Generate Credentials for Connecting to Your Eero

#### Why do I need to run a script in my config directory?

Eero doesn't have a traditional user/password login setup, so we need to use your phone's SMS or your email address to create an authenticated session. To do that, you'll need to SSH into your device running Home Assistant to run an interactive script that allows that to occur. 

#### Note for HASS.IO users

If you're running HASS.IO, be aware that the official SSH server will not allow you to run python files (so I'm told, and which we require), so use the Secure Shell community add-on. Your configuration directory will be stored under `/config` instead of `~/.homeassistant/`. 

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

If you're not running HASS.IO (default SSH user is root), and have Home Assistant configured differently, then check the permissions on the files. `chown` the files to the same permissions as your other HA configuration files (`ls -al` to check yours in your configuration directory).  Mine are owned by `homeassistant:nogroup`:

```
sudo chown homeassistant:nogroup eero.session 
sudo chown homeassistant:nogroup eero_tracker_instantiate.py 
sudo chown -R homeassistant:nogroup custom_components/
```

## Step 3: Add Tracker to Home Assistant's Configuration

Now that that installation and authentication are done, all that is left is to add the `device_tracke` to your `configuration.yaml`.

Here's an example:

```yaml
device_tracker:
  - platform: eero_tracker
    consider_home: 300
    interval_seconds: 60 # Recommended...do not set this lower than 25, we don't want to DDOS Eero
    only_macs: "11:22:33:44:55:66, 22:22:22:22:22:22"  # Optional
```

`only_macs` is optional, but allows you to reduce down the devices returned to a core set of mac addresses. The list is comma separated. 

`interval_seconds` must be 25sec or greater. Any less and it'll blow up with errors on purpose. Be nice to Eero's servers and don't DDoS them! ;)

## Step 4: Restart and test

You should see devices populate, using the devices nicknames where possible as the name of the device.

## Support

If you are experiencing any issues, first check the [community support discussion thread](https://www.reddit.com/r/homeassistant/comments/8k987c/eero_device_tracker/) to see if anyone else has solved your issue previously. You can also discuss the issue you are having there. If you feel it is a bug, please [create an github Issue with the details](https://github.com/jrlucier/eero_tracker/issues).

## See Also

* [Eero Device Tracker community discussion forum](https://www.reddit.com/r/homeassistant/comments/8k987c/eero_device_tracker/)
* [Eero Mesh WiFi routers](https://eero.com/)
