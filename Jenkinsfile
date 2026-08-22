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
// instead of GitHub Actions. See the commented-out block at the bottom for
// the real-cloud version if you want to upgrade this later.

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
                sh """
                    docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} \
                      sh -c "pip install --no-cache-dir pytest && python -m pytest tests/ -v"
                """
            }
        }

        stage('Deploy') {
            steps {
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
