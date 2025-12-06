"""Command Line Interface for Baidu Netdisk Client"""

import argparse
import os
import sys
from .client import BaiduNetdiskClient
from .shell import BaiduNetdiskShell


def main():
    parser = argparse.ArgumentParser(description="Baidu Netdisk Command Line Client")
    parser.add_argument(
        "--access-token", type=str, default=os.environ.get("baidu_netdisk_access_token", None),
        help="Baidu Netdisk access token (default: from environment variable baidu_netdisk_access_token)"
    )
    parser.add_argument(
        "--mode", type=str, choices=["upload", "download"], default=None,
        help="Operation mode: 'upload' or 'download'. If not specified, will auto-detect from paths."
    )
    parser.add_argument(
        "--set-home", "--set_home", type=str, metavar="PATH", default=None,
        dest="set_home",
        help="Set default base path for relative paths (saved to environment variable 'baidu_netdisk_base_path')"
    )
    parser.add_argument(
        "--show-home", "--show_home", action="store_true",
        dest="show_home",
        help="Show current default base path setting"
    )
    parser.add_argument(
        'paths', nargs='*',
        help='Two paths: upload <local> <remote> or download <remote> <local>. If not provided, enter interactive mode.'
    )

    args = parser.parse_args()
    
    # Handle --set-home option
    if args.set_home is not None:
        from .config import set_base_path
        # Normalize path
        home_path = args.set_home.strip()
        if not home_path.startswith("/"):
            home_path = "/" + home_path
        if home_path != "/" and not home_path.endswith("/"):
            home_path = home_path + "/"
        # Save to config file
        if set_base_path(home_path):
            print(f"Default base path set to: {home_path}")
            print("Note: This setting will be used for relative paths in future operations.")
        else:
            print("Error: Failed to save configuration")
            sys.exit(1)
        return
    
    # Handle --show-home option
    if args.show_home:
        from .config import get_base_path
        home_path = get_base_path()
        if home_path == "/":
            print("Default base path: / (root)")
        else:
            print(f"Default base path: {home_path}")
        return
    
    # If no paths provided, enter interactive mode
    if len(args.paths) == 0:
        access_token = args.access_token
        if not access_token:
            print("Error: access token must be provided by --access-token or environment variable 'baidu_netdisk_access_token'.")
            sys.exit(1)
        
        client = BaiduNetdiskClient(access_token=access_token)
        shell = BaiduNetdiskShell(client)
        shell.run()
        return
    
    # Check if script file is provided
    if len(args.paths) == 1:
        script_path = args.paths[0]
        # Check if it's a .bdnd script file
        if script_path.endswith('.bdnd') or os.path.exists(script_path):
            if not os.path.exists(script_path):
                print(f"Error: Script file '{script_path}' not found")
                sys.exit(1)
            
            access_token = args.access_token
            if not access_token:
                print("Error: access token must be provided by --access-token or environment variable 'baidu_netdisk_access_token'.")
                sys.exit(1)
            
            client = BaiduNetdiskClient(access_token=access_token)
            shell = BaiduNetdiskShell(client)
            shell.run_script(script_path)
            return
    
    # Original command-line mode requires 2 paths
    if len(args.paths) != 2:
        print("Error: Command-line mode requires 2 paths, or use interactive mode by running 'bdnd' without arguments")
        print("       Or provide a .bdnd script file: bdnd script.bdnd")
        sys.exit(1)

    access_token = args.access_token
    if not access_token:
        print("Error: access token must be provided by --access-token or environment variable 'baidu_netdisk_access_token'.")
        sys.exit(1)

    client = BaiduNetdiskClient(access_token)
    
    path1, path2 = args.paths
    
    def is_remote_path(path):
        return path.startswith('/') and not os.path.exists(path)
    
    def is_local_path(path):
        return os.path.exists(path)
    
    def is_remote_dir(path, client_ref):
        """Check if remote path is a directory (ends with / or exists as directory)"""
        if path.endswith('/'):
            return True
        # Try to check if it's a directory on remote
        fsid = client_ref.get_fsid_by_path(path.rstrip('/'))
        if fsid:
            meta_list = client_ref.get_file_info([fsid])
            if meta_list and len(meta_list) > 0:
                return meta_list[0].get('isdir', 0) == 1
        return False
    
    def is_local_dir(path):
        """Check if local path is a directory"""
        return os.path.isdir(path) if os.path.exists(path) else path.endswith(os.sep) or path.endswith('/')
    
    # Determine operation mode
    if args.mode:
        # Use explicit mode if provided
        if args.mode == "upload":
            local = path1
            remote = path2
            
            if os.path.isdir(local):
                # Source is directory
                if remote.endswith('/') or is_remote_dir(remote, client):
                    # Target is directory: copy directory contents to target
                    client.upload_directory(local, remote, recursive=True)
                else:
                    # Target is file path: error (cannot copy directory to file)
                    print(f"Error: Cannot copy directory '{local}' to file path '{remote}'")
                    sys.exit(1)
            else:
                # Source is file
                if remote.endswith('/') or is_remote_dir(remote, client):
                    # Target is directory: copy file to directory
                    file_name = os.path.basename(local)
                    remote_file = remote.rstrip('/') + '/' + file_name
                    client.upload_file_auto(local, remote_file)
                else:
                    # Target is file path: copy and rename
                    client.upload_file_auto(local, remote)
                    
        elif args.mode == "download":
            remote = path1
            local = path2
            
            fsid = client.get_fsid_by_path(remote.rstrip('/'))
            if fsid:
                meta_list = client.get_file_info([fsid])
                if meta_list and len(meta_list) > 0:
                    is_dir = meta_list[0].get('isdir', 0) == 1
                else:
                    is_dir = False
            else:
                is_dir = remote.endswith('/')
            
            if is_dir:
                # Source is directory
                if os.path.isdir(local) if os.path.exists(local) else local.endswith(os.sep) or local.endswith('/'):
                    # Target is directory: copy directory contents to target
                    client.download_directory(remote, local, recursive=True)
                else:
                    # Target is file path: error (cannot copy directory to file)
                    print(f"Error: Cannot copy directory '{remote}' to file path '{local}'")
                    sys.exit(1)
            else:
                # Source is file
                if os.path.isdir(local) if os.path.exists(local) else local.endswith(os.sep) or local.endswith('/'):
                    # Target is directory: copy file to directory
                    file_name = os.path.basename(remote.rstrip('/'))
                    local_file = os.path.join(local.rstrip(os.sep), file_name)
                    client.download_file_by_path(remote, local_file)
                else:
                    # Target is file path: copy and rename
                    client.download_file_by_path(remote, local)
    else:
        # Auto-detect mode from paths
        if is_local_path(path1) and is_remote_path(path2):
            local = path1
            remote = path2
            
            if os.path.isdir(local):
                # Source is directory
                if remote.endswith('/') or is_remote_dir(remote, client):
                    # Target is directory: copy directory contents to target
                    client.upload_directory(local, remote, recursive=True)
                else:
                    # Target is file path: error
                    print(f"Error: Cannot copy directory '{local}' to file path '{remote}'")
                    sys.exit(1)
            else:
                # Source is file
                if remote.endswith('/') or is_remote_dir(remote, client):
                    # Target is directory: copy file to directory
                    file_name = os.path.basename(local)
                    remote_file = remote.rstrip('/') + '/' + file_name
                    client.upload_file_auto(local, remote_file)
                else:
                    # Target is file path: copy and rename
                    client.upload_file_auto(local, remote)
                    
        elif is_remote_path(path1) and is_local_path(path2):
            remote = path1
            local = path2
            
            fsid = client.get_fsid_by_path(remote.rstrip('/'))
            if fsid:
                meta_list = client.get_file_info([fsid])
                if meta_list and len(meta_list) > 0:
                    is_dir = meta_list[0].get('isdir', 0) == 1
                else:
                    is_dir = False
            else:
                is_dir = remote.endswith('/')
            
            if is_dir:
                # Source is directory
                if os.path.isdir(local) if os.path.exists(local) else local.endswith(os.sep) or local.endswith('/'):
                    # Target is directory: copy directory contents to target
                    client.download_directory(remote, local, recursive=True)
                else:
                    # Target is file path: error
                    print(f"Error: Cannot copy directory '{remote}' to file path '{local}'")
                    sys.exit(1)
            else:
                # Source is file
                if os.path.isdir(local) if os.path.exists(local) else local.endswith(os.sep) or local.endswith('/'):
                    # Target is directory: copy file to directory
                    file_name = os.path.basename(remote.rstrip('/'))
                    local_file = os.path.join(local.rstrip(os.sep), file_name)
                    client.download_file_by_path(remote, local_file)
                else:
                    # Target is file path: copy and rename
                    client.download_file_by_path(remote, local)
        else:
            print("Error: Cannot determine operation mode. Please provide --mode or use:")
            print("  Upload: <local_path> <remote_path> (remote path must start with /)")
            print("  Download: <remote_path> <local_path> (remote path must start with /)")
            sys.exit(1)


if __name__ == "__main__":
    main()

