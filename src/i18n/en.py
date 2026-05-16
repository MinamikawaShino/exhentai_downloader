EN = {
    # App
    "app.title": "ExHentai Gallery Downloader",
    "app.ready": "Ready",
    "app.connected": "Connected",
    "app.not_connected": "Not Connected",
    "app.connecting": "Connecting...",
    "app.downloading": "Downloading...",
    "app.stopping": "Stopping...",

    # Tabs
    "tab.tasks": "Tasks",
    "tab.settings": "Settings",
    "tab.home": "Home",

    # Task tab
    "task.url_input": "URL Input (one per line)",
    "task.add_url": "Add URL",
    "task.load_failed": "Load Failed",
    "task.load_queue": "Load Queue",
    "task.clear": "Clear",
    "task.stats.queue": "Queue",
    "task.stats.completed": "Completed",
    "task.stats.failed": "Failed",
    "task.stats.current": "Current",
    "task.file_progress_ready": "Ready",
    "task.file_downloading": "Downloading: {name}  {current}/{total}",
    "task.file_download_speed": "Downloading: {name}  {current}/{total}  {speed}/s  ETA: {eta}",
    "task.file_complete": "Download Complete",
    "task.queue_progress": "Total Progress: {done}/{total}",
    "task.task_list": "Task List",
    "task.log": "Log",
    "task.start": "Start Download",
    "task.stop": "Stop",
    "task.retry_failed": "Retry Failed",
    "task.exit": "Exit",
    "task.connect_first": "Please connect to browser first",
    "task.queue_empty": "Queue is empty, please add URLs",
    "task.no_failed": "No failed records found",
    "task.no_queue": "No saved queue found",

    # Task statuses
    "status.pending": "Pending",
    "status.processing": "Processing",
    "status.completed": "Completed",
    "status.failed": "Failed",
    "status.skipped": "Skipped",

    # Settings tab
    "settings.download_dir": "Download Directory",
    "settings.library_paths": "Library Paths (dedup across dirs)",
    "settings.browse": "Browse",
    "settings.add_path": "Add Path",
    "settings.rescan": "Rescan All",
    "settings.chrome": "Chrome Browser",
    "settings.chrome_path": "Chrome:",
    "settings.user_data_dir": "User Data:",
    "settings.port": "Port:",
    "settings.launch_browser": "Launch Browser",
    "settings.connect_browser": "Connect Browser",
    "settings.connected_btn": "Connected",
    "settings.language": "Language:",
    "settings.auto_extract": "Auto Extract ZIP",
    "settings.integrity_check": "ZIP Integrity Check",
    "settings.delete_after_extract": "Delete ZIP after extraction",
    "settings.notifications": "Notifications",

    "settings.extract_dir": "Extract Directory",
    "settings.extract_dir_hint": "Leave empty to extract into download directory",

    # Library
    "lib.scanning": "Scanning: {path} ...",
    "lib.scan_done": "  Done: {count} items",
    "lib.rescanning": "Rescanning {count} directories...",
    "lib.total": "Total: {count} items",
    "lib.removed": "Removed: {path}",
    "lib.dir_count": "{dirs} dirs / {items} items",

    # Chrome
    "chrome.launched": "Chrome launched (port: {port}, user data: {user_data})",
    "chrome.login_prompt": "Chrome launched, please login then click Connect Browser",
    "chrome.launch_fail": "Cannot launch Chrome",
    "chrome.not_found": "Cannot find Chrome at: {path}",
    "chrome.no_user_data": "Please set user data directory",
    "chrome.connect_fail": "Connection failed",
    "chrome.port_not_open": "Port {port} is not open. Please make sure Chrome is running with --remote-debugging-port={port}.",
    "chrome.connect_help": "Cannot connect to Chrome (port {port})\n\nMake sure Chrome is running with debug port:\nchrome.exe --remote-debugging-port={port}\n\n{error}",
    "chrome.connect_success": "Browser connected!",
    "chrome.connection_fail": "Connection failed: {error}",

    # Download
    "download.processing": "Processing: {url}",
    "download.title_load_fail": "Title load failed, retry {attempt}/3...",
    "download.title_fail": "Error: could not load page title, skipping.",
    "download.gallery_title": "Gallery Title: {title}",
    "download.file_exists": "File already exists, skipping: {title}",
    "download.in_library": "Already in library, skipping: {title}",
    "download.no_archive": "No Archive Download link found.",
    "download.window_timeout": "New window timeout, retry {attempt}/3...",
    "download.no_window": "Cannot open download window, skipping.",
    "download.getting_link": "Got download link, starting download...",
    "download.link_fail": "Failed to get download link",
    "download.complete": "Download complete: {filename}",
    "download.retry": "Attempt {attempt}/{max} failed, retrying in {wait}s...",
    "download.max_retries": "Max retries ({max}) reached, giving up.",
    "download.fatal_error": "Fatal error: {error}",
    "download.saved_progress": "Download progress saved.",
    "download.interrupted": "Download interrupted {filename}: {error}",
    "download.failed_http": "Download failed {filename}: {error}",
    "download.auto_extract": "Extracting: {filename}...",
    "download.extract_done": "Extracted: {filename}",
    "download.integrity_check": "ZIP integrity check passed: {filename}",
    "download.integrity_fail": "ZIP integrity check FAILED: {filename}",
    "download.resuming": "Resuming download ({size} bytes already downloaded)...",
    "download.part_kept": "Partial file kept, will retry resume: {filename}",
    "download.deleted_zip": "Deleted ZIP: {filename}",

    # Queue
    "queue.restored": "Found {count} pending tasks from last session.",
    "queue.restore_prompt": "Restore? (Y/n): ",
    "queue.saved": "Saved {count} pending tasks to {file}",
    "queue.loaded": "Loaded {count} URLs",

    # Meta
    "meta.saved": "Metadata saved: {title}",

    # Status
    "status.scanning": "Loading local library from cache...",
    "status.library_loaded": "Local library loaded: {count} items",
    "status.scanning_dirs": "Scanning local directories...",
    "status.interrupted": "Task interrupted, progress saved.",
    "status.finished": "Finished  Total: {total}  Success: {completed}  Failed: {failed}",
    "status.ready": "Ready",

    # Notifications
    "notify.download_complete": "Download Complete",
    "notify.all_complete": "All downloads complete!\nSuccess: {completed}, Failed: {failed}",
    "notify.error": "Download Error",

    # CLI
    "cli.enter_urls": "Enter ExHentai gallery URLs (one per line, empty line to finish):",

    # Config
    "config.no_download_dir": "Please set download directory",
}