---
description: Spin up a temporary GCP VM for quick demos, testing, and sharing
---

# Spike Droplet - Temporary GCP VM for Quick Demos

Spin up a temporary GCP VM for quick demos, testing, and sharing. Auto-provisions with Node.js and can deploy any local project.

## Triggers
- "spike up", "spike deploy", "spike droplet"
- "temporary vm", "quick deploy", "demo server"
- "spin up a vm", "need a public url"

## Setup (one-time, before first use)

Set these in your shell profile or `.env`:
```bash
export SPIKE_GCP_PROJECT="your-gcp-project-id"
export SPIKE_GCP_ZONE="europe-west2-a"   # pick a zone near you
```

## Usage

```bash
# Create spike VM and deploy current directory
/spike up

# Create spike VM and deploy specific path
/spike up ./website

# Check spike status
/spike status

# Get spike URL
/spike url

# SSH into spike
/spike ssh

# Tear down spike
/spike down
```

## Implementation

### Environment
- **Project**: `$SPIKE_GCP_PROJECT` (set in shell profile, or falls back to current `gcloud config get-value project`)
- **Zone**: `$SPIKE_GCP_ZONE` (default `europe-west2-a`)
- **Machine**: `e2-small` (2 vCPU, 2GB RAM)
- **Image**: Ubuntu 22.04 LTS
- **Name**: `spike-{timestamp}`

### Commands

**spike up [path]**
```bash
# 1. Create VM with startup script
SPIKE_NAME="spike-$(date +%s)"
ZONE="${SPIKE_GCP_ZONE:-europe-west2-a}"
gcloud compute instances create $SPIKE_NAME \
  --project="${SPIKE_GCP_PROJECT:?set SPIKE_GCP_PROJECT first}" \
  --zone=$ZONE \
  --machine-type=e2-small \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y nodejs npm nginx
    npm install -g pm2
    ufw allow 80
    ufw allow 443
    ufw allow 3000
  '

# 2. Wait for VM to be ready
gcloud compute instances describe $SPIKE_NAME --zone=$ZONE --format='get(status)'

# 3. Get external IP
SPIKE_IP=$(gcloud compute instances describe $SPIKE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# 4. Copy project files
gcloud compute scp --recurse ${path:-.} $SPIKE_NAME:~/app --zone=$ZONE

# 5. Install and start
gcloud compute ssh $SPIKE_NAME --zone=$ZONE --command="cd ~/app && npm install && pm2 start npm --name app -- start"

# 6. Output URL
echo "Spike live at: http://$SPIKE_IP:3000"
```

**spike status**
```bash
gcloud compute instances list --filter="name~spike-*" --format="table(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

**spike url**
```bash
SPIKE_NAME=$(gcloud compute instances list --filter="name~spike-*" --format="value(name)" | head -1)
gcloud compute instances describe $SPIKE_NAME --zone="${SPIKE_GCP_ZONE:-europe-west2-a}" --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

**spike ssh**
```bash
SPIKE_NAME=$(gcloud compute instances list --filter="name~spike-*" --format="value(name)" | head -1)
gcloud compute ssh $SPIKE_NAME --zone="${SPIKE_GCP_ZONE:-europe-west2-a}"
```

**spike down**
```bash
# Delete all spike instances
ZONE="${SPIKE_GCP_ZONE:-europe-west2-a}"
gcloud compute instances list --filter="name~spike-*" --format="value(name)" | while read name; do
  gcloud compute instances delete $name --zone=$ZONE --quiet
done
echo "All spike instances deleted"
```

### Firewall Rules (one-time setup)
```bash
gcloud compute firewall-rules create allow-http --allow tcp:80 --target-tags=http-server 2>/dev/null || true
gcloud compute firewall-rules create allow-https --allow tcp:443 --target-tags=https-server 2>/dev/null || true
gcloud compute firewall-rules create allow-node --allow tcp:3000 --target-tags=http-server 2>/dev/null || true
```

## Notes
- Spike VMs are temporary - remember to `/spike down` when done
- Cost: ~$0.02/hour for e2-small (check current GCP pricing)
- Data is NOT persisted - copy anything important before teardown
- For production, use proper deployment (Cloud Run, GKE, etc.)
- Requires `gcloud` CLI authenticated against your own GCP project

<!-- CUSTOMISE: this command originally hardcoded a specific GCP
     project id. Set SPIKE_GCP_PROJECT to your own project before use. -->
