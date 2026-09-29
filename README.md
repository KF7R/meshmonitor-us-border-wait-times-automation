# U.S. Border Wait Times — MeshMonitor Automation Engine

A MeshMonitor **Automation Engine** version of the U.S. land-border wait-time responder.

It reports current passenger-vehicle and pedestrian wait times for U.S. land ports of entry on both the Mexican and Canadian borders using the public U.S. Customs and Border Protection (CBP) Border Wait Times JSON feed.

No CBP API key is required.

This repository is intentionally separate from the older Auto Responder/script-trigger implementation.

## How it works

The Automation Engine handles the Meshtastic trigger and transmission:

```text
Message Trigger → Run Script → Conditional Branches → Send Message
```

The included `border_wait.py` script does only the CBP lookup, port resolution, formatting, and JSON return value.

The incoming Meshtastic message is available to the script as `MESSAGE`.

## Commands

Commands use the form `/<port>bwt`. These are **city/CBP port-level commands**: when CBP groups more than one Port of Entry (POE)/crossing under that city or port, the command returns **all of those POEs**. If the combined report is too large for one Meshtastic reply, the Automation Engine can send it as **multiple messages**.

Commands marked **ALL POEs** below are notable examples where one city/port command can return several crossings from the current CBP grouping.

Examples:

```text
/nogalesbwt
/detroitbwt
/blainebwt
/sanysidrobwt
```

### Mexican border

- `/andradebwt`
- `/brownsvillebwt` — **ALL POEs** grouped by CBP under Brownsville
- `/calexicobwt` — **ALL POEs** grouped by CBP under Calexico
- `/columbusbwt`
- `/delriobwt`
- `/douglasbwt`
- `/eaglepassbwt`
- `/elpasobwt` — **ALL POEs** grouped by CBP under El Paso
- `/forthancockbwt`
- `/hidalgopharrbwt`
- `/laredobwt` — **ALL POEs** grouped by CBP under Laredo
- `/lukevillebwt`
- `/nacobwt`
- `/nogalesbwt` — **ALL POEs** grouped by CBP under Nogales (for example DeConcini, Mariposa and Morley Gate)
- `/otaymesabwt`
- `/presidiobwt`
- `/progresobwt`
- `/riograndecitybwt`
- `/romabwt`
- `/sanluisbwt`
- `/sanysidrobwt` (alias: `/sandiegobwt`) — returns all crossings CBP groups under the San Ysidro port entry
- `/santateresabwt`
- `/tecatebwt`

### Canadian border

- `/alexandriabaybwt`
- `/blainebwt` — **ALL POEs** grouped by CBP under Blaine (for example Pacific Highway, Peace Arch and Point Roberts)
- `/buffalobwt` — **ALL POEs** grouped by CBP under Buffalo/Niagara Falls
- `/calaisbwt`
- `/champlainbwt`
- `/derbylinebwt`
- `/detroitbwt` — **ALL POEs** grouped by CBP under Detroit (for example Ambassador Bridge, Gordie Howe International Bridge and Windsor Tunnel)
- `/highgatespringsbwt`
- `/houltonbwt`
- `/internationalfallsbwt`
- `/jackmanbwt`
- `/lyndenbwt`
- `/madawaskabwt`
- `/massenabwt`
- `/nortonbwt`
- `/ogdensburgbwt`
- `/pembinabwt`
- `/porthuronbwt`
- `/saultstemariebwt`
- `/sumasbwt`
- `/sweetgrassbwt`

**Important:** the responder follows CBP's `port_name` grouping rather than maintaining its own city-to-crossing list. Therefore a city/port command returns every matching POE/crossing present in that CBP group at the time of the request. Large groups—such as Nogales, El Paso, Brownsville, Laredo, Buffalo/Niagara Falls, Detroit and others—may exceed the compact reply budget and trigger **two or more Meshtastic messages**. The exact number depends on the crossings and wait-time data returned by CBP.

## What it reports

- 🟢 / 🔴 CBP open or closed status
- Published hours of operation
- 🚗 standard passenger-vehicle wait
- `READY` Ready Lane wait when available
- `SENTRI` on the Mexican border
- `NEXUS` on the Canadian border
- 🚶 pedestrian wait when available

Commercial traffic is intentionally omitted.

Example:

```text
🟢 DeConcini · 24 hrs · 🚗90m SENTRI 60m 🚶5m
🔴 Mariposa · CLOSED · 6am-10pm
```

## Data source

The script makes one request per invocation to:

```text
https://bwt.cbp.gov/api/waittimes
```

No authentication is required.

## Installation

Bind-mount a scripts directory into MeshMonitor if you do not already have one:

```yaml
services:
  meshmonitor:
    volumes:
      - meshmonitor-data:/data
      - ./scripts:/data/scripts
```

Copy `border_wait.py` into the mounted directory and make it executable:

```bash
cp border_wait.py ~/meshmonitor/scripts/
chmod +x ~/meshmonitor/scripts/border_wait.py
```

## Automation Engine setup

Create a JSON variable in MeshMonitor:

```text
Name: border_wait
Type: JSON
Scope: Global
Default: {}
Constant: Off
```

Create an Automation Engine workflow that starts with a message trigger for the border command pattern you want to serve.

Basic graph:

```text
Message Trigger
    ↓
Run Script: border_wait.py
    ↓
Store result: border_wait
```

The script returns one of these forms.

Single reply:

```json
{"response":"<reply text>"}
```

Multiple replies:

```json
{"responses":["<reply 1>","<reply 2>","<reply 3>"]}
```

For a single reply, add a condition that checks for `border_wait.response` and then a **Send Message** action using that value.

For multiple replies, create branches for available array elements:

```text
border_wait.responses[0]
border_wait.responses[1]
border_wait.responses[2]
```

Send each existing element with a separate **Send Message** action.

A delay between sequential messages is **required for reliable multi-POE delivery**. Without it, MeshMonitor may attempt to transmit several Meshtastic packets too quickly and later replies can be missed. Use a **2-second Delay (`action.delay`)** between each Send Message action.

Example:

```text
Run Script
 ├─ response exists ─────────────→ Send Message
 └─ responses[0] exists ─────────→ Send Message 0
                                  ↓
                               Delay 2s
                                  ↓
                    responses[1] exists?
                         ├─ yes → Send Message 1
                         │          ↓
                         │        Delay 2s
                         │          ↓
                         │   responses[2] exists?
                         │       └─ yes → Send Message 2
```

Select the MeshMonitor source and Meshtastic channel you want the replies transmitted on in the **Send Message** actions.

For multi-POE commands such as `/detroitbwt`, `/nogalesbwt`, `/elpasobwt`, `/laredobwt`, `/buffalobwt`, and `/blainebwt`, do **not** connect multiple Send Message actions directly back-to-back. The tested pattern is:

```text
Send Message 0 → Delay 2s → Send Message 1 → Delay 2s → Send Message 2
```

This pacing is part of the intended Automation Engine setup, not just an optional cosmetic delay. It was verified in a live multi-POE test: `/detroitbwt` successfully delivered all three Detroit POE messages after the responses were serialized with 2-second Delay actions.

## Testing

Test the script directly inside the MeshMonitor container without transmitting:

```bash
docker exec -e MESSAGE="/nogalesbwt" meshmonitor \
  python3 /data/scripts/border_wait.py
```

You should receive JSON on stdout.

For example:

```json
{"response":"🟢 DeConcini · 24 hrs · 🚗5m SENTRI 10m 🚶0m"}
```

MeshMonitor Automation Engine test/dry-run can validate the graph and stored result. Use a live Meshtastic message as the final end-to-end test of the selected source and channel.

## Behavior

- Uses CBP `port_status` for open/closed state.
- Uses CBP's published hours.
- Uses numeric `delay_minutes` when available.
- Treats an explicitly closed lane as unavailable.
- Shows only lane categories with usable current data.
- Labels trusted-traveler lanes as `SENTRI` for Mexico and `NEXUS` for Canada.
- Keeps open crossings visible as `waits pending` when wait data is missing.
- Does not show stale lane waits when the overall port is closed.
- Uses an 8-second HTTP timeout.
- Uses a compact 195-character reply budget before returning multiple responses.
- Does not transmit commercial lane data.

## Requirements

- MeshMonitor with Automation Engine and Run Script / Send Message actions
- Python 3
- Network access from the MeshMonitor container to the CBP endpoint

No third-party Python packages are required.

## License

MIT
