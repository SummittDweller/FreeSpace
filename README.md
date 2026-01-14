# FreeSpace

A Python/Flet GUI application to support a hard disk "move with verification to external storage" workflow to free up hard drive space.

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

- **Directory Selection**: Easy selection of one or more source directories from your hard drive
- **External Storage Destination**: Select any external storage (USB, network drive, external HDD/SSD) as the destination
- **Organized Destination Structure**: Automatically creates `from-FreeSpace/<hostname>-<timestamp>/` subdirectories for each session
- **Full Path Preservation**: The complete directory structure is preserved at the destination, maintaining the full path hierarchy
- **Safe Copy**: Copy directories to external storage with progress indication and real-time logging
- **Verification**: Verify that all files were copied correctly (checks existence and file sizes)
- **Flexible Symbolic Links**: 
  - **Default Mode**: Replace entire directory with a single symlink (recommended)
  - **File-Level Mode**: Replace each file individually with symlinks while preserving directory structure
- **Real-Time Monitoring**: Live log display shows current operations and completion status
- **Detailed Logging**: Timestamped JSON logs for all operations (copy, verify, finalize)
- **User Confirmations**: Multiple confirmation dialogs to prevent accidental data loss

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

# Copy directory
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
```

See `freespace_api.py` for more details.

### Workflow

#### Quick Start (Auto-Complete Mode)

1. **Add Source Directories**: Select directories you want to move
2. **Select Destination**: Choose the base destination folder
3. **Enable Auto-Complete**: Check "Auto-complete workflow" checkbox
4. **One-Click Process**: Click "1. Copy to Destination" - the app will automatically:
   - Copy all directories to the destination
   - Verify all copied files
   - Delete originals and create symbolic links
   - Show progress for each step in the real-time log

#### Manual Step-by-Step Mode

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

### Workflow Options

- **Auto-complete workflow**: Automatically runs verify and finalize after copy completes. Perfect for routine operations when you're confident about the source and destination.
- **Replace each file with individual symlinks**: Uses file-level symlinks instead of directory-level. Useful when you need to preserve the original directory structure with individual file links.

### Safety Features

- **Multiple Confirmations**: The application asks for confirmation before copying and before deleting originals
- **Step-by-step Process**: Operations are done in stages (copy → verify → finalize) to ensure safety
- **Verification**: Files are verified before deletion is allowed
- **Detailed Logging**: All operations are logged with timestamps in JSON format

### Logs

Logs are stored in two locations:
1. **Local**: `~/freespace_logs/` on your computer
2. **Destination**: `<destination>/from-FreeSpace/<hostname>-<timestamp>/freespace_logs/` on your external storage

The real-time log display in the app shows the most recent 15 operations with timestamps for easy monitoring.

Log files include:
- `copy_log_<timestamp>.json` - Details of copy operations
- `verify_log_<timestamp>.json` - Verification results including any mismatches or skipped files
- `finalize_log_<timestamp>.json` - Finalization details including space freed and any errors

## Troubleshooting

### Verification Fails
- Check the log files for specific files that failed verification
- Files with permission errors are automatically skipped and logged
- Re-run verification after addressing any issues

### Destination Already Exists
- If you re-run a copy, already-existing destinations are skipped and logged
- Each session creates a new timestamped folder to avoid conflicts

### Permission Denied Errors
- Some system files may have restricted permissions
- These are automatically skipped and logged
- Review the log's "skipped" section to see which files were affected

Log files include:
- `copy_log_YYYYMMDD_HHMMSS.json` - Copy operation details
- `verify_log_YYYYMMDD_HHMMSS.json` - Verification results
- `finalize_log_YYYYMMDD_HHMMSS.json` - Finalization details including:
  - `files_processed`: Number of files successfully replaced with symlinks
  - `files_skipped`: Number of immutable/protected files skipped
  - `files_failed`: Number of files that failed to process
  - `skipped_details`: List of skipped files with reasons
  - `failed_details`: List of failed files with error messages

Having logs in both locations ensures you have a complete record of all operations both locally and with your backed-up data.

## Example Use Case

You have large media directories on your hard drive that you want to move to external storage:

1. Launch FreeSpace
2. Add `/home/user/Videos/Projects` and `/home/user/Photos/2024`
3. Select destination `/media/external/backup/` (could be USB drive, network drive, external SSD, etc.)
4. Copy → Verify → Finalize
5. Original directories become symbolic links:
   - `/home/user/Videos/Projects` → `/media/external/backup/home/user/Videos/Projects`
   - `/home/user/Photos/2024` → `/media/external/backup/home/user/Photos/2024`

The full directory structure is preserved at the destination, making it easy to restore or relocate files later.

## Important Notes

- **Backup First**: Always have backups before using this tool
- **Symbolic Links**: The tool creates symbolic links that work on Linux/Mac. On Windows, you may need administrator privileges
- **External Storage**: Make sure your destination storage has enough space and remains accessible throughout the process (keep USB drives connected, network drives mounted, etc.)
- **Log Files**: Keep log files for reference in case you need to verify or troubleshoot operations
- **Immutable Files**: Files protected with the immutable flag (common in macOS apps like Receipts, Mail, etc.) are automatically skipped and remain as original files. The application reports how many files were skipped in the status message and logs detailed information.
- **Directory Structure**: The finalization process preserves directory structure. Only individual files are replaced with symbolic links, not entire directories.

## License

This project is open source and available for personal use.
