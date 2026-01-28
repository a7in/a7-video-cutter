"""
Video Cutter - A simple video segment editor using Tkinter and FFmpeg
Requirements: 
    pip install opencv-python pillow
    ffmpeg.exe must be in the same directory as this script
"""
defOpts = "-c:v libx264 -preset ultrafast -crf 18"

import configparser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image, ImageTk
import subprocess
import os
import threading
import time
import tempfile
class VideoCutter:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Cutter")
        self.root.geometry("1100x750")
        self.root.configure(bg="#2b2b2b")
        
        # Video variables
        self.video_path = None
        self.cap = None
        self.total_frames = 0
        self.fps = 30
        self.current_frame = 0
        self.is_playing = False
        self.duration = 0
        self.video_width = 0
        self.video_height = 0
        
        # Marking variables
        self.start_mark = None
        self.end_mark = None
        self.segments = []  # List of tuples: (start_time, end_time)
        
        # Threading
        self.play_thread = None
        self.stop_thread = False
        self.slider_dragging = False
        
        # Encoding settings
        self.encoding_mode = "copy"          # default
        self.reencode_options = defOpts
        self.load_config()
        self.encoding_var = tk.StringVar(value=self.encoding_mode)     
        
        self.setup_ui()
        self.setup_styles()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TScale", background="#2b2b2b", troughcolor="#404040")
        
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - video and controls
        left_frame = tk.Frame(main_frame, bg="#2b2b2b")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Top controls
        top_frame = tk.Frame(left_frame, bg="#2b2b2b")
        top_frame.pack(fill=tk.X, pady=5)
        
        # Open button
        open_btn = tk.Button(top_frame, text="Open Video", command=self.open_video,
                            bg="#4a90d9", fg="white", font=("Arial", 11, "bold"),
                            padx=15, pady=5, relief=tk.FLAT, cursor="hand2")
        open_btn.pack(side=tk.LEFT, padx=5)
        
        # File name label
        self.file_label = tk.Label(top_frame, text="No file opened", 
                                   bg="#2b2b2b", fg="#aaaaaa", font=("Arial", 10))
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        # Video canvas
        canvas_frame = tk.Frame(left_frame, bg="#1a1a1a", bd=2, relief=tk.SUNKEN)
        canvas_frame.pack(pady=10, padx=5)
        
        self.canvas = tk.Canvas(canvas_frame, width=720, height=405, bg="#1a1a1a",
                               highlightthickness=0)
        self.canvas.pack()
        
        # Slider frame
        slider_frame = tk.Frame(left_frame, bg="#2b2b2b")
        slider_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Custom slider using Canvas for better control
        self.slider_canvas = tk.Canvas(slider_frame, height=30, bg="#2b2b2b", 
                                       highlightthickness=0)
        self.slider_canvas.pack(fill=tk.X)
        self.slider_canvas.bind("<Button-1>", self.on_slider_click)
        self.slider_canvas.bind("<B1-Motion>", self.on_slider_drag)
        self.slider_canvas.bind("<ButtonRelease-1>", self.on_slider_release)
        self.slider_value = 0
        self.draw_slider()
        
        # Time label
        self.time_label = tk.Label(left_frame, text="00:00:00.000 / 00:00:00.000",
                                   bg="#2b2b2b", fg="#ffffff", font=("Consolas", 11))
        self.time_label.pack()
        
        # Playback controls
        control_frame = tk.Frame(left_frame, bg="#2b2b2b")
        control_frame.pack(pady=15)
        
        # Frame step buttons
        self.prev_frame_btn = tk.Button(control_frame, text="-1 Frame", width=10,
                                        command=lambda: self.step_frame(-1),
                                        bg="#555555", fg="white", relief=tk.FLAT)
        self.prev_frame_btn.pack(side=tk.LEFT, padx=3)
        self.prev_frame10_btn = tk.Button(control_frame, text="-10 Frame", width=10,
                                        command=lambda: self.step_frame(-10),
                                        bg="#555555", fg="white", relief=tk.FLAT)
        self.prev_frame10_btn.pack(side=tk.LEFT, padx=3)
        self.prev_frame100_btn = tk.Button(control_frame, text="-100 Frame", width=10,
                                        command=lambda: self.step_frame(-100),
                                        bg="#555555", fg="white", relief=tk.FLAT)
        self.prev_frame100_btn.pack(side=tk.LEFT, padx=3)
             
        self.next_frame100_btn = tk.Button(control_frame, text="+100 Frame", width=10,
                                        command=lambda: self.step_frame(100),
                                        bg="#555555", fg="white", relief=tk.FLAT)
        self.next_frame100_btn.pack(side=tk.LEFT, padx=3)
        self.next_frame10_btn = tk.Button(control_frame, text="+10 Frame", width=10,
                                        command=lambda: self.step_frame(10),
                                        bg="#555555", fg="white", relief=tk.FLAT)
        self.next_frame10_btn.pack(side=tk.LEFT, padx=3)
        self.next_frame_btn = tk.Button(control_frame, text="+1 Frame", width=10,
                                        command=lambda: self.step_frame(1),
                                        bg="#555555", fg="white", relief=tk.FLAT)
        self.next_frame_btn.pack(side=tk.LEFT, padx=3)
        
        # Marking controls
        mark_frame = tk.Frame(left_frame, bg="#2b2b2b")
        mark_frame.pack(pady=15)
        
        self.mark_start_btn = tk.Button(mark_frame, text="[ Mark Start",
                                        command=self.mark_start,
                                        bg="#ff9800", fg="white", font=("Arial", 10, "bold"),
                                        padx=15, pady=8, relief=tk.FLAT, cursor="hand2")
        self.mark_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.mark_end_btn = tk.Button(mark_frame, text="Mark End ]",
                                      command=self.mark_end,
                                      bg="#ff5722", fg="white", font=("Arial", 10, "bold"),
                                      padx=15, pady=8, relief=tk.FLAT, cursor="hand2")
        self.mark_end_btn.pack(side=tk.LEFT, padx=5)
        
        self.add_btn = tk.Button(mark_frame, text="Add to List",
                                 command=self.add_segment,
                                 bg="#9c27b0", fg="white", font=("Arial", 10, "bold"),
                                 padx=15, pady=8, relief=tk.FLAT, cursor="hand2")
        self.add_btn.pack(side=tk.LEFT, padx=15)
        
        # Mark labels
        mark_info_frame = tk.Frame(left_frame, bg="#3a3a3a", padx=20, pady=10)
        mark_info_frame.pack(pady=5)
        
        self.start_label = tk.Label(mark_info_frame, text="Start: --:--:--.---",
                                    bg="#3a3a3a", fg="#ff9800", font=("Consolas", 11))
        self.start_label.pack(side=tk.LEFT, padx=10)
        
        tk.Label(mark_info_frame, text="|", bg="#3a3a3a", fg="#666666",
                font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        
        self.end_label = tk.Label(mark_info_frame, text="End: --:--:--.---",
                                  bg="#3a3a3a", fg="#ff5722", font=("Consolas", 11))
        self.end_label.pack(side=tk.LEFT, padx=10)
        
        # Right side - segment list
        right_frame = tk.Frame(main_frame, width=280, bg="#353535")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="Segment List", font=("Arial", 13, "bold"),
                bg="#353535", fg="white").pack(pady=15)
        
        # Listbox with scrollbar
        list_frame = tk.Frame(right_frame, bg="#353535")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.segment_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                          bg="#2b2b2b", fg="white", 
                                          font=("Consolas", 10),
                                          selectbackground="#4a90d9",
                                          selectforeground="white",
                                          bd=0, highlightthickness=0)
        self.segment_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.segment_listbox.yview)
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#2b2b2b", fg="white")
        self.context_menu.add_command(label="Delete Segment", command=self.delete_segment)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Move Up", command=self.move_up)
        self.context_menu.add_command(label="Move Down", command=self.move_down)
        
        self.segment_listbox.bind("<Button-3>", self.show_context_menu)
        self.segment_listbox.bind("<Double-Button-1>", self.goto_segment)
        
        # Buttons at bottom of right panel
        btn_frame = tk.Frame(right_frame, bg="#353535")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.clear_btn = tk.Button(btn_frame, text="Clear All",
                                   command=self.clear_segments,
                                   bg="#666666", fg="white", relief=tk.FLAT,
                                   cursor="hand2")
        self.clear_btn.pack(fill=tk.X, pady=3)
        
        self.cut_btn = tk.Button(btn_frame, text="CUT VIDEO",
                                 command=self.cut_video,
                                 bg="#e91e63", fg="white", 
                                 font=("Arial", 12, "bold"),
                                 pady=10, relief=tk.FLAT, cursor="hand2")
        self.cut_btn.pack(fill=tk.X, pady=10)
        
        # Encoding options frame
        encoding_frame = tk.LabelFrame(right_frame, text="Output Encoding", 
                                       bg="#353535", fg="#bbbbbb", padx=10, pady=10)
        encoding_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Radiobutton(encoding_frame, 
                       text="copy mode", 
                       variable=self.encoding_var,
                       value="copy",
                       command=self.update_encoding_mode,
                       bg="#353535", fg="white", selectcolor="#4a4a4a", 
                       activebackground="#353535", activeforeground="white",
                       font=("Arial", 10)).pack(anchor=tk.W, pady=3)

        tk.Radiobutton(encoding_frame, 
                       text="full encode mode", 
                       variable=self.encoding_var,
                       value="reencode",
                       command=self.update_encoding_mode,
                       bg="#353535", fg="white", selectcolor="#4a4a4a", 
                       activebackground="#353535", activeforeground="white",
                       font=("Arial", 10)).pack(anchor=tk.W, pady=3)

        # Current options label
        tk.Label(encoding_frame, text="encode options:", 
                 bg="#353535", fg="#88ff88", font=("Consolas", 9)).pack(anchor=tk.W, pady=(8,2))

        self.options_text = tk.Text(encoding_frame, height=4, width=28, 
                                    bg="#2b2b2b", fg="#dddddd", font=("Consolas", 10),
                                    insertbackground="white")
        self.options_text.insert(tk.END, self.reencode_options)
        self.options_text.pack(fill=tk.X, pady=2)

        # Save config button
        save_config_btn = tk.Button(encoding_frame, text="Save Config", 
                                    command=self.save_encoding_settings,
                                    bg="#607d8b", fg="white", font=("Arial", 9, "bold"),
                                    relief=tk.FLAT, cursor="hand2")
        save_config_btn.pack(pady=8, fill=tk.X)        
        
        # Status bar
        self.status_label = tk.Label(right_frame, text="Ready",
                                     bg="#353535", fg="#888888",
                                     font=("Arial", 9))
        self.status_label.pack(pady=5)
    def draw_slider(self):
        self.slider_canvas.delete("all")
        width = self.slider_canvas.winfo_width()
        if width < 10:
            width = 700
        
        # Draw track
        self.slider_canvas.create_rectangle(10, 12, width-10, 18, 
                                           fill="#404040", outline="")
        
        # Draw marked regions
        if self.total_frames > 0:
            for start, end in self.segments:
                x1 = 10 + (start / self.duration) * (width - 20)
                x2 = 10 + (end / self.duration) * (width - 20)
                self.slider_canvas.create_rectangle(x1, 10, x2, 20,
                                                   fill="#9c27b0", outline="")
        
        # Draw current marks
        if self.start_mark is not None and self.duration > 0:
            x = 10 + (self.start_mark / self.duration) * (width - 20)
            self.slider_canvas.create_line(x, 5, x, 25, fill="#ff9800", width=2)
            
        if self.end_mark is not None and self.duration > 0:
            x = 10 + (self.end_mark / self.duration) * (width - 20)
            self.slider_canvas.create_line(x, 5, x, 25, fill="#ff5722", width=2)
        
        # Draw progress
        pos = 10 + self.slider_value * (width - 20)
        self.slider_canvas.create_rectangle(10, 12, pos, 18, fill="#4a90d9", outline="")
        
        # Draw handle
        self.slider_canvas.create_oval(pos-8, 7, pos+8, 23, fill="#ffffff", outline="#cccccc")
    def on_slider_click(self, event):
        if self.cap is None:
            return
        self.slider_dragging = True
        was_playing = self.is_playing
        if was_playing:
            self.pause_video()
        self.update_slider_from_mouse(event.x)
        
    def on_slider_drag(self, event):
        if self.slider_dragging and self.cap is not None:
            self.update_slider_from_mouse(event.x)
            
    def on_slider_release(self, event):
        self.slider_dragging = False
        
    def update_slider_from_mouse(self, x):
        width = self.slider_canvas.winfo_width()
        value = (x - 10) / (width - 20)
        value = max(0, min(1, value))
        self.slider_value = value
        
        # Seek to frame
        frame_num = int(value * self.total_frames)
        self.seek_to_frame(frame_num)
        self.draw_slider()
    def open_video(self):
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ]
        path = filedialog.askopenfilename(title="Open Video File", filetypes=filetypes)
        
        if path:
            self.load_video(path)
    
    def load_video(self, path):
        if self.cap is not None:
            self.stop_thread = True
            time.sleep(0.1)
            self.cap.release()
            
        self.cap = cv2.VideoCapture(path)
        
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open video file!")
            return
            
        self.video_path = path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
        self.duration = self.total_frames / self.fps
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.current_frame = 0
        self.is_playing = False
        self.stop_thread = False
        self.start_mark = None
        self.end_mark = None
        self.segments = []
        self.segment_listbox.delete(0, tk.END)
        
        # Update UI
        filename = os.path.basename(path)
        self.file_label.config(text=filename)
        self.root.title(f"Video Cutter - {filename}")
        
        self.update_mark_labels()
        self.slider_value = 0
        self.draw_slider()
        
        # Show first frame
        self.show_frame(0)
        self.update_time_label()
        
        self.status_label.config(text=f"{self.video_width}x{self.video_height} | {self.fps:.2f} fps")
    
    def show_frame(self, frame_num):
        if self.cap is None:
            return
            
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        
        if ret:
            self.current_frame = frame_num
            
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fit canvas while maintaining aspect ratio
            canvas_width = 720
            canvas_height = 405
            
            h, w = frame.shape[:2]
            scale = min(canvas_width / w, canvas_height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Convert to PhotoImage
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image)
            
            # Center on canvas
            x = (canvas_width - new_w) // 2
            y = (canvas_height - new_h) // 2
            
            self.canvas.delete("all")
            self.canvas.create_image(x, y, anchor=tk.NW, image=photo)
            self.canvas.image = photo  # Keep reference
            
            # Update slider
            if self.total_frames > 0:
                self.slider_value = frame_num / self.total_frames
                if not self.slider_dragging:
                    self.draw_slider()
            
            self.update_time_label()
    
    def seek_to_frame(self, frame_num):
        frame_num = max(0, min(frame_num, self.total_frames - 1))
        self.show_frame(frame_num)
    
    def play_video(self):
        self.is_playing = True
        self.play_btn.config(text="Pause", bg="#ff5722")
        self.stop_thread = False
        
        self.play_thread = threading.Thread(target=self.play_loop)
        self.play_thread.daemon = True
        self.play_thread.start()
    
    def pause_video(self):
        self.is_playing = False
        self.stop_thread = True
        self.play_btn.config(text="Play", bg="#4CAF50")
    
    def play_loop(self):
        frame_time = 1.0 / self.fps
        
        while not self.stop_thread and self.current_frame < self.total_frames - 1:
            start_time = time.time()
            
            self.current_frame += 1
            self.root.after(0, lambda f=self.current_frame: self.show_frame(f))
            
            # Maintain frame rate
            elapsed = time.time() - start_time
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        if self.current_frame >= self.total_frames - 1:
            self.root.after(0, self.pause_video)
    
    def step_frame(self, delta):
        if self.cap is None:
            return
        if self.is_playing:
            self.pause_video()
        new_frame = self.current_frame + delta
        new_frame = max(0, min(new_frame, self.total_frames - 1))
        self.show_frame(new_frame)
    
    def get_current_time(self):
        if self.cap is None:
            return 0
        return self.current_frame / self.fps
    
    def format_time(self, seconds):
        if seconds is None:
            return "--:--:--.---"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def update_time_label(self):
        current = self.format_time(self.get_current_time())
        total = self.format_time(self.duration)
        self.time_label.config(text=f"{current} / {total}")
    
    def update_mark_labels(self):
        self.start_label.config(text=f"Start: {self.format_time(self.start_mark)}")
        self.end_label.config(text=f"End: {self.format_time(self.end_mark)}")
    
    def mark_start(self):
        if self.cap is None:
            messagebox.showwarning("Warning", "Please open a video first!")
            return
        self.start_mark = self.get_current_time()
        self.update_mark_labels()
        self.draw_slider()
        self.status_label.config(text="Start point marked")
    
    def mark_end(self):
        if self.cap is None:
            messagebox.showwarning("Warning", "Please open a video first!")
            return
        self.end_mark = self.get_current_time()
        self.update_mark_labels()
        self.draw_slider()
        self.status_label.config(text="End point marked")
    
    def add_segment(self):
        if self.start_mark is None or self.end_mark is None:
            messagebox.showwarning("Warning", "Please mark both start and end points!")
            return
            
        if self.start_mark >= self.end_mark:
            messagebox.showwarning("Warning", "Start time must be before end time!")
            return
        
        segment = (self.start_mark, self.end_mark)
        self.segments.append(segment)
        
        # Add to listbox
        idx = len(self.segments)
        text = f"{idx}. {self.format_time(self.start_mark)} > {self.format_time(self.end_mark)}"
        self.segment_listbox.insert(tk.END, text)
        
        # Reset marks
        self.start_mark = None
        self.end_mark = None
        self.update_mark_labels()
        self.draw_slider()
        
        self.status_label.config(text=f"Segment {idx} added")
    
    def show_context_menu(self, event):
        try:
            self.segment_listbox.selection_clear(0, tk.END)
            self.segment_listbox.selection_set(self.segment_listbox.nearest(event.y))
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def delete_segment(self):
        selection = self.segment_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        self.segment_listbox.delete(idx)
        del self.segments[idx]
        
        # Renumber remaining segments
        self.refresh_listbox()
        self.draw_slider()
        self.status_label.config(text="Segment deleted")
    
    def move_up(self):
        selection = self.segment_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        idx = selection[0]
        self.segments[idx], self.segments[idx-1] = self.segments[idx-1], self.segments[idx]
        self.refresh_listbox()
        self.segment_listbox.selection_set(idx-1)
    
    def move_down(self):
        selection = self.segment_listbox.curselection()
        if not selection or selection[0] >= len(self.segments) - 1:
            return
        idx = selection[0]
        self.segments[idx], self.segments[idx+1] = self.segments[idx+1], self.segments[idx]
        self.refresh_listbox()
        self.segment_listbox.selection_set(idx+1)
    
    def refresh_listbox(self):
        self.segment_listbox.delete(0, tk.END)
        for i, (start, end) in enumerate(self.segments):
            text = f"{i+1}. {self.format_time(start)} > {self.format_time(end)}"
            self.segment_listbox.insert(tk.END, text)
    
    def clear_segments(self):
        if not self.segments:
            return
        if messagebox.askyesno("Confirm", "Clear all segments?"):
            self.segments = []
            self.segment_listbox.delete(0, tk.END)
            self.draw_slider()
            self.status_label.config(text="All segments cleared")
    
    def goto_segment(self, event):
        selection = self.segment_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        start_time = self.segments[idx][0]
        frame_num = int(start_time * self.fps)
        self.seek_to_frame(frame_num)
    
    def cut_video(self):
        if not self.segments:
            messagebox.showwarning("Warning", "No segments to cut!")
            return
        
        if self.video_path is None:
            messagebox.showwarning("Warning", "No video loaded!")
            return
        
        # Get ffmpeg path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
        
        if not os.path.exists(ffmpeg_path):
            # Try just 'ffmpeg' in PATH
            ffmpeg_path = "ffmpeg"
        
        # Create output filename
        base, ext = os.path.splitext(self.video_path)
        if self.encoding_mode == "reencode":
            ext = ".mp4"
        output_path = f"{base}_cut{ext}"
        
        # Ask for confirmation
        if os.path.exists(output_path):
            if not messagebox.askyesno("Confirm", f"Output file already exists:\n{output_path}\n\nOverwrite?"):
                return
        
        self.status_label.config(text="Processing... Please wait")
        self.cut_btn.config(state=tk.DISABLED)
        self.root.update()
        
        # Run cutting in a thread
        thread = threading.Thread(target=self.do_cut, args=(ffmpeg_path, output_path))
        thread.start()

    def update_encoding_mode(self):
        self.encoding_mode = self.encoding_var.get()
        self.status_label.config(text=f"Encode mode: {self.encoding_mode}")
        # self.options_text.config(state="normal" if self.encoding_mode == "reencode" else "disabled")

    def save_encoding_settings(self):
        new_options = self.options_text.get("1.0", tk.END).strip()
        if self.encoding_mode == "reencode":
            self.reencode_options = new_options if new_options else defOpts
        self.save_config()
        self.status_label.config(text="Encoding config saved")    
    
    def do_cut(self, ffmpeg_path, output_path):
        try:
            temp_files = []
            temp_dir = tempfile.gettempdir()

            # Определяем параметры кодирования
            if self.encoding_mode == "copy":
                encode_params = ["-c", "copy", "-avoid_negative_ts", "make_zero"]
            else:
                # Разбиваем строку на аргументы, учитывая кавычки (простой вариант)
                encode_params = self.reencode_options.split()

            for i, (start, end) in enumerate(self.segments):
                if self.encoding_mode == "reencode":
                    temp_ext = ".mp4"
                else:
                    temp_ext = os.path.splitext(self.video_path)[1]
                temp_file = os.path.join(temp_dir, f"segment_{i}{temp_ext}")
                temp_files.append(temp_file)

                duration = end - start

                cmd = [
                    ffmpeg_path,
                    "-y",
                    "-ss", str(start),
                    "-i", self.video_path,
                    "-t", str(duration),
                    *encode_params,
                    temp_file
                ]
                
                with open("ffmpeg.log", "w", encoding="utf-8", errors="ignore") as log:
                    p = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        creationflags=0
                    )

                    for line in p.stdout:
                        print(line, end="")
                        log.write(line)

                    p.wait()

            # Если один сегмент — просто копируем
            if len(temp_files) == 1:
                import shutil
                shutil.copy(temp_files[0], output_path)
            else:
                # Создаём concat файл
                concat_file = os.path.join(temp_dir, "concat_list.txt")
                with open(concat_file, "w", encoding="utf-8") as f:
                    for temp_file in temp_files:
                        escaped = temp_file.replace("\\", "/").replace("'", "'\\''")
                        f.write(f"file '{escaped}'\n")

                # Для конкатенации всегда используем copy, даже если перекодировали сегменты
                cmd = [
                    ffmpeg_path,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_file,
                    "-c", "copy",
                    output_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

                if result.returncode != 0:
                    raise Exception(f"FFmpeg concat error:\n{result.stderr}")

                os.remove(concat_file)

            # Удаляем временные файлы
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

            self.root.after(0, lambda: self.cut_complete(True, output_path))

        except Exception as exc:
            self.root.after(0, self.cut_complete, False, str(exc))
    
    def cut_complete(self, success, message):
        self.cut_btn.config(state=tk.NORMAL)
        
        if success:
            self.status_label.config(text="Cut complete!")
            messagebox.showinfo("Success", f"Video saved to:\n{message}")
        else:
            self.status_label.config(text="Cut failed!")
            messagebox.showerror("Error", f"Failed to cut video:\n{message}")
    
    def on_close(self):
        self.stop_thread = True
        if self.cap is not None:
            self.cap.release()
        self.root.destroy()
        
    def load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        
        if os.path.exists(config_path):
            config.read(config_path)
            if "Encoding" in config:
                self.encoding_mode = config["Encoding"].get("mode", "copy")
                self.reencode_options = config["Encoding"].get("reencode_options", defOpts)
        else:
            self.encoding_mode = "copy"
            self.reencode_options = defOpts
            self.save_config()

        if hasattr(self, 'encoding_var'):
            self.encoding_var.set(self.encoding_mode)

    def save_config(self):
        config = configparser.ConfigParser()
        config["Encoding"] = {
            "mode": self.encoding_mode,
            "reencode_options": self.reencode_options
        }
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        with open(config_path, "w", encoding="utf-8") as configfile:
            config.write(configfile)        
        
def main():
    root = tk.Tk()
    app = VideoCutter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Bind resize event for slider redraw
    def on_resize(event):
        if hasattr(app, 'draw_slider'):
            app.draw_slider()
    root.bind("<Configure>", on_resize)
    
    root.mainloop()
if __name__ == "__main__":
    main()
