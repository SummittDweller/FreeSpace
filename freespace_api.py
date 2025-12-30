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
from pathlib import Path


class FreeSpaceAPI:
    """Programmatic API for FreeSpace operations."""
    
    def __init__(self, log_directory=None):
        """Initialize the API with optional custom log directory."""
        self.log_directory = Path(log_directory) if log_directory else Path.home() / "freespace_logs"
        self.log_directory.mkdir(exist_ok=True)
    
    def copy_directory(self, source: str, destination: str) -> dict:
        """
        Copy a directory to a destination.
        
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
        
        shutil.copytree(source, dest_path)
        
        log_data = {
            "timestamp": timestamp,
            "operation": "copy",
            "source": source,
            "destination": dest_path,
            "status": "completed"
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return {"status": "success", "destination": dest_path, "log_file": str(log_file)}
    
    def verify_copy(self, source: str, destination: str) -> dict:
        """
        Verify that a directory was copied correctly.
        
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
        Delete source directory and create a symbolic link.
        Uses a safe multi-step process to prevent data loss.
        
        Args:
            source: Original source directory to delete
            destination: Destination directory to link to
            
        Returns:
            dict with operation results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_directory / f"finalize_log_{timestamp}.json"
        
        if not os.path.exists(destination):
            raise FileNotFoundError(f"Destination does not exist: {destination}")
        
        # Safety: Create symlink first, then delete original
        temp_link = source + ".tmp_link"
        backup_dir = source + ".backup_" + timestamp
        
        try:
            # Step 1: Create symlink with temporary name
            os.symlink(destination, temp_link)
            
            # Step 2: Rename original to backup
            os.rename(source, backup_dir)
            
            # Step 3: Move symlink to final location
            os.rename(temp_link, source)
            
            # Step 4: Delete backup only after symlink is in place
            shutil.rmtree(backup_dir)
            
            log_data = {
                "timestamp": timestamp,
                "operation": "finalize",
                "deleted": source,
                "symlink_target": destination,
                "symlink_path": source,
                "status": "completed"
            }
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            return {"status": "success", "symlink": source, "log_file": str(log_file)}
            
        except Exception as ex:
            # Rollback on error
            if os.path.exists(temp_link):
                os.remove(temp_link)
            if os.path.exists(backup_dir) and not os.path.exists(source):
                os.rename(backup_dir, source)
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
