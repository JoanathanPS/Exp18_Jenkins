// Jenkinsfile — Declarative Pipeline for LAB EX18
//
// Stages: Checkout -> Build image -> Test (inside image) -> Deploy locally
//         -> Smoke test
//
// Deploy target: this Jenkins container itself talks to the HOST's Docker
// daemon (via the docker.sock mount in jenkins-docker-compose.yml, i.e.
// Docker-outside-of-Docker), so "deploy" here means: (re)start the
// container on this machine. No Docker Hub account or cloud VM required —
// same idea as the EX19 self-hosted-runner deploy, just driven by Jenkins
// instead of GitHub Actions. Swap the Deploy stage for a real
// docker push + SSH-to-EC2/GCE flow later if you want the literal
// "cloud platform" version (see commented-out block at the bottom).

pipeline {
    agent any

    environment {
        IMAGE_NAME = "ci-cd-lab-app"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                dir('Exp18/app') {
                    sh """
                        docker build \
                          --build-arg APP_VERSION=${IMAGE_TAG} \
                          -t ${IMAGE_NAME}:${IMAGE_TAG} \
                          -t ${IMAGE_NAME}:latest \
                          .
                    """
                }
            }
        }

        stage('Run Tests') {
            steps {
                // Run pytest *inside* a throwaway container from the image
                // we just built — proves the artifact being shipped is the
                // artifact being tested (no "works on my machine" drift).
                sh """
                    docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} \
                      sh -c "pip install --no-cache-dir pytest && python -m pytest tests/ -v"
                """
            }
        }

        stage('Deploy') {
            steps {
                // Redeploy on the same host Jenkins is running on.
                sh """
                    docker stop ci-cd-lab-app || true
                    docker rm ci-cd-lab-app || true
                    docker run -d --name ci-cd-lab-app \
                        -p 5050:5000 --restart unless-stopped \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
        }

        stage('Smoke Test') {
            steps {
                sh """
                    sleep 3
                    curl -sf http://host.docker.internal:5050/health || curl -sf http://localhost:5050/health
                """
            }
        }
    }

    post {
        success {
            echo "Build ${IMAGE_TAG} deployed successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo "Pipeline failed — check the stage logs above."
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}

/*
---- Going further: real cloud deploy (AWS EC2 example) ----
Replace the 'Deploy' stage above with something like:

stage('Push to Registry') {
    steps {
        withCredentials([usernamePassword(
                credentialsId: 'dockerhub-creds',
                usernameVariable: 'REG_USER',
                passwordVariable: 'REG_PASS')]) {
            sh """
                echo "$REG_PASS" | docker login -u "$REG_USER" --password-stdin
                docker push yourdockerhubuser/${IMAGE_NAME}:${IMAGE_TAG}
            """
        }
    }
}

stage('Deploy to Cloud (AWS EC2)') {
    steps {
        sshagent(credentials: ['ec2-ssh-key']) {
            sh """
                ssh -o StrictHostKeyChecking=no ec2-user@YOUR_EC2_IP '
                    docker pull yourdockerhubuser/${IMAGE_NAME}:${IMAGE_TAG} &&
                    docker stop ci-cd-lab-app || true &&
                    docker rm ci-cd-lab-app || true &&
                    docker run -d --name ci-cd-lab-app -p 80:5000 --restart unless-stopped \
                        yourdockerhubuser/${IMAGE_NAME}:${IMAGE_TAG}
                '
            """
        }
    }
}

This needs: a Docker Hub account + Jenkins credential 'dockerhub-creds'
(username/password), a running EC2 instance, and an SSH key added to
Jenkins as credential 'ec2-ssh-key'.
*/
