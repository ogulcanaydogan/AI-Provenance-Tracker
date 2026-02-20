# Data Retention & Privacy

Policies and procedures for data lifecycle management in the AI Provenance Tracker.

---

## Analysis Record Lifecycle

Detection results are stored in the `analysis_records` database table with no automatic expiry.

| Field | Stored | Sensitive? |
|-------|--------|-----------|
| `analysis_id` | UUID | No |
| `content_type` | text/image/audio/video | No |
| `result` | JSON detection output | Low — contains scores and signals, not raw content |
| `content_hash` | SHA-256 of input | Low — irreversible hash, not the original content |
| `input_size` | Byte count | No |
| `filename` | Original filename (media only) | Low |
| `source` | "api" or "extension" | No |
| `source_url` | URL where content was found | Medium — may identify browsing activity |
| `created_at` | Timestamp | No |

**Raw content is never stored.** Only the hash, metadata, and detection result are persisted.

### In-Memory Eviction

The `AnalysisStore` maintains an in-memory cache with a configurable `max_items` limit. When the limit is reached, the oldest records are evicted from memory (but remain in the database).

### Recommended Retention Policy

- **Active data:** Keep the last 90 days of analysis records for dashboard analytics.
- **Archive:** Move records older than 90 days to cold storage or delete them.
- **Purge command:** `DELETE FROM analysis_records WHERE created_at < datetime('now', '-90 days');`

---

## Audit Event Retention

Audit events track HTTP requests and system events for security observability.

| Field | Stored | Sensitive? |
|-------|--------|-----------|
| `event_type` | e.g., "http.request" | No |
| `severity` | info/warning/error | No |
| `actor_id` | From X-Actor-Id header | Medium — identifies the requester |
| `request_id` | From X-Request-Id header | No |
| `payload.client_ip` | Client IP address | High — personally identifiable |
| `payload.path` | Request path | Low |
| `payload.method` | HTTP method | No |

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `APT_AUDIT_EVENTS_ENABLED` | `true` | Master toggle for audit logging |
| `APT_AUDIT_LOG_HTTP_REQUESTS` | `true` | Log individual HTTP requests |
| `APT_AUDIT_EVENTS_MAX_ITEMS` | 20000 | In-memory circular buffer size |

### Recommended Retention Policy

- **Active data:** Keep 30 days for incident investigation.
- **Compliance archive:** Keep 1 year if required by your organisation's security policy.
- **Purge command:** `DELETE FROM audit_events WHERE created_at < datetime('now', '-30 days');`

### Disabling IP Collection

To stop collecting client IP addresses in audit events, set `APT_AUDIT_LOG_HTTP_REQUESTS=false`. This disables all HTTP request audit logging. Individual detection events are still logged without IP data.

---

## Database Maintenance

### SQLite

```bash
# Reclaim space after deletions
sqlite3 data/provenance.db "VACUUM;"

# Check database integrity
sqlite3 data/provenance.db "PRAGMA integrity_check;"

# Database file size
ls -lh data/provenance.db
```

### PostgreSQL

```sql
-- Reclaim space (autovacuum handles this normally)
VACUUM ANALYZE analysis_records;
VACUUM ANALYZE audit_events;

-- Rebuild indexes for performance
REINDEX TABLE analysis_records;
REINDEX TABLE audit_events;

-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(oid))
FROM pg_class WHERE relname IN ('analysis_records', 'audit_events');
```

---

## Log Rotation

The backend outputs structured JSON logs to stdout/stderr.

### Docker

Configure the Docker logging driver to limit log file size:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
```

### Bare Metal

Use `logrotate` for systemd journal or file-based logging:

```
/var/log/provenance-tracker/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
```

### Log Aggregation

Structured JSON logs are compatible with ELK Stack (Elasticsearch, Logstash, Kibana), Grafana Loki, and Datadog. Point your log shipper at the container stdout.

---

## Evidence Directory Cleanup

Scheduled pipeline runs and webhook retries create JSON artifacts:

| Directory | Contents | Growth Rate |
|-----------|----------|-------------|
| `evidence/runs/scheduled/` | X intelligence pipeline output | ~1 file per scheduled run |
| `evidence/calibration/` | Calibration/evaluation reports | ~1 file per evaluation run |
| `evidence/webhooks/retry_queue.json` | Pending webhook retries | Rewritten on each drain cycle |
| `evidence/webhooks/dead_letter.jsonl` | Failed webhook deliveries | Append-only, grows over time |

### Recommended Cleanup

```bash
# Archive runs older than 30 days
find evidence/runs/scheduled/ -name "*.json" -mtime +30 -exec gzip {} \;

# Delete archives older than 90 days
find evidence/runs/scheduled/ -name "*.json.gz" -mtime +90 -delete

# Truncate dead-letter queue after review
> evidence/webhooks/dead_letter.jsonl
```

---

## GDPR Considerations

### Data Collected

| Data Type | Source | Purpose |
|-----------|--------|---------|
| Client IP addresses | HTTP requests | Audit trail, rate limiting |
| Content hashes | Uploaded content | Deduplication, audit trail |
| Source URLs | Extension-submitted analyses | Provenance tracking |
| X/Twitter usernames | Intel collection | Public social media analysis |

### Right to Erasure

To delete all data associated with a specific user:

```sql
-- Delete by actor ID
DELETE FROM audit_events WHERE actor_id = 'user-to-delete';

-- Delete by IP address
DELETE FROM audit_events WHERE payload->>'client_ip' = '1.2.3.4';

-- Delete by analysis ID
DELETE FROM analysis_records WHERE analysis_id = 'specific-analysis-id';
```

### Data Minimisation

- **Disable HTTP audit logging:** `APT_AUDIT_LOG_HTTP_REQUESTS=false` stops collecting IP addresses and request metadata.
- **Disable audit events entirely:** `APT_AUDIT_EVENTS_ENABLED=false` stops all audit event recording.
- **Raw content is never stored:** Only hashes, metadata, and detection results are persisted.

### X/Twitter Data

Intel collection stores only publicly available Twitter data (usernames, tweet text, engagement metrics). No private or protected account data is collected. This data is stored in `evidence/runs/scheduled/` as JSON files and can be deleted per the cleanup schedule above.
