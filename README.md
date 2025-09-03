# Wi-Sense - Real-time WiFi Signal Monitoring

A macOS application for real-time WiFi signal monitoring and analysis using `wdutil` command. This tool is designed for materials testing and WiFi signal analysis by monitoring RSSI (Received Signal Strength Indicator), noise levels, and SNR (Signal-to-Noise Ratio).

## Features

### Real-time Monitoring

- **Live WiFi Metrics**: Continuously monitors RSSI, noise, and calculated SNR
- **Visual Dashboard**: Real-time plotting with matplotlib showing signal trends
- **Configurable Sampling**: Default 0.5-second intervals with 5-minute rolling window
- **Scrollable Timeline**: Interactive navigation through data with 60-second default view
- **Zoom and Pan**: Mouse wheel and keyboard controls for detailed analysis
- **Auto-scroll Mode**: Automatically follows live data or manual navigation
- **Cross-platform**: Uses macOS `wdutil` command for accurate WiFi metrics

### Material Testing Support

- **Material Classification**: Built-in support for 7 different materials:
  - Baseline (reference measurement)
  - Wood
  - Plastic
  - Glass
  - Aluminum
  - Copper
  - Brass
- **Interactive Marking**: Use keyboard shortcuts (1-7) to mark current material during testing
- **Visual Indicators**: Vertical lines on charts mark material transition points
- **Background Color Coding**: Each material gets a distinct background color for easy visual identification
- **Statistical Analysis**: Real-time mean and median SNR calculations per material

### Band Support

- **Multi-band Monitoring**: Toggle between 2.4GHz and 5GHz bands
- **Band Labeling**: Current band displayed in the statistics panel
- **Easy Switching**: Press 'b' to toggle between bands during measurement

### Data Export

- **CSV Export**: Automatic data logging with timestamps
- **Comprehensive Data**: Includes timestamp, band, material, RSSI, noise, and SNR values
- **Auto-save**: Data saved automatically when program exits
- **Manual Save**: Press 'q' to save and quit at any time

## Installation

### Prerequisites

- macOS (required for `wdutil` command)
- Python 3.13+
- sudo access (required for `wdutil info`)

### Setup

1. Clone or download the project
2. Install dependencies using uv:

   ```bash
   uv sync
   ```

### Dependencies

- `matplotlib>=3.10.5` - For real-time plotting
- `pandas>=2.3.2` - For data manipulation and CSV export

## Usage

### Starting the Program

```bash
uv run python main.py
```

The program will:

1. Request sudo password for `wdutil` access
2. Open a matplotlib window showing real-time WiFi metrics
3. Start collecting data immediately

### Controls

#### Material and Data Controls

- **1-7**: Select material type (baseline, wood, plastic, glass, aluminum, copper, brass)
- **b**: Toggle between 2.4GHz and 5GHz band labels
- **s**: Switch to statistics view (histogram of median values per material)
- **c**: Clear graph and reset to baseline (in live view) / Return to live view (from statistics)
- **q**: Quit program and save CSV data

#### Navigation Controls (Live View Only)

- **Mouse wheel**: Zoom in/out at cursor position
- **Arrow keys**:
  - Left/Right: Pan horizontally through timeline
  - Up/Down: Zoom in/out
- **Home key**: Return to auto-scroll mode (follow live data)
- **Manual navigation**: Click and drag, or use built-in matplotlib toolbar

### Understanding the Display

#### Live View (Default)

- **Blue Line**: RSSI (Received Signal Strength) in dBm
- **Orange Line**: Noise floor in dBm  
- **Green Line**: SNR (Signal-to-Noise Ratio) in dB
- **Gray Dashed Lines**: Material transition markers
- **Background Colors**: Each material has a distinct background color to visually separate testing phases
- **Statistics Box**: Shows current material, band, and per-material statistics
- **Auto-scroll Indicator**: Shows current navigation mode

#### Navigation Modes

- **Auto-scroll Mode**: Default mode that follows live data, showing the last 60 seconds
- **Manual Navigation Mode**: Activated when user zooms or pans, allows exploration of historical data
- **Zoom Range**: From 10 seconds to full 5-minute window
- **Pan Capability**: Navigate through entire data timeline

#### Statistics View (Press 's')

- **Bar Chart**: Histogram showing median values for each tested material
- **Blue Bars**: Median RSSI values for each material
- **Orange Bars**: Median Noise values for each material
- **Green Bars**: Median SNR values for each material
- **Value Labels**: Exact median values displayed on top of each bar
- **Material Colors**: Background colors match the material color scheme
- **Comparison**: Easy visual comparison of material performance

#### Material Background Colors

- **Baseline**: Light gray background
- **Wood**: Light brown background
- **Plastic**: Light blue background
- **Glass**: Light green background
- **Aluminum**: Light blue-gray background
- **Copper**: Light orange background
- **brass**: Very light gray background

#### Interpreting Values

- **RSSI**: Higher (less negative) values indicate stronger signal
- **Noise**: Typically around -90 dBm, represents background interference
- **SNR**: Higher values indicate better signal quality (RSSI - Noise)

### Output Files

Data is saved to CSV files with timestamp in filename:

```text
wifi_readings_YYYYMMDD_HHMMSS.csv
```

CSV contains columns:

- `timestamp`: ISO format timestamp
- `band`: Current band setting (2.4 or 5)
- `material`: Current material being tested
- `rssi_dbm`: RSSI value in dBm
- `noise_dbm`: Noise value in dBm  
- `snr_db`: Calculated SNR in dB

## Use Cases

### Material Testing

1. Start program and establish baseline measurement
2. Place test material between WiFi source and receiver
3. Press corresponding number key (2-7) to mark material
4. Observe signal changes in real-time
5. Repeat for all materials you want to test
6. Press 's' to view statistics and compare median values across materials
7. Press 'c' to return to live view for more testing
8. Press 'c' again to clear graph and start fresh measurements when needed

### Signal Analysis

- Monitor WiFi stability over time
- Identify interference patterns
- Compare performance across different bands
- Analyze environmental effects on signal quality

### Research Applications

- Materials science: Testing RF transparency of materials
- Network optimization: Finding optimal AP placement
- Interference analysis: Identifying sources of signal degradation

## Technical Details

### WiFi Metrics Source

Uses macOS `sudo wdutil info` command which provides:

- Current RSSI from active WiFi connection
- Noise floor measurements
- Comprehensive WiFi adapter information

### Data Processing

- Rolling window keeps last 5 minutes of data in memory
- Real-time statistical calculations (mean, median) per material
- Automatic scaling and chart updates
- Thread-safe CSV logging

### Performance

- 0.5-second sampling interval (configurable)
- Minimal CPU usage with efficient data structures
- Real-time plotting without blocking data collection

## Configuration

### Customizable Parameters

```python
SAMPLE_INTERVAL_SEC = 0.5    # Sampling frequency
ROLLING_WINDOW_SEC = 300     # Data retention window (5 minutes)
MATERIAL_KEYS = {...}        # Material definitions
```

### Adding Materials

Modify the `MATERIAL_KEYS` dictionary in `main.py` to add custom materials or change key mappings.

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure sudo access for `wdutil info`
2. **No WiFi Connection**: Program requires active WiFi connection
3. **Missing Dependencies**: Run `uv sync` to install required packages

### Debug Information

The program includes error handling for parsing failures and will display specific error messages if `wdutil` output format changes.

## License

This project is provided as-is for research and educational purposes.