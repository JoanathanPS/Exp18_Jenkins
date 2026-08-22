# LAB EX18 — CI/CD Pipeline for a Containerized Application

This kit gives you a complete, runnable answer to all four tasks in the lab sheet, plus the reasoning behind each piece so you understand *why* it's built this way, not just how to run it.

```
ci-cd-lab/
├── app/
│   ├── app.py              # the sample Flask application
│   ├── requirements.txt
│   ├── Dockerfile          # Task 2
│   ├── .dockerignore
│   └── tests/test_app.py   # unit tests Jenkins runs in Task 3
├── Jenkinsfile              # Task 3 + 4
├── jenkins-docker-compose.yml  # Task 1 (local Jenkins)
└── README.md                # this file
```

---

## Task 1 — Set up Jenkins

You have two realistic options. Pick the one that matches what your lab expects.

### Option A: Jenkins in Docker (fastest, recommended for a lab)

```bash
docker compose -f jenkins-docker-compose.yml up -d
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open `http://localhost:8080`, paste that password, choose **Install suggested plugins**, then create your admin user.

**Why the docker.sock mount matters:** Jenkins itself runs inside a container, but Task 3 requires it to run `docker build`. Rather than nesting a second Docker engine inside the Jenkins container (fragile, slow), we mount the *host's* `docker.sock` into the Jenkins container. Jenkins' `docker` CLI then talks straight to the host's Docker daemon — this pattern is called **Docker-outside-of-Docker (DooD)**, as opposed to Docker-in-Docker (DinD).

### Option B: Jenkins natively on a Linux server/VM

```bash
sudo apt update
sudo apt install -y fontconfig openjdk-17-jre
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee \
  /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" | sudo tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt update && sudo apt install -y jenkins docker.io
sudo usermod -aG docker jenkins        # let jenkins user run docker
sudo systemctl restart jenkins
```

Either way, once inside Jenkins, install two extra plugins from **Manage Jenkins → Plugins**: **Docker Pipeline** and **SSH Agent** (both used by the `Jenkinsfile`).

---

## Task 2 — Dockerfile (containerize the app)

`app/Dockerfile` uses a **two-stage build**:

1. **Builder stage** (`python:3.12-slim`) installs pip packages into an isolated layer.
2. **Runtime stage** copies only the installed packages (not pip's cache, build tools, etc.) into a fresh slim image, and runs as a non-root `appuser`.

This matters for two reasons you should be able to explain in a viva: it keeps the final image small (faster pulls/deploys), and running as non-root limits blast radius if the container is ever compromised.

Test it locally before wiring it into Jenkins:

```bash
cd app
docker build -t ci-cd-lab-app:local .
docker run --rm -p 5000:5000 ci-cd-lab-app:local
curl http://localhost:5000/health
```

---

## Task 3 — Jenkinsfile (build, test, deploy)

The `Jenkinsfile` at the repo root is a **declarative pipeline** with these stages, each mapping directly to a lab requirement:

| Stage | What it does | Why |
|---|---|---|
| Checkout | `checkout scm` — pulls the exact commit that triggered the build | Reproducibility: you always build what was actually committed |
| Build Docker Image | `docker build` tagged with `${BUILD_NUMBER}` and `latest` | Unique, traceable tag per build — never overwrite history with just `latest` |
| Run Tests | `docker run` the *just-built* image and executes `pytest` inside it | Tests run against the real artifact, not your host's Python — eliminates "works on my machine" |
| Push to Registry | `docker push` to Docker Hub using stored credentials | Makes the image pullable from the deploy target |
| Deploy to Cloud | SSH into an AWS EC2 instance, `docker pull` + restart the container | Task 3's "deploy to a cloud platform" requirement |
| Smoke Test | `curl` the `/health` endpoint after deploy | Fails the build loudly if the new deployment is actually broken |

### Credentials you must create in Jenkins (Manage Jenkins → Credentials)

1. **`dockerhub-creds`** — type "Username with password", your Docker Hub username + an access token (not your account password).
2. **`ec2-ssh-key`** — type "SSH Username with private key", the `.pem` key for your EC2 instance.

Then edit these three lines at the top of `Jenkinsfile` to match your setup:

```groovy
IMAGE_NAME  = "yourdockerhubuser/ci-cd-lab-app"
DEPLOY_HOST = "ec2-user@YOUR_EC2_PUBLIC_IP"
```

### Deploying to GCP instead of AWS

The deploy stage is just SSH + Docker, so it's cloud-agnostic. Replace `DEPLOY_HOST` with a GCE instance's external IP (`ssh <user>@<gce-external-ip>`), open port 80 in a GCP firewall rule, and the same stage works unchanged. This is worth understanding: **the pipeline doesn't care which cloud it's talking to — it only cares that it can SSH in and run Docker commands.** Swap in `gcloud compute scp`/`ssh` if you'd rather avoid managing raw SSH keys, or swap the whole stage for `aws ecs update-service` / `gcloud run deploy` if your lab specifically wants a managed container platform instead of a raw VM.

---

## Task 4 — Trigger builds on commit / PR

### Recommended: GitHub webhook (push-based, near-instant)

1. Push this project to a GitHub repo.
2. In Jenkins: **New Item → Pipeline**, name it, under **Pipeline** section choose "Pipeline script from SCM", SCM = Git, paste your repo URL, script path = `Jenkinsfile`.
3. Under **Build Triggers**, tick **GitHub hook trigger for GITScm polling**.
4. On GitHub: repo **Settings → Webhooks → Add webhook**, Payload URL = `http://<your-jenkins-url>/github-webhook/`, content type `application/json`, event = "Just the push event" (add "Pull requests" too if you want PR-triggered builds).

If Jenkins is only reachable on `localhost` (no public URL — common in a lab), GitHub's webhook can't reach it. Use **ngrok** to expose it temporarily:

```bash
ngrok http 8080
# use the printed https://xxxx.ngrok.io URL as the webhook payload URL
```

The `Jenkinsfile` also includes a `pollSCM('H/5 * * * *')` trigger as a fallback — Jenkins polls the repo every 5 minutes even if the webhook never fires, so your pipeline still runs (just less instantly). Remove it once you've confirmed the webhook works, to avoid double-triggering.

### Triggering on pull requests specifically

For real PR-triggered builds (build the PR's merge commit, report status back to GitHub), use a **Multibranch Pipeline** job instead of a single Pipeline job — it auto-discovers branches and PRs via the GitHub Branch Source plugin and needs no manual webhook wiring beyond installing that plugin and pointing it at your GitHub org/repo.

---

## Running it end-to-end, start to finish

1. `docker compose -f jenkins-docker-compose.yml up -d` → configure Jenkins (Task 1).
2. `cd app && docker build -t ci-cd-lab-app:local . && docker run --rm -p 5000:5000 ci-cd-lab-app:local` → confirm the app works (Task 2).
3. Push this whole folder to a GitHub repo.
4. Create the Pipeline job pointing at that repo + `Jenkinsfile` (Task 3).
5. Add the GitHub webhook (Task 4).
6. Commit something small (e.g. edit the message string in `app.py`) and push — watch Jenkins pick it up automatically and run all five stages.

## What to say in your viva

- **Why multi-stage Docker build?** Smaller final image, no leftover build tooling/cache in the shipped artifact.
- **Why test inside the built image rather than on the Jenkins host?** Guarantees the tested artifact is byte-for-byte the deployed artifact.
- **Why tag with `BUILD_NUMBER` instead of only `latest`?** `latest` is mutable and gives you no way to roll back to a specific known-good build; a numbered tag does.
- **Why a webhook over polling?** Webhooks are push-based (event-driven, near-instant); polling wastes resources and adds latency proportional to the poll interval.
- **What does "CI" vs "CD" mean here?** Checkout+Build+Test = Continuous *Integration* (verifying every commit is good); Push+Deploy = Continuous *Deployment* (automatically shipping that verified commit).

## Going further (optional, for extra credit / innovation points)

- Swap Flask's dev server for **gunicorn** in the `Dockerfile` CMD for production-grade serving.
- Add a **Trivy** stage (`aroa/trivy-action` or CLI) to scan the built image for CVEs before pushing.
- Replace the raw SSH deploy stage with **AWS ECS** (`aws ecs update-service --force-new-deployment`) or **Kubernetes** (`kubectl set image`) for a more realistic production deploy story.
- Add a **rollback** stage that redeploys the previous `BUILD_NUMBER` tag automatically if the smoke test fails.
