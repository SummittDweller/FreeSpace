# Kill Switch, Granular Logging, and Interrupted Operation Recovery

## Overview

FreeSpace now includes three major usability improvements:
1. **Kill Switch** - Stop operations in progress
2. **Granular Logging** - Detailed step-by-step operation progress
3. **Interrupted Operation Recovery** - Handle incomplete moves gracefully

## 1. Kill Switch (STOP OPERATION Button)

### What It Does
The Kill Switch allows you to stop a move or restore operation that's in progress. This is useful if you realize you made a mistake or need to cancel the operation.

### How to Use
1. During a Move or Restore operation, a red "STOP OPERATION" button appears at the top right of the Log window
2. Click the button at any time to cancel the operation
3. The button disappears when the operation completes

### Key Features
- **Immediate Response**: Stops the operation as soon as possible
- **Safe Cancellation**: The operation checks for the kill signal at strategic points
- **Clear Feedback**: Logs "KILL signal received" and "⏹ Operation cancelled by user"
- **Thread-Safe**: Uses `threading.Event()` to signal background threads

### When to Use
- You selected the wrong source or destination directory
- You need to cancel due to system requirements (running out of space, etc.)
- The operation is taking longer than expected
- You notice something is wrong during the move/restore

## 2. Granular Logging

### What's New
The Log window now shows detailed, step-by-step information about what the application is doing:

#### Log Levels
- **ℹ INFO** - Regular informational messages (light blue checkmark)
- **✓ SUCCESS** - Successful completion of steps (green checkmark)
- **⚠ WARNING** - Warnings that don't stop operation (orange warning symbol)
- **✗ ERROR** - Error conditions that stop operation (red X)
- **⏹ STOP** - Operation was cancelled (stop symbol)

#### Example Log Output
```
[14:23:45] Starting move operation for Downloads...
[14:23:45] Normalizing paths...
[14:23:45] Source: /Users/mark/Downloads
[14:23:45] Destination: /Volumes/External/Downloads
[14:23:45] Checking if destination exists...
[14:23:45] Checking if source is a symlink...
[14:23:45] Calculating directory size...
[14:23:45] Directory contains 1547 files (18.42 GB)
[14:23:45] Starting atomic move operation...
[14:23:47] Move operation completed successfully
[14:23:47] Creating symlink at original location...
[14:23:47] ✓ Successfully moved Downloads
[14:23:47] Move operation completed successfully
```

### Benefits
- **Transparency**: You can see exactly what's happening
- **Debugging**: Easier to understand what went wrong if operation fails
- **Estimation**: See directory size and file count before move starts
- **Safety**: Shows status at each critical step

## 3. Interrupted Operation Recovery

### The Problem
In previous versions, if you interrupted a move operation (by force-quitting the app), the directory might be left in an inconsistent state:
- Directory could be partially moved
- Original location might have a `.backup_*` directory
- Symlink might not have been created

### How Recovery Works

FreeSpace now handles interrupted operations gracefully. If you try to move the same directory again:

1. **Detection**: The application checks for any `.backup_*` directories at the original location
2. **Notification**: Logs detailed information about what it finds
3. **Atomic Retry**: Completes or restarts the operation from where it left off
4. **Confirmation**: Shows you what will happen before proceeding

### Example Scenario

**Previous Behavior:**
```
User: Interrupts move of ~/Downloads
Result: Directory in bad state - ~/Downloads.backup_20260209_* exists
Next attempt: Fails or unpredictable behavior
```

**New Behavior:**
```
User: Interrupts move of ~/Downloads
Result: Logs show interruption point
Next attempt: 
  [14:25:00] Checking for interrupted moves...
  [14:25:00] Found incomplete move state - recovering
  [14:25:00] Resuming from interrupted move
  [14:25:02] ✓ Move completed successfully
```

### What Happens If Move Is Interrupted

If you interrupt a move mid-operation:

1. **During size calculation**: Safe to retry - nothing changed yet
2. **During actual move**: Some files might be at destination, some at source
   - Retry will detect state and complete or restart cleanly
3. **During symlink creation**: Core move is done, just needs symlink
   - Retry will verify and complete

### Best Practices

1. **Don't Force-Quit During Move**: Use the STOP button instead
   - More controlled
   - Logs exactly what state it's in
   - Can be more safely recovered

2. **Use STOP Button Appropriately**: 
   - Press once - waits for current step to finish
   - Multiple presses may terminate immediately (less safe)

3. **Rerun If Interrupted**:
   - Same selections should work fine
   - Check the log to understand what happened
   - Operation will complete on next attempt

## Implementation Details

### Kill Switch Architecture
```python
# Threading event used to signal stop
self.stop_operation = threading.Event()

# Check at strategic points in operation
if self.stop_operation.is_set():
    self.log_message("Operation cancelled by user", level="STOP")
    return
```

### Log Levels
```python
def log_message(self, message: str, level: str = "INFO"):
    """
    level can be: "INFO", "SUCCESS", "WARNING", "ERROR", "STOP"
    Automatically formats with appropriate symbols
    """
```

### Operation State Management
```python
# Before starting operation
self.operation_in_progress = True
self.stop_operation.clear()
self.kill_button.visible = True

# After operation completes
self.operation_in_progress = False
self.kill_button.visible = False
```

## Version Information

- **Feature Added**: February 9, 2026
- **FreeSpace Version**: 1.2+
- **Status**: Production Ready

## Troubleshooting

### Kill Button Doesn't Appear
- Make sure you've started a Move or Restore operation
- Button should appear at top-right of Log window once operation starts
- If not visible, try scrolling the window

### Interrupted Move - Can't Recover
- Check the log for what state was interrupted
- Manually clean up any `.backup_*` directories if needed
- Try moving to a different destination location
- Use `ls -la /path/to/source/` to see backup directories

### Granular Logging is Missing Steps
- Some fast operations may skip certain log messages
- This is normal - operation completed successfully
- Check the final status message for confirmation

## See Also
- [SUDO_IMPLEMENTATION.md](SUDO_IMPLEMENTATION.md) - Elevated privileges support
- [README.md](README.md) - Main documentation
