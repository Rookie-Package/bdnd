"""Baidu Netdisk Client Implementation"""

import time
import requests
import urllib3
import ssl
from tqdm import tqdm
import json
import hashlib
import os
from urllib.parse import quote, urlencode
try:
    from env_key_manager import APIKeyManager
except ImportError:
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "env-key-manager"])
        from env_key_manager import APIKeyManager
    except Exception as e:
        raise ImportError(
            "env-key-manager module not found and automatic installation failed. Please install it manually with: pip install env-key-manager"
        ) from e

key_manager = APIKeyManager()
key_manager.setup_api_key(["baidu_netdisk_access_token"])

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaiduNetdiskClient:
    def __init__(self, access_token=None, base_path=None):
        """
        Initialize Baidu Netdisk Client
        
        Args:
            access_token: Baidu Netdisk access token. If None, will try to get from environment variable 'baidu_netdisk_access_token'
            base_path: Base path for relative paths. If None, will try to get from config file, then environment variable 'baidu_netdisk_base_path', or default to "/"
        """
        # Get access_token from parameter or environment variable
        if access_token is None:
            access_token = os.environ.get("baidu_netdisk_access_token", None)
        self.access_token = access_token
        
        # Get base_path from parameter, config file, environment variable, or default to "/"
        if base_path is None:
            # Try to load from config file first
            try:
                from .config import get_base_path
                base_path = get_base_path()
            except ImportError:
                # Fallback to environment variable
                base_path = os.environ.get("baidu_netdisk_base_path", "/")
        # Ensure base_path starts with / and ends with / if not root
        if not base_path.startswith("/"):
            base_path = "/" + base_path
        if base_path != "/" and not base_path.endswith("/"):
            base_path = base_path + "/"
        self.base_path = base_path

    def set_access_token(self, access_token):
        self.access_token = access_token
    
    def set_base_path(self, base_path):
        """Set base path for relative paths"""
        if not base_path.startswith("/"):
            base_path = "/" + base_path
        if base_path != "/" and not base_path.endswith("/"):
            base_path = base_path + "/"
        self.base_path = base_path
    
    def _sanitize_url(self, url):
        """Remove sensitive information (like access_token) from URL for logging"""
        if not url or not isinstance(url, str):
            return url
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            # Remove access_token from query parameters
            if 'access_token' in query_params:
                query_params['access_token'] = ['***REDACTED***']
            # Rebuild URL without access_token
            new_query = urlencode(query_params, doseq=True)
            new_parsed = parsed._replace(query=new_query)
            return urlunparse(new_parsed)
        except Exception:
            # If parsing fails, try simple string replacement
            import re
            # Replace access_token=... with access_token=***REDACTED***
            sanitized = re.sub(r'access_token=[^&]*', 'access_token=***REDACTED***', url)
            return sanitized
    
    def _resolve_path(self, path):
        """
        Resolve relative path to absolute path.
        If path starts with '/', it's treated as absolute path.
        Otherwise, it's treated as relative to self.base_path.
        
        Args:
            path: Path to resolve (can be absolute or relative)
            
        Returns:
            Absolute path string
        """
        if not path:
            return self.base_path.rstrip("/") or "/"
        
        # If path starts with '/', it's absolute
        if path.startswith("/"):
            return path
        
        # Otherwise, it's relative to base_path
        # Remove leading './' if present
        if path.startswith("./"):
            path = path[2:]
        
        # Combine base_path and relative path
        base = self.base_path.rstrip("/") or "/"
        if base == "/":
            return "/" + path
        else:
            return base + "/" + path

    def _safe_request(self, method, url, max_retries=3, **kwargs):
        """Safe request with SSL error handling and retry"""
        ssl_configs = [{"verify": True}, {"verify": False}]
        
        # Disable proxy to avoid connection issues
        # Also disable system environment proxy settings
        proxies = {'http': None, 'https': None}
        
        # Remove any proxy-related environment variables for this request
        original_env = {}
        proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                         'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']
        for var in proxy_env_vars:
            if var in os.environ:
                original_env[var] = os.environ[var]
                del os.environ[var]
        
        try:
        for retry in range(max_retries):
            for ssl_config in ssl_configs:
                try:
                    response = requests.request(
                        method,
                        url,
                        timeout=(10, 60),
                            proxies=proxies,
                        **ssl_config,
                        **kwargs
                    )
                    response.raise_for_status()
                    return response
                    except requests.exceptions.SSLError as e:
                    if ssl_config == ssl_configs[-1] and retry < max_retries - 1:
                        time.sleep(2 ** retry)
                        continue
                        # Last attempt failed
                        if retry == max_retries - 1:
                            print(f"Error: SSL connection failed: {e}")
                            print(f"  URL: {self._sanitize_url(url)}")
                            print("  Note: Tried with both SSL verification enabled and disabled")
                    except requests.exceptions.ProxyError as e:
                        print(f"Error: Proxy connection failed: {e}")
                        print(f"  URL: {self._sanitize_url(url)}")
                        print("  Note: Proxy has been disabled, but system may still be using proxy settings")
                        if retry < max_retries - 1:
                            time.sleep(2 ** retry)
                            continue
                    except requests.exceptions.ConnectionError as e:
                        print(f"Error: Connection failed: {e}")
                        print(f"  URL: {self._sanitize_url(url)}")
                        print("  Possible causes:")
                        print("    - Network connectivity issue")
                        print("    - Firewall blocking connection")
                        print("    - DNS resolution failure")
                        print("    - Proxy settings interfering")
                        if retry < max_retries - 1:
                            time.sleep(2 ** retry)
                            continue
                    except requests.exceptions.Timeout as e:
                        print(f"Error: Request timeout: {e}")
                        print(f"  URL: {self._sanitize_url(url)}")
                        if retry < max_retries - 1:
                            time.sleep(2 ** retry)
                            continue
                    except requests.exceptions.RequestException as e:
                        print(f"Error: Request failed: {e}")
                        print(f"  URL: {self._sanitize_url(url)}")
                    if retry < max_retries - 1:
                        time.sleep(2 ** retry)
                        continue
                    raise
        finally:
            # Restore original environment variables
            for var, value in original_env.items():
                os.environ[var] = value
        
        return None

    def get_user_info(self):
        """Get user info"""
        if not self.access_token:
            return None
        url = f"https://pan.baidu.com/rest/2.0/xpan/nas?access_token={self.access_token}&method=uinfo&vip_version=v2"
        headers = {'User-Agent': 'pan.baidu.com'}
        response = self._safe_request("GET", url, headers=headers, data={}, files={})
        if response:
            return response.json()
            return None

    def get_quota(self):
        """Get quota info"""
        if not self.access_token:
            return None
        url = f"https://pan.baidu.com/api/quota?access_token={self.access_token}&checkfree=1&checkexpire=1"
        headers = {'User-Agent': 'pan.baidu.com'}
        response = self._safe_request("GET", url, headers=headers, data={}, files={})
        if response:
            return response.json()
            return None

    def list_files(self, directory="/", order="time", start=0, limit=100, folder=0, desc=1):
        """Get file list"""
        if not self.access_token:
            return None
        # Resolve relative path
        directory = self._resolve_path(directory)
        url = (
            "https://pan.baidu.com/rest/2.0/xpan/file"
            "?method=list"
            f"&dir={directory}"
            f"&order={order}"
            f"&start={start}"
            f"&limit={limit}"
            f"&web=web"
            f"&folder={folder}"
            f"&access_token={self.access_token}"
            f"&desc={desc}"
        )
        headers = {'User-Agent': 'pan.baidu.com'}
        response = self._safe_request("GET", url, headers=headers, data={}, files={})
        if not response:
            return None
        
        try:
            result = response.json()
            # Check for API errors
            if result.get('errno') != 0 and result.get('errno') is not None:
                errno = result.get('errno')
                errmsg = result.get('errmsg', 'Unknown error')
                
                # Handle specific error codes
                if errno == -6:
                    # -6 usually means path doesn't exist or no permission
                    # For root directory, try to suggest a valid path
                    if directory == "/" or directory == "":
                        print(f"Error: Cannot access root directory '/' (errno={errno})")
                        print("Suggestion: Try setting a default path with: bdnd --set-home /apps/autodl")
                        print("Or use 'cd' command to navigate to a valid directory")
                    else:
                        print(f"Error: Cannot access directory '{directory}' (errno={errno}): {errmsg}")
                else:
                    print(f"Error: List files failed (errno={errno}): {errmsg}")
                return None
            # Return list of files
            file_list = result.get('list', [])
            return file_list if file_list else []
        except Exception as e:
            print(f"Error: Failed to parse response: {e}")
            return None

    def list_all_files_recursive(self, path="/", start=0, limit=1000, web=1, recursion=1):
        """Recursively get all files in path"""
        if not self.access_token:
            return None
        
        # Resolve relative path
        path = self._resolve_path(path)
        encoded_path = quote(path, safe='/')
        all_files = []
        current_start = start
        
        while True:
            url = (
                "https://pan.baidu.com/rest/2.0/xpan/multimedia"
                f"?method=listall"
                f"&path={encoded_path}"
                f"&access_token={self.access_token}"
                f"&web={web}"
                f"&recursion={recursion}"
                f"&start={current_start}"
                f"&limit={limit}"
            )
            
            headers = {'User-Agent': 'pan.baidu.com'}
            response = self._safe_request("GET", url, headers=headers, data={}, files={})
            
            if not response:
                break

            try:
                result = response.json()
                file_list = result.get('list', [])
                if not file_list:
                    break

                for item in file_list:
                    entry = {
                        "category": item.get("category"),
                        "fs_id": item.get("fs_id"),
                        "isdir": item.get("isdir"),
                        "local_ctime": item.get("local_ctime"),
                        "local_mtime": item.get("local_mtime"),
                        "md5": item.get("md5"),
                        "path": item.get("path"),
                        "server_ctime": item.get("server_ctime"),
                        "server_filename": item.get("server_filename"),
                        "server_mtime": item.get("server_mtime"),
                        "size": item.get("size"),
                    }
                    all_files.append(entry)

                has_more = result.get('has_more', 0)
                if has_more == 0:
                    break

                current_start += len(file_list)

            except (json.JSONDecodeError, Exception):
                break

        return all_files

    @staticmethod
    def build_authorize_url(client_id, redirect_uri="oob"):
        """Build authorize URL"""
        url = (
            f"https://openapi.baidu.com/oauth/2.0/authorize?"
            f"response_type=token&"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=basic,netdisk"
        )
        return "".join(url)

    def precreate(self, save_path, size, block_list, isdir=0, rtype=1, autoinit=1):
        """Precreate upload, return uploadid"""
        if not self.access_token:
            return None
        # Resolve relative path
        save_path = self._resolve_path(save_path)
        url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=precreate&access_token={self.access_token}"
        payload = {
            'path': save_path,
            'size': str(size),
            'rtype': str(rtype),
            'isdir': str(isdir),
            'autoinit': str(autoinit),
            'block_list': block_list if isinstance(block_list, str) else json.dumps(block_list)
        }
        headers = {'User-Agent': 'pan.baidu.com'}
        response = self._safe_request("POST", url, headers=headers, data=payload, files=[])
        if response:
            return response.json()
        return None

    def upload_file_auto(self, file_path, save_path, show_progress=True, file_pbar=None):
        """Upload file using chunked upload method: precreate -> upload chunks -> create file"""
        if not self.access_token:
            print("Error: Access token not set")
            return None

        try:
            # Resolve relative path
            save_path = self._resolve_path(save_path)
            file_name = os.path.basename(file_path)
            if save_path.endswith('/'):
                save_path = save_path + file_name

            def calc_md5(parts):
                md5s = []
                for part in parts:
                    m = hashlib.md5()
                    m.update(part)
                    md5s.append(m.hexdigest())
                return md5s

            block_size = 4 * 1024 * 1024
            blocks = []
            try:
                file_size = os.path.getsize(file_path)
                with open(file_path, "rb") as f:
                    while True:
                        part = f.read(block_size)
                        if not part:
                            break
                        blocks.append(part)
            except FileNotFoundError:
                print(f"Error: File not found: {file_path}")
                return None
            except PermissionError:
                print(f"Error: Permission denied: {file_path}")
                return None
            except Exception as e:
                print(f"Error: Failed to read file {file_path}: {e}")
                return None

            block_md5s = calc_md5(blocks)
            block_list_str = json.dumps(block_md5s)

            precreate_resp = self.precreate(save_path, file_size, block_list_str)
            if not precreate_resp:
                print(f"Error: Precreate request failed for {save_path}")
                return None
            if precreate_resp.get("errno") != 0:
                errno = precreate_resp.get("errno")
                errmsg = precreate_resp.get("errmsg", "Unknown error")
                print(f"Error: Precreate failed (errno={errno}): {errmsg}")
                return None
            uploadid = precreate_resp.get("uploadid")
            if not uploadid:
                print(f"Error: No uploadid returned from precreate")
                return None
        except Exception as e:
            print(f"Error: Unexpected error during upload preparation: {e}")
            import traceback
            traceback.print_exc()
            return None

        headers = {'User-Agent': 'pan.baidu.com'}
        total_blocks = len(blocks)
        file_name = os.path.basename(file_path)
        
        if file_pbar is not None:
            pbar = file_pbar
        elif show_progress:
            pbar = tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=file_name[:30],
                ncols=120,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'
            )
        else:
            pbar = None
        
        total_uploaded = 0
        start_time = time.time()
        
        try:
            for idx, part in enumerate(blocks):
                url = (
                    "https://c3.pcs.baidu.com/rest/2.0/pcs/superfile2"
                    f"?method=upload"
                    f"&access_token={self.access_token}"
                    f"&path={save_path}"
                    f"&type=tmpfile"
                    f"&uploadid={uploadid}"
                    f"&partseq={idx}"
                )
                files = [('file', (file_name, part))]
                
                # Use _safe_request for chunk upload
                resp = self._safe_request("POST", url, headers=headers, data={}, files=files)
                
                if not resp:
                    if pbar:
                        pbar.close()
                    print(f"Error: Failed to upload chunk {idx+1}/{total_blocks}")
                    return None
                
                part_size = len(part)
                total_uploaded += part_size
                if pbar:
                    pbar.update(part_size)
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        avg_speed = total_uploaded / elapsed_time
                        if file_pbar is None:
                            pbar.set_postfix({
                                'Chunk': f"{idx+1}/{total_blocks}",
                                'Speed': f"{self._format_size(avg_speed)}/s"
                            })
                        else:
                            pbar.set_postfix({'Speed': f"{self._format_size(avg_speed)}/s"})
        
            if pbar and file_pbar is None:
                pbar.close()

            url_create = "https://pan.baidu.com/rest/2.0/xpan/file?method=create"
            data = {
                "path": save_path,
                "size": str(file_size),
                "isdir": "0",
                "uploadid": uploadid,
                "block_list": block_list_str,
                "rtype": "1",
                "access_token": self.access_token
            }
            resp = self._safe_request("POST", url_create, data=data, headers=headers)
            if resp:
                result = resp.json()
                if result.get("errno") != 0:
                    errno = result.get("errno")
                    errmsg = result.get("errmsg", "Unknown error")
                    print(f"Error: Create file failed (errno={errno}): {errmsg}")
                    return None
                return result
            else:
                print(f"Error: Create file request failed for {save_path}")
                return None
        except KeyboardInterrupt:
            if pbar:
                pbar.close()
            print("\nError: Upload interrupted by user")
            return None
        except Exception as e:
            if pbar:
                pbar.close()
            print(f"Error: Unexpected error during upload: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_directory(self, dir_path):
        """Create directory on Baidu Netdisk"""
        if not self.access_token:
            return False
        
        # Resolve relative path
        dir_path = self._resolve_path(dir_path)
        url = "https://pan.baidu.com/rest/2.0/xpan/file?method=create"
        data = {
            "path": dir_path,
            "size": "0",
            "isdir": "1",
            "rtype": "1",
            "access_token": self.access_token
        }
        headers = {'User-Agent': 'pan.baidu.com'}
        
        response = self._safe_request("POST", url, headers=headers, data=data)
        if response:
            result = response.json()
            return result.get('errno') == 0
        return False

    def upload_directory(self, local_dir, remote_dir, recursive=True, file_filter=None):
        """Upload entire directory to Baidu Netdisk"""
        if not self.access_token:
            return 0
        
        if not os.path.isdir(local_dir):
            return 0
        
        local_dir = os.path.abspath(local_dir)
        
        # Resolve relative path
        remote_dir = self._resolve_path(remote_dir)
        if not remote_dir.endswith('/'):
            remote_dir += '/'
        
        remote_base_dir = remote_dir.rstrip('/')
        if remote_base_dir:
            self.create_directory(remote_base_dir)
        
        files_to_upload = []
        dirs_to_create = []
        
        if recursive:
            for root, dirs, files in os.walk(local_dir):
                rel_root = os.path.relpath(root, local_dir)
                if rel_root == '.':
                    rel_root = ''
                
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    rel_dir = os.path.join(rel_root, d).replace('\\', '/') if rel_root else d
                    remote_dir_path = remote_dir + rel_dir + '/'
                    dirs_to_create.append(remote_dir_path)
                
                for f in files:
                    file_path = os.path.join(root, f)
                    rel_file = os.path.join(rel_root, f).replace('\\', '/') if rel_root else f
                    remote_file_path = remote_dir + rel_file
                    files_to_upload.append((file_path, remote_file_path))
        else:
            for item in os.listdir(local_dir):
                item_path = os.path.join(local_dir, item)
                if os.path.isdir(item_path):
                    dirs_to_create.append(remote_dir + item + '/')
                elif os.path.isfile(item_path):
                    if file_filter is None or file_filter(item):
                        files_to_upload.append((item_path, remote_dir + item))
        
        created_dirs = set()
        unique_dirs = set(dirs_to_create)
        sorted_dirs = sorted(unique_dirs, key=lambda x: x.count('/'))
        
        if sorted_dirs:
            all_dirs_to_create = []
            for dir_path in sorted_dirs:
                parts = dir_path.rstrip('/').split('/')
                for i in range(1, len(parts) + 1):
                    parent_dir = '/'.join(parts[:i])
                    if i > 1:
                        parent_dir += '/'
                    if parent_dir not in created_dirs and parent_dir and parent_dir != '/':
                        clean_path = parent_dir.rstrip('/')
                        if clean_path and clean_path not in all_dirs_to_create:
                            all_dirs_to_create.append(clean_path)
                            created_dirs.add(parent_dir)
            
            if all_dirs_to_create:
                dir_pbar = tqdm(
                    total=len(all_dirs_to_create),
                    desc="Creating directories",
                    unit="dir",
                    ncols=120,
                    bar_format='{desc}: {percentage:3.0f}%|{bar}| {n}/{total} [{elapsed}<{remaining}]'
                )
                
                for dir_path in all_dirs_to_create:
                    self.create_directory(dir_path)
                    dir_pbar.update(1)
                
                dir_pbar.close()
        
        if file_filter:
            files_to_upload = [(f, r) for f, r in files_to_upload if file_filter(os.path.basename(f))]
        
        total_files = len(files_to_upload)
        if total_files == 0:
            return 0
        
        success_count = 0
        pbar = tqdm(
            total=total_files, 
            desc="Uploading", 
            unit="file", 
            ncols=120,
            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n} [{elapsed}<{remaining}{postfix}]'
        )
        start_time = time.time()
        total_uploaded = 0
        
        for local_file, remote_file in files_to_upload:
            file_name = os.path.basename(local_file)
            file_size = os.path.getsize(local_file)
            
            pbar.set_description(f"Uploading {file_name[:25]} ({self._format_size(file_size)})")
            
            file_pbar = tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=f"{file_name[:25]}:",
                ncols=120,
                position=1,
                leave=False,
                bar_format='{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            )
            
            try:
                result = self.upload_file_auto(local_file, remote_file, show_progress=False, file_pbar=file_pbar)
                if result:
                    success_count += 1
                    total_uploaded += file_size
                else:
                    print(f"Warning: Failed to upload {file_name}")
            except Exception as e:
                print(f"Error: Exception while uploading {file_name}: {e}")
                import traceback
                traceback.print_exc()
            
            file_pbar.close()
            pbar.update(1)
            
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                avg_speed = total_uploaded / elapsed_time
                pbar.set_postfix({
                    'OK': success_count,
                    'Speed': f"{self._format_size(avg_speed)}/s"
                })
            else:
                pbar.set_postfix({'OK': success_count})
        
        pbar.close()
        return success_count

    @staticmethod
    def _format_size(bytes_num):
        """Format file size"""
        if bytes_num >= 1024 * 1024 * 1024:
            return f"{bytes_num / (1024*1024*1024):.2f} GB"
        elif bytes_num >= 1024 * 1024:
            return f"{bytes_num / (1024*1024):.2f} MB"
        elif bytes_num >= 1024:
            return f"{bytes_num / 1024:.2f} KB"
        return f"{bytes_num} B"

    def get_file_info(self, fsids, dlink=1, thumb=1, extra=1, needmedia=1, detail=1):
        """Get file info and download link (dlink) via filemetas API"""
        if not self.access_token:
            return None
        
        if not isinstance(fsids, list):
            fsids = [fsids]
        
        try:
            fsids_int = [int(fsid) for fsid in fsids]
        except (ValueError, TypeError):
            return None
        
        fsids_json = json.dumps(fsids_int, separators=(',', ':'))
        fsids_encoded = quote(fsids_json)
        
        other_params = {
            'method': 'filemetas',
            'access_token': self.access_token,
            'thumb': str(thumb),
            'dlink': str(dlink),
            'extra': str(extra),
            'needmedia': str(needmedia),
            'detail': str(detail)
        }
        
        url = f"https://pan.baidu.com/rest/2.0/xpan/multimedia?{urlencode(other_params)}&fsids={fsids_encoded}"
        headers = {'User-Agent': 'pan.baidu.com'}
        
        try:
            response = self._safe_request("GET", url, headers=headers, data={}, files={})
            if response:
                result = response.json()
                if result.get('errno') == 0:
                    return result.get('list', [])
            return None
        except Exception:
            return None

    def get_fsid_by_path(self, file_path):
        """Get file fsid by file path"""
        if not self.access_token:
            return None
        
        # Resolve relative path
        file_path = self._resolve_path(file_path)
        file_path = file_path.rstrip('/')
        if not file_path:
            file_path = "/"
        
        if file_path == "/":
            return None
        
        parts = file_path.rsplit('/', 1)
        if len(parts) == 2:
            dir_path = parts[0] if parts[0] else "/"
            file_name = parts[1]
        else:
            dir_path = "/"
            file_name = parts[0]
        
        if not file_name:
            return None
        
        file_list = self.list_files(directory=dir_path, folder=0)
        if file_list is None or len(file_list) == 0:
            return None
        
        # Find matching file by name
        for file_info in file_list:
            if file_info.get('server_filename') == file_name:
                return file_info.get('fs_id')
        
            return None

    def get_download_url(self, file_path=None, fsid=None):
        """Get download URL (dlink) for file"""
        if not self.access_token:
            return None
        
        if fsid is None:
            if file_path is None:
                return None
            # get_fsid_by_path will resolve the path
            fsid = self.get_fsid_by_path(file_path)
            if fsid is None:
                return None
        
        file_info_list = self.get_file_info(fsids=[fsid], dlink=1)
        if not file_info_list or len(file_info_list) == 0:
            return None
        
        dlink = file_info_list[0].get('dlink')
        if not dlink:
            return None
        
        separator = '&' if '?' in dlink else '?'
        return f"{dlink}{separator}access_token={self.access_token}"

    def download_file_by_path(self, file_path, save_path=None, chunk_size=8192, resume=True, show_progress=True):
        """Download file by file path"""
        if not self.access_token:
            return False
        
        # Resolve relative path
        file_path = self._resolve_path(file_path)
        download_url = self.get_download_url(file_path=file_path)
        if not download_url:
            return False
        
        if save_path is None:
            file_name = os.path.basename(file_path)
            save_path = os.path.join(os.getcwd(), file_name)
        
        return self.download_file(download_url, save_path, chunk_size=chunk_size, resume=resume, show_progress=show_progress)

    def download_file_by_fsid(self, fsid, save_path, chunk_size=8192, resume=True, show_progress=True):
        """Download file by fsid"""
        if not self.access_token:
            return False
        
        download_url = self.get_download_url(fsid=fsid)
        if not download_url:
            return False
        
        return self.download_file(download_url, save_path, chunk_size=chunk_size, resume=resume, show_progress=show_progress)

    def download_directory(self, directory_path, save_dir, recursive=True, file_filter=None):
        """Download all files in directory"""
        if not self.access_token:
            return 0
        
        # Resolve relative path
        directory_path = self._resolve_path(directory_path)
        save_dir = os.path.abspath(save_dir.rstrip('/\\'))
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        
        if recursive:
            all_files = self.list_all_files_recursive(path=directory_path)
        else:
            file_list = self.list_files(directory=directory_path, folder=0)
            if file_list is None or len(file_list) == 0:
                return 0
            all_files = file_list
        
        if not all_files:
            return 0
        
        files = [f for f in all_files if f.get('isdir', 1) == 0]
        directories = [f for f in all_files if f.get('isdir', 1) == 1]
        
        if directories:
            created_dirs = set()
            dir_pbar = tqdm(
                total=len(directories),
                desc="Creating directories",
                unit="dir",
                ncols=120,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n}/{total} [{elapsed}<{remaining}]'
            )
            
            for dir_info in directories:
                dir_path = dir_info.get('path')
                if dir_path.startswith(directory_path):
                    relative_path = dir_path[len(directory_path):].lstrip('/')
                else:
                    relative_path = dir_info.get('server_filename', '')
                
                if relative_path:
                    local_dir_path = os.path.join(save_dir, relative_path)
                    if local_dir_path not in created_dirs:
                        if not os.path.exists(local_dir_path):
                            os.makedirs(local_dir_path, exist_ok=True)
                        created_dirs.add(local_dir_path)
                dir_pbar.update(1)
            
            dir_pbar.close()
        else:
            created_dirs = set()
        
        if file_filter:
            files = [f for f in files if file_filter(f)]
        
        total_files = len(files)
        if total_files == 0:
            return 0
        
        success_count = 0
        pbar = tqdm(
            total=total_files, 
            desc="Downloading", 
            unit="file", 
            ncols=120,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n} [{elapsed}<{remaining}{postfix}]'
        )
        start_time = time.time()
        total_downloaded = 0
        
        for file_info in files:
            file_path = file_info.get('path')
            file_name = file_info.get('server_filename', 'unknown_file')
            fsid = file_info.get('fs_id')
            file_size = file_info.get('size', 0)
            
            if file_path.startswith(directory_path):
                relative_path = file_path[len(directory_path):].lstrip('/')
            else:
                relative_path = file_name
            
            local_save_path = os.path.join(save_dir, relative_path)
            local_save_dir = os.path.dirname(local_save_path)
            
            if local_save_dir and not os.path.exists(local_save_dir):
                os.makedirs(local_save_dir, exist_ok=True)
            
            pbar.set_description(f"Downloading {file_name[:30]}")
            if self.download_file_by_fsid(fsid, local_save_path, show_progress=False):
                success_count += 1
                total_downloaded += file_size
            pbar.update(1)
            
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                avg_speed = total_downloaded / elapsed_time
                pbar.set_postfix({
                    'OK': success_count,
                    'Speed': f"{self._format_size(avg_speed)}/s"
                })
            else:
                pbar.set_postfix({'OK': success_count})
        
        pbar.close()
        return success_count

    def download_file(self, download_url, save_path, chunk_size=8192, resume=True, show_progress=True):
        """Download file from URL"""
        headers = {'User-Agent': 'pan.baidu.com'}
        
        file_size = 0
        resume_position = 0
        
        if resume and os.path.exists(save_path):
            resume_position = os.path.getsize(save_path)
        
        try:
            head_response = self._safe_request("HEAD", download_url, headers=headers)
            if head_response and 'Content-Length' in head_response.headers:
                file_size = int(head_response.headers['Content-Length'])
            elif head_response and 'content-length' in head_response.headers:
                file_size = int(head_response.headers['content-length'])
        except Exception:
            pass
        
        if resume and resume_position > 0:
            headers['Range'] = f'bytes={resume_position}-'
            if file_size > 0:
                file_size = file_size - resume_position
        
        file_name = os.path.basename(save_path)
        save_dir = os.path.dirname(save_path)
        
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        
        try:
            response = self._safe_request("GET", download_url, headers=headers, stream=True)
            
            if not response or response.status_code not in [200, 206]:
                return False
            
            total_size = file_size if file_size > 0 else None
            initial = resume_position if resume and resume_position > 0 else 0
            
            if show_progress:
                pbar = tqdm(
                    total=total_size,
                    initial=initial,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=file_name[:30],
                    ncols=120,
                    bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'
                )
            else:
                pbar = None
            
            mode = 'ab' if resume and resume_position > 0 else 'wb'
            with open(save_path, mode) as f:
                start_time = time.time()
                downloaded = resume_position
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if pbar:
                            pbar.update(len(chunk))
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 0:
                                avg_speed = downloaded / elapsed_time
                                pbar.set_postfix({'Speed': f"{self._format_size(avg_speed)}/s"})
            
            if pbar:
                pbar.close()
            return True
            
        except KeyboardInterrupt:
            return False
        except Exception:
            if os.path.exists(save_path) and os.path.getsize(save_path) == 0:
                try:
                    os.remove(save_path)
                except:
                    pass
            return False

    def delete_file(self, file_path):
        """Delete file or directory by path"""
        if not self.access_token:
            return False
        
        # Resolve relative path
        file_path = self._resolve_path(file_path)
        file_path = file_path.rstrip('/')
        
        if file_path == "/":
            print("Error: Cannot delete root directory")
            return False
        
        # Use path-based deletion (as shown in the API example)
        return self.delete_file_by_paths([file_path])
    
    def delete_file_by_paths(self, file_paths):
        """Delete files or directories by paths"""
        if not self.access_token:
            return False
        
        if not isinstance(file_paths, list):
            file_paths = [file_paths]
        
        # Resolve and normalize paths
        resolved_paths = []
        for path in file_paths:
            resolved_path = self._resolve_path(path)
            resolved_path = resolved_path.rstrip('/')
            if resolved_path and resolved_path != "/":
                resolved_paths.append(resolved_path)
        
        if not resolved_paths:
            return False
        
        # URL encode paths and create JSON array
        # According to the API example, paths should be URL encoded in the JSON array
        from urllib.parse import quote
        import time
        
        encoded_paths = [quote(path, safe='') for path in resolved_paths]
        filelist_json = json.dumps(encoded_paths, separators=(',', ':'))
        
        # Build URL with access_token as query parameter
        url = (
            "https://pan.baidu.com/rest/2.0/xpan/file"
            f"?method=filemanager"
            f"&opera=delete"
            f"&access_token={self.access_token}"
        )
        
        # Use async=2 as shown in the example (async=0 may fail with errno=12)
        data = {
            'async': '2',
            'filelist': filelist_json
        }
        headers = {'User-Agent': 'pan.baidu.com'}
        
        try:
            # Print debug info before request
            print(f"Debug - Attempting to delete paths: {resolved_paths}")
            print(f"Debug - Encoded paths: {encoded_paths}")
            print(f"Debug - Filelist JSON: {filelist_json}")
            
            response = self._safe_request("POST", url, headers=headers, data=data)
            if response:
                result = response.json()
                print(f"Debug - API Response: {result}")
                errno = result.get('errno')
                
                if errno == 0:
                    # Check if there's a taskid (async operation)
                    taskid = result.get('taskid')
                    if taskid:
                        print(f"Debug - Async deletion task started, taskid: {taskid}")
                        # For async operations, wait and poll for completion
                        max_wait_time = 10  # Maximum wait time in seconds
                        check_interval = 1  # Check every 1 second
                        waited = 0
                        
                        while waited < max_wait_time:
                            time.sleep(check_interval)
                            waited += check_interval
                            
                            # Check if files still exist
                            all_deleted = True
                            for path in resolved_paths:
                                fsid = self.get_fsid_by_path(path)
                                if fsid:
                                    all_deleted = False
                                    break
                            
                            if all_deleted:
                                print(f"Debug - Successfully deleted (async, waited {waited}s): {resolved_paths}")
                                return True
                        
                        # After max wait time, do final check
                        all_deleted = True
                        for path in resolved_paths:
                            fsid = self.get_fsid_by_path(path)
                            if fsid:
                                print(f"Warning: File still exists after {max_wait_time}s wait: {path}")
                                all_deleted = False
                        
                        if all_deleted:
                            print(f"Debug - Successfully deleted: {resolved_paths}")
                            return True
                        else:
                            # Files still exist after waiting - might be a real issue
                            print(f"Error: Files still exist after async deletion (waited {max_wait_time}s)")
                            return False
                    else:
                        # Synchronous deletion, wait a bit and verify
                        time.sleep(0.5)
                        
                        # Verify deletion
                        all_deleted = True
                        for path in resolved_paths:
                            fsid = self.get_fsid_by_path(path)
                            if fsid:
                                print(f"Warning: File still exists after deletion: {path}")
                                all_deleted = False
                        
                        if all_deleted:
                            print(f"Debug - Successfully deleted: {resolved_paths}")
                            return True
                        else:
                            # Wait a bit more and check again
                            time.sleep(1)
                            all_deleted = True
                            for path in resolved_paths:
                                fsid = self.get_fsid_by_path(path)
                                if fsid:
                                    print(f"Error: File still exists after deletion: {path}")
                                    all_deleted = False
                            return all_deleted
                else:
                    # Check info array for detailed error messages
                    info = result.get('info', [])
                    if info:
                        for item in info:
                            item_errno = item.get('errno')
                            item_path = item.get('path', '')
                            print(f"Error: Delete failed for path '{item_path}' (errno={item_errno})")
                    
                    errmsg = result.get('errmsg', 'Unknown error')
                    print(f"Error: Delete failed (errno={errno}): {errmsg}")
                    print(f"Debug - Full response: {result}")
                    return False
            else:
                print(f"Error: No response from server")
                return False
        except Exception as e:
            print(f"Error: Delete request failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_file_by_fsid(self, fsid):
        """Delete file or directory by fsid (converts to path first)"""
        if not self.access_token:
            return False
        
        if not isinstance(fsid, list):
            fsids = [fsid]
        else:
            fsids = fsid
        
        # Convert fsids to paths
        paths = []
        for f in fsids:
            try:
                fsid_int = int(f)
                # Get file info to get path
                file_info_list = self.get_file_info(fsids=[fsid_int], dlink=0)
                if file_info_list and len(file_info_list) > 0:
                    path = file_info_list[0].get('path')
                    if path:
                        paths.append(path)
            except (ValueError, TypeError):
                continue
        
        if not paths:
            return False
        
        # Use path-based deletion
        return self.delete_file_by_paths(paths)

    def rename_file(self, file_path, new_name):
        """
        Rename file or directory
        
        Args:
            file_path: Current file or directory path
            new_name: New name (without path, just the filename)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.access_token:
            return False
        
        # Resolve relative path
        file_path = self._resolve_path(file_path)
        file_path = file_path.rstrip('/')
        
        if file_path == "/":
            print("Error: Cannot rename root directory")
            return False
        
        # Validate new_name (should not contain path separators)
        if '/' in new_name or '\\' in new_name:
            print("Error: New name should not contain path separators")
            return False
        
        # Build filelist in the format required by API
        filelist = [{
            "path": file_path,
            "newname": new_name
        }]
        
        # Build URL with access_token as query parameter
        url = (
            "https://pan.baidu.com/rest/2.0/xpan/file"
            f"?method=filemanager"
            f"&opera=rename"
            f"&access_token={self.access_token}"
        )
        
        data = {
            'async': '2',
            'ondup': 'fail',
            'filelist': json.dumps(filelist, separators=(',', ':'))
        }
        headers = {'User-Agent': 'pan.baidu.com'}
        
        try:
            response = self._safe_request("POST", url, headers=headers, data=data)
            if response:
                result = response.json()
                if result.get('errno') == 0:
                    return True
                else:
                    errno = result.get('errno')
                    errmsg = result.get('errmsg', 'Unknown error')
                    print(f"Error: Rename failed (errno={errno}): {errmsg}")
                    # Print response for debugging
                    if errno != 0:
                        print(f"Response: {result}")
                    return False
            else:
                print("Error: No response from server")
                return False
        except Exception as e:
            print(f"Error: Rename request failed: {e}")
            import traceback
            traceback.print_exc()
            return False

