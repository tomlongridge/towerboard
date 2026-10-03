# Towerboard

A self-updating simulator, strikometer and belfry information system.

## Hardware requirements

* Raspberry Pi version 4 Model or later, with Pi OS Trixie (Debian 13)
* A microSD card (16 GB or larger) and a way to plug it into your Mac
* The Pi's power supply
* An Ethernet cable to your home router (strongly recommended for setting up)
* Speakers (USB, or wired into the Pi 4's headphone socket)
* [Bagley simulator](http://www.bagleybells.co.uk/sensors/sensors.htm) or similar
* Monitor (micro HDMI)

## Installation instructions

This guide takes you from a brand-new Raspberry Pi to a working Towerboard, using a Mac. You don't need to know how to program, but you will type a few commands. Allow about an hour.

### Before you start: a few words

* **Terminal** is the Mac app where you type commands. Open it from *Applications → Utilities → Terminal*.
* Each grey box below holds one command. Copy it, paste it into Terminal, and press Return. Wait for it to finish (you get your prompt back) before the next one.
* Some steps run **on your Mac** and some **on the Pi**. You "log in to the Pi" from Terminal using **SSH**, a way of typing commands on another computer over the network. When you are logged in, the prompt starts with your Pi username, e.g. `ringer@towerboard:~ $`.
* This guide uses the Pi name **`towerboard`** and the username **`ringer`**. If you choose different ones in step 6, change them wherever they appear.
* When Terminal asks for a password, nothing appears as you type. That's normal: type it and press Return.

### Part A: prepare your Mac (once)

**1. Install Apple's developer tools.** A window pops up; choose *Install*. If it says they are already installed, carry on.

```bash
xcode-select --install
```

**2. Install `uv`**, which runs Towerboard's tools with the right version of Python:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then **quit Terminal and open it again** so it finds `uv`.

**3. Download Towerboard.** This puts it in a folder called `towerboard` in your home folder. (You need access to the repository on GitHub; you may be asked to sign in.)

```bash
git clone https://github.com/tomlongridge/towerboard.git ~/towerboard
```

**4. Create your release key.** Every Towerboard release is signed with this key, and the Pi only accepts software signed by it. When asked for a passphrase, press Return twice for none, or choose one (you'll then type it each time you build a release).

```bash
ssh-keygen -t ed25519 -f ~/.ssh/tower-release -C tower-release
```

Now make the file that tells the Pi to trust this key:

```bash
echo "tower-release $(cat ~/.ssh/tower-release.pub)" > ~/tower-allowed_signers
```

> **Keep `~/.ssh/tower-release` safe and private.** Anyone with it can send software to your Pi. If you lose it, you'll need to reinstall Towerboard with a new key.

### Part B: prepare the Pi's SD card

**5. Install Raspberry Pi Imager** from [raspberrypi.com/software](https://www.raspberrypi.com/software/) and open it.

**6. Write the operating system to the card.** In Imager:

1. **Device:** choose your Pi model.
2. **Operating system:** choose *Raspberry Pi OS (other)* → **Raspberry Pi OS Lite (64-bit)**. Check it says **Trixie**. ("Lite" means no desktop; Towerboard doesn't need one.)
3. **Storage:** choose your SD card. Be careful: everything on it will be erased.
4. When asked whether to **customise settings**, choose to edit them:
   * **Hostname:** `towerboard`
   * **Username and password:** username `ringer`, and a password you'll remember.
   * **Wireless LAN:** leave this **off** if you'll use an Ethernet cable (recommended). If you have no way to use a cable, fill in your home WiFi here and see *No Ethernet cable?* after step 14.
   * **Locale:** your time zone and keyboard.
   * **Services:** turn on **SSH**, with **password authentication**.
5. Save, then write the card. It takes a few minutes.

**7. Start the Pi.** Put the card in the Pi, connect the Ethernet cable to your router, plug in your speakers and the monitor (on a Pi 4, the micro HDMI socket nearest the power socket), then plug in the power. Wait about two minutes for the first start-up to finish.

### Part C: check you can reach the Pi

**8. Log in to the Pi** from Terminal on your Mac:

```bash
ssh ringer@towerboard.local
```

The first time, it asks whether you trust this computer: type `yes` and press Return, then type your Pi password. Your prompt should change to `ringer@towerboard:~ $`.

> **"Could not resolve hostname"?** The Pi may still be starting: wait a minute and try again. Check the Ethernet cable is in and the Pi's lights are on.

**9. Check the Pi is on Trixie** (still logged in to the Pi):

```bash
grep PRETTY /etc/os-release; python3 --version
```

You should see `Debian GNU/Linux 13 (trixie)` and `Python 3.13`.

**10. Bring the Pi up to date.** This can take a while.

```bash
sudo apt-get update && sudo apt-get full-upgrade -y
```

**11. Check the two packages Towerboard needs are available:**

```bash
apt-cache policy python3-numpy python3-alsaaudio | grep -E "^python3|Candidate"
```

Both should show a **Candidate** with a version number. If either says `Candidate: (none)`, stop here and ask for help.

**12. Log out of the Pi**, back to your Mac:

```bash
exit
```

### Part D: build Towerboard and copy it to the Pi (on your Mac)

**13. Build a release.** This runs Towerboard's checks, then packs and signs everything into one file in `~/towerboard/dist`.

```bash
cd ~/towerboard && git pull && uv sync && uv run python -m unittest discover -s tests
```

The last line should say `OK`. Then:

```bash
uv run python -m tower.release build --key ~/.ssh/tower-release
```

It prints the name of the new file, like `dist/tower-0.3.0+g1a2b3c4.tower`.

**14. Copy the release, your trust file and the installer to the Pi.** First clear out any releases copied there before, so the installer can't pick up an old one:

```bash
ssh ringer@towerboard.local 'rm -f ~/tower-*.tower'
```

Then copy the newest release in `dist`, with the other two files:

```bash
scp "$(ls -t dist/*.tower | head -1)" ~/tower-allowed_signers deploy/install.sh ringer@towerboard.local:~
```

> **No Ethernet cable?** Towerboard always turns the Pi's WiFi into its own network for ringers' phones, so once it starts, the Pi leaves your home WiFi and your Mac loses touch with it. That's expected. In step 15, run the installer as `sudo TOWER_ALLOW_AP_TAKEOVER=1 sh install.sh tower-*.tower tower-allowed_signers` instead. When it disconnects, join the WiFi network `towerboard` (password `bellringing`) on your Mac, and use `http://10.42.0.1/` wherever this guide says `http://towerboard.local/` (and `ringer@10.42.0.1` for SSH). While your Mac is on the Pi's network it has no internet; switch back to your own WiFi when you're done.

### Part E: install (on the Pi)

**15. Log in to the Pi again** (step 8), then run the installer:

```bash
sudo sh install.sh tower-*.tower tower-allowed_signers
```

It takes a while (ten minutes or more on a slow connection, mostly downloading the browser for the belfry display), and finishes with a line like `Installed 0.3.0+g1a2b3c4`.

If it stops with an error, fix what it says and run the same command again: it picks up where it left off.

> **Disconnected at the end?** As the installer finishes, Towerboard starts up and sets up the Pi's network, which can cut off your connection. You may see `Connection … closed by remote host` or `Broken pipe` straight after a line about `tower-kiosk.service`. That's fine: the install has finished. Wait a minute, log in again (step 8) and carry on with step 16.

> **No monitor on this Pi?** Run the installer as `sudo TOWER_KIOSK=0 sh install.sh tower-*.tower tower-allowed_signers` instead, to skip the belfry display.

**16. Check it's running:**

```bash
systemctl --no-pager status tower tower-rt tower-kiosk | grep -E "●|Active"
```

All three should say `active (running)`.

### Part F: first use

**17. Open Towerboard on your Mac.** In Safari, go to [http://towerboard.local/](http://towerboard.local/). You should see the home page, with QR codes for joining the tower WiFi.

**18. Set the admin PIN.** Click **Admin** and choose a PIN of 4 to 12 digits. The first person to open the admin page sets it, so do this straight away. If you ever forget it, ask for help resetting it.

**19. Name your WiFi network.** Out of the box, the Pi makes a WiFi network called `towerboard` with the password `bellringing`. Change both in **Admin → Network**. Leave *Let phones … use the Pi's internet connection* unticked unless you want ringers' phones to use the Pi's internet (if it has one, through a network cable); unticked, they keep using their own mobile data. Ringers' phones join this network, then open `http://10.42.0.1/` (or scan the QR codes on the home page).

**20. Let the Pi reach the internet for updates.** Towerboard fetches new versions from GitHub by itself. With a network cable plugged in, it uses that and there's nothing to do. Otherwise, add a WiFi network it may use under **Admin → Network → Known WiFi networks**: the tower's WiFi, your home WiFi, or a phone hotspot. If the Pi has only its built-in WiFi, it joins that network briefly when it starts and when you press *Check for updates*. While it's online, the Towerboard WiFi is off for a few minutes and the belfry screen says so. With no known networks and no cable, the Pi never goes online.

**21. Set up sound.** Log in to the Pi (step 8) and list its sound outputs:

```bash
aplay -l
```

For a Pi 4's headphone socket, the card is called `Headphones`. Tell Towerboard to use it:

```bash
printf '\n[audio]\ndevice = "plughw:CARD=Headphones"\n' | sudo tee -a /etc/tower/tower.toml && sudo systemctl restart tower-rt
```

(For USB speakers, use the name after `card 1:` from `aplay -l` in place of `Headphones`.) Then in **Admin → Calibration**, press **Ring** next to a bell. You should hear it.

**22. Connect the bell sensors.** Plug the sensor box into a USB socket on the Pi, then open **Diagnostics**. Under *source*, the status should say `open`.

**23. Check the belfry screen.** The monitor should show Towerboard full screen: the QR codes when the bells are quiet, and the bells lighting up as they ring. It starts by itself whenever the Pi is switched on, and refreshes itself after an update. If it's blank, see *If something goes wrong*.

### Updating Towerboard later

New versions arrive by themselves, from GitHub:

1. The Pi checks when it starts, then daily if it has a cable or USB WiFi dongle. With only its built-in WiFi, it checks when it starts and when you press **Check for updates** under **Admin → Software** (wait until the bells are quiet: it does).
2. When a new version has been downloaded and checked, the same page shows **Version … is ready to install**, with what's new. Nothing changes until you press **Apply update**.
3. The Pi installs it and restarts. If the new version doesn't start properly, it goes back to the previous one by itself, says so on the admin page, and won't offer that version again.

For a Pi that never goes online, open **Install from a file instead** on the same page and upload a `.tower` release file (download it from the project's GitHub releases page).

### If something goes wrong

* **Diagnostics** (link at the top of every page) shows what the Pi is doing, with no passwords. It's the page to read out or screenshot when asking for help.
* For the sound and sensor service's log, log in to the Pi and run:

  ```bash
  journalctl -u tower-rt -n 40 --no-pager
  ```

* If the belfry screen stays blank, log in to the Pi and check the display's log:

  ```bash
  journalctl -u tower-kiosk -n 40 --no-pager
  ```

* You can see the belfry view on any other screen too: open `http://towerboard.local/?display=wall` in a browser.

## Documentation

* [docs/requirements.md](docs/requirements.md) for high level system specs.
* [docs/development.md](docs/development.md) for notes on running the system for making changes.
* [docs/tower-system-design.md](docs/tower-system-design.md) for a breakdown of components and implementation plan.
