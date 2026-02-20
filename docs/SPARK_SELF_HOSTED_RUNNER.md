# Spark Self-Hosted Runner Runbook

This runbook documents the production self-hosted GitHub Actions runner used for Spark deploys.

## Target

- Repo: `ogulcanaydogan/AI-Provenance-Tracker`
- Runner name: `spark-self-hosted`
- Labels: `self-hosted`, `Linux`, `ARM64`, `spark`

## 1) Install runner on Spark host (ARM64)

```bash
mkdir -p ~/actions-runner-spark
cd ~/actions-runner-spark
curl -L -o actions-runner-linux-arm64-2.331.0.tar.gz \
  https://github.com/actions/runner/releases/download/v2.331.0/actions-runner-linux-arm64-2.331.0.tar.gz
tar xzf actions-runner-linux-arm64-2.331.0.tar.gz
```

## 2) Register runner

Generate a fresh registration token in GitHub:

- `Settings` -> `Actions` -> `Runners` -> `New self-hosted runner`

Then configure:

```bash
cd ~/actions-runner-spark
./config.sh \
  --url https://github.com/ogulcanaydogan/AI-Provenance-Tracker \
  --token <REGISTRATION_TOKEN> \
  --name spark-self-hosted \
  --labels spark,arm64 \
  --unattended \
  --replace
```

## 3) Persist with systemd (user service)

Prerequisite:

- `loginctl show-user "$USER" -p Linger` should return `Linger=yes`.

Create and enable service:

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/github-actions-runner.service <<'EOF'
[Unit]
Description=GitHub Actions Runner (Spark)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/actions-runner-spark
ExecStart=%h/actions-runner-spark/run.sh
Restart=always
RestartSec=5
KillMode=process

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now github-actions-runner.service
systemctl --user status github-actions-runner.service --no-pager
```

If an old `@reboot` cron entry exists for `start.sh`, remove it to avoid double starts.

## 4) Validate runner health

From local repo:

```bash
gh api repos/ogulcanaydogan/AI-Provenance-Tracker/actions/runners \
  --jq '.runners[] | {name,status,labels:[.labels[].name]}'
```

Expected:

- `name`: `spark-self-hosted`
- `status`: `online`

## 5) Trigger real pinned deploy

```bash
gh workflow run deploy-spark.yml \
  -f use_pinned_images=true \
  -f image_tag=<commit_sha> \
  -f verify_signatures=true \
  -f deploy_frontend=false \
  -f run_smoke=true \
  -f rollback_on_smoke_failure=true \
  -f runner_type=self-hosted
```

## 6) Security and operations notes

- Rotate runner registration tokens on reconfiguration.
- Keep `SPARK_SSH_KEY` permissions strict (`600`) and `known_hosts` pinned.
- Keep `RAILWAY_*` secrets out of this path; Spark deploy uses SSH + GHCR.
- For ARM64 Spark hosts, publish multi-arch images (`linux/amd64,linux/arm64`) before pinned deploys.
- Keep signature verification enabled for pinned deploys (`verify_signatures=true`).
