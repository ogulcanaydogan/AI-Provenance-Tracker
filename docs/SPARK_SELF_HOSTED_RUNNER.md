# Spark Runner Pool Runbook

This runbook documents the self-hosted runner pool split used by production CI/CD and GPU training.

## Runner Pools

- Repo: `ogulcanaydogan/AI-Provenance-Tracker`
- Runtime runner name: `spark-runtime-01`
- Runtime labels: `self-hosted`, `linux`, `x64`, `spark-runtime`
- A100 runner name: `gpu-a100-01`
- A100 labels: `self-hosted`, `linux`, `x64`, `a100`
- V100 runner name: `gpu-v100-01`
- V100 labels: `self-hosted`, `linux`, `x64`, `v100`

## 1) Install each runner service

```bash
mkdir -p ~/actions-runner-runtime
cd ~/actions-runner-runtime
curl -L -o actions-runner-linux-x64-2.331.0.tar.gz \
  https://github.com/actions/runner/releases/download/v2.331.0/actions-runner-linux-x64-2.331.0.tar.gz
tar xzf actions-runner-linux-x64-2.331.0.tar.gz
```

## 2) Register runtime runner

Generate a fresh registration token in GitHub:

- `Settings` -> `Actions` -> `Runners` -> `New self-hosted runner`

Then configure:

```bash
cd ~/actions-runner-runtime
./config.sh \
  --url https://github.com/ogulcanaydogan/AI-Provenance-Tracker \
  --token <REGISTRATION_TOKEN> \
  --name spark-runtime-01 \
  --labels spark-runtime,x64 \
  --unattended \
  --replace
```

Register GPU runners with the same pattern using dedicated service directories:

- `gpu-a100-01` labels: `a100,x64`
- `gpu-v100-01` labels: `v100,x64`

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
WorkingDirectory=%h/actions-runner-runtime
ExecStart=%h/actions-runner-runtime/run.sh
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

- `spark-runtime-01`: `online`, labels include `spark-runtime`
- `gpu-a100-01`: `online`, labels include `a100`
- `gpu-v100-01`: `online`, labels include `v100`

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
- For ARM64 runtime hosts, publish multi-arch images (`linux/amd64,linux/arm64`) before pinned deploys.
- Keep signature verification enabled for pinned deploys (`verify_signatures=true`).
- Keep SBOM attestation checks enabled for pinned deploys (automatic when verification is enabled).
