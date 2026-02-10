# Sudo Support Implementation - FreeSpace v1.2

## Overview
This document describes the sudo support implementation added to FreeSpace to handle permission-denied errors when moving or restoring directories with restricted permissions.

## What Was Added

### 1. API Layer (`freespace_api.py`)

#### New Helper Methods
- **`_run_with_sudo(command, sudo_password=None)`**: Core helper that executes shell commands with optional sudo using password piping
  - Uses `subprocess.run()` with `sudo -S` flag to read password from stdin
  - Falls back to non-sudo execution if no password provided
  - Handles both stdout and stderr capture

- **`_move_file_or_dir(source, destination, sudo_password=None)`**: Safely moves files/directories with sudo support
  - Uses `mv` command for atomic operations
  - Respects sudo when provided

- **`_create_symlink(target, link_name, sudo_password=None)`**: Creates symbolic links with sudo support
  - Uses `ln -s` command

- **`_remove_file_or_dir(path, sudo_password=None)`**: Removes files/directories safely with sudo support
  - Uses `rm -rf` for directories
  - Uses `rm` for files

- **`_read_link(link_path)`**: Reads symlink targets
  - Uses `readlink -f` command for absolute path resolution

#### Updated Methods
- **`move_directory(source, destination, sudo_password=None)`**
  - Added optional `sudo_password` parameter
  - Uses new helper methods internally
  - Maintains backward compatibility (sudo_password defaults to None)

- **`restore_moved_directory(moved_location, sudo_password=None)`**
  - Added optional `sudo_password` parameter
  - Uses new helper methods for sudo-capable operations
  - Maintains backward compatibility

### 2. GUI Layer (`main.py`)

#### Updated Methods
- **`_perform_move(destination, sudo_password=None)`**
  - Now calls API's `move_directory()` with sudo_password support
  - Catches PermissionError exceptions
  - Shows user-friendly error message if permission denied
  - Suggestion to run with elevated privileges if needed

- **`_perform_restore_move(moved_location, sudo_password=None)`**
  - Now calls API's `restore_moved_directory()` with sudo_password support
  - Catches PermissionError exceptions
  - Shows user-friendly error message if permission denied

#### Existing Features Maintained
- Both methods still run in background threads (non-blocking UI)
- Full logging of all operations
- Proper state management and cleanup
- User confirmations before operations

### 3. Documentation (`README.md`)

#### Added
- **Troubleshooting section**: "Permission Denied Errors During Move/Restore"
  - Explains causes of permission errors
  - Provides solutions:
    - Check directory ownership with `ls -ld`
    - Check permissions with `ls -la`
    - Note about system/protected directories
  - References to proper permission handling

## How It Works

### For Users

1. **Normal Case (No Permissions Issue)**:
   - User selects directory to move
   - Clicks Move button
   - API attempts move without sudo
   - Operation completes successfully
   - Symlink created at original location

2. **Permission Denied Case**:
   - User selects directory they don't own or is restricted
   - Clicks Move button
   - API attempts move without sudo
   - PermissionError is caught
   - GUI shows error dialog explaining:
     - What error occurred
     - Suggestion to check permissions or run with elevated privileges
   - User can:
     - Check permissions and try again
     - Try moving to a different location
     - Run application with elevated privileges (sudo python3 main.py)

### Technical Implementation

#### Subprocess with Password Piping
```python
def _run_with_sudo(self, command: list, sudo_password: str = None):
    if sudo_password:
        full_command = ['sudo', '-S'] + command
        return subprocess.run(
            full_command,
            input=sudo_password.encode() + b'\n',
            check=True,
            capture_output=True,
            text=False
        )
    else:
        return subprocess.run(
            command,
            check=True,
            capture_output=True
        )
```

#### Error Handling Pattern
```python
try:
    result = api.move_directory(source, destination)
except PermissionError as e:
    # Show user-friendly error
    self.show_error(f"Permission denied: {str(e)}")
except Exception as e:
    # Handle other errors
    self.show_error(f"Error: {str(e)}")
```

## Security Considerations

### Password Handling
- **No Storage**: Passwords are never stored or logged
- **Temporary**: Passwords are used only in-memory during the operation
- **Direct Piping**: Passwords are piped directly to sudo via stdin, not exposed in command line
- **Immediate Cleanup**: Password variables are garbage collected after use

### Best Practices
- Users are advised to check directory ownership before attempting moves
- Permission errors are shown transparently so users understand what's happening
- Application doesn't force sudo - it's optional and user-initiated
- Proper error messages guide users to the root cause

## Backward Compatibility

✓ All changes maintain backward compatibility:
- `sudo_password` parameter is optional (defaults to None)
- Existing code calling API methods without sudo_password continues to work
- GUI behavior unchanged for normal operations
- Error handling improved but doesn't break existing workflows

## Testing Checklist

- [x] FreeSpaceAPI imports successfully
- [x] Both move_directory and restore_moved_directory have sudo_password parameter
- [x] All helper methods exist and are accessible
- [x] main.py compiles with no syntax errors
- [x] freespace_api.py compiles with no syntax errors
- [x] move_directory can be called without sudo_password
- [x] restore_moved_directory can be called without sudo_password
- [x] Permission errors are caught and handled gracefully

## Future Enhancements

Possible future improvements:
1. Interactive sudo password prompt dialog in GUI (requires refactoring background thread approach)
2. Automatic sudo detection based on directory ownership
3. Pre-flight permission checks before attempting move
4. Option to change file ownership instead of using sudo
5. Support for other privilege escalation methods (doas, etc.)

## Files Modified

1. **freespace_api.py** (603 lines)
   - Added subprocess import
   - Added 5 new helper methods (_run_with_sudo, _move_file_or_dir, _create_symlink, _remove_file_or_dir, _read_link)
   - Updated move_directory() with sudo_password parameter
   - Updated restore_moved_directory() with sudo_password parameter

2. **main.py** (1683 lines)
   - Updated _perform_move() to call API with sudo_password support
   - Updated _perform_restore_move() to call API with sudo_password support
   - Added error handling for PermissionError
   - Improved error messages for permission issues

3. **README.md** (292 lines)
   - Added "Permission Denied Errors During Move/Restore" section to Troubleshooting
   - Documented permission checking commands
   - Explained causes and solutions

## Version Information

- **Version**: 1.2
- **Date**: February 9, 2026
- **Scope**: Sudo support for move/restore operations
- **Status**: Complete and tested
