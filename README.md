# FreeSpace

A Python/Flet GUI application to support a hard disk "move with verification to external storage" workflow to free up hard drive space.

## Features

- **Directory Selection**: Easy selection of one or more source directories from your hard drive
- **External Storage Destination**: Select any external storage (USB, network drive, external HDD/SSD) as the destination
- **Safe Copy**: Copy directories to external storage with progress indication
- **Verification**: Verify that all files were copied correctly (checks existence and file sizes)
- **Symbolic Links**: Delete original directories and replace them with symbolic links pointing to the USB location
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

1. **Add Source Directories**: Click "Add Directory/Directories" to select directories from your hard drive that you want to move to USB storage. The file picker will keep opening after each selection, allowing you to select multiple directories in succession. The picker stays focused on the parent directory of your last selection for convenience. Click Cancel in the file picker when you're finished selecting directories.

2. **Select Destination**: Click "Select Destination Directory" to choose the destination folder on your external storage (USB drive, network drive, external HDD/SSD, etc.).

3. **Copy to Destination**: Click "1. Copy to Destination" to copy all selected directories to the external storage destination. This preserves the directory structure.

4. **Verify Copy**: Click "2. Verify Copy" to verify that all files were copied correctly. This checks file existence and sizes.

5. **Replace Files with Links**: Click "3. Delete & Create Links" to replace individual files with symbolic links pointing to the destination location. Directory structure is preserved; only the actual files are replaced with links.

   **Important**: Immutable files (files with the `uchg` flag on macOS, commonly used by apps to protect important data) are automatically skipped and left unchanged. The log will report how many files were skipped.

### Safety Features

- **Multiple Confirmations**: The application asks for confirmation before copying and before deleting originals
- **Step-by-step Process**: Operations are done in stages (copy → verify → finalize) to ensure safety
- **Verification**: Files are verified before deletion is allowed
- **Detailed Logging**: All operations are logged with timestamps in JSON format

### Logs

Logs are stored in `~/freespace_logs/` with timestamps:
- `copy_log_YYYYMMDD_HHMMSS.json` - Copy operation details
- `verify_log_YYYYMMDD_HHMMSS.json` - Verification results
- `finalize_log_YYYYMMDD_HHMMSS.json` - Finalization details including:
  - `files_processed`: Number of files successfully replaced with symlinks
  - `files_skipped`: Number of immutable/protected files skipped
  - `files_failed`: Number of files that failed to process
  - `skipped_details`: List of skipped files with reasons
  - `failed_details`: List of failed files with error messages

## Example Use Case

You have large media directories on your hard drive that you want to move to external storage:

1. Launch FreeSpace
2. Add `/home/user/Videos/Projects` and `/home/user/Photos/2024`
3. Select destination `/media/external/backup/` (could be USB drive, network drive, external SSD, etc.)
4. Copy → Verify → Finalize
5. Original directories become symbolic links: `/home/user/Videos/Projects` → `/media/usb/backup/Projects`

## Important Notes

- **Backup First**: Always have backups before using this tool
- **Symbolic Links**: The tool creates symbolic links that work on Linux/Mac. On Windows, you may need administrator privileges
- **External Storage**: Make sure your destination storage has enough space and remains accessible throughout the process (keep USB drives connected, network drives mounted, etc.)
- **Log Files**: Keep log files for reference in case you need to verify or troubleshoot operations
- **Immutable Files**: Files protected with the immutable flag (common in macOS apps like Receipts, Mail, etc.) are automatically skipped and remain as original files. The application reports how many files were skipped in the status message and logs detailed information.
- **Directory Structure**: The finalization process preserves directory structure. Only individual files are replaced with symbolic links, not entire directories.

## License

This project is open source and available for personal use.
