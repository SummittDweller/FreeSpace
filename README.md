# FreeSpace

A Python/Flet GUI application to support hard disk space management workflows including "move with verification to external storage" and "direct directory relocation with symlink replacement" to free up hard drive space.

## Recent Changes (v1.2 - February 2026)

- **New Move Directory Workflow**: Direct move any directory to a new location with automatic symlink replacement
- **Restore Moved Directory**: Undo a move operation and restore a directory to its original location (safeguard feature)
- **Move Metadata Tracking**: Automatically saves metadata in moved directories to enable restoration
- **Instant Space Reclamation**: Move directories between drives or to new locations instantly
- **Atomic Operations**: Safe move operations with automatic rollback on failure
- **Comprehensive Logging**: All move operations logged with timestamps and details

## Recent Changes (v1.1 - January 2026)

- **Auto-Complete Workflow**: New checkbox option to automatically run copy→verify→finalize in one click
- **Session-Based Organization**: Each copy session now creates a unique subfolder structure: `from-FreeSpace/<hostname>-<timestamp>/` at the destination
- **Real-Time Log Display**: Added live log window showing recent operations with timestamps
- **Background Operations**: Verify operation now runs in background thread (no more UI freezing)
- **Flexible Symlink Options**: Choose between:
  - **Default**: Replace entire directory with single symlink (faster, simpler)
  - **File-level**: Replace each file with individual symlinks (preserves directory structure)
- **Better Error Handling**: Gracefully handles permission errors and already-existing destinations
- **Skipped Files Tracking**: Operations log which files were skipped due to permissions or other issues

## Features

### Copy & Verify Workflow
- **Directory Selection**: Easy selection of one or more source directories from your hard drive
- **External Storage Destination**: Select any external storage (USB, network drive, external HDD/SSD) as the destination
- **Organized Destination Structure**: Automatically creates `from-FreeSpace/<hostname>-<timestamp>/` subdirectories for each session
- **Full Path Preservation**: The complete directory structure is preserved at the destination, maintaining the full path hierarchy
- **Safe Copy**: Copy directories to external storage with progress indication and real-time logging
- **Verification**: Verify that all files were copied correctly (checks existence and file sizes)
- **Flexible Symbolic Links**: 
  - **Default Mode**: Replace entire directory with a single symlink (recommended)
  - **File-Level Mode**: Replace each file individually with symlinks while preserving directory structure

### Move Directory Workflow (NEW)
- **Direct Move**: Move entire directories to any location with a single operation
- **Automatic Symlink Replacement**: Original directory automatically replaced with symlink to new location
- **No Verification Needed**: Move operation is atomic - contents are moved and symlink is created in one step
- **Works Across Filesystems**: Move directories between different drives or partitions
- **Safe Rollback**: Automatic rollback to original state if move fails at any point
- **Restore Capability**: Undo a move operation with a single click to restore the directory to its original location
- **Move Metadata**: Automatically saves metadata in moved directories to track original location and enable restoration

### General Features
- **Real-Time Monitoring**: Live log display shows current operations and completion status
- **Detailed Logging**: Timestamped JSON logs for all operations (copy, verify, finalize, move, restore)
- **User Confirmations**: Multiple confirmation dialogs to prevent accidental data loss
- **Restoration**: Ability to restore original files from symlinks when needed
- **Move Undo**: Restore moved directories to original locations as needed

## Requirements

- Python 3.7 or higher
- Flet 0.80.0 or higher

## Installation

1. Clone this repository:
```bash
git clone https://github.com/SummittDweller/FreeSpace.git
cd FreeSpace
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

### GUI Mode (Recommended)

Run the application:
```bash
python3 main.py
```

### Programmatic API

For advanced users, you can also use the programmatic API:

```python
from freespace_api import FreeSpaceAPI

# Initialize API
api = FreeSpaceAPI()

# Copy directory to external storage
result = api.copy_directory(
    source="/path/to/source/directory",
    destination="/path/to/external/storage"
)

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

# OR use the new move_directory method for direct relocation
move_result = api.move_directory(
    source="/path/to/source/directory",
    destination="/path/to/new/location"
)

# Restore a previously moved directory to original location
restore_result = api.restore_moved_directory(
    moved_location="/path/to/new/location/directory"
)
```

See `freespace_api.py` for more details.

### Workflows

#### Workflow 1: Move Directory (NEW - Simple & Fast)

Use this for direct relocation of directories to new locations without copying verification overhead.

1. **Add Source Directories**: Click "Add Directory/Directories" to select the directory you want to move
2. **Click Move Directory Button**: Select the destination location in the file picker
3. **Confirm the Move**: Review the move plan and confirm
4. **Done!**: The directory is moved and replaced with a symlink automatically

**Need to undo?** Click "Restore Moved Directory" and select the moved directory to restore it to its original location.

**When to use:**
- Moving directories between different drives/filesystems
- Relocating directories to free up primary drive space for applications/swap
- When you want the fastest possible operation without verification

**Example:**
- Move `~/Library/Application Support/LargeApp` to `/Volumes/ExternalDrive/AppSupport`
- Move `/var/cache` to `/mnt/slowstorage/cache`

#### Workflow 2: Copy, Verify, Then Finalize (Conservative - Safe)

Use this for copying to external storage with built-in verification.

1. **Add Source Directories**: Select directories you want to move
2. **Select Destination**: Choose the base destination folder (USB drive, external SSD, network drive, etc.)
3. **Enable Auto-Complete (Optional)**: Check "Auto-complete workflow" for one-click processing
4. **One-Click or Manual Process**:
   - **Auto-Complete**: Click "1. Copy to Destination" - automatically runs all steps
   - **Manual**: 
     - Click "1. Copy to Destination" to copy all directories
     - Click "2. Verify Copy" to verify all files were copied correctly
     - Click "3. Delete & Create Links" to replace originals with symlinks

**When to use:**
- Backing up to external storage
- When you want verification before deletion
- Creating reliable backups with symlink forwarding

#### Step-by-Step Details (Copy/Verify/Finalize Workflow)

1. **Add Source Directories**: Click "Add Directory/Directories" to select directories from your hard drive that you want to move to external storage. The file picker will keep opening after each selection, allowing you to select multiple directories in succession. The picker stays focused on the parent directory of your last selection for convenience. Click Cancel in the file picker when you're finished selecting directories.

2. **Select Destination**: Click "Select Destination Directory" to choose the base destination folder on your external storage. The app will automatically create a session-specific subdirectory: `from-FreeSpace/<hostname>-<timestamp>/` where all files will be copied.

3. **Copy to Destination**: Click "1. Copy to Destination" to copy all selected directories to the external storage. This preserves the complete directory structure by maintaining the full path hierarchy. Watch the real-time log for progress updates. If a destination already exists, it will be skipped and logged.

4. **Verify Copy**: Click "2. Verify Copy" to verify that all files were copied correctly. This checks file existence and sizes. The verification runs in the background and logs progress in real-time. Files that cannot be accessed due to permissions are skipped and logged.

5. **Replace with Links**: Click "3. Delete & Create Links" to finalize the move:
   - **Default Mode (Unchecked)**: Replaces each entire directory with a single symbolic link to the destination copy. This is faster and simpler.
   - **File-Level Mode (Checked)**: Replaces individual files with symbolic links while preserving the directory structure. Check the "Replace each file with individual symlinks" option if you need this behavior.

   **Important**: 
   - Immutable files (files with the `uchg` flag on macOS) are automatically skipped in file-level mode
   - Already-existing symbolic links are skipped
   - The log reports how many items were processed, skipped, or failed

## Troubleshooting

### Permission Denied Errors During Move/Restore

If you encounter "Permission denied" errors when moving or restoring directories:

**Cause**: The application doesn't have sufficient permissions to move directories that are owned by other users or have restricted permissions (like system directories or directories owned by root).

**Solution**: 
1. **For non-system directories**: Ensure you own the directory you're trying to move (check with `ls -ld /path/to/directory`)
2. **For system/protected directories**: You may need to run the application with elevated privileges or move them to a location you own first
3. **Check permissions**: Use `ls -la /path/to/directory` to see who owns the directory and what permissions are set

### Verification Fails
- Check the log files for specific files that failed verification
- Files with permission errors are automatically skipped and logged
- Re-run verification after addressing any issues

### Destination Already Exists
- If you re-run a copy, already-existing destinations are skipped and logged
- Each session creates a new timestamped folder to avoid conflicts

### Restoring a Moved Directory
- Click "Restore Moved Directory" button
- Select the directory in its current (moved) location
- The app will automatically find the original location using the metadata file
- Confirm the restoration
- The directory is restored and the symlink is removed

**Note**: The metadata file (`.freespace_move_metadata.json`) is automatically created in the moved directory and must remain there for restoration to work.

## Logs

Logs are stored in two locations:
1. **Local**: `~/freespace_logs/` on your computer
2. **Destination**: `<destination>/from-FreeSpace/<hostname>-<timestamp>/freespace_logs/` on your external storage (for copy/verify/finalize workflows)

The real-time log display in the app shows the most recent 15 operations with timestamps for easy monitoring.

Log files include:
- `move_log_YYYYMMDD_HHMMSS.json` - Move operation details (new!)
- `restore_move_log_YYYYMMDD_HHMMSS.json` - Restore move operation details (new!)
- `copy_log_YYYYMMDD_HHMMSS.json` - Copy operation details
- `verify_log_YYYYMMDD_HHMMSS.json` - Verification results
- `finalize_log_YYYYMMDD_HHMMSS.json` - Finalization details including:
  - `files_processed`: Number of files successfully replaced with symlinks
  - `files_skipped`: Number of immutable/protected files skipped
  - `files_failed`: Number of files that failed to process
  - `skipped_details`: List of skipped files with reasons
  - `failed_details`: List of failed files with error messages

Having logs in both locations ensures you have a complete record of all operations both locally and with your backed-up data.

## Example Use Cases

### Use Case 1: Free Up Primary Drive Space

Move large directories to a secondary drive to make room for applications, swap space, and system operations:

1. Launch FreeSpace
2. Add `/Users/mark/Library/Application Support/LargeApp` (5GB) and `/Users/mark/Library/Caches` (10GB)
3. Click **"Move Directory"** button
4. Select `/Volumes/ExternalSSD/` as the destination
5. Confirm the move
6. The directories are instantly moved and replaced with symlinks
7. Primary drive now has 15GB of free space!
8. `LargeApp` continues working transparently through the symlink

### Use Case 2: Archive to External Storage with Verification

Back up large media collections to external storage before archiving:

1. Launch FreeSpace
2. Add `/home/user/Videos/Projects` and `/home/user/Photos/Archive`
3. Select destination `/media/external/backup/`
4. Check "Auto-complete workflow"
5. Copy → Verify → Finalize (automatic)
6. Original directories become symbolic links pointing to the backup
7. Logs saved in both locations for verification

### Use Case 3: Consolidate Storage

Move directories from multiple primary drives to a large storage array:

1. Add multiple directories to move
2. Click "Move Directory"
3. Select `/mnt/storage-array/archive/` as destination
4. Complete move with automatic rollback if anything goes wrong
5. All directories are relocated and replaced with symlinks

## Important Notes

- **Backup First**: Always have backups before using this tool, especially for critical data
- **Symbolic Links**: The tool creates symbolic links that work on Linux/Mac. On Windows, you may need administrator privileges
- **External Storage**: Make sure your destination storage has enough space and remains accessible throughout the process (keep USB drives connected, network drives mounted, etc.)
- **Log Files**: Keep log files for reference in case you need to verify or troubleshoot operations
- **Moved vs Copied**: 
  - **Move Directory**: Relocates content instantly (no copy overhead), perfect for internal storage reorganization
  - **Copy/Verify/Finalize**: Creates a backup copy, perfect for external storage and archival

- **Immutable Files**: Files protected with the immutable flag (common in macOS apps like Receipts, Mail, etc.) are automatically skipped and remain as original files. The application reports how many files were skipped in the status message and logs detailed information.
- **Directory Structure**: The finalization process preserves directory structure. Only individual files are replaced with symbolic links, not entire directories.

## License

This project is open source and available for personal use.
