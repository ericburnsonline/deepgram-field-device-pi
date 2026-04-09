# Field Notes Device (Raspberry Pi + Deepgram)

A field-deployable voice capture and transcription system built on Raspberry Pi with physical controls, LED state feedback, and real-time transcription using Deepgram.

This project is designed as a hands-on demo platform for exploring how unstructured voice input can be captured, processed, and surfaced through a simple UI in near real time.

## Demo

![Web UI](docs/ui-screenshot.png)  
![Breadboard Setup](docs/breadboard.jpg)

Note:  
The demo uses a 4-button membrane switch. All four buttons are wired and available for future functionality such as WiFi configuration.

## Recent Changes

- Refactored GPIO layout to enable optional I2S microphone support without pin conflicts
- Reassigned button inputs to maintain clean separation between control and audio interfaces
- Added multi-device audio support with automatic detection (I2S preferred, USB fallback)
- Improved resilience for real-world demo environments where hardware may vary

## What It Does

- Push-to-record voice capture (hardware button)
- Stores audio locally as `.wav`
- Sends recordings to Deepgram for transcription
- Displays transcripts and metadata in a web UI
- Uses LEDs to indicate device state
- Hosts a local web interface
- Auto-refreshing UI
- Supports multiple microphone types (auto-detect)

## Why This Exists

How do you turn real-world, unstructured voice input into structured, usable data at the edge?

## Hardware Requirements

- Raspberry Pi 4 (targeting Pi Zero 2 W in future)
- 3 LEDs (Red, Yellow, Green)
- 3+ buttons (Record, Upload, Skip, optional Spare)

### Microphone (Optional)

The system supports multiple microphone types:

- I2S MEMS microphone (e.g., INMP441) - preferred
- USB microphone or webcam mic (fallback)

If no microphone is detected, the system will enter an error state.

## GPIO Pin Mapping

### LEDs

| Function | GPIO | Physical Pin |
|----------|------|--------------|
| Red      | 17   | 11           |
| Yellow   | 27   | 13           |
| Green    | 22   | 15           |

### Buttons

| Function | GPIO | Physical Pin |
|----------|------|--------------|
| Record   | 24   | 16           |
| Upload   | 12   | 32           |
| Skip     | 21   | 40           |
| Spare    | 23   | 18           |

## LED State Mapping

| State      | Red   | Yellow | Green |
|------------|-------|--------|-------|
| Idle       | Off   | Off    | On    |
| Recording  | Off   | On     | Off   |
| Processing | On    | Off    | Off   |
| Error      | Blink | Off    | Off   |

## Wiring / Schematic

Add schematic here:

```
docs/schematic.png
```

Note:  
The microphone is optional and may not be present in the base wiring diagram.

## Project Structure

```
app/
  config.py
  deepgram_client.py
  device.py
  gpio_controller.py
  recorder.py
  state_manager.py
  storage.py
  webapp.py

data/
  recordings/
  transcripts/

.env
.env.example
```

## Setup

```
git clone https://github.com/ericburnsonline/deepgram-field-device-pi.git
cd deepgram-field-device-pi

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
nano .env
```

Add your Deepgram API key:

```
DEEPGRAM_API_KEY=your_key_here
```

## Audio Configuration

You can optionally force a specific microphone:

```
AUDIO_DEVICE=plughw:1,0
```

If left blank, the system will:
1. Prefer I2S microphones
2. Fall back to USB microphones

## Run

```
python -m app.device
```

## Web UI

```
http://<raspberry-pi-ip>:5000
```

## Audio Device Notes

List available devices:

```
arecord -l
```

Test recording:

```
arecord -D plughw:1,0 -f S16_LE -r 16000 test.wav
aplay test.wav
```

## Workflow

1. Press and hold Record
2. Speak
3. Release → saved locally
4. Press Upload
5. Transcription appears in UI

## UI Features

- Auto-refresh without full page reload
- Copy transcript button
- Download audio button
- Audio playback with duration
- Expandable metadata view
- Deep Dive JSON display
- Processing time display

## Development Approach (Vibe Coding)

This project was built using a vibe coding workflow:

- Rapid AI-assisted iteration
- Focus on working system first
- Structure evolved over time

## Security Notes

- `.env` excluded from version control
- Audio and transcript files are not committed
- Prototype/demo system, not production hardened

## Next Steps

- Highlight low-confidence words in transcripts
- Improve error handling and retry logic
- Offline / queued recording mode
- Tagging and structured note extraction
- Add OLED display for status and configuration
- Support Raspberry Pi Zero 2 W form factor

## Future Ideas

- Authentication for web interface
- Export integrations (Slack, email, etc.)
- Device configuration UI
- Enhanced demo modes for showcasing AI capabilities

## License

MIT

## Author

Eric Burns

## Final Thought

Capture → Process → Structure → Present
