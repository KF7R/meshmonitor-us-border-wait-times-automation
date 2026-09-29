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

Commands use the form `/<port>border`.

Examples:

```text
/nogalesborder
/detroitborder
/blaineborder
/sanysidroborder
```

### Mexican border

- `/andradeborder`
- `/brownsvilleborder`
- `/calexicoborder`
- `/columbusborder`
- `/delrioborder`
- `/douglasborder`
- `/eaglepassborder`
- `/elpasoborder`
- `/forthancockborder`
- `/hidalgopharrborder`
- `/laredoborder`
- `/lukevilleborder`
- `/nacoborder`
- `/nogalesborder`
- `/otaymesaborder`
- `/presidioborder`
- `/progresoborder`
- `/riograndecityborder`
- `/romaborder`
- `/sanluisborder`
- `/sanysidroborder` (alias: `/sandiegoborder`)
- `/santateresaborder`
- `/tecateborder`

### Canadian border

- `/alexandriabayborder`
- `/blaineborder`
- `/buffaloborder`
- `/calaisborder`
- `/champlainborder`
- `/derbylineborder`
- `/detroitborder`
- `/highgatespringsborder`
- `/houltonborder`
- `/internationalfallsborder`
- `/jackmanborder`
- `/lyndenborder`
- `/madawaskaborder`
- `/massenaborder`
- `/nortonborder`
- `/ogdensburgborder`
- `/pembinaborder`
- `/porthuronborder`
- `/saultstemarieborder`
- `/sumasborder`
- `/sweetgrassborder`

CBP can group multiple crossings under one port. For example, `/nogalesborder` can include DeConcini, Mariposa and Morley Gate.

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

A short pause between sequential messages is recommended so multiple packets are not transmitted back-to-back.

Example:

```text
Run Script
 ├─ response exists ─────────────→ Send Message
 └─ responses[0] exists ─────────→ Send Message 0
                                  ↓
                               Pause
                                  ↓
                    responses[1] exists?
                         ├─ yes → Send Message 1
                         │          ↓
                         │        Pause
                         │          ↓
                         │   responses[2] exists?
                         │       └─ yes → Send Message 2
```

Select the MeshMonitor source and Meshtastic channel you want the replies transmitted on in the **Send Message** actions.

## Testing

Test the script directly inside the MeshMonitor container without transmitting:

```bash
docker exec -e MESSAGE="/nogalesborder" meshmonitor \
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
