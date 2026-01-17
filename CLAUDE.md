# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**object_backup_to_baidu_pan** - A backup system that uploads local files/folders to Baidu Net Disk (百度网盘). This is v2 of "item_backup_simple", currently in early development (v0.1.0).

## Development Commands

```bash
# Install dependencies and setup
uv sync

# Add dependencies
uv add <package>

# Run the application
uv run object_backup_to_baidu_pan

# Run tests (when implemented)
uv run pytest
```

## Architecture

### Core Processing Flow
1. Source scan → DB comparison → Hash calculation
2. Compression → Hash verification → Decompression check
3. Upload queue → Async upload → DB update → Cleanup

### Key Components

| Path | Purpose |
|------|---------|
| `src/object_backup_to_baidu_pan/service/zip_service.py` | ZIP compression/decompression with AES encryption |
| `src/object_backup_to_baidu_pan/service/upload_service/` | Baidu Pan upload orchestration with chunked upload |
| `src/object_backup_to_baidu_pan/service/upload_service/openapi_client/` | Auto-generated Baidu API client |

### Path Conventions

- **Local ZIP path**: `{target_dir}/YYYYMMDD/解压密码_{password}/{source_name}.zip`
- **Baidu Pan path**: `/item_backup/{date}/{password}/{filename}.zip`
- Use `extract_date_and_password_from_path()` in `service/upload_service/utils.py` to parse paths

### Configuration

- **Config format**: TOML files for settings, `.env` for secrets
- **Database**: MySQL with SQLAlchemy ORM 2.0 style
- **Env files**: `upload.env` (Baidu tokens), `mysql.env` (DB creds), `163_email.env` (SMTP)

### Resource Management

- **Disk threshold**: 80GB (configurable)
- **Upload chunk size**: 20MB default
- **Retry policy**: 3 attempts for compression, 5 for upload

### Technology Stack

- Python 3.13+, pathlib for all paths
- `pyzipper` for AES-encrypted ZIPs
- MySQL + SQLAlchemy 2.0 ORM

## Notes

- `main.py` is empty - main entry point needs implementation
- Database models not yet defined
- Some services exist but need integration per README section 9
