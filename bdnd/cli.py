"""Command Line Interface for Baidu Netdisk Client"""

import argparse
import os
import sys
from .client import BaiduNetdiskClient


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
        'paths', nargs=2,
        help='Two paths: upload <local> <remote> or download <remote> <local>'
    )

    args = parser.parse_args()

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

