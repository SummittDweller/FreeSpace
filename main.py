#!/usr/bin/env python3
"""
FreeSpace - Hard Disk Move with Verification Workflow
A Python/Flet GUI application to move directories to external storage with verification.

IMPORTANT FLET CONVENTIONS:
- Always use ft.Icons (uppercase) - NOT ft.icons
- Always use ft.Colors (uppercase) - NOT ft.colors
"""

import flet as ft
import os
import shutil
import hashlib
import datetime
import json
import stat
import errno
import asyncio
import threading
import socket
import sys
from pathlib import Path
from typing import List, Dict


class FreeSpaceApp:
    """Main application class for FreeSpace."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "FreeSpace - Move Directory Workflow"
        self.page.window.width = 900
        self.page.window.height = 800
        self.page.window.min_width = 900
        self.page.window.min_height = 800
        self.page.window.resizable = True
        self.page.scroll = ft.ScrollMode.AUTO
        
        # State variables - simplified for single directory move
        self.source_directory: str = ""  # Single directory only
        self.destination_directory: str = ""  # Direct destination, no session subdirs
        self.log_directory = Path.home() / "freespace_logs"
        self.log_directory.mkdir(exist_ok=True)
        
        # Operation control - for kill switch functionality
        self.operation_in_progress = False
        self.stop_operation = threading.Event()  # Signal to stop current operation
        
        # UI Components
        self.source_text = None
        self.destination_text = None
        self.status_text = None
        self.log_text_area = None
        self.kill_button = None  # Kill switch button
        self.progress_bar = None
        self.copy_button = None
        self.verify_button = None
        self.finalize_button = None
        self.sudo_password_field = None  # Sudo password input
        
        # FilePicker services
        self.source_picker = ft.FilePicker()
        self.destination_picker = ft.FilePicker()
        self.page.services.extend([self.source_picker, self.destination_picker])
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Title
        title = ft.Text(
            "FreeSpace - Hard Disk Move Workflow",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_700
        )
        
        # Source directory section - now for single selection only
        source_section = ft.Container(
            content=ft.Column([
                ft.Text("Source Directory (to move)", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Button(
                        "Select Directory",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.pick_source_directory
                    ),
                    ft.Button(
                        "Clear",
                        icon=ft.Icons.CLEAR,
                        on_click=self.clear_source_directory
                    ),
                ]),
                ft.Container(
                    content=ft.Text("No directory selected", italic=True, color=ft.Colors.GREY_700),
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.GREY_400),
                    border_radius=5,
                ),
            ], spacing=6),
            padding=10,
            border=ft.Border.all(1, ft.Colors.BLUE_200),
            border_radius=10,
        )
        self.source_text = source_section.content.controls[2].content
        
        # Destination directory section - simplified, no session subdirectories
        destination_section = ft.Container(
            content=ft.Column([
                ft.Text("Destination Device/Location", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Button(
                        "Select Location",
                        icon=ft.Icons.STORAGE,
                        on_click=self.pick_destination_directory
                    ),
                    ft.Button(
                        "Clear",
                        icon=ft.Icons.CLEAR,
                        on_click=self.clear_destination_directory
                    ),
                ]),
                ft.Container(
                    content=ft.Text("No location selected", italic=True, color=ft.Colors.GREY_700),
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.GREY_400),
                    border_radius=5,
                ),
            ], spacing=6),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREEN_200),
            border_radius=10,
        )
        self.destination_text = destination_section.content.controls[2].content
        
        # Action buttons - old copy/verify/finalize workflow disabled
        self.copy_button = ft.Button(
            "1. Copy to Destination",
            icon=ft.Icons.COPY_ALL,
            on_click=self.copy_directories,
            disabled=True,
            visible=False,  # Hidden - not used in simplified move-only interface
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_500
            )
        )
        
        self.verify_button = ft.Button(
            "2. Verify Copy",
            icon=ft.Icons.VERIFIED,
            on_click=self.verify_copy,
            disabled=True,
            visible=False,  # Hidden - not used in simplified move-only interface
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_500
            )
        )
        
        self.finalize_button = ft.Button(
            "3. Delete & Create Links",
            icon=ft.Icons.LINK,
            on_click=self.finalize_move,
            disabled=True,
            visible=False,  # Hidden - not used in simplified move-only interface
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.ORANGE_700
            )
        )
        
        self.restore_button = ft.Button(
            "4. Restore",
            icon=ft.Icons.RESTORE,
            on_click=self.restore_files,
            disabled=True,
            visible=False,  # Hidden - not used in simplified move-only interface
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_700
            )
        )
        
        self.move_button = ft.Button(
            "Move Directory",
            icon=ft.Icons.DRIVE_FILE_MOVE,
            on_click=self.move_directory,
            disabled=True,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.PURPLE_700
            ),
            tooltip="Move entire directory to new location and replace with symlink"
        )
        
        self.restore_move_button = ft.Button(
            "Restore Moved Directory",
            icon=ft.Icons.RESTORE_FROM_TRASH,
            on_click=self.restore_moved_directory,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.DEEP_ORANGE_700
            ),
            tooltip="Restore a previously moved directory to its original location"
        )
        
        # Workflow options - hidden for simplified move-only interface
        self.auto_complete_checkbox = ft.Checkbox(
            label="Auto-complete workflow (automatically verify and finalize after copy)",
            value=False,
            visible=False,
            tooltip="Check this to automatically run verify and finalize steps after copying completes"
        )
        
        self.file_level_symlinks_checkbox = ft.Checkbox(
            label="Replace each file with individual symlinks (default: replace entire directory)",
            value=False,
            visible=False,
            tooltip="Check this to create a symlink for each copied file instead of replacing the entire directory with one symlink"
        )
        
        # Sudo password field
        self.sudo_password_field = ft.TextField(
            label="Sudo Password (leave blank if not needed)",
            password=True,
            can_reveal_password=True,
            width=300,
            on_focus=lambda e: print("DEBUG: Sudo password field focused")
        )
        
        action_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.copy_button,
                    self.verify_button,
                    self.finalize_button,
                    self.restore_button,
                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                ft.Row([
                    self.move_button,
                    self.restore_move_button,
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=20),
                ft.Row([
                    self.sudo_password_field,
                ], alignment=ft.MainAxisAlignment.CENTER),
                self.auto_complete_checkbox,
                self.file_level_symlinks_checkbox,
            ], spacing=5),
            padding=10,
        )
        
        # Progress bar
        self.progress_bar = ft.ProgressBar(
            width=800,
            visible=False,
            color=ft.Colors.BLUE_500,
        )
        
        # Status text
        self.status_text = ft.Text(
            "Ready to start. Select source and destination directories.",
            size=14,
            color=ft.Colors.GREY_700,
            italic=True,
            selectable=True
        )
        
        # Log text area for real-time updates
        self.log_text_area = ft.TextField(
            value="",
            multiline=True,
            read_only=True,
            min_lines=6,
            max_lines=6,
            border_color=ft.Colors.GREY_400,
            text_size=12,
            expand=True,
        )
        
        # Kill button - initially hidden
        self.kill_button = ft.OutlinedButton(
            "STOP OPERATION",
            icon=ft.Icons.STOP,
            on_click=self.kill_operation,
            visible=False  # Hidden until operation starts
        )
        
        # Status section
        status_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Status", size=16, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.CONTENT_COPY,
                        tooltip="Copy status text",
                        icon_size=20,
                        on_click=self.copy_status_to_clipboard
                    ),
                ], spacing=0),
                self.progress_bar,
                self.status_text,
                ft.Row([
                    ft.Text("Recent Log:", size=14, weight=ft.FontWeight.BOLD),
                    self.kill_button,
                ], spacing=10, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.log_text_area,
            ], spacing=4),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=10,
        )
        
        # Main layout
        self.page.add(
            ft.Container(
                content=ft.Column([
                    title,
                    source_section,
                    destination_section,
                    action_section,
                    status_section,
                ], scroll=ft.ScrollMode.AUTO, spacing=8),
                padding=15,
            )
        )
    
    async def pick_source_directory(self, e):
        """Open directory picker for single source directory selection."""
        path = await self.source_picker.get_directory_path(
            dialog_title="Select the directory to move"
        )
        
        if path:
            self.source_directory = path
            self.source_text.value = path
            self.source_text.italic = False
            self.source_text.color = ft.Colors.BLUE_700
            self.update_button_states()
            self.page.update()
    
    def clear_source_directory(self, e):
        """Clear the source directory selection."""
        self.source_directory = ""
        self.source_text.value = "No directory selected"
        self.source_text.italic = True
        self.source_text.color = ft.Colors.GREY_700
        self.update_button_states()
        self.page.update()

    
    async def pick_destination_directory(self, e):
        """Open directory picker for destination device/location."""
        path = await self.destination_picker.get_directory_path(
            dialog_title="Select destination device or location (where to move the directory)"
        )
        
        if path:
            self.destination_directory = path
            self.destination_text.value = path
            self.destination_text.italic = False
            self.destination_text.color = ft.Colors.BLUE_700
            self.update_button_states()
            self.page.update()
    
    def clear_destination_directory(self, e):
        """Clear the destination directory selection."""
        self.destination_directory = ""
        self.destination_text.value = "No location selected"
        self.destination_text.italic = True
        self.destination_text.color = ft.Colors.GREY_700
        self.update_button_states()
        self.page.update()
    
    def update_button_states(self):
        """Update the enabled/disabled state of action buttons."""
        has_source = bool(self.source_directory)
        has_destination = bool(self.destination_directory)
        
        # Move button needs both source and destination
        self.move_button.disabled = not (has_source and has_destination)
        # Restore button always available (user picks the moved directory in the dialog)
        self.restore_move_button.disabled = False
        self.page.update()
    
    def update_status(self, message: str, show_progress: bool = False):
        """Update status message and progress bar."""
        self.status_text.value = message
        self.progress_bar.visible = show_progress
        self.page.update()
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add a message to the log text area with timestamp and level, and echo to terminal."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        # Format based on level
        if level == "ERROR":
            log_entry = f"[{timestamp}] ✗ {message}\n"
            terminal_output = f"[{timestamp}] ERROR: {message}"
        elif level == "SUCCESS":
            log_entry = f"[{timestamp}] ✓ {message}\n"
            terminal_output = f"[{timestamp}] SUCCESS: {message}"
        elif level == "WARNING":
            log_entry = f"[{timestamp}] ⚠ {message}\n"
            terminal_output = f"[{timestamp}] WARNING: {message}"
        elif level == "STOP":
            log_entry = f"[{timestamp}] ⏹ {message}\n"
            terminal_output = f"[{timestamp}] STOP: {message}"
        else:
            log_entry = f"[{timestamp}] {message}\n"
            terminal_output = f"[{timestamp}] {message}"
        
        # Echo to terminal
        print(terminal_output)
        
        self.log_text_area.value += log_entry
        # Auto-scroll by keeping only last ~10 lines
        lines = self.log_text_area.value.split('\n')
        if len(lines) > 15:
            self.log_text_area.value = '\n'.join(lines[-15:])
        self.page.update()
    
    def kill_operation(self, e):
        """Kill/stop the current operation."""
        self.log_message("KILL signal received - stopping operation...", level="STOP")
        self.stop_operation.set()  # Signal the background thread to stop
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def copy_directories(self, e):
        """Copy selected directories to destination."""
        if not self.source_directories or not self.destination_directory:
            self.show_error("Please select source and destination directories.")
            return
        
        # Check if auto-complete is enabled
        auto_complete = self.auto_complete_checkbox.value
        
        # Confirm action
        if auto_complete:
            confirmed = await self.ask_yes_no(
                "Confirm Auto-Complete Workflow",
                f"This will automatically:\n"
                f"1. Copy {len(self.source_directories)} director{'y' if len(self.source_directories) == 1 else 'ies'} to {self.destination_directory}\n"
                f"2. Verify all copied files\n"
                f"3. Delete originals and create symbolic links\n\n"
                f"This is a complete workflow that will modify your original directories!\n\n"
                f"Are you sure you want to proceed?"
            )
        else:
            confirmed = await self.ask_yes_no(
                "Confirm Copy",
                f"Copy {len(self.source_directories)} director{'y' if len(self.source_directories) == 1 else 'ies'} "
                f"to {self.destination_directory}?\n\nThis may take a while depending on the size."
            )
        
        if confirmed:
            # Store auto_complete state for use in background thread
            self._auto_complete_mode = auto_complete
            
            # Run the copy operation in a background thread to avoid blocking UI
            def run_copy():
                try:
                    self._perform_copy()
                except Exception as ex:
                    print(f"Exception during copy: {ex}")
                    import traceback
                    traceback.print_exc()
            
            thread = threading.Thread(target=run_copy, daemon=True)
            thread.start()
    
    def _perform_copy(self):
        """Perform the actual copy operation."""
        self.update_status("Copying directories to destination...", show_progress=True)
        self.log_message("Starting copy operation...")
        self.copy_button.disabled = True
        self.page.update()  # Force UI update before starting long operation
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"copy_log_{timestamp}.json"
        
        copy_log = {
            "timestamp": timestamp,
            "source_directories": self.source_directories,
            "destination_directory": self.actual_destination_directory,
            "copies": []
        }
        
        try:
            for src_dir in self.source_directories:
                # Preserve full directory structure at destination
                # Convert absolute path to relative path structure
                src_path = Path(src_dir).resolve()
                
                # Create the full path at destination by preserving the directory structure
                # Remove leading slash to make it relative, then join with destination
                rel_structure = str(src_path).lstrip('/')
                dest_dir = os.path.join(self.actual_destination_directory, rel_structure)
                
                self.update_status(f"Copying: {src_dir}...", show_progress=True)
                self.log_message(f"Copying {os.path.basename(src_dir)}...")
                
                if os.path.exists(dest_dir):
                    error_msg = f"Destination already exists: {dest_dir}"
                    self.log_message(f"SKIPPED: {os.path.basename(src_dir)} (already exists)")
                    copy_log["copies"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "skipped",
                        "reason": "destination already exists"
                    })
                    continue
                
                # Copy with error handling for individual files
                errors = []
                skipped_trashes = []
                def copy_with_errors(src, dst, *, follow_symlinks=True):
                    try:
                        return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
                    except Exception as e:
                        errors.append((src, str(e)))
                        return None
                
                def ignore_items(dir, files):
                    ignored = []
                    for f in files:
                        full_path = os.path.join(dir, f)
                        # Skip symbolic links
                        if os.path.islink(full_path):
                            ignored.append(f)
                        # Skip .Trashes directories and files
                        elif f == '.Trashes' or f.startswith('.Trashes'):
                            ignored.append(f)
                            skipped_trashes.append(full_path)
                            self.log_message(f"Deleted (not copied): {os.path.relpath(full_path, src_dir)}")
                    return ignored
                
                shutil.copytree(src_dir, dest_dir, copy_function=copy_with_errors, 
                               ignore=ignore_items)
                
                self.log_message(f"✓ Copied {os.path.basename(src_dir)}")
                
                copy_log["copies"].append({
                    "source": src_dir,
                    "destination": dest_dir,
                    "status": "copied" if not errors else "partial",
                    "files_failed": len(errors),
                    "failed_files": errors[:10] if errors else None,  # Log first 10 failures
                    "trashes_skipped": len(skipped_trashes),
                    "trashes_items": skipped_trashes if skipped_trashes else None
                })
            
            # Save log locally
            with open(log_file, 'w') as f:
                json.dump(copy_log, f, indent=2)
            
            # Copy log to destination as well
            dest_log_dir = os.path.join(self.actual_destination_directory, "freespace_logs")
            os.makedirs(dest_log_dir, exist_ok=True)
            dest_log_file = os.path.join(dest_log_dir, f"copy_log_{timestamp}.json")
            shutil.copy2(log_file, dest_log_file)
            
            self.log_message("Copy operation completed!")
            self.update_status(f"Copy completed! Log saved to: {log_file} and {dest_log_file}", show_progress=False)
            self.verify_button.disabled = False
            self.page.update()
            
            # If auto-complete is enabled, continue with verify
            if hasattr(self, '_auto_complete_mode') and self._auto_complete_mode:
                self.log_message("Auto-complete: Starting verification...")
                self._perform_verify()
            
        except Exception as ex:
            self.log_message(f"ERROR: {str(ex)}")
            self.show_error(f"Error during copy: {str(ex)}")
            self.copy_button.disabled = False
            self.update_status("Copy failed.", show_progress=False)
    
    async def verify_copy(self, e):
        """Verify that copied files match originals."""
        if not self.source_directories or not self.actual_destination_directory:
            self.show_error("No copy operation to verify.")
            return
        
        # Run verification in background thread
        def run_verify():
            try:
                self._perform_verify()
            except Exception as ex:
                print(f"Exception during verify: {ex}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=run_verify, daemon=True)
        thread.start()
    
    def _perform_verify(self):
        """Perform the actual verification operation."""
        self.update_status("Verifying copied files...", show_progress=True)
        self.log_message("Starting verification...")
        self.verify_button.disabled = True
        self.page.update()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"verify_log_{timestamp}.json"
        
        verify_log = {
            "timestamp": timestamp,
            "verifications": []
        }
        
        try:
            all_verified = True
            
            for src_dir in self.source_directories:
                # Use full path structure like in copy
                src_path = Path(src_dir).resolve()
                rel_structure = str(src_path).lstrip('/')
                dest_dir = os.path.join(self.actual_destination_directory, rel_structure)
                
                self.update_status(f"Verifying: {src_dir}...", show_progress=True)
                self.log_message(f"Verifying {os.path.basename(src_dir)}...")
                
                if not os.path.exists(dest_dir):
                    all_verified = False
                    self.log_message(f"✗ FAILED: {os.path.basename(src_dir)} (destination not found)")
                    self.page.update()
                    verify_log["verifications"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "failed",
                        "reason": "destination does not exist"
                    })
                    continue
                
                # Verify directory structure and files
                verification_result = self._verify_directory(src_dir, dest_dir)
                verify_log["verifications"].append(verification_result)
                
                if verification_result["status"] != "verified":
                    all_verified = False
                    self.log_message(f"✗ FAILED: {os.path.basename(src_dir)} ({len(verification_result.get('mismatches', []))} mismatches)")
                    self.page.update()
                else:
                    skipped_count = len(verification_result.get('skipped', []))
                    if skipped_count > 0:
                        self.log_message(f"✓ Verified {os.path.basename(src_dir)} ({skipped_count} files skipped)")
                        self.page.update()
                    else:
                        self.log_message(f"✓ Verified {os.path.basename(src_dir)}")
                        self.page.update()
            
            # Save log locally
            with open(log_file, 'w') as f:
                json.dump(verify_log, f, indent=2)
            
            # Copy log to destination
            dest_log_dir = os.path.join(self.actual_destination_directory, "freespace_logs")
            os.makedirs(dest_log_dir, exist_ok=True)
            dest_log_file = os.path.join(dest_log_dir, f"verify_log_{timestamp}.json")
            shutil.copy2(log_file, dest_log_file)
            
            if all_verified:
                self.log_message("Verification completed successfully!")
                self.page.update()
                self.update_status(f"Verification successful! Log saved to: {log_file} and {dest_log_file}", show_progress=False)
                self.finalize_button.disabled = False
                self.page.update()
                
                # If auto-complete is enabled, continue with finalize
                if hasattr(self, '_auto_complete_mode') and self._auto_complete_mode:
                    self.log_message("Auto-complete: Starting finalization...")
                    self.page.update()
                    self._perform_finalize()
            else:
                self.log_message("Verification completed with errors")
                self.page.update()
                self.update_status(f"Verification failed! Check log: {log_file} and {dest_log_file}", show_progress=False)
                self.verify_button.disabled = False
                self.page.update()
            
            self.page.update()
            
        except Exception as ex:
            self.log_message(f"ERROR: {str(ex)}")
            self.show_error(f"Error during verification: {str(ex)}")
            self.verify_button.disabled = False
            self.update_status("Verification failed.", show_progress=False)
    
    def _verify_directory(self, src_dir: str, dest_dir: str) -> Dict:
        """Verify that a directory was copied correctly, skipping symbolic links."""
        result = {
            "source": src_dir,
            "destination": dest_dir,
            "status": "verified",
            "mismatches": [],
            "skipped": []
        }
        
        # Check all files exist and match
        for root, dirs, files in os.walk(src_dir, onerror=lambda e: None):
            # Filter out directories we can't access
            dirs[:] = [d for d in dirs if os.access(os.path.join(root, d), os.R_OK)]
            
            for file in files:
                src_file = os.path.join(root, file)
                
                # Skip symbolic links
                if os.path.islink(src_file):
                    continue
                
                # Check if we can read the file
                if not os.access(src_file, os.R_OK):
                    rel_path = os.path.relpath(src_file, src_dir)
                    result["skipped"].append({
                        "file": rel_path,
                        "reason": "permission denied"
                    })
                    continue
                
                rel_path = os.path.relpath(src_file, src_dir)
                dest_file = os.path.join(dest_dir, rel_path)
                
                if not os.path.exists(dest_file):
                    result["status"] = "failed"
                    result["mismatches"].append({
                        "file": rel_path,
                        "reason": "missing in destination"
                    })
                    continue
                
                try:
                    # Check file sizes match
                    if os.path.getsize(src_file) != os.path.getsize(dest_file):
                        result["status"] = "failed"
                        result["mismatches"].append({
                            "file": rel_path,
                            "reason": "size mismatch"
                        })
                        continue
                except (OSError, PermissionError) as e:
                    result["skipped"].append({
                        "file": rel_path,
                        "reason": f"cannot access: {str(e)}"
                    })
                    continue
        
        # Note: For performance reasons, this verification checks existence and size only.
        # For critical data, consider running a full checksum verification separately.
        
        return result
    
    async def finalize_move(self, e):
        """Delete original directories and create symbolic links."""
        # Determine which mode we're using
        file_level = self.file_level_symlinks_checkbox.value
        
        if file_level:
            mode_description = "Files will be replaced with individual symlinks (directory structure preserved)."
        else:
            mode_description = "Each entire directory will be replaced with a single symlink."
        
        # Strong confirmation required
        confirmed = await self.ask_yes_no(
            "⚠️ Final Confirmation",
            f"This will DELETE the original {len(self.source_directories)} "
            f"director{'y' if len(self.source_directories) == 1 else 'ies'} "
            f"and replace {'it' if len(self.source_directories) == 1 else 'them'} with symbolic {'link' if len(self.source_directories) == 1 else 'links'} "
            f"to the destination copies.\n\n"
            f"{mode_description}\n\n"
            "This action cannot be undone!\n\n"
            "Are you absolutely sure?"
        )
        
        if confirmed:
            # Run the finalize operation in a background thread to avoid blocking UI
            def run_finalize():
                try:
                    self._perform_finalize()
                except Exception as ex:
                    print(f"Exception during finalize: {ex}")
                    import traceback
                    traceback.print_exc()
            
            thread = threading.Thread(target=run_finalize, daemon=True)
            thread.start()
    
    def _perform_finalize(self):
        """Perform the finalization based on selected mode."""
        if self.file_level_symlinks_checkbox.value:
            self._perform_finalize_file_level()
        else:
            self._perform_finalize_directory_level()
    
    def _perform_finalize_directory_level(self):
        """Perform the finalization: replace entire directories with symlinks to destination."""
        self.update_status("Finalizing move: replacing directories with links...", show_progress=True)
        self.log_message("Starting finalization (directory-level mode)...")
        self.finalize_button.disabled = True
        self.page.update()  # Force UI update before starting long operation
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"finalize_log_{timestamp}.json"
        
        finalize_log = {
            "timestamp": timestamp,
            "mode": "directory_level",
            "operations": []
        }
        
        try:
            for src_dir in self.source_directories:
                # Use full path structure like in copy
                src_path = Path(src_dir).resolve()
                rel_structure = str(src_path).lstrip('/')
                dest_dir = os.path.join(self.actual_destination_directory, rel_structure)
                
                self.update_status(f"Finalizing: {src_dir}...", show_progress=True)
                self.log_message(f"Finalizing {os.path.basename(src_dir)}...")
                
                if not os.path.exists(dest_dir):
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "skipped",
                        "reason": "destination does not exist"
                    })
                    continue
                
                # Check if source is already a symlink
                if os.path.islink(src_dir):
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "skipped",
                        "reason": "source is already a symbolic link"
                    })
                    continue
                
                try:
                    # Calculate space to be freed
                    bytes_freed = 0
                    for root, dirs, files in os.walk(src_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if not os.path.islink(file_path):
                                try:
                                    bytes_freed += os.path.getsize(file_path)
                                except (OSError, PermissionError):
                                    pass
                    
                    # Create backup directory name
                    backup_dir = src_dir + ".backup_" + timestamp
                    
                    # Rename original directory to backup
                    os.rename(src_dir, backup_dir)
                    
                    try:
                        # Create symlink at original location pointing to destination
                        os.symlink(dest_dir, src_dir)
                        
                        # Delete backup after successful symlink creation
                        shutil.rmtree(backup_dir)
                        
                        self.log_message(f"✓ Finalized {os.path.basename(src_dir)}")
                        
                        finalize_log["operations"].append({
                            "source": src_dir,
                            "destination": dest_dir,
                            "status": "completed",
                            "bytes_freed": bytes_freed
                        })
                        
                    except Exception as symlink_ex:
                        # Rollback on error: restore backup
                        if os.path.exists(src_dir) and os.path.islink(src_dir):
                            os.remove(src_dir)
                        os.rename(backup_dir, src_dir)
                        raise symlink_ex
                    
                except Exception as ex:
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "failed",
                        "error": str(ex)
                    })
                    raise
            
            # Save log locally
            with open(log_file, 'w') as f:
                json.dump(finalize_log, f, indent=2)
            
            # Copy log to destination
            dest_log_dir = os.path.join(self.actual_destination_directory, "freespace_logs")
            os.makedirs(dest_log_dir, exist_ok=True)
            dest_log_file = os.path.join(dest_log_dir, f"finalize_log_{timestamp}.json")
            shutil.copy2(log_file, dest_log_file)
            
            # Count successful operations and total bytes freed
            total_completed = sum(1 for op in finalize_log["operations"] if op.get("status") == "completed")
            total_failed = sum(1 for op in finalize_log["operations"] if op.get("status") == "failed")
            total_skipped = sum(1 for op in finalize_log["operations"] if op.get("status") == "skipped")
            total_bytes_freed = sum(op.get("bytes_freed", 0) for op in finalize_log["operations"])
            
            # Format disk space freed
            if total_bytes_freed >= 1024**3:  # GB
                space_freed = f"{total_bytes_freed / (1024**3):.2f} GB"
            elif total_bytes_freed >= 1024**2:  # MB
                space_freed = f"{total_bytes_freed / (1024**2):.2f} MB"
            elif total_bytes_freed >= 1024:  # KB
                space_freed = f"{total_bytes_freed / 1024:.2f} KB"
            else:
                space_freed = f"{total_bytes_freed} bytes"
            
            status_msg = f"Move finalized! {total_completed} director{'y' if total_completed == 1 else 'ies'} replaced with symbolic links. Space freed: {space_freed}."
            if total_skipped > 0:
                status_msg += f" ({total_skipped} skipped)"
            if total_failed > 0:
                status_msg += f" ({total_failed} failed - check log)"
            status_msg += f" Logs saved to: {log_file} and {dest_log_file}"
            
            self.update_status(status_msg, show_progress=False)
            
            # Reset state for next operation
            self.source_directories.clear()
            self.destination_directory = ""
            self.actual_destination_directory = ""
            self.update_source_list()
            self.destination_text.value = "No destination selected"
            self.destination_text.italic = True
            self.destination_text.color = ft.Colors.GREY_700
            self.update_button_states()
            
        except Exception as ex:
            self.show_error(f"Error during finalization: {str(ex)}")
            self.finalize_button.disabled = False
            self.update_status("Finalization failed.", show_progress=False)
    
    def _perform_finalize_file_level(self):
        """Perform the finalization: replace individual files with symlinks to destination."""
        self.update_status("Finalizing move: replacing files with links...", show_progress=True)
        self.finalize_button.disabled = True
        self.page.update()  # Force UI update before starting long operation
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"finalize_log_{timestamp}.json"
        
        finalize_log = {
            "timestamp": timestamp,
            "mode": "file_level",
            "operations": []
        }
        
        try:
            for src_dir in self.source_directories:
                # Use full path structure like in copy
                src_path = Path(src_dir).resolve()
                rel_structure = str(src_path).lstrip('/')
                dest_dir = os.path.join(self.actual_destination_directory, rel_structure)
                
                self.update_status(f"Finalizing: {src_dir}...", show_progress=True)
                
                if not os.path.exists(dest_dir):
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "skipped",
                        "reason": "destination does not exist"
                    })
                    continue
                
                # Replace individual files with symlinks
                files_processed = []
                files_failed = []
                files_skipped = []
                bytes_freed = 0
                
                try:
                    # Walk through all files in source directory
                    for root, dirs, files in os.walk(src_dir):
                        for file in files:
                            src_file = os.path.join(root, file)
                            rel_path = os.path.relpath(src_file, src_dir)
                            dest_file = os.path.join(dest_dir, rel_path)
                            
                            # Skip symbolic links - don't process existing links
                            if os.path.islink(src_file):
                                files_skipped.append({
                                    "file": rel_path,
                                    "reason": "already a symbolic link"
                                })
                                continue
                            
                            if not os.path.exists(dest_file):
                                files_failed.append({
                                    "file": rel_path,
                                    "reason": "destination file does not exist"
                                })
                                continue
                            
                            # Check if file is immutable (protected)
                            try:
                                file_stat = os.stat(src_file)
                                if hasattr(stat, 'UF_IMMUTABLE') and (file_stat.st_flags & stat.UF_IMMUTABLE):
                                    files_skipped.append({
                                        "file": rel_path,
                                        "reason": "file is immutable (protected)"
                                    })
                                    continue
                            except Exception:
                                pass  # If we can't check flags, try to process anyway
                            
                            try:
                                # Get file size before replacing
                                file_size = os.path.getsize(src_file)
                                
                                # Create backup of original file
                                backup_file = src_file + ".backup_" + timestamp
                                os.rename(src_file, backup_file)
                                
                                # Create symlink to destination file
                                os.symlink(dest_file, src_file)
                                
                                # Delete backup after successful symlink creation
                                os.remove(backup_file)
                                
                                # Track space freed
                                bytes_freed += file_size
                                files_processed.append(rel_path)
                                
                            except Exception as file_ex:
                                # Rollback this file on error
                                backup_file = src_file + ".backup_" + timestamp
                                if os.path.exists(backup_file):
                                    if os.path.exists(src_file) and os.path.islink(src_file):
                                        os.remove(src_file)
                                    os.rename(backup_file, src_file)
                                
                                files_failed.append({
                                    "file": rel_path,
                                    "reason": str(file_ex)
                                })
                    
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "completed" if not files_failed else "partial",
                        "files_processed": len(files_processed),
                        "files_skipped": len(files_skipped),
                        "files_failed": len(files_failed),
                        "bytes_freed": bytes_freed,
                        "skipped_details": files_skipped if files_skipped else None,
                        "failed_details": files_failed if files_failed else None
                    })
                    
                except Exception as ex:
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "failed",
                        "error": str(ex)
                    })
                    raise
            
            # Save log locally
            with open(log_file, 'w') as f:
                json.dump(finalize_log, f, indent=2)
            
            # Copy log to destination
            dest_log_dir = os.path.join(self.actual_destination_directory, "freespace_logs")
            os.makedirs(dest_log_dir, exist_ok=True)
            dest_log_file = os.path.join(dest_log_dir, f"finalize_log_{timestamp}.json")
            shutil.copy2(log_file, dest_log_file)
            
            # Count total files processed and disk space freed
            total_processed = sum(op.get("files_processed", 0) for op in finalize_log["operations"])
            total_skipped = sum(op.get("files_skipped", 0) for op in finalize_log["operations"])
            total_failed = sum(op.get("files_failed", 0) for op in finalize_log["operations"])
            total_bytes_freed = sum(op.get("bytes_freed", 0) for op in finalize_log["operations"])
            
            # Format disk space freed
            if total_bytes_freed >= 1024**3:  # GB
                space_freed = f"{total_bytes_freed / (1024**3):.2f} GB"
            elif total_bytes_freed >= 1024**2:  # MB
                space_freed = f"{total_bytes_freed / (1024**2):.2f} MB"
            elif total_bytes_freed >= 1024:  # KB
                space_freed = f"{total_bytes_freed / 1024:.2f} KB"
            else:
                space_freed = f"{total_bytes_freed} bytes"
            
            status_msg = f"Move finalized! {total_processed} files replaced with symbolic links. Space freed: {space_freed}."
            if total_skipped > 0:
                status_msg += f" ({total_skipped} files skipped)"
            if total_failed > 0:
                status_msg += f" ({total_failed} files failed - check log)"
            status_msg += f" Logs saved to: {log_file} and {dest_log_file}"
            
            self.update_status(status_msg, show_progress=False)
            
            # Reset state for next operation
            self.source_directories.clear()
            self.destination_directory = ""
            self.actual_destination_directory = ""
            self.update_source_list()
            self.destination_text.value = "No destination selected"
            self.destination_text.italic = True
            self.destination_text.color = ft.Colors.GREY_700
            self.update_button_states()
            
        except Exception as ex:
            self.show_error(f"Error during finalization: {str(ex)}")
            self.finalize_button.disabled = False
    async def restore_files(self, e):
        """Restore original files from symlinks by copying from destination."""
        # Confirmation
        confirmed = await self.ask_yes_no(
            "⚠️ Restore Confirmation",
            f"This will find all symbolic links in the selected {len(self.source_directories)} "
            f"director{'y' if len(self.source_directories) == 1 else 'ies'} "
            f"and restore the original files from their destinations.\n\n"
            "The symlinks will be replaced with actual file copies.\n\n"
            "Are you sure?"
        )
        
        if confirmed:
            # Run the restore operation in a background thread to avoid blocking UI
            def run_restore():
                try:
                    self._perform_restore()
                except Exception as ex:
                    print(f"Exception during restore: {ex}")
                    import traceback
                    traceback.print_exc()
            
            thread = threading.Thread(target=run_restore, daemon=True)
            thread.start()
    
    def _perform_restore(self):
        """Perform the restoration: find symlinks and restore original files."""
        self.update_status("Restoring: scanning for symbolic links...", show_progress=True)
        self.restore_button.disabled = True
        self.page.update()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"restore_log_{timestamp}.json"
        
        restore_log = {
            "timestamp": timestamp,
            "operations": []
        }
        
        total_restored = 0
        total_failed = 0
        total_skipped = 0
        total_bytes_restored = 0
        
        try:
            for src_dir in self.source_directories:
                self.update_status(f"Restoring: scanning {src_dir}...", show_progress=True)
                self.log_message(f"Scanning {os.path.basename(src_dir)}...")
                
                dir_log = {
                    "source": src_dir,
                    "symlinks_found": 0,
                    "files": []
                }
                
                # Check if the entire directory is a symlink
                if os.path.islink(src_dir):
                    try:
                        link_target = os.readlink(src_dir)
                        self.log_message(f"Directory {os.path.basename(src_dir)} is a symlink to {link_target}")
                        
                        if not os.path.exists(link_target):
                            dir_log["files"].append({
                                "path": src_dir,
                                "status": "failed",
                                "reason": "symlink target does not exist"
                            })
                            total_failed += 1
                        else:
                            # Remove symlink and copy entire directory back
                            backup_link = src_dir + ".link_backup_" + timestamp
                            os.rename(src_dir, backup_link)
                            
                            try:
                                # Copy directory from destination back to source
                                shutil.copytree(link_target, src_dir)
                                
                                # Calculate bytes restored
                                bytes_restored = 0
                                for root, dirs, files in os.walk(src_dir):
                                    for file in files:
                                        try:
                                            bytes_restored += os.path.getsize(os.path.join(root, file))
                                        except (OSError, PermissionError):
                                            pass
                                
                                # Remove backup symlink after successful restore
                                os.remove(backup_link)
                                
                                total_restored += 1
                                total_bytes_restored += bytes_restored
                                dir_log["symlinks_found"] = 1
                                dir_log["files"].append({
                                    "path": src_dir,
                                    "status": "restored",
                                    "type": "directory",
                                    "bytes_restored": bytes_restored
                                })
                                self.log_message(f"✓ Restored directory {os.path.basename(src_dir)}")
                                
                            except Exception as restore_ex:
                                # Rollback on error: restore symlink
                                if os.path.exists(src_dir):
                                    shutil.rmtree(src_dir)
                                os.rename(backup_link, src_dir)
                                dir_log["files"].append({
                                    "path": src_dir,
                                    "status": "failed",
                                    "reason": str(restore_ex)
                                })
                                total_failed += 1
                                self.log_message(f"✗ Failed to restore {os.path.basename(src_dir)}: {restore_ex}")
                        
                    except Exception as ex:
                        dir_log["files"].append({
                            "path": src_dir,
                            "status": "failed",
                            "reason": str(ex)
                        })
                        total_failed += 1
                        self.log_message(f"✗ Error processing {os.path.basename(src_dir)}: {ex}")
                
                else:
                    # Walk through directory and find file-level symlinks
                    symlinks_found = []
                    for root, dirs, files in os.walk(src_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.islink(file_path):
                                symlinks_found.append(file_path)
                    
                    dir_log["symlinks_found"] = len(symlinks_found)
                    
                    if len(symlinks_found) == 0:
                        self.log_message(f"No symlinks found in {os.path.basename(src_dir)}")
                        total_skipped += 1
                    else:
                        self.log_message(f"Found {len(symlinks_found)} symlink(s) in {os.path.basename(src_dir)}")
                        
                        # Restore each symlink
                        for symlink_path in symlinks_found:
                            try:
                                link_target = os.readlink(symlink_path)
                                rel_path = os.path.relpath(symlink_path, src_dir)
                                
                                if not os.path.exists(link_target):
                                    dir_log["files"].append({
                                        "path": rel_path,
                                        "status": "failed",
                                        "reason": "symlink target does not exist"
                                    })
                                    total_failed += 1
                                    continue
                                
                                # Get file size
                                file_size = os.path.getsize(link_target)
                                
                                # Backup symlink
                                backup_link = symlink_path + ".link_backup_" + timestamp
                                os.rename(symlink_path, backup_link)
                                
                                try:
                                    # Copy file from destination to replace symlink
                                    shutil.copy2(link_target, symlink_path)
                                    
                                    # Remove backup after successful restore
                                    os.remove(backup_link)
                                    
                                    total_restored += 1
                                    total_bytes_restored += file_size
                                    dir_log["files"].append({
                                        "path": rel_path,
                                        "status": "restored",
                                        "type": "file",
                                        "bytes_restored": file_size
                                    })
                                    
                                except Exception as restore_ex:
                                    # Rollback on error: restore symlink
                                    if os.path.exists(symlink_path):
                                        os.remove(symlink_path)
                                    os.rename(backup_link, symlink_path)
                                    dir_log["files"].append({
                                        "path": rel_path,
                                        "status": "failed",
                                        "reason": str(restore_ex)
                                    })
                                    total_failed += 1
                                
                            except Exception as ex:
                                dir_log["files"].append({
                                    "path": os.path.relpath(symlink_path, src_dir) if src_dir in symlink_path else symlink_path,
                                    "status": "failed",
                                    "reason": str(ex)
                                })
                                total_failed += 1
                        
                        if dir_log["symlinks_found"] > 0:
                            restored_count = sum(1 for f in dir_log["files"] if f.get("status") == "restored")
                            self.log_message(f"✓ Restored {restored_count}/{dir_log['symlinks_found']} file(s) in {os.path.basename(src_dir)}")
                
                restore_log["operations"].append(dir_log)
            
            # Save log
            restore_log["summary"] = {
                "total_restored": total_restored,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "total_bytes_restored": total_bytes_restored
            }
            
            with open(log_file, 'w') as f:
                json.dump(restore_log, f, indent=2)
            
            # Format bytes restored
            if total_bytes_restored >= 1024**3:  # GB
                space_restored = f"{total_bytes_restored / (1024**3):.2f} GB"
            elif total_bytes_restored >= 1024**2:  # MB
                space_restored = f"{total_bytes_restored / (1024**2):.2f} MB"
            elif total_bytes_restored >= 1024:  # KB
                space_restored = f"{total_bytes_restored / 1024:.2f} KB"
            else:
                space_restored = f"{total_bytes_restored} bytes"
            
            status_msg = f"Restore complete! {total_restored} item(s) restored. Space used: {space_restored}."
            if total_skipped > 0:
                status_msg += f" ({total_skipped} director{'y' if total_skipped == 1 else 'ies'} had no symlinks)"
            if total_failed > 0:
                status_msg += f" ({total_failed} failed - check log)"
            status_msg += f" Log saved to: {log_file}"
            
            self.update_status(status_msg, show_progress=False)
            self.log_message("Restore operation completed.")
            
        except Exception as ex:
            self.show_error(f"Error during restore: {str(ex)}")
            self.update_status("Restore failed.", show_progress=False)
        finally:
            self.restore_button.disabled = False
            self.page.update()
    
            self.update_status("Finalization failed.", show_progress=False)
    
    async def move_directory(self, e):
        """Move selected directory to the destination and replace with symlink."""
        print("DEBUG: move_directory function called")
        if not self.source_directory or not self.destination_directory:
            self.show_error("Please select both a directory to move and a destination location.")
            return
        
        # Build move plan description
        dir_name = os.path.basename(self.source_directory)
        dest_path = os.path.join(self.destination_directory, dir_name)
        
        # Strong confirmation required
        confirmed = await self.ask_yes_no(
            "⚠️ Move Directory Confirmation",
            f"This will MOVE the directory:\n"
            f"  {self.source_directory}\n\n"
            f"To:\n"
            f"  {dest_path}\n\n"
            f"The original directory will be replaced with a symbolic link.\n\n"
            "This action cannot be undone!\n\n"
            "Are you absolutely sure?"
        )
        
        if confirmed:
            print("DEBUG: Move confirmed")
            # Get sudo password from the text field
            sudo_password = self.sudo_password_field.value if self.sudo_password_field.value else None
            print(f"DEBUG: Got sudo_password from field: {bool(sudo_password)}")
            
            # Reset kill switch for new operation
            self.stop_operation.clear()
            self.operation_in_progress = True
            self.kill_button.visible = True
            self.page.update()
            
            # Run the move operation in a background thread to avoid blocking UI
            def run_move():
                try:
                    self._perform_move(self.destination_directory, sudo_password=sudo_password)
                except Exception as ex:
                    print(f"Exception during move: {ex}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self.operation_in_progress = False
                    self.kill_button.visible = False
                    self.page.update()
            
            thread = threading.Thread(target=run_move, daemon=True)
            thread.start()
    
    def _perform_move(self, destination: str, sudo_password: str = None):
        """Perform the move operation for a single directory, with optional sudo support."""
        src_dir = self.source_directory
        dir_name = os.path.basename(src_dir)
        dest_path = os.path.join(destination, dir_name)
        
        self.update_status(f"Moving directory: {dir_name}...", show_progress=True)
        self.log_message(f"Starting move operation for {dir_name}...", level="INFO")
        self.move_button.disabled = True
        self.page.update()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"move_log_{timestamp}.json"
        
        try:
            # Normalize paths
            self.log_message(f"Normalizing paths...", level="INFO")
            src_dir = os.path.abspath(src_dir)
            dest_path = os.path.abspath(dest_path)
            self.log_message(f"Source: {src_dir}", level="INFO")
            self.log_message(f"Destination: {dest_path}", level="INFO")
            
            # Check if operation was killed
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled by user", level="STOP")
                self.update_status("Move cancelled", show_progress=False)
                return
            
            # Check if destination already exists - this could be from a previous interrupted move
            self.log_message(f"Checking if destination exists...", level="INFO")
            self.page.update()
            
            if os.path.exists(dest_path):
                self.log_message(f"Destination already exists", level="WARNING")
                self.page.update()
                
                # Check if source is already a symlink - if so, move is already complete
                if os.path.islink(src_dir):
                    self.log_message(f"Source is already a symlink - move already complete", level="SUCCESS")
                    self.update_status("Move already complete - symlink already in place", show_progress=False)
                    return
                else:
                    # Destination exists but source is not a symlink - treat as interrupted move and recover
                    self.log_message(f"Treating as interrupted move - will complete by creating symlink", level="INFO")
                    self.page.update()
                    # Continue below to complete the move
            
            # Check if operation was killed
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled by user", level="STOP")
                self.update_status("Move cancelled", show_progress=False)
                return
            
            # Calculate bytes to be moved
            self.log_message(f"Calculating directory size...", level="INFO")
            bytes_moved = 0
            file_count = 0
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_count += 1
                    file_path = os.path.join(root, file)
                    if not os.path.islink(file_path):
                        try:
                            bytes_moved += os.path.getsize(file_path)
                        except (OSError, PermissionError):
                            pass
            
            # Format bytes moved
            if bytes_moved >= 1024**3:  # GB
                space_moved = f"{bytes_moved / (1024**3):.2f} GB"
            elif bytes_moved >= 1024**2:  # MB
                space_moved = f"{bytes_moved / (1024**2):.2f} MB"
            elif bytes_moved >= 1024:  # KB
                space_moved = f"{bytes_moved / 1024:.2f} KB"
            else:
                space_moved = f"{bytes_moved} bytes"
            
            self.log_message(f"Directory contains {file_count} files ({space_moved})", level="INFO")
            
            # Check if operation was killed
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled by user", level="STOP")
                self.update_status("Move cancelled", show_progress=False)
                return
            
            # Use the API to perform the move (which handles sudo)
            self.log_message(f"Starting atomic move operation...", level="INFO")
            from freespace_api import FreeSpaceAPI
            api = FreeSpaceAPI(log_directory=str(self.log_directory))
            result = api.move_directory(src_dir, dest_path, sudo_password=sudo_password)
            
            # Check if operation was killed during move
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled during move", level="STOP")
                self.update_status("Move cancelled", show_progress=False)
                return
            
            # Log the result
            if result.get("status") == "already_complete":
                self.log_message(f"✓ Move already complete - symlink already in place", level="SUCCESS")
            else:
                # Log details about files that were moved
                if "files_moved" in result or "file_count" in result:
                    file_count = result.get("file_count", len(result.get("files_moved", [])))
                    self.log_message(f"✓ Moved {file_count} files", level="SUCCESS")
                    # Log a sample of moved files
                    if "files_moved" in result:
                        for f in result.get("files_moved", [])[:10]:
                            self.log_message(f"  ✓ {f}", level="INFO")
                        if len(result.get("files_moved", [])) > 10:
                            remaining = file_count - 10
                            self.log_message(f"  ... and {remaining} more files", level="INFO")
            
            self.log_message(f"Move operation completed successfully", level="SUCCESS")
            self.log_message(f"Creating symlink at original location...", level="INFO")
            self.log_message(f"✓ Successfully moved {dir_name}", level="SUCCESS")
            
            status_msg = f"✓ Move completed! {dir_name} moved to {destination}. Space freed: {space_moved}."
            self.update_status(status_msg, show_progress=False)
            print("DEBUG: Move operation completed and status updated")
            sys.stdout.flush()
            
            # Reset state
            self.source_directory = ""
            self.destination_directory = ""
            self.source_text.value = "No directory selected"
            self.source_text.italic = True
            self.source_text.color = ft.Colors.GREY_700
            self.destination_text.value = "No location selected"
            self.destination_text.italic = True
            self.destination_text.color = ft.Colors.GREY_700
            self.update_button_states()
            print("DEBUG: State reset and button states updated")
            sys.stdout.flush()
            
        except PermissionError as perm_ex:
            # Permission denied - shouldn't happen now with sudo support
            self.log_message(f"✗ Permission denied: {str(perm_ex)}", level="ERROR")
            self.show_error(f"Permission denied: {str(perm_ex)}\n\nTry running with sudo enabled.")
            
        except OSError as os_ex:
            # OSError includes permission denied when wrapped by subprocess
            error_msg = str(os_ex)
            if "Permission denied" in error_msg or "permission" in error_msg.lower():
                self.log_message(f"✗ Permission denied: {error_msg}", level="ERROR")
                self.show_error(f"Permission denied.\n\nThe move operation requires elevated privileges.\n\nError: {error_msg}")
            else:
                self.log_message(f"✗ OS Error: {error_msg}", level="ERROR")
                self.show_error(f"OS Error during move: {error_msg}")
            
        except FileExistsError as exists_ex:
            # Destination already exists - this should have been handled, log as warning only
            self.log_message(f"⚠ Destination already exists, checking for interrupted move recovery", level="WARNING")
            self.update_status("Destination already exists", show_progress=False)
            
        except Exception as ex:
            self.show_error(f"Error during move operation: {str(ex)}")
            self.update_status("Move operation failed.", show_progress=False)
            self.log_message(f"✗ Move operation failed: {ex}")
        finally:
            print("DEBUG: Move operation finally block - re-enabling button and updating page")
            sys.stdout.flush()
            self.move_button.disabled = False
            self.page.update()
            print("DEBUG: Page updated in finally block")
            sys.stdout.flush()
    
    async def restore_moved_directory(self, e):
        """Restore a previously moved directory to a chosen location."""
        # Ask user for the moved directory location
        moved_location = await self.destination_picker.get_directory_path(
            dialog_title="Select the directory to restore (the moved location)"
        )
        
        if not moved_location:
            return
        
        # Check for metadata to show original location
        metadata_file = os.path.join(moved_location, ".freespace_move_metadata.json")
        original_location = "unknown location"
        
        try:
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    original_location = metadata.get("original_location", "unknown location")
        except Exception:
            pass
        
        # Ask where to restore the directory
        restore_destination = await self.destination_picker.get_directory_path(
            dialog_title="Select destination where to restore the directory"
        )
        
        if not restore_destination:
            return
        
        # Confirmation
        confirmed = await self.ask_yes_no(
            "⚠️ Restore Moved Directory",
            f"This will restore the directory from:\n"
            f"  {moved_location}\n\n"
            f"To the destination:\n"
            f"  {restore_destination}\n\n"
            f"(Original location was: {original_location})\n\n"
            "The symlink at the original location will be removed and replaced with the actual directory.\n\n"
            "Are you sure?"
        )
        
        if confirmed:
            # Get sudo password from the text field
            sudo_password = self.sudo_password_field.value if self.sudo_password_field.value else None
            print(f"DEBUG: Got sudo_password from field: {bool(sudo_password)}")
            
            # Reset kill switch for new operation
            self.stop_operation.clear()
            self.operation_in_progress = True
            self.kill_button.visible = True
            self.page.update()
            
            # Run the restore operation in a background thread
            def run_restore():
                try:
                    self._perform_restore_move(moved_location, restore_destination, sudo_password=sudo_password)
                except Exception as ex:
                    print(f"Exception during restore move: {ex}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self.operation_in_progress = False
                    self.kill_button.visible = False
                    self.page.update()
            
            thread = threading.Thread(target=run_restore, daemon=True)
            thread.start()
    
    def _perform_restore_move(self, moved_location: str, restore_destination: str, sudo_password: str = None):
        """Perform the restore move operation, with optional sudo support."""
        self.update_status("Restoring moved directory...", show_progress=True)
        self.log_message("Starting restore move operation...", level="INFO")
        self.log_message(f"Moved location: {moved_location}", level="INFO")
        self.log_message(f"Restore destination: {restore_destination}", level="INFO")
        self.restore_move_button.disabled = True
        self.page.update()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"restore_move_log_{timestamp}.json"
        
        try:
            # Check if operation was killed
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled by user", level="STOP")
                self.update_status("Restore cancelled", show_progress=False)
                return
            
            self.log_message("Reading move metadata...", level="INFO")
            from freespace_api import FreeSpaceAPI
            api = FreeSpaceAPI(log_directory=str(self.log_directory))
            
            # Check if operation was killed
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled by user", level="STOP")
                self.update_status("Restore cancelled", show_progress=False)
                return
            
            self.log_message("Starting restore operation...", level="INFO")
            result = api.restore_moved_directory(moved_location, restore_destination, sudo_password=sudo_password)
            
            # Check if operation was killed during restore
            if self.stop_operation.is_set():
                self.log_message("Operation cancelled during restore", level="STOP")
                self.update_status("Restore cancelled", show_progress=False)
                return
            
            bytes_restored = result.get("bytes_restored", 0)
            
            # Format bytes restored
            if bytes_restored >= 1024**3:  # GB
                space_restored = f"{bytes_restored / (1024**3):.2f} GB"
            elif bytes_restored >= 1024**2:  # MB
                space_restored = f"{bytes_restored / (1024**2):.2f} MB"
            elif bytes_restored >= 1024:  # KB
                space_restored = f"{bytes_restored / 1024:.2f} KB"
            else:
                space_restored = f"{bytes_restored} bytes"
            
            self.log_message(f"Removing symlink from original location...", level="INFO")
            self.log_message(f"Restore operation completed successfully", level="SUCCESS")
            self.log_message(f"✓ Directory restored to {restore_destination}", level="SUCCESS")
            
            status_msg = f"Restore completed! Directory restored to: {restore_destination}. Space used: {space_restored}."
            
            self.update_status(status_msg, show_progress=False)
            
        except PermissionError as perm_ex:
            # Permission denied - show error
            self.log_message(f"Permission denied: {str(perm_ex)}", level="ERROR")
            self.show_error(f"Permission denied: {str(perm_ex)}\n\nYou may need to run the app with elevated privileges or try again.")
            
        except Exception as ex:
            self.log_message(f"Restore operation failed: {str(ex)}", level="ERROR")
            self.show_error(f"Error during restore operation: {str(ex)}")
            self.update_status("Restore operation failed.", show_progress=False)
            self.log_message(f"✗ Restore operation failed: {ex}")
        finally:
            print("DEBUG: Restore operation finally block - re-enabling button and updating page")
            sys.stdout.flush()
            self.restore_move_button.disabled = False
            self.page.update()
            print("DEBUG: Restore page updated in finally block")
            sys.stdout.flush()
    
    def show_error(self, message: str):
        """Show an error dialog."""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error", color=ft.Colors.RED_700),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
    
    def show_info(self, message: str):
        """Show an info dialog."""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Information", color=ft.Colors.BLUE_700),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
    
    async def ask_yes_no(self, title: str, message: str) -> bool:
        """Show a yes/no dialog and return the result."""
        result = [False]  # Use list to allow modification in nested function
        
        def on_yes(e):
            result[0] = True
            dlg.open = False
            self.page.update()
        
        def on_no(e):
            result[0] = False
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Yes", on_click=on_yes),
                ft.TextButton("No", on_click=on_no),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
        
        # Wait for dialog to close
        while dlg.open:
            await asyncio.sleep(0.1)
        
        return result[0]
    
    async def prompt_for_password(self, title: str = "Enter Password", message: str = "Enter your sudo password:") -> str:
        """Show a password prompt dialog and return the password."""
        result = [""]  # Use list to allow modification
        
        password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        def on_ok(e):
            result[0] = password_field.value
            dlg.open = False
            self.page.update()
        
        def on_cancel(e):
            result[0] = ""
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Column([
                ft.Text(message),
                password_field
            ], spacing=10),
            actions=[
                ft.TextButton("OK", on_click=on_ok),
                ft.TextButton("Cancel", on_click=on_cancel),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        password_field.focus()
        self.page.update()
        
        # Wait for dialog to close
        while dlg.open:
            await asyncio.sleep(0.1)
        
        return result[0]
        
        return result[0]
    
    def copy_status_to_clipboard(self, e):
        """Copy the current status text to clipboard."""
        try:
            self.page.set_clipboard(self.status_text.value)
            # Show a brief confirmation
            original_value = self.status_text.value
            self.status_text.value = "✓ Status copied to clipboard!"
            self.page.update()
            
            # Reset after a brief delay
            import time
            def reset_status():
                time.sleep(1)
                self.status_text.value = original_value
                self.page.update()
            
            thread = threading.Thread(target=reset_status, daemon=True)
            thread.start()
        except Exception as ex:
            print(f"Clipboard error: {ex}")


def main(page: ft.Page):
    """Main entry point for the Flet application."""
    FreeSpaceApp(page)


if __name__ == "__main__":
    ft.run(main)
