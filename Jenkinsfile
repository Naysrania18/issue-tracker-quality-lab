// Declarative pipeline equivalent to .github/workflows/ci.yml.
// Agent requirements: Linux with Python 3.10+, JDK 17+, Maven, Google Chrome. Swift is optional.
// Plugins used: JUnit, Pipeline, HTML Publisher (optional).
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        COVERAGE_THRESHOLD = '85'
        TRACKER_DB = "${WORKSPACE}/ci.db"
        VENV = "${WORKSPACE}/.venv"
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv "$VENV"
                    "$VENV/bin/pip" install -q -r requirements.txt -r requirements-dev.txt
                '''
            }
        }

        stage('Lint and types') {
            steps {
                sh '"$VENV/bin/ruff" check .'
                sh '"$VENV/bin/mypy" app qtools mcp_server agent'
            }
        }

        stage('Python tests') {
            steps {
                // Quality gates: zero failed smoke tests, then coverage threshold on the full run.
                sh '"$VENV/bin/pytest" -m smoke -q'
                sh '''
                    "$VENV/bin/pytest" -q --junitxml=reports/junit/run-001.xml \
                        --cov=app --cov=qtools --cov=mcp_server --cov=agent \
                        --cov-report=xml:reports/coverage.xml --cov-report=html:reports/htmlcov \
                        --cov-fail-under="$COVERAGE_THRESHOLD"
                '''
            }
            post { always { junit 'reports/junit/*.xml' } }
        }

        stage('Selenium UI') {
            steps {
                sh '"$VENV/bin/pytest" ui_tests -m smoke -q'
                sh '"$VENV/bin/pytest" ui_tests -v --junitxml=reports/ui-junit.xml'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/ui-junit.xml'
                    archiveArtifacts artifacts: 'screenshots/**', allowEmptyArchive: true
                }
            }
        }

        stage('Java API tests') {
            steps {
                sh '''
                    nohup "$VENV/bin/python" -m uvicorn app.main:app --port 8000 --log-level warning > uvicorn.log 2>&1 &
                    echo $! > uvicorn.pid
                    for i in $(seq 1 30); do curl -sf http://127.0.0.1:8000/api/health && break; sleep 1; done
                '''
                dir('java-api-tests') {
                    sh 'mvn -B test'
                }
            }
            post {
                always {
                    sh 'kill $(cat uvicorn.pid) || true'
                    junit allowEmptyResults: true, testResults: 'java-api-tests/target/surefire-reports/*.xml'
                    archiveArtifacts artifacts: 'java-api-tests/target/allure-results/**', allowEmptyArchive: true
                }
            }
        }

        stage('Swift XCTest') {
            when { expression { sh(returnStatus: true, script: 'command -v swift') == 0 } }
            steps {
                dir('swift-client') {
                    sh 'swift test --xunit-output ../swift-xunit.xml'
                }
            }
            post { always { archiveArtifacts artifacts: 'swift-xunit*.xml', allowEmptyArchive: true } }
        }

        stage('Quality report') {
            steps {
                // Exits with code 1 (failing the build) when the decision is NO-GO, e.g. any open P1.
                sh '''
                    "$VENV/bin/python" -m qtools readiness --junit-dir reports/junit \
                        --issues-file data/release_candidate_issues.json \
                        --coverage-xml reports/coverage.xml --out-dir reports/readiness --fail-on-no-go
                '''
            }
            post { always { archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true } }
        }
    }
}
