# Hardware bring-up checklist

Use this once the Pi 5, Create 2, and D455 are physically assembled. The software side (G0, G1) is already validated on the M2 Air; everything from G2 onward requires the real robot.

## Bill of materials

| Item | Status / source |
| --- | --- |
| iRobot Create 2 | On hand. |
| Pi 5 (4 GB or 8 GB) + microSD (32 GB+) | On hand. |
| Pi 5 active cooler | Required — passive cooling throttles under sustained ROS load. |
| Intel RealSense D455 | On hand. |
| Create 2 USB-serial cable (Mini-DIN 7 → USB) | Verify it handles 0-5 V serial. |
| USB-C PD power bank (≥ 27 W) or rated buck converter | **Do not** power the Pi from Create 2 Vpwr. |
| Short USB3-A → USB-C cable for D455 | A bad cable causes 80% of D455 disconnects. |
| Rigid D455 mount | 3D-printed or aluminum bracket. Pose stability matters for scan projection. |

## Pi 5 OS setup

1. Flash Ubuntu Server 24.04 LTS (arm64) via Raspberry Pi Imager. Pre-set hostname `quickbot`, enable SSH, set Wi-Fi.
2. First boot: `sudo apt update && sudo apt full-upgrade -y`.
3. Install Docker Engine (not Docker Desktop):
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER && newgrp docker
   sudo apt install -y docker-compose-plugin
   ```
4. Clone the repo:
   ```bash
   git clone git@github.com:TafyLabs/quickbot.git ~/quickbot
   cd ~/quickbot
   ```
5. Build the kilted-base image on the Pi (slow — leave overnight if needed):
   ```bash
   docker build -f docker/kilted-base.Dockerfile -t quickbot:kilted-base .
   ```
   Alternative: push the M2 Air image to a registry (e.g. GHCR) and `docker pull` on the Pi. Both Mac and Pi are arm64 so the image is portable.

## Wiring

```
Pi 5 USB-A 3.0  ──── short USB3 cable ────  D455 USB-C
Pi 5 USB-A 2.0  ──── Create 2 USB-serial ──── Create 2 OI Mini-DIN
USB-C PD bank   ────────────  Pi 5 USB-C power
```

Do **not** plug anything into the Create 2 Vpwr pins to power the Pi. The 200 mA limit will brown out the Pi under ROS load and may damage the Create 2 fuse.

## Pre-G2 sanity check

Before running `tools/g2_devices.sh`:

```bash
# On the Pi 5 host (not in container)
ls /dev/ttyUSB*           # expect /dev/ttyUSB0 (or /dev/ttyACM0 — adjust compose.yaml)
lsusb | grep -i intel     # expect "Intel Corp. RealSense D455"
sudo usermod -aG dialout $USER && newgrp dialout   # if /dev/ttyUSB0 needs root otherwise
```

If `/dev/ttyUSB0` is owned by root + dialout and your user is not in `dialout`, the container needs `--privileged: true` (already set in `compose.yaml`) or your user needs to join the group.

## D455 firmware

```bash
docker compose run --rm robot bash -lc '
  rs-fw-update --recover  # only if rs-enumerate-devices shows recovery mode
  rs-fw-update --update_fw  # update to latest firmware
'
```

Skip unless `rs-enumerate-devices` reports an outdated firmware version.

## Network

- Pi and workstation on the **same** Wi-Fi network / subnet.
- AP "client isolation" or "AP isolation" **off**.
- Cyclone DDS multicast not blocked by firewall.
- Same `ROS_DOMAIN_ID` (default `9` in compose.yaml).
- If multiple QuickBots ever share a network: increment `ROS_DOMAIN_ID` per robot, or use Zenoh bridges.

## Power-on order

1. Charge Create 2 to full (green LED solid).
2. USB-C bank powering Pi; wait for Pi boot LEDs to settle.
3. SSH from workstation: `ssh quickbot@quickbot.local` (or static IP).
4. `cd ~/quickbot && docker compose run --rm robot bash`.
5. Inside: `python3 -m create2_driver.smoke --duration 0.5 --speed 50` for first contact.

## Power-off order

1. Cancel any active Nav2 / RMF tasks.
2. `docker compose down` if `compose up` was used (run-style stops on exit).
3. `sudo shutdown -h now` on the Pi; wait for green LED to extinguish.
4. Unplug the USB-C bank.
5. Power off Create 2 with the physical button.
