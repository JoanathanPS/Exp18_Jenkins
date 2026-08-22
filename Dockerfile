# Custom Jenkins image with the Docker CLI baked in.
#
# Why this exists: jenkins-docker-compose.yml uses Docker-outside-of-Docker
# (mounting the HOST's docker.sock so Jenkins can talk to the host's Docker
# engine) but the stock jenkins/jenkins image has no `docker` binary at all.
#
# This copies the CLI binary directly out of Docker's own official
# docker:cli image via a multi-stage build -- the binary ships with correct
# permissions already, sidestepping any apt/GPG-key flakiness.

FROM docker:27-cli AS dockercli

FROM jenkins/jenkins:lts-jdk17

USER root
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
RUN chmod 755 /usr/local/bin/docker
USER jenkins
