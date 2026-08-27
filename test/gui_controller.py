import customtkinter as ctk
from tkinter import messagebox
from tkinter import filedialog
import serial
import threading
import queue
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import matplotlib.dates as mdates
import json
import os
import re
import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib.figure import Figure

# Set modern theme defaults
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("blue")

class SDI12AnalyzerWindow(ctk.CTkToplevel):
    def __init__(self, master, log_file, base_dir):
        super().__init__(master)
        self.title("Live SDI-12 Analysis")
        self.geometry("900x600")
        self.log_file = log_file
        self.base_dir = base_dir
        self.df = None

        # Top Control Bar
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.pack(fill="x", padx=10, pady=10)
        
        self.refresh_btn = ctk.CTkButton(ctrl_frame, text="Refresh Data", command=self.load_data)
        self.refresh_btn.pack(side="left", padx=5)
        
        ctk.CTkLabel(ctrl_frame, text="Select Sensor:").pack(side="left", padx=(20, 5))
        self.sensor_var = ctk.StringVar(value="None")
        self.sensor_dropdown = ctk.CTkOptionMenu(ctrl_frame, variable=self.sensor_var, command=self.update_plots)
        self.sensor_dropdown.pack(side="left", padx=5)

        self.save_btn = ctk.CTkButton(ctrl_frame, text="Save All Results", command=self.save_all_results, fg_color="#17a2b8", hover_color="#138496")
        self.save_btn.pack(side="right", padx=5)

        # Tabbed View for Clutter Management
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        self.tab_ts = self.tabs.add("Time Series")
        self.tab_corr = self.tabs.add("Correlation")
        self.tab_reg = self.tabs.add("Regression")

        # Setup Matplotlib Figures for each tab
        self.fig_ts = Figure(figsize=(8, 3.5), dpi=100)
        self.canvas_ts = FigureCanvasTkAgg(self.fig_ts, master=self.tab_ts)
        self.canvas_ts.get_tk_widget().pack(fill="both", expand=True)

        self.fig_corr = Figure(figsize=(6, 3.5), dpi=100)
        self.canvas_corr = FigureCanvasTkAgg(self.fig_corr, master=self.tab_corr)
        self.canvas_corr.get_tk_widget().pack(fill="both", expand=True)
        
        self.fig_reg = Figure(figsize=(8, 3.5), dpi=100)
        self.canvas_reg = FigureCanvasTkAgg(self.fig_reg, master=self.tab_reg)
        self.canvas_reg.get_tk_widget().pack(fill="both", expand=True)

        self.load_data()

    def save_all_results(self):
        """Batch processes all sensors and saves figures to the selected directory."""
        if self.df is None or self.df.empty:
            messagebox.showwarning("Warning", "No data to save.")
            return

        # Setup Folders
        results_dir = os.path.join(self.base_dir, 'Results')
        dirs = {
            'timeseries': os.path.join(results_dir, 'Time Series'),
            'correlation': os.path.join(results_dir, 'Correlation'),
            'regression': os.path.join(results_dir, 'Regression')
        }
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)

        self.save_btn.configure(text="Saving...", state="disabled")
        self.update()

        # Iterate through all sensors in the dataset
        for sensor_id, group in self.df.groupby('Address'):
            m_cols = [c for c in group.columns if c.startswith('M')]
            t_cols = [c for c in group.columns if c.startswith('T') and c != 'Timestamp']
            
            m_data = group[['Timestamp'] + m_cols].dropna(axis=1, how='all').set_index('Timestamp').apply(pd.to_numeric, errors='coerce').dropna()
            t_data = group[['Timestamp'] + t_cols].dropna(axis=1, how='all').set_index('Timestamp').apply(pd.to_numeric, errors='coerce').dropna()
            
            if m_data.empty or t_data.empty: continue

            # Save Time Series
            fig_ts = Figure(figsize=(10, 8))
            ax1, ax2 = fig_ts.subplots(2, 1)
            m_data.plot(ax=ax1, title=f"Sensor {sensor_id}: Moisture (VMC)")
            t_data.plot(ax=ax2, title=f"Sensor {sensor_id}: Temperature (°C)")
            fig_ts.tight_layout()
            fig_ts.savefig(os.path.join(dirs['timeseries'], f'Sensor_{sensor_id}_TimeSeries.jpg'))

            # Save Correlation
            combined = pd.concat([m_data, t_data], axis=1).dropna()
            with np.errstate(divide='ignore', invalid='ignore'):
                corr_matrix = combined[m_data.columns].apply(lambda s: combined[t_data.columns].corrwith(s))
            fig_corr = Figure(figsize=(8, 6))
            ax_corr = fig_corr.add_subplot(111)
            sns.heatmap(corr_matrix, annot=True, cmap='viridis', fmt=".2f", ax=ax_corr)
            ax_corr.set_title(f"Sensor {sensor_id}: Pearson Correlation")
            fig_corr.tight_layout()
            fig_corr.savefig(os.path.join(dirs['correlation'], f'Sensor_{sensor_id}_Correlation.jpg'))

            # Save Regressions
            num_m = len(m_data.columns)
            cols = min(3, num_m)
            rows = int(np.ceil(num_m / cols))
            fig_reg = Figure(figsize=(4*cols, 4*rows))
            axes_reg = fig_reg.subplots(rows, cols)
            if num_m == 1: axes_reg = [axes_reg]
            else: axes_reg = axes_reg.flatten()

            for idx, m_col in enumerate(m_data.columns):
                correlations = corr_matrix[m_col].abs().dropna()
                if correlations.empty: continue
                best_t = correlations.idxmax()
                
                x, y = combined[best_t].values, combined[m_col].values
                p = np.polyfit(x, y, 1)
                
                ax = axes_reg[idx]
                ax.scatter(x, y, alpha=0.6)
                ax.plot(x, np.polyval(p, x), color='red')
                ax.set_title(f"{m_col} vs {best_t}")
                ax.text(0.05, 0.95, f"$R^2$={(corr_matrix.at[best_t, m_col]**2):.3f}\nCoeff={p[0]:.4f}", transform=ax.transAxes, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))

            fig_reg.tight_layout()
            fig_reg.savefig(os.path.join(dirs['regression'], f'Sensor_{sensor_id}_Regression.jpg'))

        self.save_btn.configure(text="Save All Results", state="normal")
        messagebox.showinfo("Success", f"Results saved to:\n{results_dir}")

    def load_data(self):
        try:
            self.df = pd.read_csv(self.log_file)
            self.df['Timestamp'] = pd.to_datetime(self.df['Timestamp'])
            sensors = [str(s) for s in self.df['Address'].unique()]
            self.sensor_dropdown.configure(values=sensors)
            if sensors and self.sensor_var.get() not in sensors:
                self.sensor_var.set(sensors[0])
            self.update_plots(self.sensor_var.get())
        except Exception as e:
            print(f"Waiting for valid CSV data... ({e})")

    def update_plots(self, sensor_id):
        if self.df is None or sensor_id == "None": return
        
        # Clear previous plots
        self.fig_ts.clf()
        self.fig_corr.clf()
        self.fig_reg.clf()

        # Filter Data
        group = self.df[self.df['Address'] == int(sensor_id)]
        m_cols = [c for c in group.columns if c.startswith('M')]
        t_cols = [c for c in group.columns if c.startswith('T') and c != 'Timestamp']
        
        m_data = group[['Timestamp'] + m_cols].dropna(axis=1, how='all').set_index('Timestamp').apply(pd.to_numeric, errors='coerce').dropna()
        t_data = group[['Timestamp'] + t_cols].dropna(axis=1, how='all').set_index('Timestamp').apply(pd.to_numeric, errors='coerce').dropna()
        
        if m_data.empty or t_data.empty: return

        # 1. Plot Time Series
        ax1, ax2 = self.fig_ts.subplots(2, 1)
        m_data.plot(ax=ax1, title="Moisture (VMC)")
        t_data.plot(ax=ax2, title="Temperature (°C)")
        self.fig_ts.tight_layout()
        self.canvas_ts.draw()

        # 2. Plot Correlation
        combined = pd.concat([m_data, t_data], axis=1).dropna()
        with np.errstate(divide='ignore', invalid='ignore'):
            corr_matrix = combined[m_data.columns].apply(lambda s: combined[t_data.columns].corrwith(s))
        ax_corr = self.fig_corr.add_subplot(111)
        sns.heatmap(corr_matrix, annot=True, cmap='viridis', fmt=".2f", ax=ax_corr)
        ax_corr.set_title("Pearson Correlation")
        self.fig_corr.tight_layout()
        self.canvas_corr.draw()

        # 3. Plot Regressions
        num_m = len(m_data.columns)
        cols = min(3, num_m)
        rows = int(np.ceil(num_m / cols))
        axes_reg = self.fig_reg.subplots(rows, cols)
        if num_m == 1: axes_reg = [axes_reg]
        else: axes_reg = axes_reg.flatten()

        for idx, m_col in enumerate(m_data.columns):
            correlations = corr_matrix[m_col].abs().dropna()
            if correlations.empty: continue
            best_t = correlations.idxmax()
            
            x, y = combined[best_t].values, combined[m_col].values
            p = np.polyfit(x, y, 1)
            
            ax = axes_reg[idx]
            ax.scatter(x, y, alpha=0.6)
            ax.plot(x, np.polyval(p, x), color='red')
            ax.set_title(f"{m_col} vs {best_t}")
            ax.text(0.05, 0.95, f"$R^2$={(corr_matrix.at[best_t, m_col]**2):.3f}\nCoeff={p[0]:.4f}", transform=ax.transAxes, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))

        self.fig_reg.tight_layout()
        self.canvas_reg.draw()

class ThermalControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thermal Controller Dashboard")
        self.root.geometry("800x700")
        
        self.data_queue = queue.Queue()
        self.is_running = False
        self.serial_conn = None
        self.PROFILE = [] 
        self.master_scroll = ctk.CTkScrollableFrame(root)
        self.master_scroll.pack(fill="both", expand=True)
        
        # Data storage for the graph
        self.time_data = []
        self.temp_data = []
        self.setpoint_data = []
        self.upper_band = []
        self.lower_band = []
        self.heat_data = []
        self.comp_data = []

        # --- 1. Connection & Editor Panel ---
        self.top_frame = ctk.CTkFrame(self.master_scroll, fg_color="transparent")
        self.top_frame.pack(pady=5, padx=20, fill="x")
        
        # Connection
        self.conn_frame = ctk.CTkFrame(self.top_frame)
        self.conn_frame.pack(side="left", fill="y", padx=(0, 5))
        
        # --- Thermal COM ---
        ctk.CTkLabel(self.conn_frame, text="Thermal COM:").pack(pady=(5,0))
        self.port_entry = ctk.CTkEntry(self.conn_frame, width=80)
        self.port_entry.insert(0, "COM10") 
        self.port_entry.pack(pady=2, padx=10)

        # --- SDI-12 COM ---
        ctk.CTkLabel(self.conn_frame, text="SDI-12 COM:").pack(pady=(5,0))
        self.sdi_port_entry = ctk.CTkEntry(self.conn_frame, width=80)
        self.sdi_port_entry.insert(0, "COM11") 
        self.sdi_port_entry.pack(pady=2, padx=10)
        
        # --- NEW: Sensor Count ---
        ctk.CTkLabel(self.conn_frame, text="# of Sensors Addr (0-N):").pack(pady=(5,0))
        self.sdi_count_entry = ctk.CTkEntry(self.conn_frame, width=80)
        self.sdi_count_entry.insert(0, "6") # Defaults to 6 sensors (0-5)
        self.sdi_count_entry.pack(pady=2, padx=10)

        ctk.CTkLabel(self.conn_frame, text="Working Directory:").pack(pady=(5,0))
        
        self.dir_frame = ctk.CTkFrame(self.conn_frame, fg_color="transparent")
        self.dir_frame.pack(fill="x", padx=10, pady=2)
        
        self.dir_var = ctk.StringVar(value=os.getcwd())
        self.dir_entry = ctk.CTkEntry(self.dir_frame, textvariable=self.dir_var, width=120)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.browse_btn = ctk.CTkButton(self.dir_frame, text="Browse", width=60, command=self.browse_dir)
        self.browse_btn.pack(side="left")

        ctk.CTkLabel(self.conn_frame, text="Log File Name:").pack(pady=(5,0))
        self.log_name_entry = ctk.CTkEntry(self.conn_frame, width=80)
        self.log_name_entry.insert(0, "GPLP_Live") 
        self.log_name_entry.pack(pady=2, padx=10)

        self.connect_btn = ctk.CTkButton(self.conn_frame, text="Connect & Run", command=self.toggle_connection, fg_color="#28a745", hover_color="#218838", width=100)
        self.connect_btn.pack(pady=10, padx=10)

        # --- 2. Profile Editor Panel ---

        self.editor_frame = ctk.CTkFrame(self.top_frame)
        self.editor_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        # Top Settings Row
        settings_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        settings_frame.pack(pady=5, fill="x")
        
        ctk.CTkLabel(settings_frame, text="Start Temp (°C):").grid(row=0, column=0, padx=5)
        
        # We trace this variable so changing the start temp updates the rates live
        self.start_temp_var = ctk.StringVar(value="25.0")
        self.start_temp_var.trace_add("write", self.update_rates)
        self.start_temp_entry = ctk.CTkEntry(settings_frame, width=60, textvariable=self.start_temp_var)
        self.start_temp_entry.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(settings_frame, text="Steps:").grid(row=0, column=2, padx=5)

        self.target_count_var = ctk.StringVar(value="1")
        self.step_count_entry = ctk.CTkEntry(settings_frame, width=50, textvariable=self.target_count_var)
        self.step_count_entry.grid(row=0, column=3, padx=5)

        self.update_steps_btn = ctk.CTkButton(settings_frame, text="Set", width=40, command=self.adjust_target_rows)
        self.update_steps_btn.grid(row=0, column=4, padx=5)

        # Dynamic Scrollable Area for Targets
        self.targets_scroll = ctk.CTkScrollableFrame(self.editor_frame, height=90)
        self.targets_scroll.pack(pady=5, padx=10, fill="x")
        self.target_rows = [] # Will hold our dynamic row data
        
        # Buttons and Listbox
        btn_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        self.generate_btn = ctk.CTkButton(btn_frame, text="Load Profile", width=120, command=self.generate_profile)
        self.generate_btn.pack(side="left", padx=10)
        
        self.clear_btn = ctk.CTkButton(btn_frame, text="Clear", width=60, fg_color="#dc3545", hover_color="#c82333", command=self.clear_profile)
        self.clear_btn.pack(side="left", padx=5)

        self.profile_listbox = ctk.CTkTextbox(self.editor_frame, height=70)
        self.profile_listbox.pack(pady=5, padx=10, fill="x")
        self.profile_listbox.configure(state="disabled")

        self.save_btn = ctk.CTkButton(btn_frame, text="Save Profile", width=100, command=self.save_profile)
        self.save_btn.pack(side="left", padx=5)

        self.load_def_btn = ctk.CTkButton(btn_frame, text="Load Saved Profile", width=100, command=self.load_profile)
        self.load_def_btn.pack(side="left", padx=5)
        
        # Build the initial single row
        self.adjust_target_rows()

        # --- 3. Telemetry Dashboard ---
        self.dash_frame = ctk.CTkFrame(self.master_scroll, fg_color="transparent")
        self.dash_frame.pack(pady=5)
        self.profile_label = ctk.CTkLabel(self.dash_frame, text="Waiting to start...", font=("Roboto", 14, "bold"), text_color="#17a2b8")
        self.profile_label.pack()
        self.temp_label = ctk.CTkLabel(self.dash_frame, text="Current Temp: -- °C  |  Setpoint: -- °C", font=("Roboto", 20))
        self.temp_label.pack()
        self.hardware_label = ctk.CTkLabel(self.dash_frame, text="Compressor: --  |  Heater: --", font=("Roboto", 14))
        self.hardware_label.pack()

        self.analysis_btn = ctk.CTkButton(self.dash_frame, text="View Live Analysis", command=self.open_analysis)
        self.analysis_btn.pack(pady=10)

        # --- 4. Live Graph ---
        self.graph_frame = ctk.CTkFrame(self.master_scroll)
        self.graph_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Setup Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(7, 3), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b') 
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temperature (°C)")
        self.ax.set_title("Live Thermal Profile", color="white")
        self.ax2 = self.ax.twinx()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- 5. Log Output ---
        self.log_text = ctk.CTkTextbox(self.master_scroll, width=760, height=60)
        self.log_text.pack(pady=10, padx=20)
        self.log_text.configure(state="disabled")

        self.root.after(100, self.process_queue)

    # --- Editor Logic ---
    def adjust_target_rows(self, *args):
        """Adds or removes rows to match the entry box without deleting existing data."""
        # --- NEW: Error checking for manual text input ---
        try:
            count = int(self.target_count_var.get())
            if count <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid positive number for steps.")
            return

        current_count = len(self.target_rows)
        
        if count > current_count:
            # Add new rows to the bottom
            for i in range(current_count, count):
                row_frame = ctk.CTkFrame(self.targets_scroll, fg_color="transparent")
                row_frame.pack(pady=2, fill="x")
                
                ctk.CTkLabel(row_frame, text=f"Step {i+1}:  Target (°C):").pack(side="left", padx=2)
                temp_var = ctk.StringVar(value="")
                temp_var.trace_add("write", self.update_rates)
                t_entry = ctk.CTkEntry(row_frame, width=50, textvariable=temp_var)
                t_entry.pack(side="left", padx=2)
                
                ctk.CTkLabel(row_frame, text="Mins:").pack(side="left", padx=2)
                dur_var = ctk.StringVar(value="")
                dur_var.trace_add("write", self.update_rates)
                d_entry = ctk.CTkEntry(row_frame, width=50, textvariable=dur_var)
                d_entry.pack(side="left", padx=2)
                
                rate_label = ctk.CTkLabel(row_frame, text="Rate: -- °C/hr", text_color="#17a2b8")
                rate_label.pack(side="left", padx=10)
                
                self.target_rows.append({
                    'frame': row_frame,
                    'temp_var': temp_var,
                    'dur_var': dur_var,
                    'rate_label': rate_label
                })
        elif count < current_count:
            # Remove excess rows from the bottom
            for i in range(current_count - 1, count - 1, -1):
                self.target_rows[i]['frame'].destroy()
                self.target_rows.pop(i)
                
        self.update_rates()

    def browse_dir(self):
        selected_dir = filedialog.askdirectory(initialdir=self.dir_var.get(), title="Select Working Directory")
        if selected_dir:
            self.dir_var.set(selected_dir)

    def update_rates(self, *args):
        """Calculates and updates the °C/hr label for every row live as you type."""
        try:
            prev_temp = float(self.start_temp_var.get())
        except ValueError:
            prev_temp = 0.0
            
        for row in self.target_rows:
            try:
                target = float(row['temp_var'].get())
                mins = float(row['dur_var'].get())
                
                if mins > 0:
                    # Calculate degrees per hour
                    rate = (target - prev_temp) / (mins / 60.0)
                    row['rate_label'].configure(text=f"Rate: {rate:+.1f} °C/hr")
                else:
                    row['rate_label'].configure(text="Rate: -- °C/hr")
                
                # The target of this step becomes the starting point for the next step
                prev_temp = target
            except ValueError:
                # If fields are empty or invalid, show placeholder
                row['rate_label'].configure(text="Rate: -- °C/hr")

    def open_analysis(self):
        log_filename = self.log_name_entry.get().strip()
        if not log_filename.lower().endswith(".csv"):
            log_filename += ".csv"
        
        full_log_path = os.path.join(self.dir_var.get(), log_filename)
        
        SDI12AnalyzerWindow(self.root, full_log_path, self.dir_var.get())

    def generate_profile(self):
        """Reads the rows and saves them to the PROFILE array for the hardware."""
        if self.is_running:
            messagebox.showwarning("Warning", "Cannot load a new profile while running.")
            return
            
        self.PROFILE.clear()
        self.profile_listbox.configure(state="normal")
        self.profile_listbox.delete("1.0", "end")
        
        step_num = 1
        for row in self.target_rows:
            try:
                target = float(row['temp_var'].get())
                duration = float(row['dur_var'].get())
                
                if duration <= 0:
                    raise ValueError
                    
                self.PROFILE.append((target, duration))
                
                # Determine if this is a hold or a ramp for the display label
                if step_num == 1:
                    prev = float(self.start_temp_var.get())
                else:
                    prev = self.PROFILE[step_num - 2][0]
                    
                if target == prev:
                    action = "Hold at"
                else:
                    action = "Ramp to"
                    
                self.profile_listbox.insert("end", f"Step {step_num}: {action} {target}°C for {duration} mins\n")
                step_num += 1
                
            except ValueError:
                messagebox.showerror("Error", f"Missing or invalid data in Step {step_num}.")
                return
                
        self.profile_listbox.configure(state="disabled")

    def clear_profile(self):
        if self.is_running: return
        self.PROFILE.clear()
        self.profile_listbox.configure(state="normal")
        self.profile_listbox.delete("1.0", "end")
        self.profile_listbox.configure(state="disabled")

    # --- Threading & Comms ---
    def log(self, message):
        self.data_queue.put({"type": "log", "msg": message})

    def update_profile_status(self, message):
        self.data_queue.put({"type": "status", "msg": message})

    def toggle_connection(self):
        if not self.PROFILE:
            messagebox.showerror("Error", "Please add at least one step.")
            return

        if not self.is_running:
            port = self.port_entry.get()
            self.is_running = True
            self.connect_btn.configure(text="Disconnect & Stop", fg_color="#dc3545", hover_color="#c82333")
            
            # Clear graph data for a new run
            self.time_data.clear()
            self.temp_data.clear()
            self.setpoint_data.clear()
            self.upper_band.clear()
            self.lower_band.clear()
            self.heat_data.clear()
            self.comp_data.clear()
            self.ax.clear()
            self.canvas.draw()
            
            self.thread = threading.Thread(target=self.serial_worker, args=(port,), daemon=True)
            self.thread.start()

            sdi_port = self.sdi_port_entry.get()
            try:
                sdi_port = self.sdi_port_entry.get().strip()
                raw_count = self.sdi_count_entry.get()
                
                # Format the filename safely
                log_filename = self.log_name_entry.get().strip()
                if not log_filename:
                    log_filename = "GPLP_Live"
                if not log_filename.lower().endswith(".csv"):
                    log_filename += ".csv"

                full_log_path = os.path.join(self.dir_var.get(), log_filename)
                
                try:
                    num_sensors = int(raw_count)
                except ValueError:
                    num_sensors = 0
                    self.log(f"Notice: SDI-12 skipped. '{raw_count}' is not a valid number.")
                    
                if sdi_port and num_sensors > 0:
                    # Pass the log_filename as the third argument here
                    self.sdi_thread = threading.Thread(target=self.sdi12_worker, args=(sdi_port, num_sensors, log_filename), daemon=True)
                    self.sdi_thread.start()
                elif not sdi_port:
                    self.log("Notice: SDI-12 skipped. No COM port entered.")
            except Exception as e:
                self.log(f"CRITICAL GUI ERROR starting SDI-12: {e}")

        else:
            self.is_running = False
            self.connect_btn.configure(text="Connect & Run", fg_color="#28a745", hover_color="#218838")
            self.update_profile_status("Profile Stopped.")

    def serial_worker(self, port):
        """BACKGROUND THREAD: Handles real serial comms and profile timing."""
        try:
            self.log(f"Connecting to ESP32 on {port}...")
            self.serial_conn = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            self.log("Connected! Live data active.")

            current_step_index = 0
            run_start_time = time.time()
            step_start_time = run_start_time
            current_duration_sec = 0

            def send_step(index):
                target, duration_mins = self.PROFILE[index]
                command = f"T:{target},D:{duration_mins}\n"
                status_msg = f"Running Cycle {index + 1}/{len(self.PROFILE)}: Target {target}°C"
                self.log(f"\n>> Sending {status_msg} -> {command.strip()}")
                self.update_profile_status(status_msg)
                
                if self.serial_conn: 
                    self.serial_conn.write(command.encode('utf-8'))
                return time.time(), duration_mins * 60.0

            if self.PROFILE:
                step_start_time, current_duration_sec = send_step(current_step_index)

            while self.is_running:
                # --- Cycle Management Logic ---
                if current_step_index < len(self.PROFILE):
                    elapsed_time = time.time() - step_start_time
                    if elapsed_time >= current_duration_sec:
                        current_step_index += 1
                        if current_step_index < len(self.PROFILE):
                            step_start_time, current_duration_sec = send_step(current_step_index)
                        else:
                            self.log("\n>> Profile complete! Holding final temperature.")
                            self.update_profile_status("Profile Complete. Holding final temp.")
                            current_step_index += 1

                # --- REAL Telemetry Reading Logic ---
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    
                    if line.startswith("ACK:"):
                        self.log(f">> ESP32 Confirms: {line}")
                    elif "," in line:
                        data = line.split(',')
                        if len(data) == 4:
                            # Convert to floats for plotting
                            curr_temp = float(data[0]) 
                            setpoint = float(data[1])
                            comp_on = "ON" if data[2] == "1" else "OFF"
                            heat_on = "ON" if data[3] == "1" else "OFF"
                            
                            current_timestamp = datetime.now()
                            
                            self.data_queue.put({
                                "type": "telemetry", 
                                "time": current_timestamp,
                                "temp": curr_temp, 
                                "setpoint": setpoint,
                                "comp": comp_on,
                                "heat": heat_on
                            })
                time.sleep(0.1)
                
        except serial.SerialException:
            self.log(f"\nError: Could not open {port}. Is the board plugged in?")
            self.update_profile_status("Connection Error.")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            self.log("Disconnected.")

    def process_queue(self):
        """MAIN THREAD: Updates the GUI and Graph."""
        try:
            while True:
                data = self.data_queue.get_nowait()
                
                if data["type"] == "log":
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", data["msg"] + "\n")
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
                    
                elif data["type"] == "telemetry":
                    self.temp_label.configure(
                        text=f"Current Temp: {data['temp']:.1f} °C  |  Setpoint: {data['setpoint']:.1f} °C"
                    )
                    self.hardware_label.configure(
                        text=f"Compressor: {data['comp']}  |  Heater: {data['heat']}"
                    )
                    
                    # Update Graph Data Arrays
                    self.time_data.append(data["time"])
                    self.temp_data.append(data["temp"])
                    self.setpoint_data.append(data["setpoint"])
                    self.upper_band.append(data["setpoint"] + 1.0)
                    self.lower_band.append(data["setpoint"] - 1.0)
                    self.heat_data.append(1.0 if data["heat"] == "ON" else 0.0)
                    self.comp_data.append(0.8 if data["comp"] == "ON" else 0.0)

                    self.update_graph()
                
                elif data["type"] == "status":
                    self.profile_label.configure(text=data["msg"])
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def update_graph(self):
        """Redraws the Matplotlib graph with new data."""
        self.ax.clear()
        self.ax2.clear() # Clear the secondary axis too
        
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        self.fig.autofmt_xdate(rotation=45) 
        
        self.ax.set_xlabel("Time", color="white")
        self.ax.set_ylabel("Temperature (°C)", color="white")
        
        # Plot Temp Data
        self.ax.fill_between(self.time_data, self.lower_band, self.upper_band, color='#17a2b8', alpha=0.3, label="±1°C Band")
        self.ax.plot(self.time_data, self.setpoint_data, color='#17a2b8', linestyle='--', linewidth=2, label="Setpoint")
        self.ax.plot(self.time_data, self.temp_data, color='#dc3545', linewidth=2, label="Actual Temp")
        
        # --- NEW: Plot Hardware States ---
        # Set a large Y-limit (e.g., 5) so the 1.0 and 0.8 lines stay pushed to the bottom of the graph
        self.ax2.set_ylim(-0.1, 5)
        self.ax2.set_yticks([]) # Hide the numbers on the right side to prevent clutter
        
        # Plot as square-wave step lines
        self.ax2.step(self.time_data, self.heat_data, color='#ffc107', alpha=0.8, linewidth=2, label="Heater ON", where="post")
        self.ax2.step(self.time_data, self.comp_data, color='#007bff', alpha=0.8, linewidth=2, label="Comp ON", where="post")
        
        self.ax.legend(loc="upper left", facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        self.ax2.legend(loc="lower left", facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        
        self.canvas.draw()

    def save_profile(self):
        """Extracts text from the dynamic rows and saves to a user-defined JSON file."""
        profile_data = []
        for row in self.target_rows:
            temp = row['temp_var'].get()
            dur = row['dur_var'].get()
            
            # Only save rows that actually have data
            if temp and dur:
                profile_data.append({"temp": temp, "dur": dur})
                
        if not profile_data:
            messagebox.showwarning("Warning", "No data to save.")
            return

        # Prompt user for file location and name
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Profile As"
        )
        
        if file_path:
            with open(file_path, "w") as f:
                json.dump(profile_data, f, indent=4)
            messagebox.showinfo("Success", f"Profile saved successfully!")

    def load_profile(self):
        """Prompts the user to select a JSON file and reconstructs the GUI input rows."""
        if self.is_running:
            messagebox.showwarning("Warning", "Cannot load a profile while running.")
            return

        # Prompt user to select a file
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Select Profile to Load"
        )
        
        if not file_path:
            return # User cancelled the dialog
            
        with open(file_path, "r") as f:
            profile_data = json.load(f)
            
        if not profile_data:
            return

        # 1. Set the step count box to match the saved data
        self.target_count_var.set(str(len(profile_data)))
        
        # 2. Rebuild the dynamic rows
        self.adjust_target_rows()
        
        # 3. Populate the rows with the saved data
        for i, row_data in enumerate(profile_data):
            self.target_rows[i]['temp_var'].set(row_data["temp"])
            self.target_rows[i]['dur_var'].set(row_data["dur"])
            
        # Optional: Automatically push it to the listbox 
        self.generate_profile()

    def sdi12_worker(self, port, num_sensors, log_file):
        """BACKGROUND THREAD: Compliant SDI-12 Polling and CSV Logging."""
        try:
            self.log(f"Connecting to SDI-12 adapter on {port}...")
            sdi_conn = serial.Serial(port, 9600, timeout=0.1) 
            
            # Aggressively clear any leftover zombie data
            sdi_conn.reset_input_buffer()
            sdi_conn.reset_output_buffer()
            
            time.sleep(2)
            self.log(f"SDI-12 Connected! Polling {num_sensors} sensors. Logging to {log_file}")
            
            # --- NEW: Define max columns to keep CSV alignment stable ---
            MAX_M_COLS = 10
            MAX_T_COLS = 10

            if not os.path.exists(log_file):
                with open(log_file, "w") as f:
                    # Generate dynamic headers: Timestamp, Address, M1..Mn, T1..Tn
                    headers = ["Timestamp", "Address"]
                    headers.extend([f"M{i+1}" for i in range(MAX_M_COLS)])
                    headers.extend([f"T{i+1}" for i in range(MAX_T_COLS)])
                    f.write(",".join(headers) + "\n")
            
            def read_sdi_line(timeout_sec):
                """Reads a line byte-by-byte, actively ignoring blank phantom lines."""
                start_t = time.time()
                buffer = b""
                while time.time() - start_t < timeout_sec:
                    if not self.is_running: return ""
                    
                    if sdi_conn.in_waiting > 0:
                        char = sdi_conn.read(1)
                        if char == b'\n':
                            res = buffer.decode('utf-8', errors='ignore').strip()
                            if res:  
                                return res
                            else:
                                buffer = b"" 
                        elif char != b'\r':
                            buffer += char
                    else:
                        time.sleep(0.01)
                
                return buffer.decode('utf-8', errors='ignore').strip()

            def sdi_measure(addr, cmd_type="M"):
                """Strict SDI-12 Handshake State Machine - Returns list of data values."""
                if not sdi_conn.is_open: return []
                sdi_conn.reset_input_buffer()
                
                # 1. Send Measure Command
                cmd_m = f"{addr}{cmd_type}!"
                self.log(f"SDI-12 Sent: {cmd_m}")
                sdi_conn.write(cmd_m.encode('utf-8'))
                
                # 2. Read the Acknowledgment
                ack = read_sdi_line(2.0)
                if not ack: return []
                self.log(f"SDI-12 Recv: {ack}")
                
                if ack.startswith(cmd_m):
                    ack_data = ack[len(cmd_m):]
                else:
                    ack_data = ack
                    
                wait_time = 2.0 
                if len(ack_data) >= 4:
                    try:
                        wait_time = float(ack_data[1:4])
                    except ValueError:
                        pass
                
                # 3. Wait up to 'wait_time' for the Service Request
                sr = read_sdi_line(wait_time + 1.0)
                if sr:
                    self.log(f"SDI-12 Recv: {sr}")
                
                # 4. Send Read Command
                cmd_d = f"{addr}D0!"
                self.log(f"SDI-12 Sent: {cmd_d}")
                sdi_conn.write(cmd_d.encode('utf-8'))
                
                # 5. Read Data String
                data_str = read_sdi_line(3.0)
                if data_str:
                    self.log(f"SDI-12 Recv: {data_str}")
                    
                    if data_str.startswith(cmd_d):
                        clean_data = data_str[len(cmd_d):]
                    else:
                        clean_data = data_str
                        
                    vals = re.findall(r'[+-]?\d+\.?\d*', clean_data)
                    
                    # Return just the data values (skipping vals[0] which is the address)
                    if len(vals) > 1:
                        return vals[1:]
                return []

            # --- Main Polling Loop ---
            while self.is_running:
                cycle_start = time.time()
                
                for addr in range(num_sensors):
                    if not self.is_running: break
                    
                    # --- WAKE UP COMMAND ---
                    cmd_i = f"{addr}I!"
                    self.log(f"SDI-12 Sent: {cmd_i}")
                    sdi_conn.write(cmd_i.encode('utf-8')) 
                    id_str = read_sdi_line(1.0)
                    if id_str:
                        self.log(f"SDI-12 Recv: {id_str}")
                    
                    time.sleep(1.0) 
                    
                    # --- GET M AND M1 MEASUREMENTS ---
                    m_vals = sdi_measure(addr, "M")  
                    time.sleep(0.5) 
                    t_vals = sdi_measure(addr, "M1") 
                
                    # --- NEW: COMBINE AND LOG TO CSV ---
                    if m_vals or t_vals:
                        # Pad lists with empty strings to maintain CSV column alignment
                        m_padded = m_vals[:MAX_M_COLS] + [""] * (MAX_M_COLS - len(m_vals[:MAX_M_COLS]))
                        t_padded = t_vals[:MAX_T_COLS] + [""] * (MAX_T_COLS - len(t_vals[:MAX_T_COLS]))
                        
                        t_stamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                        
                        # Build the full row
                        csv_row_data = [t_stamp, str(addr)] + m_padded + t_padded
                        
                        with open(log_file, "a") as f:
                            f.write(",".join(csv_row_data) + "\n")

                # Wait for the remainder of the 10-second cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(0, 10.0 - elapsed)
                
                for _ in range(int(sleep_time / 0.1)):
                    if not self.is_running: break
                    time.sleep(0.1)
                    
        except serial.SerialException:
            self.log(f"SDI-12 Error: Could not open {port}.")
        except Exception as e:
            self.log(f"SDI-12 Thread Error: {e}")
        finally:
            if 'sdi_conn' in locals() and sdi_conn.is_open:
                sdi_conn.close()
            self.log("SDI-12 Disconnected.")

if __name__ == "__main__":
    root = ctk.CTk()
    app = ThermalControllerApp(root)
    root.mainloop()