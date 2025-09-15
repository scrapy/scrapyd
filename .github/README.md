# GitHub Actions Workflows

This directory contains comprehensive GitHub Actions workflows to support the Scrapyd project with automated testing, building, security scanning, and deployment.

## Workflow Overview

### 🔄 [CI/CD Pipeline](workflows/ci.yml)
**Trigger:** Push to any branch, Pull Requests to master/develop

Comprehensive continuous integration and deployment pipeline with:

- **Code Quality & Linting**: Ruff formatting and linting checks
- **Multi-Version Testing**: Python 3.10, 3.11, 3.12 compatibility
- **Integration Tests**: Full integration test suite with server fixtures
- **Coverage Reporting**: Code coverage with Codecov integration
- **Security Scanning**: Safety, Bandit security analysis
- **Package Building**: Test package building and validation
- **Docker Testing**: Docker image build and basic functionality tests
- **Performance Tests**: Automated benchmarks (master branch only)

### 🐳 [Docker Build & Push](workflows/docker.yml)
**Trigger:** Push to master, tags, Pull Requests

Multi-architecture Docker image management:

- **Multi-Platform Builds**: Linux AMD64 and ARM64 support
- **Automated Tagging**: Semantic versioning, branch-based, and SHA tags
- **Registry Publishing**: GitHub Container Registry (ghcr.io)
- **Security Scanning**: Trivy vulnerability scanning
- **Documentation Sync**: Automated Docker Hub README updates

### 🚀 [Release Automation](workflows/release.yml)
**Trigger:** Git tags (v*)

Automated release process:

- **Version Validation**: Semantic version parsing and validation
- **Release Creation**: Automated GitHub releases with changelog
- **PyPI Publishing**: Automatic publishing to PyPI (stable) and TestPyPI (pre-release)
- **Docker Deployment**: Triggered Docker image builds for releases
- **Documentation Updates**: Automated docs deployment to GitHub Pages

### 🔒 [Security & Dependencies](workflows/security.yml)
**Trigger:** Daily schedule, manual dispatch, push to master

Comprehensive security monitoring:

- **Vulnerability Scanning**: Safety, Bandit, Semgrep, CodeQL analysis
- **Dependency Auditing**: pip-audit for known vulnerabilities
- **License Compliance**: Automated license checking
- **Automated Updates**: Daily dependency updates with PR creation
- **Security Reporting**: Consolidated security status reports

### ☁️ [Cloud Run Deployment](workflows/deploy-cloudrun.yml)
**Trigger:** Manual dispatch, push to master (with file changes)

Production-ready Cloud Run deployments:

- **Environment Management**: Staging and Production environments
- **Pre-deployment Testing**: Comprehensive test suite execution
- **Blue-Green Deployment**: Zero-downtime deployments with rollback
- **Health Verification**: Post-deployment smoke tests
- **Rollback Capabilities**: Automatic rollback on deployment failures

## Setup Requirements

### Repository Secrets

Configure these secrets in your GitHub repository settings:

#### Required for Docker & Release
- `DOCKERHUB_USERNAME`: Docker Hub username (optional, for README sync)
- `DOCKERHUB_TOKEN`: Docker Hub access token (optional)

#### Required for Cloud Run Deployment
- `GCP_PROJECT_ID`: Google Cloud Project ID
- `GCP_SERVICE_ACCOUNT_KEY`: Service account JSON key with Cloud Run permissions

#### Optional for Enhanced Features
- `CODECOV_TOKEN`: Codecov upload token for coverage reports

### Repository Variables

Configure these variables for Cloud Run deployment:

- `GCP_REGION`: Google Cloud region (e.g., `us-central1`)
- `CLOUDRUN_SERVICE_NAME`: Cloud Run service name

### Branch Protection

Recommended branch protection rules for `master`:

```yaml
Protection Rules:
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Required status checks:
  - Code Quality & Linting
  - Unit Tests (3.10, 3.11, 3.12)
  - Integration Tests
  - Package Build Test
  - Docker Build Test
```

## Workflow Details

### CI/CD Pipeline Jobs

1. **quality-checks**: Code formatting, linting, and type checking
2. **unit-tests**: Multi-version Python testing matrix
3. **integration-tests**: Full integration test suite
4. **coverage**: Test coverage reporting and upload
5. **security-scan**: Security vulnerability analysis
6. **package-build**: Python package building and validation
7. **docker-build**: Docker image build testing
8. **performance-tests**: Benchmark execution (master only)
9. **status-check**: Overall pipeline status validation

### Docker Workflow Features

- **Multi-platform builds**: AMD64 and ARM64 architectures
- **Smart tagging strategy**:
  - `latest` for master branch
  - `vX.Y.Z` for release tags
  - `branch-SHA` for feature branches
  - `pr-NUMBER` for pull requests
- **Security integration**: Trivy scanning with SARIF upload
- **Build caching**: GitHub Actions cache for faster builds

### Release Workflow Process

1. **Tag Validation**: Semantic version validation
2. **Comprehensive Testing**: Full test suite execution
3. **Package Building**: Python package creation and validation
4. **Release Creation**: GitHub release with automated notes
5. **Distribution**: PyPI publishing (stable) or TestPyPI (pre-release)
6. **Documentation**: GitHub Pages deployment

### Security Workflow Capabilities

- **Daily Scanning**: Automated daily security checks
- **Multiple Tools**: Safety, Bandit, Semgrep, CodeQL, pip-audit
- **SARIF Integration**: Security results uploaded to GitHub Security tab
- **Dependency Updates**: Automated PRs for dependency updates
- **License Monitoring**: License compliance verification

### Cloud Run Deployment Features

- **Environment Isolation**: Separate staging and production workflows
- **Pre-deployment Validation**: Tests must pass before deployment
- **Health Checks**: Comprehensive post-deployment verification
- **Rollback Support**: Automatic rollback on deployment failures
- **Manual Override**: Force deployment option for emergency releases

## Usage Examples

### Manual Deployment

Deploy to staging:
```bash
# Via GitHub UI: Actions → Deploy to Cloud Run → Run workflow
# Select: staging environment
```

Deploy to production:
```bash
# Via GitHub UI: Actions → Deploy to Cloud Run → Run workflow
# Select: production environment
```

### Release Process

Create a new release:
```bash
git tag v1.2.3
git push origin v1.2.3
# Automated release workflow triggers
```

### Security Scan

Run manual security scan:
```bash
# Via GitHub UI: Actions → Security & Dependency Updates → Run workflow
```

## Monitoring & Maintenance

### Workflow Status

Monitor workflow health:
- Check Actions tab for recent runs
- Review security scan results in Security tab
- Monitor deployment status in Environments tab

### Dependency Updates

- Automated PRs created daily for dependency updates
- Review and merge dependency update PRs regularly
- Security vulnerabilities trigger immediate notifications

### Performance Monitoring

- Performance tests run on master branch commits
- Benchmark results stored as artifacts
- Compare performance across releases

## Troubleshooting

### Common Issues

1. **Failed Tests**: Review test logs in Actions tab
2. **Docker Build Failures**: Check Dockerfile and dependencies
3. **Deployment Failures**: Verify GCP credentials and permissions
4. **Security Scan Failures**: Review security scan artifacts

### Debug Mode

Enable debug logging by adding these secrets:
- `ACTIONS_STEP_DEBUG`: `true`
- `ACTIONS_RUNNER_DEBUG`: `true`

### Manual Intervention

For critical issues:
1. Use `workflow_dispatch` triggers for manual runs
2. Use `force_deploy` option for emergency deployments
3. Monitor rollback procedures in Cloud Run console

## Best Practices

### Development Workflow

1. Create feature branches from `develop`
2. Ensure all CI checks pass before creating PR
3. Review security scan results
4. Test Docker builds locally before pushing

### Release Management

1. Use semantic versioning for tags
2. Test releases in staging environment first
3. Monitor deployment health after production releases
4. Keep release notes updated

### Security

1. Regularly review security scan results
2. Update dependencies promptly
3. Monitor for new vulnerabilities
4. Keep secrets and tokens secure

This comprehensive GitHub Actions setup provides enterprise-grade CI/CD capabilities for the Scrapyd project with automated testing, security scanning, and deployment workflows.