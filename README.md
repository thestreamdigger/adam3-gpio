# ADAM3-GPIO

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/thestreamdigger/adam3-gpio)
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)](https://www.raspberrypi.org/)
[![Python](https://img.shields.io/badge/python-3.7%2B-yellow.svg)](https://www.python.org/)
[![MPD](https://img.shields.io/badge/MPD-compatible-lightgrey.svg)](https://www.musicpd.org/)
[![moOde](https://img.shields.io/badge/moOde-9.2%2B-orange.svg)](https://moodeaudio.org/)

## Overview & Background
ADAM3-GPIO blends hardware and software to recreate an early CD player-style interface on a Raspberry Pi running moOde audio player—where you can literally watch the seconds tick away as the music plays, see the status lights come alive to indicate different functions, and even check how many tracks are loaded or the total runtime of the current album/playlist. It's all glowingly presented without the need to scroll or unlock screens (like on a tablet or a phone). The setup features a spartan 4-digit 7-segment LED display, four status LEDs, and a single multi-function push button—just enough for that straightforward, track-and-time display we all know from traditional CD players.

Version 3.0 uses the TM1652 display with UART communication and WS2812D status LEDs for improved performance and simplified wiring.

## What Has Been Achieved
Adam has grown from the ground up along with my coding knowledge, with valuable assistance from Claude AI for code reviews and optimization. This partnership helped surpass the initial goal of a single script driving the display hardware. The various toggle scripts now manage key playback modes (random, repeat, single, consume) by lighting up the appropriate status LEDs in blue, while the display can easily switch between showing elapsed or remaining time (on the fly), total runtime, or even the number of tracks in the current playlist/album.

Delivering these features required fine-tuning real-time GPIO interactions and code structure—a process that offered me invaluable learning experiences. In essence, Adam now provides the streamlined, no-distractions user experience I originally envisioned.

## Hardware Constraints and Alternatives
The migration to WS2812D status LEDs has eliminated previous GPIO limitations. With only a single data pin required for four LEDs, there are no longer conflicts with I2S audio output, and PWM oscillation issues are completely resolved. The digital control provides precise brightness levels and stable operation.

While exploring other options, I came across Python-compatible microcontrollers—especially the Raspberry Pi Pico (RP2040)—which are both affordable and flexible for handling multiple LEDs. The WS2812D approach maintains this flexibility while keeping the system simple and focused.

## Future Development
The hardware side of the project now relies on even simpler elements. The WS2812D status LEDs open possibilities for enhanced visual feedback, including different colors for various states, fade effects, or breathing patterns. The single-pin requirement also frees up GPIO pins for additional hardware expansions.

Recently, I've been leaning toward UART connectivity for more universal integration. Nearly all SBC music streamers support USB for both control and data, offering a simpler foundation to build upon while freeing up the Pi's GPIO for more custom hardware expansions.

For now, development here will likely focus on bug fixes or new ideas I pick up when I have time to refactor, while firmly keeping the current Adam hardware design for stability and simplicity. Adam is a champion and will keep its rightful place, hopefully inspiring you to embark on your own projects.

## Features

### Visual Interface
- **4-digit LED Display (TM1652)**
  - Track numbers (`-XX-`)
  - Total tracks (`XX--`)
  - Playback time (`MM:SS`)
  - Volume levels (`--XX`)
  - Multiple brightness levels
  - Automatic colon blinking

- **Status LEDs (WS2812D)**
  - 4 individually addressable LEDs
  - Blue color indication
  - 3 synchronized brightness levels
  - Playback mode indicators
  - Stable digital control

  #### Optional LED Overlay Effects
  - Startup chase (service start)
  - Track pulse (on track change)

  Effects are short one-shots and automatically restore the normal LED state. Durations in configuration are expressed in seconds.

### Controls
- **Multi-function Button**
  - Short press: Random playback
  - Long press: System shutdown

- **System Shutdown**
  - Hardware button: Press and hold for 2+ seconds
  - Command line: `pkill -SIGINT -f "adam3-gpio.*main.py"`
  
  Both methods execute identical shutdown sequence:
  1. Stop audio playback
  2. Turn off display and LEDs
  3. Power off system

### Advanced Features
- **Real-time Configuration**
  - No restart required
  - Dynamic display modes
  - Adjustable brightness
  - Customizable timings

# Technical Manual

## Table of Contents
1. [Hardware Setup](#hardware-setup)
2. [GPIO Pinout](#gpio-pinout)
3. [Hardware Components](#hardware-components)
4. [Project Structure](#project-structure)
5. [Configuration Reference](#configuration-reference)
6. [Features & Usage](#features--usage)
7. [Service Installation](#service-installation)

## Hardware Setup

### Required Components
- Raspberry Pi (tested on Model 4B)
- TM1652 4-digit 7-segment display
- 4x WS2812D LEDs (DIP package)
- 1x Momentary push button
- Optional: Rotary encoder with push button
- Jumper wires

## GPIO Pinout

```
                           Raspberry Pi
                            +--------+
                 3.3V  [1]  | o    o |  [2]  5V
           SDA1/GPIO2  [3]  | o    o |  [4]  5V
           SCL1/GPIO3  [5]  | o    o |  [6]  GND
                GPIO4  [7]  | o    o |  [8]  GPIO14 (UART TX → Display)
                  GND  [9]  | o    o |  [10] GPIO15
               GPIO17 [11]  | o    o |  [12] GPIO18
               GPIO27 [13]  | o    o |  [14] GND
               GPIO22 [15]  | o    o |  [16] GPIO23 (Encoder A)
                 3.3V [17]  | o    o |  [18] GPIO24 (Encoder B)
               GPIO10 [19]  | o    o |  [20] GND
                GPIO9 [21]  | o    o |  [22] GPIO25
               GPIO11 [23]  | o    o |  [24] GPIO8
                  GND [25]  | o    o |  [26] GPIO7
                GPIO0 [27]  | o    o |  [28] GPIO1
                GPIO5 [29]  | o    o |  [30] GND
                GPIO6 [31]  | o    o |  [32] GPIO12
               GPIO13 [33]  | o    o |  [34] GND
               GPIO19 [35]  | o    o |  [36] GPIO16
               GPIO26 [37]  | o    o |  [38] GPIO20 (Button)
                  GND [39]  | o    o |  [40] GPIO21 (Status LEDs Data)
                            +--------+
```

### Status LEDs Chain Wiring
```
GPIO21 → Data_In(LED0) → Data_Out → Data_In(LED1) → Data_Out → Data_In(LED2) → Data_Out → Data_In(LED3)
5V     → VCC (all LEDs)
GND    → GND (all LEDs)

LED Assignment:
- LED 0: Repeat mode
- LED 1: Random mode  
- LED 2: Single mode
- LED 3: Consume mode
```

## Hardware Components

### TM1652 Display
- **Connections**:
  - TX: GPIO 14 (UART)
  - VCC: 3.3V or 5V
  - GND: GND
- **Features**:
  - 4-digit 7-segment display
  - UART communication (19200 baud)
  - Brightness control (1-8)
  - Automatic colon blinking
  - Multiple display modes

### Status LEDs Chain
- **Connections**:
  - Data: GPIO 21
  - VCC: 5V
  - GND: GND
- **Features**:
  - 4 individually addressable WS2812D LEDs
  - 24-bit color control (RGB)
  - Digital data transmission
  - 3 brightness levels (8, 16, 32)
  - Blue color indication (RGB 0,0,X)
  - No external resistors required

### Control Button
- Main button on GPIO 20
- Functions:
  - Short press: Toggle roulette mode (random playback)
  - Long press: System shutdown

### Hardware Permissions
**Important**: WS2812D LED control requires root privileges due to hardware timing requirements.

- **Status LEDs (WS2812D)**: Requires root access to `/dev/mem` for precise timing control
- **Display (TM1652)**: Accessible via UART with root privileges
- **Button**: Accessible via GPIO with root privileges

**Service Configuration**: The systemd service runs as `root` to enable LED control. This is required for the `rpi-ws281x` library to access hardware memory directly.

## Project Structure

```
adam3-gpio/
├── config/                               # Configuration files
│   └── settings.json                     # Main configuration file
│
├── docs/                                 # Documentation files
│   ├── TM1652_V1.1_EN.pdf                # TM1652 datasheet
│   └── WS2812D-F5-15MA.pdf               # WS2812D datasheet
│
├── examples/                             # Example configuration files
│   └── adam3-gpio.example.service        # Systemd service with MPD check
│
├── scripts/                              # Utility scripts
│   ├── toggle_scripts/                   # Display and playback mode toggles
│   │   ├── toggle_brightness.py
│   │   ├── toggle_consume.sh
│   │   ├── toggle_display.py
│   │   ├── toggle_headless.sh
│   │   ├── toggle_random.sh
│   │   ├── toggle_repeat.sh
│   │   └── toggle_single.sh
│   ├── roulette.sh                       # Random playbook
│   └── roulette_album.sh                 # Album-based random
│
├── src/                                  # Source code
│   ├── core/                             # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py                     # Configuration management
│   │   ├── mpd_client.py                 # MPD communication
│   │   └── signal_handler.py             # Signal handling
│   │
│   ├── hardware/                         # Hardware interfaces
│   │   ├── __init__.py
│   │   ├── button/                       # Button control
│   │   │   ├── __init__.py
│   │   │   └── controller.py
│   │   ├── display/                      # TM1652 display driver
│   │   │   ├── __init__.py
│   │   │   └── tm1652.py
│   │   └── led/                          # Status LEDs control
│   │       ├── __init__.py
│   │       └── controller.py
│   │
│   ├── service/                          # Main services
│   │   ├── __init__.py
│   │   └── player_service.py             # Main player logic
│   │
│   ├── utils/                            # Utilities
│   │   ├── __init__.py
│   │   └── logger.py                     # Logging system
│   │
│   ├── __init__.py                       # Package initialization
│   ├── __version__.py                    # Version information
│   └── main.py                           # Application entry point
│
├── CHANGELOG.md                          # Version history
├── install.sh                           # Main installation script
├── LICENSE                               # License information
├── README.md                             # Project documentation
├── requirements.txt                      # Python dependencies
└── status.sh                             # System status check script
```

### Module Descriptions

#### Core (`src/core/`)
- `config.py`: Configuration management with real-time updates
- `mpd_client.py`: MPD client wrapper with connection handling

#### Hardware (`src/hardware/`)
- `button/`: Button controller with multi-function support
- `display/`: TM1652 display driver
- `led/`: Status LEDs control

#### Service (`src/service/`)
- `player_service.py`: Main service orchestrating display, LEDs, and MPD

#### Utils (`src/utils/`)
- `logger.py`: Centralized logging system

#### Scripts (`scripts/`)
- `toggle_scripts/`: User interface control scripts
- `roulette.sh`: Random playbook scripts

#### Configuration (`config/`)
- `settings.json`: Centralized configuration for all components

## Configuration Reference

### MPD Connection
```json
"mpd": {
    "host": "localhost",                  // MPD server address
    "port": 6600                          // MPD server port
}
```
Controls the connection to the MPD server. Used by `MPDClient` in `src/core/mpd_client.py`.

### GPIO Settings
```json
"gpio": {
    "button": 20,                         // Main control button
    "display": {
        "serial_port": "/dev/ttyAMA0",    // UART port for TM1652 (default)
        "baudrate": 19200                 // Communication speed
    },
    "status_leds": {
        "pin": 21,                        // Data pin for status LEDs chain
        "count": 4,                       // Number of LEDs
        "brightness": 32,                 // Default brightness
        "order": "GRB"                    // Color order
    }
}
```
Used by hardware controllers in `src/hardware/`. Note the single status LEDs pin configuration.

### Display Settings
```json
"display": {
    "brightness": 8,                      // Default brightness level
    "brightness_levels": {
        "led": [8, 16, 32],              // Status LEDs brightness values (0-255)
        "display": [3, 6, 8]              // TM1652 brightness levels
    },
    "mode": "elapsed",                   // Time display mode (elapsed/remaining)
    "pause_mode": {
        "blink_interval": 1               // Display blink rate when paused
    },
    "play_mode": {
        "track_number": {
            "show_number": true,          // Show track numbers
            "display_time": 2             // How long to show track number
        }
    },
    "stop_mode": {
        "stop_symbol_time": 2,            // Duration of stop symbol
        "track_total_time": 2,            // Duration of track count
        "playlist_time": 2                // Duration of playlist time
    }
}
```
Controls display behavior in `src/hardware/display/tm1652.py` and status LEDs in `src/hardware/led/controller.py`.

### Timing Configuration
```json
"timing": {
    "command_cooldown": 0.5,              // Delay between commands
    "long_press_time": 2,                 // Time for long press detection
    "update_interval": 0.5,               // Display refresh rate
    "volume_display_duration": 3          // How long volume shows
}
```
Used throughout the system for timing control, especially in `PlayerService`.
 
### Effects (LED overlays)
```json
"effects": {
    "enabled": true,
    "events": {
        "on_track_change": {
            "effect": "flash",
            "repeat_count": 1,
            "on_duration": 0.18,
            "off_duration": 0.0,
            "r": 0, "g": 153, "b": 255
        }
    }
}
```
Only `on_track_change` is currently supported.

### Update Trigger
```json
"updates": {
    "trigger": {
        "file": ".update_trigger",        // Update trigger file
        "check_interval": 0.5,            // Check frequency
        "debounce_time": 0.1              // Update debounce time
    }
}
```
Used by `PlayerService` for real-time configuration updates.

### Logging
```json
"logging": {
    "enable": true,                       // Enable/disable logging
    "level": "INFO",                      // Log level
    "format": "[{level}] {message}"       // Log message format
}
```
Controls logging behavior in `src/utils/logger.py`.

## Installation

### Quick Installation

```bash
# Clone and install
git clone https://github.com/thestreamdigger/adam3-gpio.git adam3-gpio
cd adam3-gpio
./install.sh
```

### Installation Options

```bash
# Full installation with systemd service
./install.sh

# Install without systemd service
./install.sh --skip-service

# Quiet installation
./install.sh -q
```

### Requirements
- Raspberry Pi (tested on Model 4B)
- Current Raspberry Pi OS (2024+)
- moOde audio player 9.2+
- Python 3.7+

### Hardware Setup
- **TM1652 Display**: GPIO14 (UART TX), 5V, GND
- **Status LEDs**: GPIO21 (Data), 5V, GND  
- **Button**: GPIO20, GND

**Note**: The installer automatically configures GPIO permissions and user groups.

## Usage

### Manual Execution

```bash
# Run manually
./venv/bin/python3 src/main.py

# Or activate virtual environment first
source venv/bin/activate
python3 src/main.py
```

### Service Management

If installed with systemd service:

```bash
# Check service status
sudo systemctl status adam3-gpio.service

# Start/stop service
sudo systemctl start adam3-gpio.service
sudo systemctl stop adam3-gpio.service

# View logs
sudo journalctl -u adam3-gpio.service -f
```

### Status Check

```bash
# Check system status
./status.sh
```

## License
This project is free to use and modify. Feel free to tinker and tailor it to your setup.

## Acknowledgments
- [moOde audio player](https://moodeaudio.org/) - The foundation audio system that makes this project possible
- [MPD](https://www.musicpd.org/) - The robust music server at the core
- [TM1652 Datasheet](docs/TM1652_V1.1_EN.pdf) - Essential hardware documentation for UART display
- [python-mpd2](https://github.com/Mic92/python-mpd2) - Python interface to MPD
- [rpi-ws281x](https://github.com/rpi-ws281x/rpi-ws281x-python) - WS2812D LED control library
- [pyserial](https://github.com/pyserial/pyserial) - Serial communication for TM1652
- [ashuffle](https://github.com/joshkunz/ashuffle) - MPD random playback utility
- The open source community for inspiration and shared knowledge

## Support
For additional support or bug reports, please visit the project's GitHub repository.
