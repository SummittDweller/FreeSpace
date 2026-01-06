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
from pathlib import Path


class FreeSpaceAPI:
    """Programmatic API for FreeSpace operations."""
    
    def __init__(self, log_directory=None):
        """Initialize the API with optional custom log directory."""
        self.log_directory = Path(log_directory) if log_directory else Path.home() / "freespace_logs"
        self.log_directory.mkdir(exist_ok=True)
    
    def copy_directory(self, source: str, destination: str) -> dict:
        """
        Copy a directory to a destination, skipping symbolic links.
        
        Args:
            source: Source directory path
            destination: Destination base directory path
            
        Returns:
            dict with operation details and log file path
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"copy_log_{timestamp}.json"
        
        dir_name = os.path.basename(source)
        dest_path = os.path.join(destination, dir_name)
        
        if os.path.exists(dest_path):
            raise FileExistsError(f"Destination already exists: {dest_path}")
        
        # Copy directory but skip symbolic links and handle errors
        errors = []
        def copy_with_errors(src, dst, *, follow_symlinks=True):
            try:
                return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
            except Exception as e:
                errors.append((src, str(e)))
                return None
        
        shutil.copytree(source, dest_path, copy_function=copy_with_errors,
                       ignore=lambda dir, files: [f for f in files if os.path.islink(os.path.join(dir, f))])
        
        log_data = {
            "timestamp": timestamp,
            "operation": "copy",
            "source": source,
            "destination": dest_path,
            "status": "completed" if not errors else "partial",
            "files_failed": len(errors),
            "failed_files": errors[:10] if errors else None  # Log first 10 failures
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
