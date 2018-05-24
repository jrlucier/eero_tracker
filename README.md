# eero_tracker
This adds Eero device tracking to Home Assistant (HA, HASSIO, HASS OS). This project is based on @343max's eero-client project: https://github.com/343max/eero-client -- many thanks to him or this project probably wouldn't exist.  This code has no warranties, and please submit any pull requests you might have to improve upon it.

## Why do I need to run a script in my config directory?
Eero doesn't have a traditional user/password login setup, so we need to use your phone's SMS to create an authenticated session.  To do that, you'll need to SSH into your device running Home Assistant to run an interactive script that allows that to occur.  You may remove the `eero_tracker_instantiate.py` script after everything is configured.

## Note for HASS.IO users
If you're running Hass.IO, be aware that the official SSH server will not allow you to run python files (so I'm told, and which we require), so use the Secure Shell community add-on.  Your configuration directory will be stored under `/config`

## Step 1: Copy the scripts!
SSH into your device.  Then use one of the three ways to get the files copied into your HA instance:
1. Download the zip file from the releases section, then uncompress them in your configuration directory (mine is `~/.homeassistant`). Example:
    ```
    cd ~/.homeassistant/
    wget https://github.com/jrlucier/eero_tracker/releases/download/1.0.2/eero_tracker-1.0.2.zip
    unzip eero_tracker-1.0.2.zip
    ```

2. Manually copy the files from this project into your configuration directory of your Home Assistant install (eg: `~/.homeassistant`).  This directory is the same one which has the `configuration.yaml` file in it. Note: You need to maintain the exact same directory pathings as I use in this repository.

3. Use git. Go to your HA configuration directory (eg: `cd ~/.homeassistant`), and execute the following commands to have git pull it down.  
    ```
    git init .
    git remote add -t \* -f origin https://github.com/jrlucier/eero_tracker.git 
    git checkout master
    ```
    Future updates can be done by going to your configuration directory again (eg: `cd ~/.homeassistant`), and running the following:
    ```
    git pull
    ```
    If you wish to never update again via `git`, then you can blow away the `.git` directories.  You can run the following in the configuration directory (eg: `cd ~/.homeassistant`) to do that:
    ```
    ( find . -type d -name ".git" && find . -name ".gitignore" && find . -name ".gitmodules" ) | xargs -d '\n' rm -rf
    ```
  
## Step 2: Initial Configuration and Eero Session Creation
The scripts in this project rely on the "requests" package, so install it if it's not already installed:
```
python3 -m pip install requests
```

We need to get an authenticated session created with Eero's servers. So to do that, you'll need to go to your configuration directory (eg: `cd ~/.homeassistant`), and run the `eero_tracker_instantiate.py` file:
```
python3 eero_tracker_instantiate.py
```
This will prompt you for your phone number (no dashes), and then it will send you an SMS text with a code you will need to put in.  Once done, it will create an `eero.session` file in your configuration directory.  Subsequent calls to this python file will dump the list of connected wireless devices, their mac addresses, and hostnames for easier reference.  You technically shouldn't need `eero_tracker_instantiate.py` after the creation of the `eero.session` file, but I keep it around for quick mac address referencing.

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
`only_macs` is optional, but allows you to reduce down the devices returned to a core set of mac addresses.  The list is comma separated. They should be lowercase (ticket open to make it case insensitive).

### Step 4: Restart and test
You should see devices populate, using the devices nicknames where possible as the name of the device.  If you experience any issues, please let me know!
