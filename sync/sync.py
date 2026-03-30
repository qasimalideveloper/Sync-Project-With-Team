"""
Simple File Sync Client - ZIP Archive Based
Beautiful GUI for downloading and uploading project folders
"""

import os
import sys
import zipfile
import shutil
import requests
import threading
import time
from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime

# ============================================================
#  CONFIGURATION
# ============================================================
SERVER_URL = "https://projectsyncbackend.pythonanywhere.com"
WATCH_FOLDERS = ["frontend", "backend"]

# ============================================================
#  GLOBAL VARIABLES
# ============================================================
CLIENT_ID = None
is_connected = False
waiting_for_others = False

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Sync")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        # Modern color scheme
        self.bg_color = "#1e1e2e"  # Dark blue-gray
        self.card_color = "#2a2a3e"  # Slightly lighter
        self.accent_color = "#4a9eff"  # Bright blue
        self.success_color = "#4ade80"  # Green
        self.warning_color = "#fbbf24"  # Yellow
        self.text_color = "#e0e0e0"  # Light gray
        self.dark_text = "#888888"  # Gray
        
        # Configure root
        self.root.configure(bg=self.bg_color)
        
        # Create GUI
        self.create_gui()
        
        # Get client ID (this will block until name is entered)
        self.get_client_id()
        
        # Wait a moment for CLIENT_ID to be set
        self.root.update()
        
        # Check connection only after CLIENT_ID is set
        if CLIENT_ID:
            self.check_connection()
        else:
            self.update_status("⚠️ Please enter your name", self.warning_color)
        
        # Start status update thread
        self.update_status_thread()
    
    def create_gui(self):
        # Header
        header_frame = Frame(self.root, bg=self.bg_color, pady=30)
        header_frame.pack(fill=X)
        
        title_label = Label(
            header_frame,
            text="Project Sync",
            font=("Segoe UI", 28, "bold"),
            bg=self.bg_color,
            fg=self.text_color
        )
        title_label.pack()
        
        subtitle_label = Label(
            header_frame,
            text="Download latest • Upload your work",
            font=("Segoe UI", 11),
            bg=self.bg_color,
            fg=self.dark_text
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Status card
        self.status_frame = Frame(self.root, bg=self.card_color, relief=FLAT, padx=20, pady=15)
        self.status_frame.pack(fill=X, padx=20, pady=(20, 10))
        
        self.status_label = Label(
            self.status_frame,
            text="Checking connection...",
            font=("Segoe UI", 10),
            bg=self.card_color,
            fg=self.text_color,
            justify=LEFT
        )
        self.status_label.pack(anchor=W)
        
        # Main buttons frame
        buttons_frame = Frame(self.root, bg=self.bg_color, pady=20)
        buttons_frame.pack(fill=BOTH, expand=True, padx=20)
        
        # Download button
        self.download_btn = Button(
            buttons_frame,
            text="📥 Download Latest",
            font=("Segoe UI", 14, "bold"),
            bg=self.accent_color,
            fg="white",
            activebackground="#3a8eef",
            activeforeground="white",
            relief=FLAT,
            cursor="hand2",
            padx=30,
            pady=20,
            command=self.download_latest,
            state=DISABLED
        )
        self.download_btn.pack(fill=X, pady=(0, 15))
        
        # Upload button
        self.upload_btn = Button(
            buttons_frame,
            text="📤 Upload",
            font=("Segoe UI", 14, "bold"),
            bg=self.success_color,
            fg="white",
            activebackground="#3acd70",
            activeforeground="white",
            relief=FLAT,
            cursor="hand2",
            padx=30,
            pady=20,
            command=self.upload_final,
            state=DISABLED
        )
        self.upload_btn.pack(fill=X)
        
        # Progress frame
        self.progress_frame = Frame(self.root, bg=self.bg_color)
        self.progress_frame.pack(fill=X, padx=20, pady=(10, 20))
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=460
        )
        self.progress_bar.pack()
        
        self.progress_label = Label(
            self.progress_frame,
            text="",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.dark_text
        )
        self.progress_label.pack(pady=(5, 0))
        
        # Info frame
        info_frame = Frame(self.root, bg=self.card_color, relief=FLAT, padx=20, pady=15)
        info_frame.pack(fill=X, padx=20, pady=(0, 20))
        
        self.info_label = Label(
            info_frame,
            text="Ready to sync",
            font=("Segoe UI", 9),
            bg=self.card_color,
            fg=self.dark_text,
            justify=LEFT
        )
        self.info_label.pack(anchor=W)
    
    def get_client_id(self):
        """Get client ID from user"""
        dialog = Toplevel(self.root)
        dialog.title("Enter Your Name")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (150 // 2)
        dialog.geometry(f"400x150+{x}+{y}")
        
        Label(
            dialog,
            text="Enter your name:",
            font=("Segoe UI", 11),
            bg=self.bg_color,
            fg=self.text_color
        ).pack(pady=(20, 10))
        
        entry = Entry(
            dialog,
            font=("Segoe UI", 12),
            width=30,
            relief=FLAT,
            bg=self.card_color,
            fg=self.text_color,
            insertbackground=self.text_color
        )
        entry.pack(pady=5, padx=20)
        entry.focus()
        
        global CLIENT_ID
        
        def submit():
            name = entry.get().strip()
            if name:
                global CLIENT_ID
                CLIENT_ID = name
                print(f"[DEBUG] CLIENT_ID set to: {CLIENT_ID}")  # Debug
                dialog.destroy()
            else:
                messagebox.showwarning("Invalid Name", "Please enter your name")
        
        entry.bind('<Return>', lambda e: submit())
        
        Button(
            dialog,
            text="Continue",
            font=("Segoe UI", 10, "bold"),
            bg=self.accent_color,
            fg="white",
            activebackground="#3a8eef",
            activeforeground="white",
            relief=FLAT,
            cursor="hand2",
            padx=20,
            pady=5,
            command=submit
        ).pack(pady=10)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        # Verify CLIENT_ID was set
        if not CLIENT_ID or str(CLIENT_ID).strip() == "":
            print("[DEBUG] WARNING: CLIENT_ID not set after dialog closed!")
            messagebox.showerror("Error", "Name is required. Please restart the application.")
            sys.exit(1)
        
        print(f"[DEBUG] CLIENT_ID confirmed: {CLIENT_ID}")  # Debug
    
    def check_connection(self):
        """Check if server is reachable"""
        global is_connected
        if not CLIENT_ID or str(CLIENT_ID).strip() == "":
            self.update_status("⚠️ Please enter your name", self.warning_color)
            return
        
        self.update_status("🔄 Connecting to server...", self.text_color)
        
        def check():
            global is_connected
            try:
                response = requests.get(f"{SERVER_URL}/health", timeout=3)
                is_connected = response.status_code == 200
                
                if is_connected:
                    self.root.after(0, self.register_client)
                else:
                    self.root.after(0, lambda: self.update_status("🔴 Server returned error", self.warning_color))
                    self.root.after(0, lambda: self.download_btn.config(state=DISABLED))
                    self.root.after(0, lambda: self.upload_btn.config(state=DISABLED))
            except requests.exceptions.ConnectionError:
                is_connected = False
                self.root.after(0, lambda: self.update_status("🔴 Cannot connect to server", self.warning_color))
                self.root.after(0, lambda: self.download_btn.config(state=DISABLED))
                self.root.after(0, lambda: self.upload_btn.config(state=DISABLED))
            except Exception as e:
                is_connected = False
                self.root.after(0, lambda: self.update_status(f"🔴 Connection error: {str(e)}", self.warning_color))
                self.root.after(0, lambda: self.download_btn.config(state=DISABLED))
                self.root.after(0, lambda: self.upload_btn.config(state=DISABLED))
        
        threading.Thread(target=check, daemon=True).start()
    
    def register_client(self):
        """Register with server and check for other active clients"""
        global waiting_for_others
        if not CLIENT_ID or CLIENT_ID.strip() == "":
            self.root.after(0, lambda: self.update_status("⚠️ Client ID not set", self.warning_color))
            return
        
        def register():
            global waiting_for_others
            try:
                # Ensure CLIENT_ID is a string and not empty
                if not CLIENT_ID:
                    self.root.after(0, lambda: self.update_status("⚠️ Client ID not set", self.warning_color))
                    return
                
                client_id_str = str(CLIENT_ID).strip()
                if not client_id_str:
                    self.root.after(0, lambda: self.update_status("⚠️ Invalid client ID", self.warning_color))
                    return
                
                print(f"[DEBUG] Registering with client_id: {client_id_str}")  # Debug
                
                response = requests.post(
                    f"{SERVER_URL}/register",
                    json={"client_id": client_id_str},
                    timeout=5
                )
                
                print(f"[DEBUG] Registration response: {response.status_code}")  # Debug
                
                if response.status_code == 200:
                    data = response.json()
                    other_active = data.get("other_clients_active", False)
                    other_clients = data.get("other_clients", [])
                    
                    if other_active:
                        client_list = ", ".join([c.get("client_id", "unknown") for c in other_clients])
                        waiting_for_others = True
                        self.root.after(0, lambda: self.update_status(
                            f"⏳ Waiting - {client_list} is working",
                            self.warning_color
                        ))
                        self.root.after(0, lambda: self.download_btn.config(state=DISABLED))
                        self.root.after(0, lambda: self.upload_btn.config(state=DISABLED))
                        # Start checking for disconnect
                        threading.Thread(target=self.wait_for_others, daemon=True).start()
                    else:
                        waiting_for_others = False
                        self.root.after(0, lambda: self.update_status("🟢 Connected - Ready to work", self.success_color))
                        self.root.after(0, lambda: self.download_btn.config(state=NORMAL))
                        self.root.after(0, lambda: self.upload_btn.config(state=NORMAL))
                else:
                    error_msg = f"Registration failed: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data.get('error', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text}"
                    print(f"[DEBUG] {error_msg}")  # Debug
                    self.root.after(0, lambda: self.update_status(f"🔴 {error_msg}", self.warning_color))
                    self.root.after(0, lambda: self.download_btn.config(state=DISABLED))
                    self.root.after(0, lambda: self.upload_btn.config(state=DISABLED))
            except Exception as e:
                print(f"[DEBUG] Registration exception: {str(e)}")  # Debug
                self.root.after(0, lambda: self.update_status(f"🔴 Registration error: {str(e)}", self.warning_color))
                self.root.after(0, lambda: self.download_btn.config(state=DISABLED))
                self.root.after(0, lambda: self.upload_btn.config(state=DISABLED))
        
        threading.Thread(target=register, daemon=True).start()
    
    def wait_for_others(self):
        """Wait for other clients to disconnect"""
        global waiting_for_others
        while waiting_for_others:
            try:
                response = requests.get(
                    f"{SERVER_URL}/check_active",
                    params={"client_id": CLIENT_ID},
                    timeout=3
                )
                if response.status_code == 200:
                    data = response.json()
                    if not data.get("other_clients_active", False):
                        waiting_for_others = False
                        self.root.after(0, lambda: self.update_status("🟢 Connected - Ready to work", self.success_color))
                        self.root.after(0, lambda: self.download_btn.config(state=NORMAL))
                        self.root.after(0, lambda: self.upload_btn.config(state=NORMAL))
                        break
            except:
                pass
            time.sleep(2)
    
    def update_status(self, text, color=None):
        """Update status label"""
        self.status_label.config(text=text)
        if color:
            self.status_label.config(fg=color)
    
    def update_status_thread(self):
        """Periodically update status"""
        def update():
            while True:
                if is_connected and not waiting_for_others and CLIENT_ID:
                    try:
                        response = requests.post(
                            f"{SERVER_URL}/register",
                            json={"client_id": CLIENT_ID},
                            timeout=2
                        )
                    except:
                        pass
                time.sleep(10)
        
        threading.Thread(target=update, daemon=True).start()
    
    def show_progress(self, show=True, text=""):
        """Show/hide progress bar"""
        if show:
            self.progress_bar.start(10)
            self.progress_label.config(text=text)
        else:
            self.progress_bar.stop()
            self.progress_label.config(text="")
    
    def create_backup(self):
        """Create backup of current frontend and backend folders"""
        backup_base = "backup"
        
        # Create backup folder if it doesn't exist
        if not os.path.exists(backup_base):
            os.makedirs(backup_base)
        
        # Find the next backup number
        backup_number = 1
        while os.path.exists(os.path.join(backup_base, f"backup_{backup_number}")):
            backup_number += 1
        
        backup_folder = os.path.join(backup_base, f"backup_{backup_number}")
        os.makedirs(backup_folder)
        
        # Copy each watched folder to backup
        backed_up_folders = []
        for folder in WATCH_FOLDERS:
            if os.path.exists(folder):
                dest_folder = os.path.join(backup_folder, folder)
                try:
                    shutil.copytree(folder, dest_folder, dirs_exist_ok=True)
                    backed_up_folders.append(folder)
                except Exception as e:
                    print(f"Error backing up {folder}: {e}")
        
        return backup_folder, backed_up_folders
    
    def download_latest(self):
        """Download latest project files"""
        if waiting_for_others:
            messagebox.showwarning("Wait", "Another person is currently working. Please wait.")
            return
        
        self.download_btn.config(state=DISABLED)
        self.upload_btn.config(state=DISABLED)
        self.show_progress(True, "Downloading latest files...")
        
        def download():
            try:
                # Create backup of current files before downloading
                self.root.after(0, lambda: self.progress_label.config(text="Creating backup..."))
                backup_folder, backed_up = self.create_backup()
                
                if backed_up:
                    self.root.after(0, lambda: self.update_info(f"Backup created: {os.path.basename(backup_folder)}"))
                
                # Ensure folders exist
                for folder in WATCH_FOLDERS:
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                
                # Download both frontend and backend folders
                downloaded_folders = []
                for folder in WATCH_FOLDERS:
                    self.root.after(0, lambda f=folder: self.progress_label.config(text=f"Downloading {f}..."))
                    
                    response = requests.get(
                        f"{SERVER_URL}/download/{folder}",
                        timeout=30,
                        stream=True
                    )
                    
                    if response.status_code == 200:
                        # Save ZIP file
                        zip_path = f"{folder}_temp.zip"
                        with open(zip_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        # Extract ZIP
                        self.root.after(0, lambda f=folder: self.progress_label.config(text=f"Extracting {f}..."))
                        
                        # Remove existing folder contents
                        if os.path.exists(folder):
                            shutil.rmtree(folder)
                        os.makedirs(folder)
                        
                        # Extract
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(folder)
                        
                        # Remove temp ZIP
                        os.remove(zip_path)
                        downloaded_folders.append(folder)
                    elif response.status_code == 404:
                        # Folder doesn't exist on server, create empty folder
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                    else:
                        raise Exception(f"Server returned {response.status_code} for {folder}")
                
                self.root.after(0, lambda: self.show_progress(False))
                folders_str = " and ".join(downloaded_folders) if downloaded_folders else "folders"
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Downloaded {folders_str} successfully!"))
                self.root.after(0, lambda: self.update_info("Downloaded frontend and backend"))
                
            except Exception as e:
                self.root.after(0, lambda: self.show_progress(False))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Download failed: {str(e)}"))
            
            finally:
                self.root.after(0, lambda: self.download_btn.config(state=NORMAL))
                self.root.after(0, lambda: self.upload_btn.config(state=NORMAL))
        
        threading.Thread(target=download, daemon=True).start()
    
    def upload_final(self):
        """Upload final project files"""
        if waiting_for_others:
            messagebox.showwarning("Wait", "Another person is currently working. Please wait.")
            return
        
        # Confirm upload
        if not messagebox.askyesno("Confirm Upload", "This will replace the files on the server. Continue?"):
            return
        
        self.download_btn.config(state=DISABLED)
        self.upload_btn.config(state=DISABLED)
        self.show_progress(True, "Uploading files...")
        
        def upload():
            try:
                # Upload both frontend and backend folders
                uploaded_folders = []
                for folder in WATCH_FOLDERS:
                    if not os.path.exists(folder):
                        continue
                    
                    self.root.after(0, lambda f=folder: self.progress_label.config(text=f"Compressing {f}..."))
                    
                    # Create ZIP
                    zip_path = f"{folder}_temp.zip"
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # Track all directories (to handle empty ones)
                        all_dirs = set()
                        dirs_with_files = set()
                        
                        # First pass: collect all directories and files
                        for root, dirs, files in os.walk(folder):
                            dir_path = os.path.relpath(root, folder)
                            if dir_path != '.':
                                all_dirs.add(dir_path)
                            
                            # Add files and track their parent directories
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, folder)
                                zipf.write(file_path, arcname)
                                # Mark parent directory as having files
                                parent_dir = os.path.dirname(arcname)
                                if parent_dir:
                                    dirs_with_files.add(parent_dir)
                        
                        # Second pass: add empty directories
                        for dir_path in all_dirs:
                            if dir_path not in dirs_with_files:
                                # Check if directory is actually empty
                                full_dir_path = os.path.join(folder, dir_path)
                                if os.path.exists(full_dir_path) and not os.listdir(full_dir_path):
                                    # Add empty directory entry (ZIP format: trailing slash)
                                    zipf.writestr(dir_path + '/', '')
                    
                    # Upload ZIP
                    self.root.after(0, lambda f=folder: self.progress_label.config(text=f"Uploading {f}..."))
                    
                    with open(zip_path, 'rb') as f:
                        files = {'archive': (f'{folder}.zip', f, 'application/zip')}
                        data = {'client_id': CLIENT_ID}
                        response = requests.post(
                            f"{SERVER_URL}/upload/{folder}",
                            files=files,
                            data=data,
                            timeout=60
                        )
                    
                    # Remove temp ZIP
                    os.remove(zip_path)
                    
                    if response.status_code != 200:
                        raise Exception(f"Upload failed for {folder}: {response.text}")
                    
                    uploaded_folders.append(folder)
                
                self.root.after(0, lambda: self.show_progress(False))
                folders_str = " and ".join(uploaded_folders) if uploaded_folders else "folders"
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Uploaded {folders_str} successfully!"))
                self.root.after(0, lambda: self.update_info("Uploaded frontend and backend"))
                
                # Unregister after upload
                try:
                    requests.post(
                        f"{SERVER_URL}/unregister",
                        json={"client_id": CLIENT_ID},
                        timeout=2
                    )
                except:
                    pass
                
            except Exception as e:
                self.root.after(0, lambda: self.show_progress(False))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Upload failed: {str(e)}"))
            
            finally:
                self.root.after(0, lambda: self.download_btn.config(state=NORMAL))
                self.root.after(0, lambda: self.upload_btn.config(state=NORMAL))
        
        threading.Thread(target=upload, daemon=True).start()
    
    def update_info(self, text):
        """Update info label"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.info_label.config(text=f"{text} at {timestamp}")

def main():
    root = Tk()
    app = SyncApp(root)
    
    def on_closing():
        """Clean up on close"""
        if is_connected and CLIENT_ID:
            try:
                requests.post(
                    f"{SERVER_URL}/unregister",
                    json={"client_id": CLIENT_ID},
                    timeout=2
                )
            except:
                pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()

