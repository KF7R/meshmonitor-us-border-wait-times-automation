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

Match documented commands with `(?i)^/[a-z0-9]+bwt# U.S. Border Wait Times — MeshMonitor Automation Engine

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

. The script also accepts the legacy `/<name>border` suffix, but the message trigger must explicitly include it if you want to serve those commands.

## Commands

Commands use the form `/<name>bwt`.

Each border location is organized by **POE Area**. The **Area command** returns every crossing currently grouped by CBP under that area. **Individual POE commands** are nested directly below the area and return only that crossing.

### Mexican Border

#### Nogales
- **Area:** `/nogalesbwt` — all Nogales POEs
  - `/deconcinibwt` — DeConcini
  - `/mariposabwt` — Mariposa
  - `/morleybwt` — Morley Gate

#### El Paso
- **Area:** `/elpasobwt` — all El Paso POEs
  - `/botabwt` — Bridge of the Americas (BOTA)
  - `/pdnbwt` — Paso Del Norte (PDN)
  - `/stantonbwt` — Stanton DCL
  - `/ysletabwt` — Ysleta

#### Brownsville
- **Area:** `/brownsvillebwt` — all Brownsville POEs
  - B&M
  - Gateway
  - Los Indios
  - Veterans International

#### Calexico
- **Area:** `/calexicobwt` — all Calexico POEs
  - East
  - West

#### Eagle Pass
- **Area:** `/eaglepassbwt` — all Eagle Pass POEs
  - Bridge I
  - Bridge II

#### Hidalgo/Pharr
- **Area:** `/hidalgopharrbwt` — all Hidalgo/Pharr POEs
  - `/anzalduasbwt` — Anzalduas International Bridge
  - `/hidalgobwt` — Hidalgo
  - `/pharrbwt` — Pharr

#### Laredo
- **Area:** `/laredobwt` — all Laredo POEs
  - Bridge I
  - Bridge II
  - Colombia Solidarity
  - World Trade Bridge

#### Progreso
- **Area:** `/progresobwt` — all Progreso POEs
  - Donna International Bridge
  - Progreso International Bridge

#### Andrade
- **Area:** `/andradebwt`

#### Columbus
- **Area:** `/columbusbwt`

#### Del Rio
- **Area:** `/delriobwt`

#### Douglas
- **Area:** `/douglasbwt` — Douglas (Raul Hector Castro)

#### Fort Hancock
- **Area:** `/forthancockbwt`

#### Lukeville
- **Area:** `/lukevillebwt`

#### Naco
- **Area:** `/nacobwt`

#### Otay Mesa
- **Area:** `/otaymesabwt`

#### Presidio
- **Area:** `/presidiobwt`

#### Rio Grande City
- **Area:** `/riograndecitybwt`

#### Roma
- **Area:** `/romabwt`

#### San Luis
- **Area:** `/sanluisbwt`

#### San Ysidro
- **Area:** `/sanysidrobwt`
- **Alias:** `/sandiegobwt`

#### Santa Teresa
- **Area:** `/santateresabwt`

#### Tecate
- **Area:** `/tecatebwt`

### Canadian Border

#### Blaine
- **Area:** `/blainebwt` — all Blaine POEs
  - Pacific Highway
  - Peace Arch
  - Point Roberts

#### Buffalo/Niagara Falls
- **Area:** `/buffalobwt` — all Buffalo/Niagara Falls POEs
  - Lewiston Bridge
  - Peace Bridge
  - Rainbow Bridge
  - Whirlpool Bridge

#### Calais
- **Area:** `/calaisbwt` — all Calais POEs
  - Ferry Point
  - International Avenue
  - Milltown

#### Detroit
- **Area:** `/detroitbwt` — all Detroit POEs
  - Ambassador Bridge
  - Gordie Howe International Bridge
  - Windsor Tunnel

#### Alexandria Bay
- **Area:** `/alexandriabaybwt`
  - Thousand Islands Bridge

#### Champlain
- **Area:** `/champlainbwt`

#### Derby Line
- **Area:** `/derbylinebwt`
  - Derby Line I-91

#### Highgate Springs
- **Area:** `/highgatespringsbwt`

#### Houlton
- **Area:** `/houltonbwt`

#### International Falls
- **Area:** `/internationalfallsbwt`

#### Jackman
- **Area:** `/jackmanbwt`

#### Lynden
- **Area:** `/lyndenbwt`

#### Madawaska
- **Area:** `/madawaskabwt`

#### Massena
- **Area:** `/massenabwt`

#### Norton
- **Area:** `/nortonbwt`

#### Ogdensburg
- **Area:** `/ogdensburgbwt`

#### Pembina
- **Area:** `/pembinabwt`

#### Port Huron
- **Area:** `/porthuronbwt`
  - Bluewater Bridge

#### Sault Ste. Marie
- **Area:** `/saultstemariebwt`
  - International Bridge - SSM

#### Sumas
- **Area:** `/sumasbwt`

#### Sweetgrass
- **Area:** `/sweetgrassbwt`

> **Individual POE resolution:** the script checks CBP `crossing_name` before the grouped `port_name`. A unique individual crossing command therefore returns only that POE. Short aliases such as `/botabwt`, `/pdnbwt`, and `/morleybwt` are provided where useful.

> **Multiple-message behavior:** Area commands can exceed the compact reply budget. When that happens, the script returns multiple responses and the Automation Engine sends them sequentially with 2-second delays. The exact POE list can change if CBP changes its `port_name` grouping.

A live test of `/detroitbwt` successfully delivered all three Detroit POE replies using the serialized 2-second Delay workflow.

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

## Installation from GitHub

If MeshMonitor is installed in `~/meshmonitor` and `~/meshmonitor/scripts` is bind-mounted to `/data/scripts`, install the responder directly from this repository:

```bash
mkdir -p ~/meshmonitor/scripts
curl -fsSL https://raw.githubusercontent.com/KF7R/meshmonitor-us-border-wait-times-automation/main/border_wait.py \
  -o ~/meshmonitor/scripts/border_wait.py \
  && chmod +x ~/meshmonitor/scripts/border_wait.py
```

The scripts directory should be mounted into the MeshMonitor container:

```yaml
services:
  meshmonitor:
    volumes:
      - meshmonitor-data:/data
      - ./scripts:/data/scripts
```

### Verify the downloaded script

Test an individual POE directly inside the MeshMonitor container. This lookup does **not** transmit a Meshtastic message:

```bash
docker exec -e MESSAGE="/mariposabwt" meshmonitor \
  python3 /data/scripts/border_wait.py
```

Example result:

```json
{"response": "🟢 Mariposa · 6am-10pm · 🚗0m 🚶0m"}
```

Then verify an Area command:

```bash
docker exec -e MESSAGE="/nogalesbwt" meshmonitor \
  python3 /data/scripts/border_wait.py
```

The Area command should return the individual POEs currently grouped by CBP under Nogales.

### Update from GitHub

To replace the installed script with the current version from the `main` branch:

```bash
curl -fsSL https://raw.githubusercontent.com/KF7R/meshmonitor-us-border-wait-times-automation/main/border_wait.py \
  -o ~/meshmonitor/scripts/border_wait.py \
  && chmod +x ~/meshmonitor/scripts/border_wait.py
```

After updating, run one of the local verification commands above before testing over Meshtastic.

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
border_wait.responses[3]
...continue for every returned element
```

Send each existing element with a separate **Send Message** action, in array order. Three actions are not enough for all areas: Buffalo, Brownsville, El Paso, and Laredo can return four or more messages. Long crossing lines can also require additional segments. Inspect the script output for each area you serve and add a condition, send action, and delay for every array index it can return. A fixed graph will omit any entries beyond its configured last index; this repository does not provide an automatic array loop.

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
                         │                  ↓
                         │               Delay 2s
                         │                  ↓
                         │       responses[3] exists? → Send Message 3
                         │                  ↓
                         │       continue for all configured indices
```

Select the MeshMonitor source and Meshtastic channel you want the replies transmitted on in the **Send Message** actions.

### Limit replies to a single MeshMonitor source

By default, a **Send Message** action with no selected source uses the source that triggered the automation. To force BWT replies to transmit through one specific connected MeshMonitor source, set `sourceIds` in every `action.sendMessage` node.

Example:

```json
{
  "id": "send_single",
  "type": "action.sendMessage",
  "params": {
    "text": "{{ var.border_wait.response }}",
    "replyToTrigger": true,
    "sourceIds": [
      "YOUR-MESHMONITOR-SOURCE-ID"
    ]
  }
}
```

For a multi-response workflow, add the same `sourceIds` array to every Send Message node (`send_0`, `send_1`, etc.). This leaves the trigger, script, conditions, and delays unchanged.

This is especially useful for advanced JSON workflows that can no longer be opened in the visual builder because they contain branches/fanout.

A live test confirmed this configuration can receive the BWT command through any connected source while transmitting the reply only through the selected source.

> Use the source ID from your own MeshMonitor installation. Do not copy an ID from another deployment.

For multi-POE commands such as `/detroitbwt`, `/nogalesbwt`, `/elpasobwt`, `/laredobwt`, `/buffalobwt`, and `/blainebwt`, do **not** connect multiple Send Message actions directly back-to-back. The tested pattern is:

```text
Send Message 0 → Delay 2s → Send Message 1 → Delay 2s → Send Message 2 → Delay 2s → Send Message 3 → ...
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
- Bounds each reply to 195 characters and 195 UTF-8 bytes, including emoji.
- Returns multiple responses when the combined report exceeds that budget; oversized individual crossing lines are split into additional segments without dropping text.
- Returns the unavailable message for malformed or empty CBP feeds.
- Does not transmit commercial lane data.

### Local regression tests

Run `python3 -m unittest discover -s tests -v` from the repository root. Tests use synthetic CBP records and mocked network calls; they do not transmit mesh messages.

## Requirements

- MeshMonitor with Automation Engine and Run Script / Send Message actions
- Python 3
- Network access from the MeshMonitor container to the CBP endpoint

No third-party Python packages are required.

## License

MIT

