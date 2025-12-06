"""Interactive Shell for Baidu Netdisk Client"""

import os
import sys
import shlex
import fnmatch
import re
from .client import BaiduNetdiskClient

# Try to import readline for tab completion
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    # On Windows, try pyreadline
    try:
        import pyreadline3 as readline
        READLINE_AVAILABLE = True
    except ImportError:
        try:
            import pyreadline as readline
            READLINE_AVAILABLE = True
        except ImportError:
            READLINE_AVAILABLE = False


class BaiduNetdiskShell:
    """Interactive shell for Baidu Netdisk operations"""
    
    def __init__(self, client):
        """Initialize shell with BaiduNetdiskClient instance"""
        self.client = client
        # Initialize current_path from client's base_path or config
        try:
            from .config import get_base_path
            base_path = get_base_path()
            # Normalize path
            if base_path != "/" and not base_path.endswith("/"):
                base_path = base_path + "/"
            self.current_path = base_path
        except (ImportError, Exception):
            # Fallback to client's base_path or root
            self.current_path = getattr(client, 'base_path', "/")
            if self.current_path != "/" and not self.current_path.endswith("/"):
                self.current_path = self.current_path + "/"
        self.running = True
        
        # Initialize tab completion
        self._setup_completion()
    
    def _resolve_path(self, path):
        """Resolve path relative to current_path"""
        if not path:
            return self.current_path
        
        # Absolute path
        if path.startswith("/"):
            return path
        
        # Relative path
        if path.startswith("./"):
            path = path[2:]
        
        # Combine with current path
        if self.current_path == "/":
            return "/" + path
        else:
            return self.current_path.rstrip("/") + "/" + path
    
    def _format_size(self, size_bytes):
        """Format file size"""
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024*1024*1024):.2f}G"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024*1024):.2f}M"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f}K"
        return f"{size_bytes}B"
    
    def _format_time(self, timestamp):
        """Format timestamp"""
        if not timestamp:
            return "N/A"
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(timestamp)
    
    def _get_directory_size(self, dir_path):
        """
        Calculate total size of a directory (sum of all files in it and subdirectories)
        
        Args:
            dir_path: Directory path
            
        Returns:
            Total size in bytes, or 0 if error
        """
        try:
            # Normalize path
            dir_path = dir_path.rstrip('/')
            if not dir_path:
                dir_path = "/"
            
            # Get all files recursively
            all_files = self.client.list_all_files_recursive(path=dir_path)
            if all_files is None:
                return 0
            
            # Sum up all file sizes
            total_size = 0
            for item in all_files:
                if item.get('isdir', 0) == 0:  # Only count files, not directories
                    total_size += item.get('size', 0)
            
            return total_size
        except Exception:
            return 0
    
    def _expand_wildcards(self, pattern):
        """
        Expand wildcard pattern to matching file paths
        
        Args:
            pattern: Pattern with wildcards (e.g., "*.txt", "file?.txt")
            
        Returns:
            List of matching file paths
        """
        # Check if pattern contains wildcards
        if '*' not in pattern and '?' not in pattern:
            return [pattern]
        
        # Resolve base directory
        if '/' in pattern:
            # Pattern contains path
            dir_part = os.path.dirname(pattern)
            file_pattern = os.path.basename(pattern)
            if dir_part:
                base_dir = self._resolve_path(dir_part)
            else:
                base_dir = self.current_path
        else:
            # Pattern is just filename
            base_dir = self.current_path
            file_pattern = pattern
        
        # Normalize base directory
        base_dir = base_dir.rstrip('/')
        if not base_dir:
            base_dir = "/"
        else:
            base_dir = base_dir + "/"
        
        # List files in directory
        file_list = self.client.list_files(directory=base_dir)
        if file_list is None or len(file_list) == 0:
            return []
        
        # Match files against pattern
        matches = []
        for file_info in file_list:
            filename = file_info.get('server_filename', '')
            if fnmatch.fnmatch(filename, file_pattern):
                # Build full path
                if base_dir == "/":
                    full_path = "/" + filename
                else:
                    full_path = base_dir.rstrip('/') + "/" + filename
                matches.append(full_path)
        
        return matches
    
    def cmd_cd(self, args):
        """Change directory: cd [path]"""
        if len(args) == 0:
            target_path = "/"
        else:
            path_arg = args[0]
            
            # Handle special cases: .. and .
            if path_arg == "..":
                # Go to parent directory
                if self.current_path == "/":
                    print("Already at root directory")
                    return
                # Remove last directory from path
                parts = self.current_path.rstrip("/").split("/")
                if len(parts) <= 1:
                    target_path = "/"
                else:
                    target_path = "/".join(parts[:-1])
                    if not target_path:
                        target_path = "/"
                    target_path = target_path + "/"
            elif path_arg == "." or path_arg == "./":
                # Stay in current directory
                target_path = self.current_path
            elif path_arg.startswith("../"):
                # Handle multiple ../
                parts = self.current_path.rstrip("/").split("/")
                rel_parts = path_arg.split("/")
                for part in rel_parts:
                    if part == "..":
                        if len(parts) > 1:
                            parts.pop()
                        else:
                            parts = ["/"]
                            break
                    elif part and part != ".":
                        parts.append(part)
                
                if parts == ["/"] or parts == [""]:
                    target_path = "/"
                else:
                    target_path = "/".join(parts) if parts[0] == "/" else "/" + "/".join(parts)
                    if target_path != "/":
                        target_path = target_path + "/"
            else:
                # Regular path resolution
                target_path = self._resolve_path(path_arg)
        
        # Normalize path
        target_path = target_path.rstrip("/")
        if not target_path:
            target_path = "/"
        else:
            target_path = target_path + "/"
        
        # Check if path exists and is a directory
        fsid = self.client.get_fsid_by_path(target_path.rstrip("/"))
        if fsid:
            meta_list = self.client.get_file_info([fsid])
            if meta_list and len(meta_list) > 0:
                if meta_list[0].get('isdir', 0) == 1:
                    self.current_path = target_path
                    return
                else:
                    print(f"Error: '{target_path.rstrip('/')}' is not a directory")
                    return
        
        # Try to list the directory to see if it exists
        file_list = self.client.list_files(directory=target_path)
        if file_list is not None:
            self.current_path = target_path
        else:
            print(f"Error: Directory '{target_path.rstrip('/')}' not found")
    
    def cmd_ls(self, args):
        """List files: ls [path] [-s] (supports wildcards: *, ?; -s: show directory sizes)"""
        # Parse flags
        show_dir_sizes = False
        path_args = []
        
        for arg in args:
            if arg in ['-s', '--size']:
                show_dir_sizes = True
            elif not arg.startswith('-'):
                path_args.append(arg)
        
        if len(path_args) == 0:
            target_path = self.current_path
            # List all files in current directory
            file_list = self.client.list_files(directory=target_path)
            if file_list is None:
                print(f"Error: Cannot access directory '{target_path}'")
                return
            if len(file_list) == 0:
                print(f"Directory '{target_path}' is empty")
                return
            
            # Display files
            print(f"\nDirectory: {target_path}")
            print("-" * 80)
            print(f"{'Type':<6} {'Size':<12} {'Modified':<20} {'Name'}")
            print("-" * 80)
            
            for file_info in file_list:
                isdir = file_info.get('isdir', 0)
                size = file_info.get('size', 0)
                mtime = file_info.get('server_mtime', 0)
                name = file_info.get('server_filename', 'unknown')
                
                file_type = "DIR" if isdir == 1 else "FILE"
                
                # Calculate directory size only if -s flag is set
                if isdir == 1:
                    if show_dir_sizes:
                        dir_path = target_path.rstrip('/') + '/' + name
                        dir_size = self._get_directory_size(dir_path)
                        size_str = self._format_size(dir_size)
                    else:
                        size_str = "-"
                else:
                    size_str = self._format_size(size)
                
                mtime_str = self._format_time(mtime)
                
                print(f"{file_type:<6} {size_str:<12} {mtime_str:<20} {name}")
            
            print("-" * 80)
            print(f"Total: {len(file_list)} items")
        else:
            pattern = path_args[0] if path_args else None
            if pattern:
                # Check if pattern contains wildcards
                if '*' in pattern or '?' in pattern:
                    # Expand wildcards
                    matches = self._expand_wildcards(pattern)
                    if not matches:
                        print(f"No files match pattern '{pattern}'")
                        return
                    
                    # Display matched files
                    print(f"\nFiles matching '{pattern}':")
                    print("-" * 80)
                    print(f"{'Type':<6} {'Size':<12} {'Modified':<20} {'Name'}")
                    print("-" * 80)
                    
                    for match_path in matches:
                        fsid = self.client.get_fsid_by_path(match_path.rstrip('/'))
                        if fsid:
                            meta_list = self.client.get_file_info([fsid])
                            if meta_list and len(meta_list) > 0:
                                info = meta_list[0]
                                isdir = info.get('isdir', 0)
                                size = info.get('size', 0)
                                mtime = info.get('server_mtime', 0)
                                name = info.get('server_filename', os.path.basename(match_path))
                                
                                file_type = "DIR" if isdir == 1 else "FILE"
                                
                                # Calculate directory size only if -s flag is set
                                if isdir == 1:
                                    if show_dir_sizes:
                                        dir_size = self._get_directory_size(match_path.rstrip('/'))
                                        size_str = self._format_size(dir_size)
                                    else:
                                        size_str = "-"
                                else:
                                    size_str = self._format_size(size)
                                
                                mtime_str = self._format_time(mtime)
                                
                                print(f"{file_type:<6} {size_str:<12} {mtime_str:<20} {name}")
                    
                    print("-" * 80)
                    print(f"Total: {len(matches)} items")
                else:
                    # Regular directory listing
                    target_path = self._resolve_path(pattern)
                    file_list = self.client.list_files(directory=target_path)
                    if file_list is None:
                        print(f"Error: Cannot access directory '{target_path}'")
                        return
                    if len(file_list) == 0:
                        print(f"Directory '{target_path}' is empty")
                        return
                    
                    # Display files
                    print(f"\nDirectory: {target_path}")
                    print("-" * 80)
                    print(f"{'Type':<6} {'Size':<12} {'Modified':<20} {'Name'}")
                    print("-" * 80)
                    
                    for file_info in file_list:
                        isdir = file_info.get('isdir', 0)
                        size = file_info.get('size', 0)
                        mtime = file_info.get('server_mtime', 0)
                        name = file_info.get('server_filename', 'unknown')
                        
                        file_type = "DIR" if isdir == 1 else "FILE"
                        
                        # Calculate directory size only if -s flag is set
                        if isdir == 1:
                            if show_dir_sizes:
                                dir_path = target_path.rstrip('/') + '/' + name
                                dir_size = self._get_directory_size(dir_path)
                                size_str = self._format_size(dir_size)
                            else:
                                size_str = "-"
                        else:
                            size_str = self._format_size(size)
                        
                        mtime_str = self._format_time(mtime)
                        
                        print(f"{file_type:<6} {size_str:<12} {mtime_str:<20} {name}")
                    
                    print("-" * 80)
                    print(f"Total: {len(file_list)} items")
    
    def cmd_pwd(self, args):
        """Print working directory: pwd"""
        print(self.current_path)
    
    def cmd_mkdir(self, args):
        """Create directory: mkdir <path>"""
        if len(args) == 0:
            print("Usage: mkdir <path>")
            return
        
        target_path = self._resolve_path(args[0])
        if self.client.create_directory(target_path):
            print(f"Directory '{target_path}' created successfully")
        else:
            print(f"Error: Failed to create directory '{target_path}'")
    
    def cmd_upload(self, args):
        """Upload file: upload <local_path> [remote_path]"""
        if len(args) == 0:
            print("Usage: upload <local_path> [remote_path]")
            return
        
        local_path = args[0]
        if not os.path.exists(local_path):
            print(f"Error: Local path '{local_path}' does not exist")
            return
        
        if len(args) >= 2:
            remote_path = self._resolve_path(args[1])
        else:
            # Use current directory with same filename
            filename = os.path.basename(local_path)
            if self.current_path == "/":
                remote_path = "/" + filename
            else:
                remote_path = self.current_path.rstrip("/") + "/" + filename
        
        if os.path.isdir(local_path):
            # Upload directory
            print(f"Uploading directory '{local_path}' to '{remote_path}'...")
            count = self.client.upload_directory(local_path, remote_path, recursive=True)
            print(f"Uploaded {count} files")
        else:
            # Upload file
            print(f"Uploading '{local_path}' to '{remote_path}'...")
            result = self.client.upload_file_auto(local_path, remote_path)
            if result:
                print("Upload completed successfully")
            else:
                print("Upload failed")
    
    def cmd_download(self, args):
        """Download file: download <remote_path> [local_path]"""
        if len(args) == 0:
            print("Usage: download <remote_path> [local_path]")
            return
        
        remote_path = self._resolve_path(args[0])
        
        if len(args) >= 2:
            local_path = args[1]
        else:
            # Use current directory with same filename
            filename = os.path.basename(remote_path.rstrip("/"))
            local_path = os.path.join(os.getcwd(), filename)
        
        # Check if remote is directory or file
        fsid = self.client.get_fsid_by_path(remote_path.rstrip("/"))
        if fsid:
            meta_list = self.client.get_file_info([fsid])
            if meta_list and len(meta_list) > 0:
                is_dir = meta_list[0].get('isdir', 0) == 1
            else:
                is_dir = False
        else:
            is_dir = remote_path.endswith("/")
        
        if is_dir:
            # Download directory
            print(f"Downloading directory '{remote_path}' to '{local_path}'...")
            count = self.client.download_directory(remote_path, local_path, recursive=True)
            print(f"Downloaded {count} files")
        else:
            # Download file
            print(f"Downloading '{remote_path}' to '{local_path}'...")
            result = self.client.download_file_by_path(remote_path, local_path)
            if result:
                print("Download completed successfully")
            else:
                print("Download failed")
    
    def cmd_mv(self, args):
        """Rename file or directory: mv <old_path> <new_name> (supports wildcards: *, ?)"""
        if len(args) < 2:
            print("Usage: mv <old_path> <new_name>")
            print("Note: new_name should be just the filename, not a full path")
            print("      Wildcards (*, ?) supported in old_path for batch operations")
            return
        
        old_pattern = args[0]
        new_name = args[1]
        
        # Validate new_name (should not contain path separators or wildcards)
        if '/' in new_name or '\\' in new_name:
            print("Error: New name should not contain path separators")
            print("Usage: mv <old_path> <new_name>")
            return
        
        if '*' in new_name or '?' in new_name:
            print("Error: New name cannot contain wildcards")
            print("Usage: mv <old_path> <new_name>")
            return
        
        # Check if old_pattern contains wildcards
        if '*' in old_pattern or '?' in old_pattern:
            # Expand wildcards for batch rename
            matches = self._expand_wildcards(old_pattern)
            if not matches:
                print(f"No files match pattern '{old_pattern}'")
                return
            
            if len(matches) > 1:
                print(f"Error: Multiple files match pattern '{old_pattern}' ({len(matches)} files)")
                print("       Batch rename not supported. Please rename files individually.")
                return
            
            # Single match, proceed with rename
            old_path = matches[0]
        else:
            # Regular single file rename
            old_path = self._resolve_path(old_pattern)
        
        # Get file info to show what will be renamed
        # Normalize old_path for lookup (remove trailing slash for files)
        lookup_path = old_path.rstrip('/')
        if not lookup_path:
            lookup_path = "/"
        
        # Use client's get_fsid_by_path which handles path resolution
        fsid = self.client.get_fsid_by_path(lookup_path)
        if not fsid:
            print(f"Error: File or directory '{old_path}' not found")
            return
        
        meta_list = self.client.get_file_info([fsid])
        if not meta_list or len(meta_list) == 0:
            print(f"Error: Cannot get info for '{old_path}'")
            return
        
        info = meta_list[0]
        # Try multiple ways to get the filename
        old_name = (info.get('server_filename') or 
                   info.get('filename') or 
                   os.path.basename(lookup_path) or 
                   'unknown')
        is_dir = info.get('isdir', 0) == 1
        
        # Show what will be renamed
        file_type = "directory" if is_dir else "file"
        print(f"Renaming {file_type}: '{old_name}' -> '{new_name}'")
        
        # Rename the file or directory
        if self.client.rename_file(old_path, new_name):
            print(f"Successfully renamed '{old_name}' to '{new_name}'")
        else:
            print(f"Error: Failed to rename '{old_path}'")
    
    def cmd_du(self, args):
        """Show disk usage: du [path] [-s]"""
        # Parse flags
        summary_only = False
        path_args = []
        
        for arg in args:
            if arg in ['-s', '--summary']:
                summary_only = True
            elif arg in ['-h', '--human-readable']:
                # Already using human-readable format by default
                pass
            elif not arg.startswith('-'):
                path_args.append(arg)
        
        # Determine target path
        if len(path_args) == 0:
            target_path = self.current_path
        else:
            target_path = self._resolve_path(path_args[0])
        
        # Normalize path
        target_path = target_path.rstrip('/')
        if not target_path:
            target_path = "/"
        else:
            target_path = target_path + "/"
        
        # Get all files recursively
        all_files = self.client.list_all_files_recursive(path=target_path.rstrip('/'))
        if all_files is None:
            print(f"Error: Cannot access directory '{target_path.rstrip('/')}'")
            return
        
        if not all_files:
            print(f"Directory '{target_path.rstrip('/')}' is empty")
            return
        
        # Calculate sizes: directory size = sum of all files in it and subdirectories
        dir_sizes = {}
        file_sizes = {}
        
        # First, collect all files and their sizes
        for item in all_files:
            path = item.get('path', '')
            size = item.get('size', 0)
            isdir = item.get('isdir', 0)
            
            if isdir == 1:
                # Directory - initialize size to 0
                if path not in dir_sizes:
                    dir_sizes[path] = 0
            else:
                # File
                file_sizes[path] = size
                # Add file size to all parent directories
                parts = path.rstrip('/').split('/')
                for i in range(1, len(parts) + 1):
                    if i == len(parts):
                        # Root directory
                        parent_path = "/"
                    else:
                        parent_path = '/'.join(parts[:i])
                        if not parent_path:
                            parent_path = "/"
                        else:
                            parent_path = parent_path + "/"
                    
                    # Ensure parent is within target path
                    if parent_path.startswith(target_path) or parent_path == target_path:
                        if parent_path not in dir_sizes:
                            dir_sizes[parent_path] = 0
                        dir_sizes[parent_path] += size
        
        if summary_only:
            # Show only total size
            total_size = dir_sizes.get(target_path, 0)
            print(f"{self._format_size(total_size)}\t{target_path.rstrip('/')}")
        else:
            # Show detailed sizes
            print(f"\nDisk Usage for: {target_path.rstrip('/')}")
            print("-" * 80)
            print(f"{'Size':<12} {'Path'}")
            print("-" * 80)
            
            # Collect all items (files and directories) with their sizes
            items = []
            
            # Add files
            for path, size in file_sizes.items():
                if path.startswith(target_path):
                    rel_path = path[len(target_path):] if path != target_path else os.path.basename(path)
                    items.append((size, rel_path, False))
            
            # Add directories (excluding the target directory itself)
            for path, size in dir_sizes.items():
                if path.startswith(target_path) and path != target_path:
                    rel_path = path[len(target_path):] if path != target_path else os.path.basename(path)
                    if rel_path:
                        items.append((size, rel_path, True))
            
            # Sort by size (largest first)
            items.sort(key=lambda x: x[0], reverse=True)
            
            # Display items
            for size, rel_path, is_dir in items:
                display_path = rel_path + "/" if is_dir else rel_path
                print(f"{self._format_size(size):<12} {display_path}")
            
            # Show total
            total_size = dir_sizes.get(target_path, 0)
            print("-" * 80)
            print(f"{self._format_size(total_size):<12} {target_path.rstrip('/')} (total)")
    
    def _read_file_content(self, file_path, max_lines=None, from_end=False):
        """
        Download file to temp location, read content, then delete
        
        Args:
            file_path: Remote file path
            max_lines: Maximum number of lines to read (None for all)
            from_end: If True and max_lines is set, read from end (for tail)
            
        Returns:
            List of lines, or None if error
        """
        import tempfile
        
        target_path = self._resolve_path(file_path)
        fsid = self.client.get_fsid_by_path(target_path.rstrip("/"))
        if not fsid:
            return None
        
        meta_list = self.client.get_file_info([fsid])
        if not meta_list or len(meta_list) == 0:
            return None
        
        info = meta_list[0]
        if info.get('isdir', 0) == 1:
            return None  # Cannot read directory
        
        # Create temporary file
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='w+b') as tmp_file:
                tmp_path = tmp_file.name
            
            # Download file to temp location
            if not self.client.download_file_by_path(target_path, tmp_path, show_progress=False):
                return None
            
            # Read file content
            try:
                with open(tmp_path, 'rb') as f:
                    content = f.read()
                
                # Try to decode as text
                try:
                    # Try UTF-8 first
                    text = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        # Try other common encodings
                        text = content.decode('gbk')
                    except UnicodeDecodeError:
                        # If all fail, show as binary
                        return None
                
                lines = text.splitlines()
                
                # Apply line limits
                if max_lines is not None:
                    if from_end:
                        lines = lines[-max_lines:]
                    else:
                        lines = lines[:max_lines]
                
                return lines
            finally:
                # Always delete temp file
                try:
                    os.remove(tmp_path)
                except:
                    pass
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def cmd_cat(self, args):
        """Show file info and content: cat <path>"""
        if len(args) == 0:
            print("Usage: cat <path>")
            return
        
        target_path = self._resolve_path(args[0])
        fsid = self.client.get_fsid_by_path(target_path.rstrip("/"))
        if not fsid:
            print(f"Error: File or directory '{target_path}' not found")
            return
        
        meta_list = self.client.get_file_info([fsid], detail=1)
        if not meta_list or len(meta_list) == 0:
            print(f"Error: Cannot get info for '{target_path}'")
            return
        
        info = meta_list[0]
        is_dir = info.get('isdir', 0) == 1
        
        # Show file information
        print(f"\nFile Information:")
        print("-" * 60)
        print(f"Name:        {info.get('server_filename', 'N/A')}")
        print(f"Path:        {target_path}")
        print(f"Type:        {'Directory' if is_dir else 'File'}")
        if not is_dir:
            print(f"Size:        {self._format_size(info.get('size', 0))}")
        print(f"MD5:         {info.get('md5', 'N/A')}")
        print(f"Created:     {self._format_time(info.get('server_ctime', 0))}")
        print(f"Modified:    {self._format_time(info.get('server_mtime', 0))}")
        print(f"FS ID:       {info.get('fs_id', 'N/A')}")
        if 'category' in info:
            print(f"Category:    {info.get('category', 'N/A')}")
        print("-" * 60)
        
        # Show file content if it's a file
        if not is_dir:
            print(f"\nFile Content:")
            print("-" * 60)
            lines = self._read_file_content(target_path)
            if lines is None:
                print("Error: Cannot read file content (may be binary or too large)")
            else:
                for line in lines:
                    print(line)
            print("-" * 60)
    
    def cmd_head(self, args):
        """Show first N lines of file: head [-n N] <path>"""
        if len(args) == 0:
            print("Usage: head [-n N] <path>")
            print("       Default: show first 10 lines")
            return
        
        # Parse arguments
        num_lines = 10
        path_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '-n' and i + 1 < len(args):
                try:
                    num_lines = int(args[i + 1])
                    i += 2
                    continue
                except ValueError:
                    print(f"Error: Invalid number of lines: {args[i + 1]}")
                    return
            elif arg.startswith('-n'):
                # Handle -n10 format
                try:
                    num_lines = int(arg[2:])
                    i += 1
                    continue
                except ValueError:
                    print(f"Error: Invalid number of lines: {arg[2:]}")
                    return
            elif not arg.startswith('-'):
                path_args.append(arg)
            i += 1
        
        if len(path_args) == 0:
            print("Usage: head [-n N] <path>")
            return
        
        target_path = self._resolve_path(path_args[0])
        lines = self._read_file_content(target_path, max_lines=num_lines, from_end=False)
        
        if lines is None:
            print(f"Error: Cannot read file '{target_path}'")
            return
        
        for line in lines:
            print(line)
    
    def cmd_tail(self, args):
        """Show last N lines of file: tail [-n N] <path>"""
        if len(args) == 0:
            print("Usage: tail [-n N] <path>")
            print("       Default: show last 10 lines")
            return
        
        # Parse arguments
        num_lines = 10
        path_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '-n' and i + 1 < len(args):
                try:
                    num_lines = int(args[i + 1])
                    i += 2
                    continue
                except ValueError:
                    print(f"Error: Invalid number of lines: {args[i + 1]}")
                    return
            elif arg.startswith('-n'):
                # Handle -n10 format
                try:
                    num_lines = int(arg[2:])
                    i += 1
                    continue
                except ValueError:
                    print(f"Error: Invalid number of lines: {arg[2:]}")
                    return
            elif not arg.startswith('-'):
                path_args.append(arg)
            i += 1
        
        if len(path_args) == 0:
            print("Usage: tail [-n N] <path>")
            return
        
        target_path = self._resolve_path(path_args[0])
        lines = self._read_file_content(target_path, max_lines=num_lines, from_end=True)
        
        if lines is None:
            print(f"Error: Cannot read file '{target_path}'")
            return
        
        for line in lines:
            print(line)
    
    def _read_csv_file(self, file_path, max_rows=None):
        """
        Download CSV file to temp location, read with csv module, then delete
        
        Args:
            file_path: Remote CSV file path
            max_rows: Maximum number of rows to display (None for all)
            
        Returns:
            Tuple of (list of dicts, total_rows), or (None, None) if error
        """
        import tempfile
        import csv
        
        target_path = self._resolve_path(file_path)
        fsid = self.client.get_fsid_by_path(target_path.rstrip("/"))
        if not fsid:
            return None, None
        
        meta_list = self.client.get_file_info([fsid])
        if not meta_list or len(meta_list) == 0:
            return None, None
        
        info = meta_list[0]
        if info.get('isdir', 0) == 1:
            return None, None  # Cannot read directory
        
        # Create temporary file
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='w+b', suffix='.csv') as tmp_file:
                tmp_path = tmp_file.name
            
            # Download file to temp location
            if not self.client.download_file_by_path(target_path, tmp_path, show_progress=False):
                return None, None
            
            # Read CSV with csv module
            try:
                # Try different encodings
                data = None
                headers = None
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                
                for encoding in encodings:
                    try:
                        with open(tmp_path, 'r', encoding=encoding, newline='') as f:
                            reader = csv.DictReader(f)
                            headers = reader.fieldnames
                            data = list(reader)
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        # Other errors (like parsing errors) - try next encoding
                        continue
                
                if data is None or headers is None:
                    return None, None
                
                total_rows = len(data)
                
                # Limit rows if specified
                if max_rows is not None and len(data) > max_rows:
                    data = data[:max_rows]
                
                return {'data': data, 'headers': headers}, total_rows
            finally:
                # Always delete temp file
                try:
                    os.remove(tmp_path)
                except:
                    pass
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return None, None
    
    def cmd_rcsv(self, args):
        """Read and display CSV file: rcsv [-n N] [-c] [-s col1,col2,...] <path>"""
        if len(args) == 0:
            print("Usage: rcsv [-n N] [-c] [-s col1,col2,...] <path>")
            print("       -n N: Show first N rows (default: all rows)")
            print("       -c, --columns: Show column names only")
            print("       -s, --select: Select specific columns (comma-separated)")
            print("       Example: rcsv -n 10 -s name,age,email data.csv")
            return
        
        # Parse arguments
        max_rows = None
        show_columns_only = False
        select_columns = None
        path_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ['-c', '--columns']:
                show_columns_only = True
                i += 1
                continue
            elif arg in ['-s', '--select']:
                if i + 1 < len(args):
                    select_columns = [col.strip() for col in args[i + 1].split(',')]
                    i += 2
                    continue
                else:
                    print("Error: -s/--select requires column names (comma-separated)")
                    return
            elif arg == '-n' and i + 1 < len(args):
                try:
                    max_rows = int(args[i + 1])
                    i += 2
                    continue
                except ValueError:
                    print(f"Error: Invalid number of rows: {args[i + 1]}")
                    return
            elif arg.startswith('-n'):
                # Handle -n10 format
                try:
                    max_rows = int(arg[2:])
                    i += 1
                    continue
                except ValueError:
                    print(f"Error: Invalid number of rows: {arg[2:]}")
                    return
            elif not arg.startswith('-'):
                path_args.append(arg)
            i += 1
        
        if len(path_args) == 0:
            print("Usage: rcsv [-n N] [-c] [-s col1,col2,...] <path>")
            return
        
        target_path = self._resolve_path(path_args[0])
        
        # Check if file exists
        fsid = self.client.get_fsid_by_path(target_path.rstrip("/"))
        if not fsid:
            print(f"Error: File '{target_path}' not found")
            return
        
        # Read CSV file (read all rows first to get all columns, then filter)
        result, total_rows = self._read_csv_file(target_path, max_rows=None)
        
        if result is None:
            print(f"Error: Cannot read CSV file '{target_path}'")
            print("       Make sure the file is a valid CSV file")
            return
        
        data = result['data']
        headers = result['headers']
        
        # Show columns only mode
        if show_columns_only:
            print(f"\nCSV File: {target_path}")
            print("-" * 80)
            print(f"Total columns: {len(headers)}")
            print("-" * 80)
            print("Columns:")
            for idx, col in enumerate(headers, 1):
                print(f"  {idx}. {col}")
            print("-" * 80)
            return
        
        # Filter columns if specified
        if select_columns:
            # Check if all specified columns exist
            missing_cols = [col for col in select_columns if col not in headers]
            if missing_cols:
                print(f"Error: Column(s) not found: {', '.join(missing_cols)}")
                print(f"Available columns: {', '.join(headers)}")
                return
            # Filter data to only include selected columns
            filtered_data = []
            for row in data:
                filtered_row = {col: row.get(col, '') for col in select_columns}
                filtered_data.append(filtered_row)
            data = filtered_data
            headers = select_columns
        
        # Limit rows if specified
        if max_rows is not None and len(data) > max_rows:
            data = data[:max_rows]
            actual_rows = max_rows
        else:
            actual_rows = len(data)
        
        # Display CSV content
        print(f"\nCSV File: {target_path}")
        print("-" * 80)
        
        # Show basic info
        print(f"Shape: {actual_rows} rows × {len(headers)} columns")
        if max_rows is not None and actual_rows < total_rows:
            print(f"Showing first {actual_rows} of {total_rows} rows")
        if select_columns:
            print(f"Selected columns: {', '.join(select_columns)}")
        print("-" * 80)
        
        # Display CSV using tabulate for better table formatting
        from tabulate import tabulate
        
        # Convert data to list of lists for tabulate
        table_data = []
        for idx, row in enumerate(data):
            row_values = [str(row.get(col, '')) if row.get(col) is not None else '' for col in headers]
            table_data.append([idx] + row_values)
        
        # Use grid format for better readability
        print(tabulate(table_data, headers=['Index'] + headers, tablefmt='grid', 
                      maxcolwidths=[8] + [30] * len(headers)))
        print("-" * 80)
    
    def cmd_help(self, args):
        """Show help: help [command]"""
        commands = {
            "cd": "Change directory: cd [path] (supports 'cd ..' for parent directory)",
            "ls": "List files: ls [path] [-s] (supports wildcards: *, ?; -s: show directory sizes)",
            "pwd": "Print working directory: pwd",
            "du": "Show disk usage: du [path] [-s] (show directory and file sizes)",
            "mkdir": "Create directory: mkdir <path>",
            "upload": "Upload file or directory: upload <local_path> [remote_path]",
            "download": "Download file or directory: download <remote_path> [local_path]",
            "mv": "Rename file or directory: mv <old_path> <new_name> (supports wildcards: *, ?)",
            "cat": "Show file information and content: cat <path>",
            "head": "Show first N lines: head [-n N] <path> (default: 10 lines)",
            "tail": "Show last N lines: tail [-n N] <path> (default: 10 lines)",
            "rcsv": "Read and display CSV file: rcsv [-n N] [-c] [-s col1,col2,...] <path> (like SQL SELECT)",
            "whoami": "Show user and quota information: whoami",
            "clear": "Clear screen: clear",
            "help": "Show help: help [command]",
            "exit": "Exit shell: exit or quit",
            "quit": "Exit shell: exit or quit",
        }
        
        if len(args) == 0:
            print("\nAvailable commands:")
            print("-" * 60)
            for cmd, desc in sorted(commands.items()):
                print(f"  {cmd:<12} {desc}")
            print("-" * 60)
        else:
            cmd = args[0]
            if cmd in commands:
                print(commands[cmd])
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' to see all available commands")
    
    def cmd_exit(self, args):
        """Exit shell: exit or quit"""
        self.running = False
        print("Goodbye!")
    
    def cmd_quit(self, args):
        """Exit shell: exit or quit"""
        self.cmd_exit(args)
    
    def cmd_clear(self, args):
        """Clear screen: clear"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def cmd_whoami(self, args):
        """Show user information: whoami"""
        user_info = self.client.get_user_info()
        if user_info:
            print("\nUser Information:")
            print("-" * 60)
            print(f"Username:    {user_info.get('uname', 'N/A')}")
            print(f"User ID:     {user_info.get('uk', 'N/A')}")
            print(f"Avatar URL:  {user_info.get('avatar_url', 'N/A')}")
            print("-" * 60)
        else:
            print("Error: Cannot get user information")
        
        quota = self.client.get_quota()
        if quota:
            total = quota.get('total', 0)
            used = quota.get('used', 0)
            free = total - used
            print("\nQuota Information:")
            print("-" * 60)
            print(f"Total:       {self._format_size(total)}")
            print(f"Used:        {self._format_size(used)} ({used/total*100:.2f}%)" if total > 0 else f"Used:        {self._format_size(used)}")
            print(f"Free:        {self._format_size(free)}")
            print("-" * 60)
    
    def _get_commands(self):
        """Get list of available commands"""
        return [
            'cd', 'ls', 'pwd', 'du', 'mkdir', 'upload', 'download',
            'mv', 'cat', 'head', 'tail', 'rcsv', 'whoami',
            'clear', 'help', 'exit', 'quit'
        ]
    
    def _completer(self, text, state):
        """
        Tab completion function - only for commands
        
        Args:
            text: Text to complete
            state: Completion state (0, 1, 2, ...)
            
        Returns:
            Completion string or None
        """
        if not READLINE_AVAILABLE:
            return None
        
        # Get the current line
        line = readline.get_line_buffer()
        # Get the beginning position of the text being completed
        begidx = readline.get_begidx()
        
        # Split the line into parts (only the part before cursor)
        before_cursor = line[:begidx]
        
        # Try to split by spaces, but preserve quoted strings
        try:
            words = shlex.split(before_cursor)
        except ValueError:
            # If parsing fails, use simple split
            words = before_cursor.split()
        
        # Only complete commands (first word)
        if len(words) == 0:
            # No words yet, complete commands
            commands = [cmd for cmd in self._get_commands() if cmd.startswith(text)]
            if state < len(commands):
                return commands[state]
            return None
        elif len(words) == 1:
            # First word (command) - complete it
            if before_cursor.endswith(' '):
                # Command is complete, no completion needed
                return None
            else:
                # Completing the command
                commands = [c for c in self._get_commands() if c.startswith(text)]
                if state < len(commands):
                    return commands[state]
                return None
        
        # For arguments, no completion
        return None
    
    def _setup_completion(self):
        """Setup tab completion for commands only"""
        if not READLINE_AVAILABLE:
            return
        
        try:
            # Set completion function
            readline.set_completer(self._completer)
            # Use tab for completion
            readline.parse_and_bind("tab: complete")
        except Exception:
            # If setup fails, just continue without completion
            pass
    
    def _execute_command(self, line):
        """
        Execute a single command line
        
        Args:
            line: Command line string
            
        Returns:
            True if command was executed successfully, False otherwise
        """
        if not line or not line.strip():
            return True
        
        # Skip comments (lines starting with #)
        line = line.strip()
        if line.startswith('#'):
            return True
        
        # Parse command
        try:
            parts = shlex.split(line)
            if not parts:
                return True
            
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Handle exit/quit commands
            if cmd in ['exit', 'quit']:
                self.running = False
                return False
            
            # Execute command
            method_name = f"cmd_{cmd}"
            if hasattr(self, method_name):
                try:
                    getattr(self, method_name)(args)
                    return True
                except Exception as e:
                    print(f"Error executing command '{line}': {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
                return False
        except Exception as e:
            print(f"Error parsing command '{line}': {e}")
            return False
    
    def run_script(self, script_path):
        """
        Execute a batch script file
        
        Args:
            script_path: Path to the .bdnd script file
        """
        if not os.path.exists(script_path):
            print(f"Error: Script file '{script_path}' not found")
            return
        
        print(f"Executing script: {script_path}")
        print("-" * 80)
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_count = 0
            error_count = 0
            
            for line_num, line in enumerate(lines, 1):
                line_count += 1
                # Remove trailing newline and whitespace
                line = line.rstrip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Show command being executed (with line number)
                print(f"[{line_num}] {line}")
                
                # Execute command
                if not self._execute_command(line):
                    # Command requested exit
                    print(f"\nScript execution stopped at line {line_num}")
                    break
                
                # Check if shell was stopped
                if not self.running:
                    break
                
                print()  # Empty line for readability
            
            print("-" * 80)
            print(f"Script execution completed: {line_count} lines processed")
            if error_count > 0:
                print(f"Warnings: {error_count} errors encountered")
        
        except IOError as e:
            print(f"Error reading script file: {e}")
        except Exception as e:
            print(f"Error executing script: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Run interactive shell"""
        print("Baidu Netdisk Interactive Shell")
        print("Type 'help' for available commands, 'exit' or 'quit' to exit")
        print(f"Current directory: {self.current_path}\n")
        
        while self.running:
            try:
                # Get input
                prompt = f"bdnd:{self.current_path}> "
                try:
                    line = input(prompt).strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break
                
                if not line:
                    continue
                
                # Execute command
                self._execute_command(line)
                
                print()  # Empty line for readability
                
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()

