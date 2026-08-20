// Jenkinsfile — Declarative Pipeline for LAB EX18
//
// Stages: Checkout -> Build image -> Test (inside image) -> Push to registry
//         -> Deploy to cloud (AWS EC2 over SSH) -> Smoke test
//
// Trigger: configured on the Jenkins job itself (GitHub webhook -> "GitHub
// hook trigger for GITScm polling", see README section 5) so this file
// doesn't need a `triggers {}' block, though one is included as a fallback.

pipeline {
    agent any

    // ---- Configuration: edit these for your environment ----
    environment {
        IMAGE_NAME     = "yourdockerhubuser/ci-cd-lab-app"
        IMAGE_TAG      = "${env.BUILD_NUMBER}"
        REGISTRY_CREDS = "dockerhub-creds"      // Jenkins credentials ID (username/password)
        DEPLOY_HOST    = "ec2-user@YOUR_EC2_PUBLIC_IP"
        DEPLOY_SSH_CREDS = "ec2-ssh-key"        // Jenkins credentials ID (SSH private key)
    }

    // Fallback poll every 5 min in case the webhook isn't reachable
    // (e.g. Jenkins is on localhost without a public URL). Remove once
    // the webhook is confirmed working.
    triggers {
        pollSCM('H/5 * * * *')
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
                dir('app') {
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
                // we just built — this proves the artifact being shipped is
                // the artifact being tested (no "works on my machine" drift).
                sh """
                    docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} \
                      sh -c "pip install --no-cache-dir pytest && python -m pytest tests/ -v"
                """
            }
        }

        stage('Push to Registry') {
            steps {
                withCredentials([usernamePassword(
                        credentialsId: "${REGISTRY_CREDS}",
                        usernameVariable: 'REG_USER',
                        passwordVariable: 'REG_PASS')]) {
                    sh """
                        echo "\$REG_PASS" | docker login -u "\$REG_USER" --password-stdin
                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('Deploy to Cloud (AWS EC2)') {
            steps {
                // SSH onto the EC2 host, pull the new image, and restart the
                // container. For GCP swap DEPLOY_HOST for a GCE instance and
                // this stage is unchanged (it's just SSH + docker).
                sshagent(credentials: ["${DEPLOY_SSH_CREDS}"]) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_HOST} '
                            docker pull ${IMAGE_NAME}:${IMAGE_TAG} &&
                            docker stop ci-cd-lab-app || true &&
                            docker rm ci-cd-lab-app || true &&
                            docker run -d --name ci-cd-lab-app \
                                -p 80:5000 --restart unless-stopped \
                                ${IMAGE_NAME}:${IMAGE_TAG}
                        '
                    """
                }
            }
        }

        stage('Smoke Test') {
            steps {
                sh """
                    sleep 5
                    curl -sf http://\$(echo ${DEPLOY_HOST} | cut -d@ -f2)/health
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
