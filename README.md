# Griot and Grits - Digital Preservation Backend

> **PREMIS-compliant digital preservation system for Black and minority history artifacts**

A production-ready backend for managing cultural heritage artifacts with dual-tier storage (MinIO hot storage + BU Globus archive), preservation metadata tracking, and flexible metadata extraction pipeline.

## 🚀 Quick Start

```bash
# 1. Install dependencies (requires uv)
make install

# 2. Copy environment template
cp .env.example .env
# Edit .env with your configuration

# 3. Start services (MongoDB + MinIO)
make dev-services-up

# 4. Run the application
make dev-up
```

The API will be available at http://localhost:8000 with interactive docs at http://localhost:8000/docs

## Features

- **📦 Artifact Ingestion**: Multi-part file upload with metadata
- **🔒 Fixity Checking**: MD5 and SHA-256 checksums for integrity verification
- **💾 Dual-Tier Storage**: Hot storage (MinIO) + Archive (Globus)
- **📝 Preservation Events**: Complete PREMIS-compliant audit trail
- **📍 Storage Tracking**: Monitor all copies across storage tiers
- **⚡ Stream Processing**: Efficient handling of large (20GB+) files
- **🔍 RESTful API**: Auto-generated OpenAPI documentation
- **🎯 Status Tracking**: Monitor artifact processing pipeline

## Documentation

- **[Quick Start Guide](docs/quickstart.md)** - Setup and usage
- **[Implementation Summary](docs/implementation_summary.md)** - Feature details
- **[Implementation Plan](docs/implementation_plan.md)** - Architecture and design
- **[Implementation Complete](IMPLEMENTATION_COMPLETE.md)** - Deliverables overview

## 🛠️ Development Commands

```bash
# Install dependencies
make install

# Start all services
make dev-services-up

# Run API server
make dev-up

# Stop all services
make dev-services-down

# View available commands
make help
```

## 🏗️ Architecture

```
User Upload
    ↓
API (/artifacts/ingest)
    ↓
┌─────────────────────────────────┐
│   Ingestion Service             │
│  - Checksum calculation         │
│  - File streaming               │
│  - Metadata validation          │
└──────────┬──────────────────────┘
           ↓
   ┌───────┴────────┐
   ↓                ↓
Globus Arive      MongoDB
(Cold)        (Metadata)
   ↓
Minio
(Hot)
```

## API Endpoints

### Artifact Management
- `POST /artifacts/ingest` - Upload artifact with metadata
- `GET /artifacts/{id}` - Retrieve artifact
- `GET /artifacts/{id}/status` - Check processing status
- `GET /artifacts` - List artifacts with filtering

### Preservation Operations
- `GET /preservation/artifacts/{id}/events` - View audit trail
- `GET /preservation/artifacts/{id}/storage-locations` - View storage copies
- `GET /preservation/artifacts/{id}/fixity` - View checksums
- `POST /preservation/artifacts/{id}/replicate` - Trigger archive replication

## 🔧 Configuration

Environment variables (see `.env.example`):

- **Database**: `DB_URI`, `DB_NAME`
- **Storage**: `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`
- **Globus**: `GLOBUS_ENABLED`, `GLOBUS_ENDPOINT_ID`, `GLOBUS_BASE_PATH`
- **Processing**: `PROCESSING_MODE`, `PROCESSING_ENABLE_METADATA_EXTRACTION`

## 📦 Project Structure

```
app/
├── api/              # API endpoints
├── config/           # Configuration management
├── models/           # Pydantic data models
├── services/         # Business logic
│   ├── fixity_service.py
│   ├── ingestion_service.py
│   ├── preservation_event_service.py
│   └── storage_location_service.py
└── factory.py        # Dependency injection
```


## 🔮 Roadmap

- ✅ Core ingestion pipeline
- ✅ Fixity checking
- ✅ Preservation metadata
- ⏳ Globus archive integration
- ⏳ Background processing (Celery)
- ⏳ Metadata extraction pipeline
- ⏳ LLM-based enrichment
- ⏳ Automated transcription

## 📄 License

See [LICENSE](LICENSE) file.

## 🤝 Contributing

This is an open-source project for preserving Black and minority history. Contributions welcome!

## Support

See documentation in `docs/` directory for detailed information.
