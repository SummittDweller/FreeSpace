# Changelog

All notable changes to FreeSpace will be documented in this file.

## [1.1.0] - 2026-01-14

### Added
- **Auto-Complete Workflow Option**: New checkbox to automatically run the complete copy→verify→finalize workflow with one button click
  - When enabled, clicking "Copy to Destination" automatically proceeds through all three steps
  - Enhanced confirmation dialog clearly explains what will happen
  - Real-time log messages show progress through each automatic step
  - If any step fails, the automatic sequence stops safely
- **Session-Based Organization**: Each copy session now automatically creates a unique subfolder structure at the destination: `from-FreeSpace/<hostname>-<timestamp>/`
  - Hostname is extracted from the machine running FreeSpace
  - Timestamp format: `YYYY-MM-DD_HHMMSS` for easy sorting and identification
- **Real-Time Log Display**: Added scrolling log text area in the status section showing the last 15 operations with timestamps
  - Logs copy, verify, and finalize operations in real-time
  - Shows success (✓), failures (✗), and skipped items
  - Includes timestamps for each log entry
- **Flexible Symlink Options**: New checkbox to choose between two symlink modes:
  - **Directory-Level (Default)**: Replaces entire directory with a single symlink (faster, simpler)
  - **File-Level (Optional)**: Replaces each file individually with symlinks while preserving directory structure
- **Background Verification**: Verify operation now runs in a background thread to prevent UI freezing
- **Better Destination Display**: Shows both the base path and the session-specific subdirectory when destination is selected

### Changed
- **Error Handling**: Improved permission error handling in verification
  - Files with permission errors are now skipped and logged instead of causing crashes
  - Already-existing destinations are skipped and logged during copy (not an error anymore)
- **Verification Process**: 
  - Added `os.access()` checks to skip unreadable files before attempting to read them
  - Added `onerror` handler to `os.walk()` to gracefully handle inaccessible directories
  - Tracks skipped files separately from mismatches in verification logs
- **Window Size**: Increased from 720px to 1000px height to accommodate new features and ensure all content is visible
- **Status Messages**: More informative status messages with real-time progress updates
- **Log Structure**: Added "mode" field to finalize logs indicating which symlink mode was used

### Fixed
- Verify button now properly executes verification (was appearing to do nothing)
- UI no longer freezes during long-running verification operations
- Permission denied errors no longer crash the application
- Text color visibility issue when destination is selected (changed from black to blue)

### Technical Details
- Added `socket` module import for hostname detection
- Added `actual_destination_directory` state variable to track the full session-specific path
- New `log_message()` method for real-time log updates with auto-scrolling
- Split finalize into two methods: `_perform_finalize_directory_level()` and `_perform_finalize_file_level()`
- Added `_perform_verify()` method to run verification in background thread
- Enhanced `_verify_directory()` with permission checking and error handling

## [1.0.0] - Initial Release

### Features
- Multi-directory selection with persistent file picker
- Full path preservation at destination
- Three-step workflow: Copy → Verify → Finalize
- File-level symbolic link creation
- Detailed JSON logging (local and destination)
- Progress indicators and status updates
- Multiple confirmation dialogs for safety
- Immutable file detection and skipping (macOS)
- Symbolic link detection and skipping
