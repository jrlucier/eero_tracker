## Eero Device Tracker for Home Assistant

This adds [Eero](https://eero.com/) device tracking to Home Assistant (HA, HASSIO, HASS OS). This project is based on [@343max's eero-client project](https://github.com/343max/eero-client) -- many thanks to him or this project probably wouldn't exist. Thanks to [@rsnodgrass](https://github.com/rsnodgrass) for the structural improvements. This code has no warranties, and please submit any pull requests you might have to improve upon it.

#### Why do I need to run a script in my config directory?

Eero doesn't have a traditional user/password login setup, so we need to use your phone's SMS or your email address to create an authenticated session.  To do that, you'll need to SSH into your device running Home Assistant to run an interactive script that allows that to occur. 

#### Note for HASS.IO users

If you're running HASS.IO, be aware that the official SSH server will not allow you to run python files (so I'm told, and which we require), so use the Secure Shell community add-on.  Your configuration directory will be stored under `/config` instead of `~/.homeassistant/`. 

Now let's get on with installin' this thing!

### Step 1: Copy the scripts!

SSH into your device. Now we need to download the zip file from the releases section, and uncompress it in your configuration directory (mine is `~/.homeassistant`):
```
cd ~/.homeassistant/
wget https://github.com/jrlucier/eero_tracker/releases/download/1.0.4/eero_tracker-1.0.4.zip
unzip eero_tracker-1.0.4.zip
```
  
### Step 2: Initial Configuration and Eero Session Creation

The scripts in this project rely on the "requests" package, so install it if it's not already installed:
```
python3 -m pip install requests
```

We need to get an authenticated session created with Eero's servers. So to do that, you'll need to go to your configuration directory (eg: `cd ~/.homeassistant`), and run the `eero_tracker_instantiate.py` file:
```
python3 eero_tracker_instantiate.py
```
This will prompt you for your phone number (no dashes), and then it will send you an SMS text with a code you will need to put in.  You may also use an email address instead.  Once done, it will create an `eero.session` file in your configuration directory.  Subsequent calls to this python file will dump the list of connected wireless devices, their mac addresses, and hostnames for easier reference.  You technically shouldn't need `eero_tracker_instantiate.py` after the creation of the `eero.session` file, but I keep it around for quick mac address referencing.

If you're not running HASS.IO (default SSH user is root), and have Home Assistant configured differently, then check the permissions on the files. `chown` the files to the same permissions as your other HA configuration files (`ls -al` to check yours in your configuration directory).  Mine are owned by `homeassistant:nogroup`:
```
sudo chown homeassistant:nogroup eero.session 
sudo chown homeassistant:nogroup eero_tracker_instantiate.py 
sudo chown -R homeassistant:nogroup custom_components/

```
### Step 3: Add it to Home Assistant's configuration!

Now that that's done, all you need to do is update your `configuration.yaml` with the `device_tracker`.  Here's an example:
```yaml
device_tracker:
  - platform: eero_tracker
    consider_home: 300
    interval_seconds: 60 # Recommended...do not set this lower than 25, we don't want to DDOS Eero
    only_macs: "11:22:33:44:55:66, 22:22:22:22:22:22"  # Optional
```
`only_macs` is optional, but allows you to reduce down the devices returned to a core set of mac addresses.  The list is comma separated. 

`interval_seconds` must be 25sec or greater.  Any less and it'll blow up with errors on purpose.  Be nice to Eero's servers and don't DDOS them! ;)

### Step 4: Restart and test

You should see devices populate, using the devices nicknames where possible as the name of the device.  If you experience any issues, please let me know!

### Step 5: Automatic Updates with Custom Updater (Optional)

For easy updates whenever a new version is released, use the [Home Assistant custom_updater component](https://github.com/custom-components/custom_updater/wiki/Installation) and [Tracker card](https://github.com/custom-cards/tracker-card). Once those are setup, add the following custom_updater config:

``` 
custom_updater:
  track:
    - components
  component_urls:
    - https://raw.githubusercontent.com/jrlucier/eero_tracker/master/custom_updater.json
```


