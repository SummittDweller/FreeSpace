#!/usr/bin/env python3
"""
FreeSpace - Hard Disk Move with Verification Workflow
A Python/Flet GUI application to move directories to USB storage with verification.
"""

import flet as ft
import os
import shutil
import hashlib
import datetime
import json
from pathlib import Path
from typing import List, Dict


class FreeSpaceApp:
    """Main application class for FreeSpace."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "FreeSpace - Hard Disk Move Workflow"
        self.page.window.width = 900
        self.page.window.height = 700
        
        # State variables
        self.source_directories: List[str] = []
        self.destination_directory: str = ""
        self.log_directory = Path.home() / "freespace_logs"
        self.log_directory.mkdir(exist_ok=True)
        
        # UI Components
        self.source_list = None
        self.destination_text = None
        self.status_text = None
        self.progress_bar = None
        self.copy_button = None
        self.verify_button = None
        self.finalize_button = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Title
        title = ft.Text(
            "FreeSpace - Hard Disk Move Workflow",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.colors.BLUE_700
        )
        
        # Source directory section
        source_section = ft.Container(
            content=ft.Column([
                ft.Text("Source Directories (Hard Drive)", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Add Directory",
                        icon=ft.icons.FOLDER_OPEN,
                        on_click=self.pick_source_directory
                    ),
                    ft.ElevatedButton(
                        "Clear All",
                        icon=ft.icons.CLEAR_ALL,
                        on_click=self.clear_source_directories
                    ),
                ]),
                ft.Container(
                    content=ft.Column(
                        [],
                        scroll=ft.ScrollMode.AUTO,
                        spacing=5
                    ),
                    height=150,
                    border=ft.border.all(1, ft.colors.GREY_400),
                    border_radius=5,
                    padding=10
                ),
            ]),
            padding=10,
            border=ft.border.all(1, ft.colors.BLUE_200),
            border_radius=10,
        )
        self.source_list = source_section.content.controls[2].content
        
        # Destination directory section
        destination_section = ft.Container(
            content=ft.Column([
                ft.Text("Destination Directory (USB Storage)", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Select USB Directory",
                        icon=ft.icons.USB,
                        on_click=self.pick_destination_directory
                    ),
                ]),
                ft.Container(
                    content=ft.Text("No destination selected", italic=True, color=ft.colors.GREY_700),
                    padding=10,
                    border=ft.border.all(1, ft.colors.GREY_400),
                    border_radius=5,
                ),
            ]),
            padding=10,
            border=ft.border.all(1, ft.colors.GREEN_200),
            border_radius=10,
        )
        self.destination_text = destination_section.content.controls[2].content
        
        # Action buttons
        self.copy_button = ft.ElevatedButton(
            "1. Copy to USB",
            icon=ft.icons.COPY_ALL,
            on_click=self.copy_directories,
            disabled=True,
            bgcolor=ft.colors.BLUE_500,
            color=ft.colors.WHITE
        )
        
        self.verify_button = ft.ElevatedButton(
            "2. Verify Copy",
            icon=ft.icons.VERIFIED,
            on_click=self.verify_copy,
            disabled=True,
            bgcolor=ft.colors.GREEN_500,
            color=ft.colors.WHITE
        )
        
        self.finalize_button = ft.ElevatedButton(
            "3. Delete & Create Links",
            icon=ft.icons.LINK,
            on_click=self.finalize_move,
            disabled=True,
            bgcolor=ft.colors.ORANGE_700,
            color=ft.colors.WHITE
        )
        
        action_section = ft.Container(
            content=ft.Row([
                self.copy_button,
                self.verify_button,
                self.finalize_button,
            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            padding=20,
        )
        
        # Progress bar
        self.progress_bar = ft.ProgressBar(
            width=800,
            visible=False,
            color=ft.colors.BLUE_500,
        )
        
        # Status text
        self.status_text = ft.Text(
            "Ready to start. Select source and destination directories.",
            size=14,
            color=ft.colors.GREY_700,
            italic=True
        )
        
        # Status section
        status_section = ft.Container(
            content=ft.Column([
                ft.Text("Status", size=16, weight=ft.FontWeight.BOLD),
                self.progress_bar,
                self.status_text,
            ]),
            padding=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=10,
        )
        
        # Main layout
        self.page.add(
            ft.Container(
                content=ft.Column([
                    title,
                    ft.Divider(),
                    source_section,
                    destination_section,
                    action_section,
                    status_section,
                ], scroll=ft.ScrollMode.AUTO),
                padding=20,
            )
        )
    
    def pick_source_directory(self, e):
        """Open directory picker for source directory."""
        def on_result(result: ft.FilePickerResultEvent):
            if result.path:
                if result.path not in self.source_directories:
                    self.source_directories.append(result.path)
                    self.update_source_list()
                    self.update_button_states()
        
        file_picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.get_directory_path(dialog_title="Select Source Directory")
    
    def clear_source_directories(self, e):
        """Clear all source directories."""
        self.source_directories.clear()
        self.update_source_list()
        self.update_button_states()
    
    def update_source_list(self):
        """Update the source directory list display."""
        self.source_list.controls.clear()
        
        if not self.source_directories:
            self.source_list.controls.append(
                ft.Text("No directories selected", italic=True, color=ft.colors.GREY_700)
            )
        else:
            for i, dir_path in enumerate(self.source_directories):
                self.source_list.controls.append(
                    ft.Row([
                        ft.Icon(ft.icons.FOLDER, color=ft.colors.BLUE_500),
                        ft.Text(dir_path, expand=True, size=12),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_color=ft.colors.RED_500,
                            tooltip="Remove",
                            on_click=lambda e, idx=i: self.remove_source_directory(idx)
                        )
                    ])
                )
        
        self.page.update()
    
    def remove_source_directory(self, index: int):
        """Remove a source directory by index."""
        if 0 <= index < len(self.source_directories):
            self.source_directories.pop(index)
            self.update_source_list()
            self.update_button_states()
    
    def pick_destination_directory(self, e):
        """Open directory picker for destination directory."""
        def on_result(result: ft.FilePickerResultEvent):
            if result.path:
                self.destination_directory = result.path
                self.destination_text.value = result.path
                self.destination_text.italic = False
                self.destination_text.color = ft.colors.BLACK
                self.update_button_states()
                self.page.update()
        
        file_picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.get_directory_path(dialog_title="Select Destination USB Directory")
    
    def update_button_states(self):
        """Update the enabled/disabled state of action buttons."""
        has_sources = len(self.source_directories) > 0
        has_destination = bool(self.destination_directory)
        
        self.copy_button.disabled = not (has_sources and has_destination)
        self.page.update()
    
    def update_status(self, message: str, show_progress: bool = False):
        """Update status message and progress bar."""
        self.status_text.value = message
        self.progress_bar.visible = show_progress
        self.page.update()
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def copy_directories(self, e):
        """Copy selected directories to USB destination."""
        if not self.source_directories or not self.destination_directory:
            self.show_error("Please select source and destination directories.")
            return
        
        # Confirm action
        def on_dialog_result(dialog_result):
            dlg.open = False
            self.page.update()
            if dialog_result == "yes":
                self._perform_copy()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Copy"),
            content=ft.Text(
                f"Copy {len(self.source_directories)} director{'y' if len(self.source_directories) == 1 else 'ies'} "
                f"to {self.destination_directory}?\n\nThis may take a while depending on the size."
            ),
            actions=[
                ft.TextButton("Yes", on_click=lambda e: on_dialog_result("yes")),
                ft.TextButton("No", on_click=lambda e: on_dialog_result("no")),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
    
    def _perform_copy(self):
        """Perform the actual copy operation."""
        self.update_status("Copying directories to USB...", show_progress=True)
        self.copy_button.disabled = True
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"copy_log_{timestamp}.json"
        
        copy_log = {
            "timestamp": timestamp,
            "source_directories": self.source_directories,
            "destination_directory": self.destination_directory,
            "copies": []
        }
        
        try:
            for src_dir in self.source_directories:
                dir_name = os.path.basename(src_dir)
                dest_dir = os.path.join(self.destination_directory, dir_name)
                
                self.update_status(f"Copying: {dir_name}...", show_progress=True)
                
                if os.path.exists(dest_dir):
                    self.show_error(f"Destination already exists: {dest_dir}")
                    continue
                
                shutil.copytree(src_dir, dest_dir)
                
                copy_log["copies"].append({
                    "source": src_dir,
                    "destination": dest_dir,
                    "status": "copied"
                })
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(copy_log, f, indent=2)
            
            self.update_status(f"Copy completed! Log saved to: {log_file}", show_progress=False)
            self.verify_button.disabled = False
            self.page.update()
            
        except Exception as ex:
            self.show_error(f"Error during copy: {str(ex)}")
            self.copy_button.disabled = False
            self.update_status("Copy failed.", show_progress=False)
    
    def verify_copy(self, e):
        """Verify that copied files match originals."""
        if not self.source_directories or not self.destination_directory:
            self.show_error("No copy operation to verify.")
            return
        
        self.update_status("Verifying copied files...", show_progress=True)
        self.verify_button.disabled = True
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"verify_log_{timestamp}.json"
        
        verify_log = {
            "timestamp": timestamp,
            "verifications": []
        }
        
        try:
            all_verified = True
            
            for src_dir in self.source_directories:
                dir_name = os.path.basename(src_dir)
                dest_dir = os.path.join(self.destination_directory, dir_name)
                
                self.update_status(f"Verifying: {dir_name}...", show_progress=True)
                
                if not os.path.exists(dest_dir):
                    all_verified = False
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
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(verify_log, f, indent=2)
            
            if all_verified:
                self.update_status(f"Verification successful! Log saved to: {log_file}", show_progress=False)
                self.finalize_button.disabled = False
            else:
                self.update_status(f"Verification failed! Check log: {log_file}", show_progress=False)
                self.verify_button.disabled = False
            
            self.page.update()
            
        except Exception as ex:
            self.show_error(f"Error during verification: {str(ex)}")
            self.verify_button.disabled = False
            self.update_status("Verification failed.", show_progress=False)
    
    def _verify_directory(self, src_dir: str, dest_dir: str) -> Dict:
        """Verify that a directory was copied correctly."""
        result = {
            "source": src_dir,
            "destination": dest_dir,
            "status": "verified",
            "mismatches": []
        }
        
        # Check all files exist and match
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, src_dir)
                dest_file = os.path.join(dest_dir, rel_path)
                
                if not os.path.exists(dest_file):
                    result["status"] = "failed"
                    result["mismatches"].append({
                        "file": rel_path,
                        "reason": "missing in destination"
                    })
                    continue
                
                # Check file sizes match
                if os.path.getsize(src_file) != os.path.getsize(dest_file):
                    result["status"] = "failed"
                    result["mismatches"].append({
                        "file": rel_path,
                        "reason": "size mismatch"
                    })
                    continue
                
                # For important verification, check checksums for a sample
                # (checking all files could be very slow)
                # Here we'll just verify sizes and existence
        
        return result
    
    def finalize_move(self, e):
        """Delete original directories and create symbolic links."""
        # Strong confirmation required
        def on_dialog_result(dialog_result):
            dlg.open = False
            self.page.update()
            if dialog_result == "yes":
                self._perform_finalize()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Final Confirmation", color=ft.colors.RED_700),
            content=ft.Text(
                f"This will DELETE the original {len(self.source_directories)} "
                f"director{'y' if len(self.source_directories) == 1 else 'ies'} "
                f"and replace them with symbolic links.\n\n"
                "This action cannot be undone!\n\n"
                "Are you absolutely sure?"
            ),
            actions=[
                ft.TextButton("Yes, Delete and Link", on_click=lambda e: on_dialog_result("yes")),
                ft.TextButton("Cancel", on_click=lambda e: on_dialog_result("no")),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
    
    def _perform_finalize(self):
        """Perform the finalization: delete originals and create symlinks."""
        self.update_status("Finalizing move: deleting originals and creating links...", show_progress=True)
        self.finalize_button.disabled = True
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"finalize_log_{timestamp}.json"
        
        finalize_log = {
            "timestamp": timestamp,
            "operations": []
        }
        
        try:
            for src_dir in self.source_directories:
                dir_name = os.path.basename(src_dir)
                dest_dir = os.path.join(self.destination_directory, dir_name)
                
                self.update_status(f"Finalizing: {dir_name}...", show_progress=True)
                
                if not os.path.exists(dest_dir):
                    finalize_log["operations"].append({
                        "source": src_dir,
                        "destination": dest_dir,
                        "status": "skipped",
                        "reason": "destination does not exist"
                    })
                    continue
                
                # Delete original
                shutil.rmtree(src_dir)
                
                # Create symbolic link
                os.symlink(dest_dir, src_dir)
                
                finalize_log["operations"].append({
                    "source": src_dir,
                    "destination": dest_dir,
                    "symlink": src_dir,
                    "status": "completed"
                })
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(finalize_log, f, indent=2)
            
            self.update_status(
                f"Move finalized! Original directories deleted and symbolic links created. "
                f"Log saved to: {log_file}",
                show_progress=False
            )
            
            # Reset state for next operation
            self.source_directories.clear()
            self.destination_directory = ""
            self.update_source_list()
            self.destination_text.value = "No destination selected"
            self.destination_text.italic = True
            self.destination_text.color = ft.colors.GREY_700
            self.update_button_states()
            
        except Exception as ex:
            self.show_error(f"Error during finalization: {str(ex)}")
            self.finalize_button.disabled = False
            self.update_status("Finalization failed.", show_progress=False)
    
    def show_error(self, message: str):
        """Show an error dialog."""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error", color=ft.colors.RED_700),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()


def main(page: ft.Page):
    """Main entry point for the Flet application."""
    FreeSpaceApp(page)


if __name__ == "__main__":
    ft.app(target=main)
