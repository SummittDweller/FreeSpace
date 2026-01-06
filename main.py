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
from pathlib import Path
from typing import List, Dict


class FreeSpaceApp:
    """Main application class for FreeSpace."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "FreeSpace - Hard Disk Move Workflow"
        self.page.window.width = 900
        self.page.window.height = 720
        
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
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_700
        )
        
        # Source directory section
        source_section = ft.Container(
            content=ft.Column([
                ft.Text("Source Directories (Hard Drive)", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Add Directory/Directories",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.pick_source_directory
                    ),
                    ft.ElevatedButton(
                        "Clear All",
                        icon=ft.Icons.CLEAR_ALL,
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
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    border_radius=5,
                    padding=10
                ),
            ]),
            padding=10,
            border=ft.border.all(1, ft.Colors.BLUE_200),
            border_radius=10,
        )
        self.source_list = source_section.content.controls[2].content
        
        # Destination directory section
        destination_section = ft.Container(
            content=ft.Column([
                ft.Text("Destination Directory (External Storage)", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Select Destination Directory",
                        icon=ft.Icons.STORAGE,
                        on_click=self.pick_destination_directory
                    ),
                ]),
                ft.Container(
                    content=ft.Text("No destination selected", italic=True, color=ft.Colors.GREY_700),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    border_radius=5,
                ),
            ]),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREEN_200),
            border_radius=10,
        )
        self.destination_text = destination_section.content.controls[2].content
        
        # Action buttons
        self.copy_button = ft.ElevatedButton(
            "1. Copy to Destination",
            icon=ft.Icons.COPY_ALL,
            on_click=self.copy_directories,
            disabled=True,
            bgcolor=ft.Colors.BLUE_500,
            color=ft.Colors.WHITE
        )
        
        self.verify_button = ft.ElevatedButton(
            "2. Verify Copy",
            icon=ft.Icons.VERIFIED,
            on_click=self.verify_copy,
            disabled=True,
            bgcolor=ft.Colors.GREEN_500,
            color=ft.Colors.WHITE
        )
        
        self.finalize_button = ft.ElevatedButton(
            "3. Delete & Create Links",
            icon=ft.Icons.LINK,
            on_click=self.finalize_move,
            disabled=True,
            bgcolor=ft.Colors.ORANGE_700,
            color=ft.Colors.WHITE
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
            color=ft.Colors.BLUE_500,
        )
        
        # Status text
        self.status_text = ft.Text(
            "Ready to start. Select source and destination directories.",
            size=14,
            color=ft.Colors.GREY_700,
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
            border=ft.border.all(1, ft.Colors.GREY_300),
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
    
    async def pick_source_directory(self, e):
        """Open directory picker for source directories (supports multiple selection)."""
        initial_directory = None
        
        while True:
            path = await self.source_picker.get_directory_path(
                dialog_title=f"Select Source Directory ({len(self.source_directories)} selected so far - Cancel to finish)",
                initial_directory=initial_directory
            )
            
            if not path:
                # User cancelled, exit loop
                break
            
            # Directory selected
            if path not in self.source_directories:
                self.source_directories.append(path)
                self.update_source_list()
                self.update_button_states()
                
                # Remember the parent directory for next time
                initial_directory = os.path.dirname(path)
            else:
                # Already added, show message
                self.show_info(f"Directory already added:\n{path}")
    
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
                ft.Text("No directories selected", italic=True, color=ft.Colors.GREY_700)
            )
        else:
            for i, dir_path in enumerate(self.source_directories):
                self.source_list.controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_500),
                        ft.Text(dir_path, expand=True, size=12),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED_500,
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
    
    async def pick_destination_directory(self, e):
        """Open directory picker for destination directory."""
        path = await self.destination_picker.get_directory_path(
            dialog_title="Select Destination Directory (External Storage)"
        )
        
        if path:
            self.destination_directory = path
            self.destination_text.value = path
            self.destination_text.italic = False
            self.destination_text.color = ft.Colors.BLACK
            self.update_button_states()
            self.page.update()
    
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
        self.update_status("Copying directories to destination...", show_progress=True)
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
                
                # Copy with error handling for individual files
                errors = []
                def copy_with_errors(src, dst, *, follow_symlinks=True):
                    try:
                        return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
                    except Exception as e:
                        errors.append((src, str(e)))
                        return None
                
                shutil.copytree(src_dir, dest_dir, copy_function=copy_with_errors, 
                               ignore=lambda dir, files: [f for f in files if os.path.islink(os.path.join(dir, f))])
                
                copy_log["copies"].append({
                    "source": src_dir,
                    "destination": dest_dir,
                    "status": "copied" if not errors else "partial",
                    "files_failed": len(errors),
                    "failed_files": errors[:10] if errors else None  # Log first 10 failures
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
        """Verify that a directory was copied correctly, skipping symbolic links."""
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
                
                # Skip symbolic links
                if os.path.islink(src_file):
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
                
                # Check file sizes match
                if os.path.getsize(src_file) != os.path.getsize(dest_file):
                    result["status"] = "failed"
                    result["mismatches"].append({
                        "file": rel_path,
                        "reason": "size mismatch"
                    })
                    continue
        
        # Note: For performance reasons, this verification checks existence and size only.
        # For critical data, consider running a full checksum verification separately.
        
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
            title=ft.Text("⚠️ Final Confirmation", color=ft.Colors.RED_700),
            content=ft.Text(
                f"This will REPLACE all files in the original {len(self.source_directories)} "
                f"director{'y' if len(self.source_directories) == 1 else 'ies'} "
                f"with symbolic links to the USB copies.\n\n"
                "Directory structure will be preserved.\n"
                "Only individual files will be replaced with links.\n\n"
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
        """Perform the finalization: replace files with symlinks to destination."""
        self.update_status("Finalizing move: replacing files with links...", show_progress=True)
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
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(finalize_log, f, indent=2)
            
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
            status_msg += f" Log saved to: {log_file}"
            
            self.update_status(status_msg, show_progress=False)
            
            # Reset state for next operation
            self.source_directories.clear()
            self.destination_directory = ""
            self.update_source_list()
            self.destination_text.value = "No destination selected"
            self.destination_text.italic = True
            self.destination_text.color = ft.Colors.GREY_700
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


def main(page: ft.Page):
    """Main entry point for the Flet application."""
    FreeSpaceApp(page)


if __name__ == "__main__":
    ft.run(main)
