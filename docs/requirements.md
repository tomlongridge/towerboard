# Towerboard

## Mission

A belfry-based ringing simulator / "strikometer" controlled by mobile devices, but displayed to the tower, with additional news/information shown when idle.

## Feature overview

* Easy to install
* Connectivity through mobile web interface
* Simulator for selecting computer-powered bells
* Striking analyser (strikometer) for analysing human ringing
* Historical record of touches
* News, events, performances and statistics information board

## Technology overview

Towerboard runs on a Raspberry Pi in the belfry, which is connected to sensors on the bells for striking data, and to a monitor in the belfy for display. It is designed to be controlled, configured and updated entirely using mobile devices rather than an awkward keyboard and mouse setup. This is achieved by hosting an access point (AP) on the Pi to which users connect and can access a hosted web app to control the system.

One key aspect of the design is that internet connectivity is usually very limited in towers. The system therefore works with _optional_ internet access for updating its software and content: attempting to use configured mobile hotspots or falling back to a USB stick if an offline update is required.

## Hardware requirements

* Raspberry Pi version 4 Model or later
* Speakers (USB or bluetooth)
* [Bagley simulator](http://www.bagleybells.co.uk/sensors/sensors.htm) or similar
* Monitor (micro HDMI)

## Installation and updates

### Installation

The initial image for the system is supplied on an SD card with a default SSID and password. All further updates and configuration are applied by connected users to the AP network. The first user to register automatically becomes an admin with access to the Admin Control Panel (ACP).

### Internet access

The system ideally has two network cards, one of them WiFi: to allow simultaneous connection to the internet for receiving updates as well as hosting a local network for users. However, it also allows for a single network option: with the app looking for a configured set of SSIDs to connect to. If not found, or connection is lost, the system switches to AP mode until rebooted. If there is no content to download, or it has completed, the system switches to AP mode.

When in update mode, the monitor displays a message instructing users of the progress of any updates being downloaded and what to do if it gets stuck (restart and disable named networks).

### Software updates

Towerboard releases are hosted on GitHub - this detected at startup and downloaded, with an option in the ACP to apply the update.

## Features

### Bell sounds

The system is connected to sensors on the bells via a serial to USB interface. Whenever a strike is detected, the system will play the sound of the associated bell. These sound files are in a known location in the filesystem and can be uploaded by connecting to the Pi's file system or via the web app.

### Simulated touches

Users can select a touch for the system to "ring" where one or more of the bells can be omitted and rung by a real ringer to allow practices when there are fewer ringers around.

### Touch detection and recording

Touches can either be initiated manually, with a user selecting a method, or automatically when two whole pulls (i.e. handstroke and backstroke twice) of rounds has been sounded on 3 or more bells. Full touch details are available for 24 hours, configurable via the web app, for striking analysis and replay.

### Strikometer

Using the Hawkear algorithm, the striking of a touch can be analysed to give whole-band and per-ringer details of striking. This can be enabled and disabled for each touch.

## Web app

The Pi hosts a web app which is used by both the belfry monitor and connected users. These will be called "interactive" and "kiosk" mode in the documentation.

If the `?kiosk=true` querystring is passed in, the app enters "kiosk" mode and the display is automatically controlled without authentication. Otherwise the user is prompted for a username/password or to create an account. If the user decides to continue without logging in, they can access the Information screens only.

### Kiosk mode

In kiosk mode (i.e. the belfy display), the app cycles through the information screens to show notices, an events calendar, Bellboard performances and tower information. The pages shown and the length of display of a page, is configured in the ACP.

The cycle of pages is interrupted if a bell strike is detected – when this occurs, the Active Ringing page is shown until there has been a pause in ringing for 30 seconds (configurable via the ACP)

### AP footer

The footer of all screens shows the SSID of the AP network, the password and the address of the web app.

## Information screens

### Notices

Displays a list of active notices for the tower, which can be clicked on to see the details, consisting of:

* Title
* Content (HTML)
* Images

Admin users are able to add, edit, delete and archive notices. Archived notices are not shown, but can be accessed via the ACP.

In kiosk mode, each active notice is shown individually: text first and then full page images.

### Calendar

Displays a list of future events, by month, which can be clicked on to see the details, consisting of:

* Title
* Date
* Time (from / to)
* Content (HTML)

Admin users are able to add, edit and delete events. Past events are not shown, but can be accessed via the ACP.

In kiosk mode, each active event is shown individually.

### Performances

Displays a curated list of performances from Bellboard (bb.ringingworld.co.uk), which can be clicked on to see the details, consisting of:

* Date
* Tower
* Changes and method
* Images

Admin users are able to add (via URL) and delete performances. If no internet connection is available, new performances are fetched during the next update.

Admin users can also setup a filter in the ACP, which interfaces with the BellBoard search page to automatically show performances. These cannot be removed on this page, but are managed in the ACP.

### Tower information

Displays a static information page about the tower and bells, taken from Dove's Guide (dove.cccbr.org.uk) using the ID in the ACP.

### Welcome information

A welcome message to ringers in the belfry.

### Active ringing

Displays each bell number in a box - either coloured or white depending on whether it's at handstroke or backstroke - to give a visual indication of the ringing going on.

If a touch has been initiated, the current method is displayed.

In interactive mode, the following controls are available:

* Reset handstroke/backstroke state - all bells return to handstroke position
* Start / stop / reset the touch - if a touch has been initiated
* Enable/disable Strikometer

### Update mode information

Displays status of an update in-progress, including the steps to take to recover if the update fails (e.g. internet connectivity fails on connected device).

## User screens

### New touch

Allows a user to select a method for the next touch. This might be for all-humans or partly computer-rung.

Users select:

* a method - filtering on name, stage and type (Surprise, Delight, etc)
* which bells are human-controlled and which are rung by the simulator - with convenience button to make all-human
* peal speed - i.e. the speed of the ringing, if >0 computer ringers
* manual start/stop or number of whole pulls (hand + backstroke) before the method starts/ends

A button is shown to initiate the touch.

### Recent touch list

Each touch is fully stored in the system for 24 hours. The touch list shows all the touches and allows users to select one to enter the Touch Details page.

### Touch details

Displays the full details of a touch, including:

* Method and changes

### Last touch

### Ringer touch details

### Ringer stats

## Control screens

Available in interactive mode only:

### Admin control panel (ACP)

* Reboot to update mode
* Apply update
* SSID list, including add and remove
* Set AP SSID name and password
* GitHub releases URL
* User password reset and removal
* Admin user list
* Kiosk mode screens and speed
* Delay before returning to information screen cycle after ringing
* Archived notice / event list - unarchive and delete options
* BellBoard performance filters - including setting a relative from date
* Tower details page - name, Dove ID, colour scheme and welcome message
* Bell sounds - upload per bell
* Touch retention period
* Whether Strikometer is enabled by default

## Component design detail

### Database

Local persistence on the Pi is provided by a local Postgres database.

### Sound and calibration

Sound packs are zips holding `manifest.toml` and one WAV per bell (format in [tower/rt/soundpack.py](../tower/rt/soundpack.py)), uploaded on the admin page. Until one is installed, the Pi sounds synthetic bells generated in code.

### Releases

Towerboard releases are stored in GitHub and pull down to the system via WiFi (either direct or via a user's device), depending on whether the system contains one or two network cards and whether a WiFi network is reachable.

A release is a ZIP file containing the following:

* The source code bundle
* The latest method definition XML file from the [CCCBR website](http://methods.cccbr.org/)

### Methods

The system maintains a list of methods from the [CCCBR website](http://methods.cccbr.org/), which are downloaded as part of a release. They are parsed and stored during the release installation and made available to system components.

### Touches

For each touch, the following is recorded:

* Method - if selected in New Touch screen
* Changes - the number of rows rung
  * The system should start counting once two non-rounds rows have been rung and stop counting when two rows of rounds have been rung again, the first rounds should not be included in the count, but all others should
* The bells rung and which were computer controlled
* The claimed bells - bells which users have claimed as themselves, and wheher they were a conductor
* Striking data - the full data from the Stikometer, if enabled
* Striking summary - band- and ringer-level summarised data from the Strikometer, if enabled