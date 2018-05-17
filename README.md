# eero_tracker
This adds Eero device tracking to Home Assistant (HA, HASSIO, HASS OS).

## Setup
There are two ways to get the files copied into your HA instance:

1. Manually copy the files from this project into your configuration directory of your Home Assistant install (mine is `~/.homeassistant`.  This directory is the same one which has the `configuration.yaml` file in it. Note: You need to maintain the exact same directory pathings as I use in this repository.

2. Use git. Go to your HA configuration directory (eg: `cd ~/.homeassistant`), and execute the following commands to have git pull it down.  
    ```
    git init .
    git remote add -t \* -f origin origin https://github.com/jrlucier/eero_tracker.git 
    git checkout master
    ```
    Future updates can be done by going to your configuration directory again (eg: `cd ~/.homeassistant`), and running the following:
    ```
    git pull
    ```
    You can also just blow away the `.git` directories and call it good.  Your choice :)
  
## Initial Configuration
To get a session reference to Eero, you need to go to your configuration directory (eg: `cd ~/.homeassistant`), and run the `eero_tracker_instantiate.py` file:
```
python eero_tracker_instantiate.py
```
This will prompt you for your phone number (no dashes), and then it will send you an SMS text with a code you will need to put in.  Once done, it will create an `eero.session` file in your configuration directory.  Subsequent calls to this python file will dump the list of connected wireless devices, their mac addresses, and hostnames for easier reference.  You technically shouldn't need this file after the creation of the `eero.session` file, but I keep it around for my own sanity.

Now that that's done, all you need to do is update your `configuration.yaml` with the `device_tracker`.  Here's an example:
```yaml
device_tracker:
  - platform: eero_tracker
    consider_home: 300
    interval_seconds: 60 # Don't set it much lower than this.  We don't want to hammer Eero's servers
    only_macs: "11:22:33:44:55:66, 22:22:22:22:22:22"  # Optional
```
`only_macs` is optional, but allows you to reduce down the devices returned to a core set of mac addresses.  The list is comma separated.
