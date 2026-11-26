# FakeTec v0.5.5 Ad Hoc Relay and Persistence

Experimental MeshCore 1.18 companion firmware for
compatible nRF52840 ProMicro FakeTec devices.

## New features

- Companion CLI relay control.
- Optional persistent relay startup policy.
- Shared relay state between OLED and CLI.
- Safe boot-OFF policy by default.
- Existing Quick Actions and messaging features retained.

## CLI commands

    get relay
    set relay on
    set relay off
    get relay.boot
    set relay.boot last
    set relay.boot off

Select LAST to restore the previous relay state
after a reboot or power interruption.

Select OFF to always boot with custom relay disabled.

The custom ad hoc relay remains independent of
the official Off-Grid Repeat functionality.

## Build

Prepare the compatible MeshCore source checkout
using the v0.5.4 build instructions.

    bash build-faketec-v055.sh

## Intended use

Camping, hiking, temporary off-grid deployments,
disaster response, and areas with sparse or
nonexistent dedicated repeater coverage.

## Cautions

MeshCore learns and reuses message paths.
Moving or removing relays may invalidate learned
routes. Additional forwarding can increase
airtime utilization and battery consumption.

Avoid unnecessary relaying within established meshes.

Experimental community firmware.
Initial FakeTec hardware testing successful.
