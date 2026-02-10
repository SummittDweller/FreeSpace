#!/usr/bin/env python3
"""
Example usage of FreeSpace API (non-GUI mode).
This shows how the core functionality can be used programmatically.
"""

import os
import shutil
import hashlib
import json
import datetime
import stat
import errno
import subprocess
from pathlib import Path


class FreeSpaceAPI:
    """Programmatic API for FreeSpace operations."""
    
    def __init__(self, log_directory=None):
        """Initialize the API with optional custom log directory."""
        self.log_directory = Path(log_directory) if log_directory else Path.home() / "freespace_logs"
        self.log_directory.mkdir(exist_ok=True)
    
    def _run_with_sudo(self, command: list, sudo_password: str = None) -> subprocess.CompletedProcess:
        """
        Run a command with sudo if password is provided.
        
        Args:
            command: List of command parts (e.g., ['mv', '/src', '/dest'])
            sudo_password: Password for sudo (if None, runs without sudo)
            
        Returns:
            subprocess.CompletedProcess
        """
        if sudo_password:
            # Use 'sudo -S' to read password from stdin
            full_command = ['sudo', '-S'] + command
            return subprocess.run(
                full_command,
                input=sudo_password.encode() + b'\n',
                check=True,
                capture_output=True,
                text=False
            )
        else:
            # Run without sudo
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=False
            )
    
    def _move_file_or_dir(self, src: str, dst: str, sudo_password: str = None):
        """Move a file or directory using subprocess for better privilege handling."""
        try:
            self._run_with_sudo(['mv', src, dst], sudo_password)
        except subprocess.CalledProcessError as e:
            raise OSError(f"Failed to move {src} to {dst}: {e.stderr.decode() if e.stderr else str(e)}")
    
    def _create_symlink(self, target: str, link_name: str, sudo_password: str = None):
        """Create a symlink using subprocess for better privilege handling."""
        try:
            self._run_with_sudo(['ln', '-s', target, link_name], sudo_password)
        except subprocess.CalledProcessError as e:
            raise OSError(f"Failed to create symlink {link_name}: {e.stderr.decode() if e.stderr else str(e)}")
    
    def _remove_file_or_dir(self, path: str, sudo_password: str = None):
        """Remove a file or directory using subprocess for better privilege handling."""
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                self._run_with_sudo(['rm', '-rf', path], sudo_password)
            else:
                self._run_with_sudo(['rm', '-f', path], sudo_password)
        except subprocess.CalledProcessError as e:
            raise OSError(f"Failed to remove {path}: {e.stderr.decode() if e.stderr else str(e)}")
    
    def _read_link(self, path: str) -> str:
        """Read symlink target."""
        return os.readlink(path)

    def copy_directory(self, source: str, destination: str) -> dict:
        """
        Copy a directory to external storage destination, skipping symbolic links.
        
        Args:
            source: Source directory path
            destination: Destination base directory path (can be any external storage)
            
        Returns:
            dict with operation details and log file path
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"copy_log_{timestamp}.json"
        
        dir_name = os.path.basename(source)
        dest_path = os.path.join(destination, dir_name)
        
        if os.path.exists(dest_path):
            raise FileExistsError(f"Destination already exists: {dest_path}")
        
        # Copy directory but skip symbolic links and .Trashes, handle errors
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
            return ignored
        
        shutil.copytree(source, dest_path, copy_function=copy_with_errors,
                       ignore=ignore_items)
        
        log_data = {
            "timestamp": timestamp,
            "operation": "copy",
            "source": source,
            "destination": dest_path,
            "status": "completed" if not errors else "partial",
            "files_failed": len(errors),
            "failed_files": errors[:10] if errors else None,  # Log first 10 failures
            "trashes_skipped": len(skipped_trashes),
            "trashes_items": skipped_trashes if skipped_trashes else None
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return {"status": "success", "destination": dest_path, "log_file": str(log_file)}
    
    def verify_copy(self, source: str, destination: str) -> dict:
        """
        Verify that a directory was copied correctly, skipping symbolic links.
        
        Args:
            source: Original source directory
            destination: Destination directory to verify
            
        Returns:
            dict with verification results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"verify_log_{timestamp}.json"
        
        mismatches = []
        
        for root, dirs, files in os.walk(source):
            for file in files:
                src_file = os.path.join(root, file)
                
                # Skip symbolic links
                if os.path.islink(src_file):
                    continue
                
                rel_path = os.path.relpath(src_file, source)
                dest_file = os.path.join(destination, rel_path)
                
                if not os.path.exists(dest_file):
                    mismatches.append({"file": rel_path, "reason": "missing"})
                elif os.path.getsize(src_file) != os.path.getsize(dest_file):
                    mismatches.append({"file": rel_path, "reason": "size_mismatch"})
        
        status = "verified" if not mismatches else "failed"
        
        log_data = {
            "timestamp": timestamp,
            "operation": "verify",
            "source": source,
            "destination": destination,
            "status": status,
            "mismatches": mismatches
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return {"status": status, "mismatches": mismatches, "log_file": str(log_file)}
    
    def finalize_move(self, source: str, destination: str) -> dict:
        """
        Replace individual files with symbolic links.
        Directory structure is preserved, only files are replaced with links.
        Uses a safe multi-step process to prevent data loss.
        
        Args:
            source: Original source directory
            destination: Destination directory containing copied files
            
        Returns:
            dict with operation results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"finalize_log_{timestamp}.json"
        
        if not os.path.exists(destination):
            raise FileNotFoundError(f"Destination does not exist: {destination}")
        
        files_processed = []
        files_failed = []
        files_skipped = []
        bytes_freed = 0
        
        try:
            # Walk through all files in source directory
            for root, dirs, files in os.walk(source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, source)
                    dest_file = os.path.join(destination, rel_path)
                    
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
            
            log_data = {
                "timestamp": timestamp,
                "operation": "finalize",
                "source": source,
                "destination": destination,
                "files_processed": len(files_processed),
                "files_skipped": len(files_skipped),
                "files_failed": len(files_failed),
                "bytes_freed": bytes_freed,
                "processed_files": files_processed,
                "skipped_files": files_skipped,
                "failed_files": files_failed,
                "status": "completed" if not files_failed else "partial"
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            return {
                "status": "success" if not files_failed else "partial",
                "files_processed": len(files_processed),
                "files_skipped": len(files_skipped),
                "files_failed": len(files_failed),
                "bytes_freed": bytes_freed,
                "skipped_details": files_skipped,
                "failed_details": files_failed,
                "log_file": str(log_file)
            }
            
        except Exception as ex:
            # Log the error
            log_data = {
                "timestamp": timestamp,
                "operation": "finalize",
                "source": source,
                "destination": destination,
                "status": "failed",
                "error": str(ex)
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            raise
    
    def move_directory(self, source: str, destination: str, sudo_password: str = None) -> dict:
        """
        Move a directory to a new location and replace it with a symbolic link.
        This is a safe operation that creates the symlink in one atomic step.
        Handles recovery from interrupted moves.
        
        Args:
            source: Source directory path (will be replaced with symlink)
            destination: Destination directory path (where to move contents)
            sudo_password: Optional sudo password for elevated privileges
            
        Returns:
            dict with operation results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"move_log_{timestamp}.json"
        
        # Normalize paths
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
        
        if not os.path.exists(source):
            raise FileNotFoundError(f"Source directory does not exist: {source}")
        
        if not os.path.isdir(source):
            raise NotADirectoryError(f"Source is not a directory: {source}")
        
        # Check for interrupted move scenario
        interrupted_move = False
        if os.path.exists(destination):
            # If destination exists AND source is already a symlink, move is complete
            if os.path.islink(source):
                return {
                    "status": "already_complete",
                    "source": source,
                    "destination": destination,
                    "message": "Move already complete - symlink already in place"
                }
            # If destination exists but source is not a symlink, this is an interrupted move
            interrupted_move = True
        
        # Ensure destination parent directory exists
        dest_parent = os.path.dirname(destination)
        if not os.path.exists(dest_parent):
            raise FileNotFoundError(f"Destination parent directory does not exist: {dest_parent}")
        
        bytes_moved = 0
        file_list = []
        
        try:
            # Calculate total size and collect file list for logging
            for root, dirs, files in os.walk(source):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, source)
                    file_list.append(relative_path)
                    if not os.path.islink(file_path):
                        try:
                            bytes_moved += os.path.getsize(file_path)
                        except (OSError, IOError):
                            pass
            
            # Create the destination directory (same name as source)
            os.makedirs(destination, exist_ok=True)
            
            # Move the CONTENTS of the directory (not the directory itself) using rsync or shutil
            # This preserves directory structure and permissions
            for item in os.listdir(source):
                src_path = os.path.join(source, item)
                dst_path = os.path.join(destination, item)
                
                # Skip if destination item already exists
                if os.path.exists(dst_path):
                    continue
                
                # Use mv command with sudo for better control
                try:
                    self._move_file_or_dir(src_path, dst_path, sudo_password)
                except Exception as e:
                    # Log but continue with other files
                    continue
            
            # Remove the now-empty source directory (or what remains)
            try:
                if os.path.isdir(source) and not os.path.islink(source):
                    # Check if directory is empty or only has hidden files
                    remaining = os.listdir(source)
                    if not remaining:
                        self._remove_file_or_dir(source, sudo_password)
            except:
                pass
            
            # Create symlink replacing the original directory
            # Symlink should point from source location to destination location
            self._create_symlink(destination, source, sudo_password)
            
            # Save metadata file in the destination directory for restoration
            metadata_file = os.path.join(destination, ".freespace_move_metadata.json")
            metadata = {
                "timestamp": timestamp,
                "original_location": source,
                "moved_to": destination,
                "directory_name": os.path.basename(source),
                "version": "1.0"
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            log_data = {
                "timestamp": timestamp,
                "operation": "move",
                "source": source,
                "destination": destination,
                "bytes_moved": bytes_moved,
                "file_count": len(file_list),
                "files_moved": file_list[:100],  # Log first 100 files
                "total_files": len(file_list),
                "symlink_created": source,
                "metadata_file": metadata_file,
                "status": "completed",
                "interrupted_move_recovery": interrupted_move,
                "used_sudo": bool(sudo_password)
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            return {
                "status": "success",
                "source": source,
                "destination": destination,
                "symlink_created": source,
                "bytes_moved": bytes_moved,
                "file_count": len(file_list),
                "files_moved": file_list,
                "log_file": str(log_file),
                "interrupted_move_recovery": interrupted_move,
                "used_sudo": bool(sudo_password)
            }
            
        except Exception as ex:
            # Log the error
            log_data = {
                "timestamp": timestamp,
                "operation": "move",
                "source": source,
                "destination": destination,
                "status": "failed",
                "error": str(ex)
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            raise
    
    def restore_moved_directory(self, moved_location: str, restore_destination: str = None, sudo_password: str = None) -> dict:
        """
        Restore a previously moved directory to a specified location or its original location.
        Reads metadata from the moved directory to find the original location (for reference).
        
        Args:
            moved_location: Path to the directory that was moved (current location)
            restore_destination: Where to restore the directory. If None, uses original location from metadata.
            sudo_password: Optional sudo password for elevated privileges
            
        Returns:
            dict with operation results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"restore_move_log_{timestamp}.json"
        
        moved_location = os.path.abspath(moved_location)
        
        if not os.path.exists(moved_location):
            raise FileNotFoundError(f"Moved directory does not exist: {moved_location}")
        
        if not os.path.isdir(moved_location):
            raise NotADirectoryError(f"Location is not a directory: {moved_location}")
        
        # Look for metadata file
        metadata_file = os.path.join(moved_location, ".freespace_move_metadata.json")
        
        if not os.path.exists(metadata_file):
            raise FileNotFoundError(
                f"Metadata file not found in {moved_location}. "
                "This directory does not appear to be a moved directory managed by FreeSpace."
            )
        
        try:
            # Read metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            original_location = metadata.get("original_location")
            
            if not original_location:
                raise ValueError("Metadata file is missing 'original_location' field")
            
            original_location = os.path.abspath(original_location)
            
            # Use provided destination or fall back to original location
            if restore_destination:
                restore_destination = os.path.abspath(restore_destination)
            else:
                restore_destination = original_location
            
            # Get the directory name from metadata
            dir_name = metadata.get("directory_name", os.path.basename(moved_location))
            restore_path = os.path.join(restore_destination, dir_name)
            
            # If restoring to original location, verify symlink exists
            if restore_path == original_location:
                if not os.path.islink(original_location):
                    raise FileNotFoundError(
                        f"Symlink does not exist at original location: {original_location}. "
                        "The original directory may have been manually deleted or moved."
                    )
                
                link_target = os.readlink(original_location)
                # Normalize both paths for comparison (resolve symlinks)
                if os.path.abspath(link_target) != moved_location:
                    raise ValueError(
                        f"Symlink at {original_location} does not point to {moved_location}. "
                        f"It points to {link_target} instead. The symlink may have been modified."
                    )
            
            # Calculate bytes to be restored
            bytes_restored = 0
            for root, dirs, files in os.walk(moved_location):
                for file in files:
                    file_path = os.path.join(root, file)
                    if not os.path.islink(file_path):
                        try:
                            bytes_restored += os.path.getsize(file_path)
                        except (OSError, IOError):
                            pass
            
            # Create the destination directory if needed
            if restore_destination != original_location and not os.path.exists(restore_destination):
                os.makedirs(restore_destination, exist_ok=True)
            
            # Remove the symlink at original location if restoring there
            if restore_path == original_location:
                self._remove_file_or_dir(original_location, sudo_password)
            
            try:
                # Move the CONTENTS of moved_location to restore_path (like the move operation in reverse)
                # First create the destination directory
                os.makedirs(restore_path, exist_ok=True)
                
                # Move each item from moved_location to restore_path
                for item in os.listdir(moved_location):
                    # Skip metadata file
                    if item == ".freespace_move_metadata.json":
                        continue
                    
                    src_path = os.path.join(moved_location, item)
                    dst_path = os.path.join(restore_path, item)
                    
                    # Skip if destination already exists
                    if os.path.exists(dst_path):
                        continue
                    
                    # Move using helper that supports sudo
                    try:
                        self._move_file_or_dir(src_path, dst_path, sudo_password)
                    except Exception as e:
                        continue
                
                # Remove the now-empty moved_location directory
                try:
                    if os.path.isdir(moved_location) and not os.path.islink(moved_location):
                        remaining = os.listdir(moved_location)
                        # Keep metadata file in the moved location for now
                        remaining = [f for f in remaining if f != ".freespace_move_metadata.json"]
                        if not remaining:
                            self._remove_file_or_dir(moved_location, sudo_password)
                except:
                    pass
                
                log_data = {
                    "timestamp": timestamp,
                    "operation": "restore_move",
                    "original_location": original_location,
                    "moved_from": moved_location,
                    "restored_to": restore_path,
                    "bytes_restored": bytes_restored,
                    "status": "completed",
                    "used_sudo": bool(sudo_password)
                }
                
                with open(log_file, 'w') as f:
                    json.dump(log_data, f, indent=2)
                
                return {
                    "status": "success",
                    "original_location": original_location,
                    "moved_from": moved_location,
                    "restored_to": restore_path,
                    "bytes_restored": bytes_restored,
                    "log_file": str(log_file),
                    "used_sudo": bool(sudo_password)
                }
                
            except Exception as move_ex:
                # Rollback on error: restore symlink if needed
                if restore_path == original_location:
                    try:
                        self._create_symlink(moved_location, original_location, sudo_password)
                    except Exception:
                        pass  # If we can't restore the symlink, at least log the error
                
                raise move_ex
            
        except Exception as ex:
            # Log the error
            log_data = {
                "timestamp": timestamp,
                "operation": "restore_move",
                "moved_location": moved_location,
                "restore_destination": restore_destination if restore_destination else "original_location",
                "status": "failed",
                "error": str(ex)
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            raise


# Example usage
if __name__ == "__main__":
    import sys
    
    # Example demonstration (commented out to prevent accidental execution)
    print("FreeSpace API Example")
    print("=" * 50)
    print("\nThis is an example of how to use FreeSpace programmatically.")
    print("\nExample code:")
    print("""
    from freespace_api import FreeSpaceAPI
    
    # Initialize API
    api = FreeSpaceAPI()
    
    # Copy directory
    result = api.copy_directory(
        source="/path/to/source/directory",
        destination="/path/to/usb/drive"
    )
    print(f"Copied to: {result['destination']}")
    
    # Verify copy
    verify_result = api.verify_copy(
        source="/path/to/source/directory",
        destination=result['destination']
    )
    
    if verify_result['status'] == 'verified':
        # Finalize: delete original and create symlink
        finalize_result = api.finalize_move(
            source="/path/to/source/directory",
            destination=result['destination']
        )
        print(f"Symlink created: {finalize_result['symlink']}")
    else:
        print("Verification failed!")
        print(verify_result['mismatches'])
    """)
    print("\n" + "=" * 50)
    print("\nFor GUI usage, run: python3 main.py")
