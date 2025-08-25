# wifi_live_dashboard_wdutil.py
# macOS live Wi-Fi chart using `sudo wdutil info` instead of airport

import subprocess, sys, time, datetime, math, platform, threading, re
from collections import deque, defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

SAMPLE_INTERVAL_SEC = 0.5
ROLLING_WINDOW_SEC = 300
DISPLAY_WINDOW_SEC = 60  # Show only last 60 seconds by default
MATERIAL_KEYS = {
    '1': 'baseline',
    '2': 'wood',
    '3': 'plastic',
    '4': 'glass',
    '5': 'aluminium',
    '6': 'copper',
    '7': 'steel',
}

# Background colors for each material
MATERIAL_COLORS = {
    'baseline': '#f8f9fa',    # Light gray
    'wood': '#f4e4bc',        # Light brown
    'plastic': '#e3f2fd',     # Light blue
    'glass': '#f1f8e9',       # Light green
    'aluminium': '#eceff1',   # Light blue-gray
    'copper': '#fff3e0',      # Light orange
    'steel': '#fafafa',       # Very light gray
}
CSV_FILENAME = f"wifi_readings_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def parse_wdutil_output(txt: str):
    """
    Parse `sudo wdutil info` output for RSSI and noise.
    Looks for lines like:
      RSSI                 : -40 dBm
      Noise                : -90 dBm
    Only looks in the WIFI section, not BLUETOOTH section.
    """
    rssi, noise = None, None
    in_wifi_section = False
    
    for line in txt.splitlines():
        line = line.strip()
        
        # Check if we're entering the WIFI section
        if line == "WIFI":
            in_wifi_section = True
            continue
        
        # Check if we're leaving the WIFI section (entering another section)
        if line.startswith("————") and in_wifi_section:
            # Look ahead to see if next section is starting
            continue
        elif in_wifi_section and len(line) > 0 and not line.startswith("————") and line.isupper() and not ":" in line:
            # This is likely a new section header (like BLUETOOTH)
            in_wifi_section = False
            continue
            
        # Only parse RSSI/Noise if we're in the WIFI section
        if in_wifi_section:
            if "RSSI" in line and ":" in line:
                try:
                    # Extract the value between : and dBm
                    value_part = line.split(":")[1].strip()
                    rssi = float(re.findall(r"[-]?\d+", value_part)[0])
                except: pass
            elif "Noise" in line and ":" in line:
                try:
                    # Extract the value between : and dBm
                    value_part = line.split(":")[1].strip()
                    noise = float(re.findall(r"[-]?\d+", value_part)[0])
                except: pass
                
    if rssi is None or noise is None:
        raise ValueError("Could not parse RSSI/Noise from wdutil output.")
    return rssi, noise

def read_wifi_metrics_macos():
    """
    Call `sudo wdutil info` to get metrics.
    """
    cmd = ["sudo", "wdutil", "info"]
    out = subprocess.check_output(cmd, text=True)
    return parse_wdutil_output(out)

# ---------------- same LiveData class as before ----------------
class LiveData:
    def __init__(self, window_sec=ROLLING_WINDOW_SEC):
        self.window_sec = window_sec
        self.times, self.rssi, self.noise, self.snr = deque(), deque(), deque(), deque()
        self.snr_by_material = defaultdict(list)
        self.material_events = []
        self.current_material = "baseline"
        self.current_band = "2.4"
        self.csv_rows = []
        self._csv_lock = threading.Lock()
        # Track material changes for background coloring
        self.material_transitions = []  # [(time, material), ...]

    def append(self, ts, rssi, noise):
        snr = rssi - noise
        self.times.append(ts); self.rssi.append(rssi); self.noise.append(noise); self.snr.append(snr)
        cutoff = ts - self.window_sec
        while self.times and self.times[0] < cutoff:
            self.times.popleft(); self.rssi.popleft(); self.noise.popleft(); self.snr.popleft()
        # Clean up old material transitions
        self.material_transitions = [(t, m) for t, m in self.material_transitions if t >= cutoff]
        self.snr_by_material[self.current_material].append(snr)
        with self._csv_lock:
            self.csv_rows.append({
                "timestamp": datetime.datetime.fromtimestamp(ts).isoformat(),
                "band": self.current_band,
                "material": self.current_material,
                "rssi_dbm": rssi,
                "noise_dbm": noise,
                "snr_db": snr,
            })

    def set_material(self, material, timestamp):
        """Set current material and record the transition time"""
        self.current_material = material
        self.material_transitions.append((timestamp, material))

    def clear_data(self):
        """Clear all collected data and reset to baseline"""
        self.times.clear()
        self.rssi.clear()
        self.noise.clear()
        self.snr.clear()
        self.snr_by_material.clear()
        self.material_events.clear()
        self.material_transitions.clear()
        self.current_material = "baseline"
        # Keep CSV data but add a separator comment
        with self._csv_lock:
            self.csv_rows.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "band": self.current_band,
                "material": "--- CLEARED ---",
                "rssi_dbm": 0,
                "noise_dbm": 0,
                "snr_db": 0,
            })

    def export_csv(self, filename):
        with self._csv_lock:
            if self.csv_rows:
                pd.DataFrame(self.csv_rows).to_csv(filename, index=False)

# ---------------- Plotting ----------------
def main():
    data = LiveData()
    start = time.time()
    
    # Create figure with enhanced navigation
    fig, ax = plt.subplots(figsize=(12,7))
    fig.canvas.manager.set_window_title('Wi-Sense - WiFi Signal Monitor')
    
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("dBm (RSSI/Noise), dB (SNR)")
    ax.set_title("Live Wi-Fi Signal (from wdutil)")
    ax.grid(True, alpha=0.3)
    # Set initial background color for baseline
    ax.set_facecolor(MATERIAL_COLORS.get('baseline', '#ffffff'))

    (line_rssi,) = ax.plot([], [], label="RSSI")
    (line_noise,) = ax.plot([], [], label="Noise")
    (line_snr,) = ax.plot([], [], label="SNR")
    ax.legend(loc="upper right")
    stats_box = ax.text(0.02,0.98,"", transform=ax.transAxes, va="top",ha="left",
                        bbox=dict(boxstyle="round", alpha=0.1))
    
    # Track view mode and scrolling
    is_stats_view = False
    auto_scroll = True  # Auto-scroll to follow live data
    display_window = DISPLAY_WINDOW_SEC  # Current display window size

    def update_x_axis():
        """Update x-axis limits based on current mode"""
        if not data.times:
            return
            
        xs = [t-start for t in data.times]
        if not xs:
            return
            
        if auto_scroll:
            # Auto-scroll mode: show the last 'display_window' seconds
            current_time = xs[-1]
            ax.set_xlim(max(0, current_time - display_window), current_time + 5)
        # If not auto-scroll, keep current view (user has manually navigated)

    def on_scroll(event):
        """Handle mouse wheel scrolling for zooming"""
        nonlocal display_window, auto_scroll
        if is_stats_view:
            return
            
        if event.inaxes != ax:
            return
            
        # Get current x-axis limits
        xleft, xright = ax.get_xlim()
        current_width = xright - xleft
        
        # Zoom factor
        zoom_factor = 1.2 if event.button == 'down' else 1/1.2
        
        # Calculate new width
        new_width = current_width * zoom_factor
        new_width = max(10, min(new_width, ROLLING_WINDOW_SEC))  # Limit zoom range
        
        # Center the zoom on mouse position
        xdata = event.xdata if event.xdata else (xleft + xright) / 2
        new_xleft = xdata - new_width * (xdata - xleft) / current_width
        new_xright = new_xleft + new_width
        
        ax.set_xlim(new_xleft, new_xright)
        display_window = new_width
        auto_scroll = False  # Disable auto-scroll when user zooms
        plt.draw()

    def on_key_press(event):
        """Handle additional keyboard shortcuts for navigation"""
        nonlocal auto_scroll, display_window
        if is_stats_view:
            return
            
        if event.key == 'home':
            # Reset to auto-scroll mode
            auto_scroll = True
            display_window = DISPLAY_WINDOW_SEC
            print("[navigation] Auto-scroll enabled")
        elif event.key == 'left':
            # Pan left
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            ax.set_xlim(xleft - width*0.1, xright - width*0.1)
            auto_scroll = False
            plt.draw()
        elif event.key == 'right':
            # Pan right
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            ax.set_xlim(xleft + width*0.1, xright + width*0.1)
            auto_scroll = False
            plt.draw()
        elif event.key == 'up':
            # Zoom in
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            center = (xleft + xright) / 2
            new_width = width * 0.8
            ax.set_xlim(center - new_width/2, center + new_width/2)
            display_window = new_width
            auto_scroll = False
            plt.draw()
        elif event.key == 'down':
            # Zoom out
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            center = (xleft + xright) / 2
            new_width = min(width * 1.25, ROLLING_WINDOW_SEC)
            ax.set_xlim(center - new_width/2, center + new_width/2)
            display_window = new_width
            auto_scroll = False
            plt.draw()

    def create_statistics_view():
        """Update x-axis limits based on current mode"""
        if not data.times:
            return
            
        xs = [t-start for t in data.times]
        if not xs:
            return
            
        if auto_scroll:
            # Auto-scroll mode: show the last 'display_window' seconds
            current_time = xs[-1]
            ax.set_xlim(max(0, current_time - display_window), current_time + 5)
        # If not auto-scroll, keep current view (user has manually navigated)

    def on_scroll(event):
        """Handle mouse wheel scrolling for zooming"""
        nonlocal display_window, auto_scroll
        if is_stats_view:
            return
            
        if event.inaxes != ax:
            return
            
        # Get current x-axis limits
        xleft, xright = ax.get_xlim()
        current_width = xright - xleft
        
        # Zoom factor
        zoom_factor = 1.2 if event.button == 'down' else 1/1.2
        
        # Calculate new width
        new_width = current_width * zoom_factor
        new_width = max(10, min(new_width, ROLLING_WINDOW_SEC))  # Limit zoom range
        
        # Center the zoom on mouse position
        xdata = event.xdata if event.xdata else (xleft + xright) / 2
        new_xleft = xdata - new_width * (xdata - xleft) / current_width
        new_xright = new_xleft + new_width
        
        ax.set_xlim(new_xleft, new_xright)
        display_window = new_width
        auto_scroll = False  # Disable auto-scroll when user zooms
        plt.draw()

    def on_key_press(event):
        """Handle additional keyboard shortcuts for navigation"""
        nonlocal auto_scroll, display_window
        if is_stats_view:
            return
            
        if event.key == 'home':
            # Reset to auto-scroll mode
            auto_scroll = True
            display_window = DISPLAY_WINDOW_SEC
            print("[navigation] Auto-scroll enabled")
        elif event.key == 'left':
            # Pan left
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            ax.set_xlim(xleft - width*0.1, xright - width*0.1)
            auto_scroll = False
            plt.draw()
        elif event.key == 'right':
            # Pan right
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            ax.set_xlim(xleft + width*0.1, xright + width*0.1)
            auto_scroll = False
            plt.draw()
        elif event.key == 'up':
            # Zoom in
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            center = (xleft + xright) / 2
            new_width = width * 0.8
            ax.set_xlim(center - new_width/2, center + new_width/2)
            display_window = new_width
            auto_scroll = False
            plt.draw()
        elif event.key == 'down':
            # Zoom out
            xleft, xright = ax.get_xlim()
            width = xright - xleft
            center = (xleft + xright) / 2
            new_width = min(width * 1.25, ROLLING_WINDOW_SEC)
            ax.set_xlim(center - new_width/2, center + new_width/2)
            display_window = new_width
            auto_scroll = False
            plt.draw()

    def create_statistics_view():
        """Create histogram view showing median values for each material"""
        ax.clear()
        ax.set_title("Material Statistics - Median Values")
        ax.set_xlabel("Materials")
        ax.set_ylabel("Signal Strength (dBm/dB)")
        ax.grid(True, alpha=0.3)
        
        # Collect data for materials that have measurements
        materials = []
        rssi_medians = []
        noise_medians = []
        snr_medians = []
        colors = []
        
        # Calculate median values for each material
        for material, snr_values in data.snr_by_material.items():
            if snr_values:  # Only include materials with data
                materials.append(material)
                
                # Get corresponding RSSI and Noise values for this material
                material_rssi = []
                material_noise = []
                
                # Find RSSI and Noise values for this material from CSV data
                with data._csv_lock:
                    for row in data.csv_rows:
                        if row['material'] == material and row['material'] != '--- CLEARED ---':
                            material_rssi.append(row['rssi_dbm'])
                            material_noise.append(row['noise_dbm'])
                
                if material_rssi and material_noise:
                    rssi_medians.append(pd.Series(material_rssi).median())
                    noise_medians.append(pd.Series(material_noise).median())
                    snr_medians.append(pd.Series(snr_values).median())
                    colors.append(MATERIAL_COLORS.get(material, '#ffffff'))
        
        if not materials:
            ax.text(0.5, 0.5, "No data available\nStart collecting data and try again", 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            return
        
        # Create bar chart
        x_pos = range(len(materials))
        width = 0.25
        
        # Create bars for each metric
        bars1 = ax.bar([x - width for x in x_pos], rssi_medians, width, 
                      label='RSSI (dBm)', alpha=0.8, color='blue')
        bars2 = ax.bar(x_pos, noise_medians, width, 
                      label='Noise (dBm)', alpha=0.8, color='orange')
        bars3 = ax.bar([x + width for x in x_pos], snr_medians, width, 
                      label='SNR (dB)', alpha=0.8, color='green')
        
        # Customize the chart
        ax.set_xticks(x_pos)
        ax.set_xticklabels(materials, rotation=45, ha='right')
        ax.legend()
        
        # Add value labels on bars
        def add_value_labels(bars, values):
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{value:.1f}', ha='center', va='bottom', fontsize=9)
        
        add_value_labels(bars1, rssi_medians)
        add_value_labels(bars2, noise_medians)
        add_value_labels(bars3, snr_medians)
        
        # Add material color backgrounds
        for i, (material, color) in enumerate(zip(materials, colors)):
            ax.axvspan(i-0.4, i+0.4, alpha=0.2, color=color, zorder=0)
        
        plt.tight_layout()

    def restore_live_view():
        """Restore the live graph view"""
        nonlocal line_rssi, line_noise, line_snr, stats_box, auto_scroll, display_window
        ax.clear()
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("dBm (RSSI/Noise), dB (SNR)")
        ax.set_title("Live Wi-Fi Signal (from wdutil)")
        ax.grid(True, alpha=0.3)
        ax.set_facecolor(MATERIAL_COLORS.get(data.current_material, '#ffffff'))
        
        # Reset navigation
        auto_scroll = True
        display_window = DISPLAY_WINDOW_SEC
        
        # Recreate the line objects
        (line_rssi,) = ax.plot([], [], label="RSSI")
        (line_noise,) = ax.plot([], [], label="Noise")
        (line_snr,) = ax.plot([], [], label="SNR")
        ax.legend(loc="upper right")
        
        # Recreate the stats box
        stats_box = ax.text(0.02,0.98,"", transform=ax.transAxes, va="top",ha="left",
                           bbox=dict(boxstyle="round", alpha=0.1))

    def update_background_colors():
        """Update background colors based on material transitions"""
        # Clear existing background patches
        for patch in ax.patches[:]:
            if hasattr(patch, '_material_background'):
                patch.remove()
        
        if not data.times or not data.material_transitions:
            # Set default background for current material
            ax.set_facecolor(MATERIAL_COLORS.get(data.current_material, '#ffffff'))
            return
            
        # Get current time range
        start_time = min(data.times) if data.times else 0
        end_time = max(data.times) if data.times else 0
        time_range = [t - start for t in data.times]
        
        if not time_range:
            return
            
        current_x_min = min(time_range)
        current_x_max = max(time_range)
        
        # Sort transitions by time
        transitions = sorted([(t - start, m) for t, m in data.material_transitions if start_time <= t <= end_time])
        
        # Add current material at the end
        if not transitions or transitions[-1][1] != data.current_material:
            transitions.append((current_x_max, data.current_material))
            
        # Create background sections
        prev_x = current_x_min
        prev_material = 'baseline'
        
        # If we have transitions, use the first one's material for the beginning
        if transitions:
            prev_material = transitions[0][1]
            
        for x_pos, material in transitions:
            if prev_x < x_pos:
                # Create background patch for this section
                color = MATERIAL_COLORS.get(prev_material, '#ffffff')
                y_min, y_max = ax.get_ylim()
                patch = ax.axvspan(prev_x, x_pos, alpha=0.3, color=color, zorder=0)
                patch._material_background = True  # Mark as background patch
                
            prev_x = x_pos
            prev_material = material
            
        # Handle the last section
        if prev_x < current_x_max:
            color = MATERIAL_COLORS.get(prev_material, '#ffffff')
            y_min, y_max = ax.get_ylim()
            patch = ax.axvspan(prev_x, current_x_max, alpha=0.3, color=color, zorder=0)
            patch._material_background = True

    def on_key(event):
        nonlocal start, line_rssi, line_noise, line_snr, stats_box, is_stats_view, auto_scroll, display_window
        if event.key in MATERIAL_KEYS:
            if not is_stats_view:  # Only allow material changes in live view
                t = time.time()
                data.set_material(MATERIAL_KEYS[event.key], t)
                ax.axvline(t-start, ls="--", c="gray", alpha=0.5)
                print(f"[material] {data.current_material}")
        elif event.key == 'b':
            if not is_stats_view:  # Only allow band toggle in live view
                data.current_band = "5" if data.current_band=="2.4" else "2.4"
                print(f"[band] {data.current_band} GHz")
        elif event.key == 's':
            # Switch to statistics view
            is_stats_view = True
            create_statistics_view()
            print("[stats] Switched to statistics view")
        elif event.key == 'c':
            if is_stats_view:
                # Return to live view from stats
                is_stats_view = False
                restore_live_view()
                print("[live] Switched back to live view")
            else:
                # Clear graph and reset to baseline (original functionality)
                data.clear_data()
                ax.clear()
                # Recreate the plot elements
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("dBm (RSSI/Noise), dB (SNR)")
                ax.set_title("Live Wi-Fi Signal (from wdutil)")
                ax.grid(True, alpha=0.3)
                # Set initial background color
                ax.set_facecolor(MATERIAL_COLORS.get('baseline', '#ffffff'))
                # Reset navigation
                auto_scroll = True
                display_window = DISPLAY_WINDOW_SEC
                # Recreate the line objects
                (line_rssi,) = ax.plot([], [], label="RSSI")
                (line_noise,) = ax.plot([], [], label="Noise")
                (line_snr,) = ax.plot([], [], label="SNR")
                ax.legend(loc="upper right")
                # Recreate the stats box
                stats_box = ax.text(0.02,0.98,"", transform=ax.transAxes, va="top",ha="left",
                                   bbox=dict(boxstyle="round", alpha=0.1))
                # Reset start time
                start = time.time()
                print("[clear] Graph cleared, reset to baseline")
        elif event.key == 'q':
            print("Saving CSV and quitting...")
            data.export_csv(CSV_FILENAME)
            plt.close(fig)

    # Connect mouse and keyboard events
    fig.canvas.mpl_connect('scroll_event', on_scroll)
    fig.canvas.mpl_connect('key_press_event', on_key_press)
    fig.canvas.mpl_connect('key_press_event', on_key)

    def update(_frame):
        # Only update if we're in live view mode
        if is_stats_view:
            return
            
        ts = time.time()
        try:
            rssi, noise = read_wifi_metrics_macos()
        except Exception as e:
            print("Error:", e)
            return
        data.append(ts, rssi, noise)
        xs = [t-start for t in data.times]
        line_rssi.set_data(xs, list(data.rssi))
        line_noise.set_data(xs, list(data.noise))
        line_snr.set_data(xs, list(data.snr))
        
        # Update x-axis with scrolling/zooming support
        update_x_axis()
        
        # Update y-axis
        all_y = list(data.rssi)+list(data.noise)+list(data.snr)
        if all_y:
            ax.set_ylim(min(all_y)-5, max(all_y)+5)

        # Update background colors for materials
        update_background_colors()

        # show mean/median SNR per material
        lines = [f"Current material: {data.current_material} ({data.current_band} GHz)"]
        if auto_scroll:
            lines.append("Auto-scroll: ON (Home=reset, Arrows=navigate)")
        else:
            lines.append("Auto-scroll: OFF (Home=reset, Arrows=navigate)")
        for mat, snrs in data.snr_by_material.items():
            if snrs:
                mean = pd.Series(snrs).mean()
                med = pd.Series(snrs).median()
                lines.append(f"{mat:<10} mean={mean:.1f}  med={med:.1f}")
        stats_box.set_text("\n".join(lines))
        return line_rssi,line_noise,line_snr,stats_box

    from matplotlib.animation import FuncAnimation
    ani = FuncAnimation(fig, update, interval=int(SAMPLE_INTERVAL_SEC*1000))
    print("Controls: 1..7=materials, b=toggle band, s=statistics, c=clear/return")
    print("Navigation: Mouse wheel=zoom, Arrow keys=pan/zoom, Home=auto-scroll, q=quit+save CSV")
    plt.show()
    data.export_csv(CSV_FILENAME)
    print("CSV saved to", CSV_FILENAME)

if __name__=="__main__":
    main()