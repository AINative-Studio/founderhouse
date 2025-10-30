# DevOps Setup Checklist - AI Chief of Staff

Use this checklist to verify your DevOps infrastructure is properly configured.

## Phase 1: Local Development Setup

### Prerequisites
- [ ] Python 3.11+ installed (`python3 --version`)
- [ ] Docker Desktop installed and running
- [ ] Git installed (`git --version`)
- [ ] Make installed (`make --version`)

### Environment Setup
- [ ] Repository cloned
- [ ] `.env` file created from `.env.example`
- [ ] Supabase account created
- [ ] Supabase project created
- [ ] Supabase credentials added to `.env`
- [ ] Secret keys generated and added to `.env`

### Local Services
- [ ] Docker services start successfully (`make docker-up`)
- [ ] PostgreSQL is healthy (`docker-compose ps`)
- [ ] Redis is healthy (`docker-compose ps`)
- [ ] API responds at http://localhost:8000
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] Health check passes (`curl http://localhost:8000/health`)

### Development Tools
- [ ] Virtual environment created (`python3 -m venv venv`)
- [ ] Dependencies installed (`make install`)
- [ ] Dev dependencies installed (`make install-dev`)
- [ ] Pre-commit hooks installed (`pre-commit install`)
- [ ] Tests run successfully (`make test`)
- [ ] Coverage meets threshold (`make test-cov`)

## Phase 2: GitHub Configuration

### Repository Setup
- [ ] Repository created on GitHub
- [ ] Local repository connected to remote
- [ ] Main branch protected
- [ ] Branch protection rules configured

### GitHub Actions
- [ ] CI workflow file exists (`.github/workflows/ci.yml`)
- [ ] Staging deployment workflow exists (`.github/workflows/deploy-staging.yml`)
- [ ] Production deployment workflow exists (`.github/workflows/deploy-production.yml`)
- [ ] Workflows enabled in repository settings

### GitHub Secrets
- [ ] `RAILWAY_TOKEN` secret added
- [ ] `RAILWAY_PROJECT_ID` secret added
- [ ] `PRODUCTION_API_KEY` secret added
- [ ] `CODECOV_TOKEN` secret added (optional)

## Phase 3: Railway Setup

### Account & Project
- [ ] Railway account created
- [ ] Railway CLI installed (`railway --version`)
- [ ] Logged into Railway CLI (`railway login`)
- [ ] Railway project created
- [ ] Project linked locally (`railway link`)

### Database Services
- [ ] PostgreSQL plugin added
- [ ] Redis plugin added (optional)
- [ ] Database credentials verified
- [ ] pgvector extension enabled in Supabase

### Environments
- [ ] Staging environment created
- [ ] Production environment created
- [ ] Can switch between environments

### Environment Variables (Staging)
- [ ] `API_ENV=staging`
- [ ] `SECRET_KEY` set (generated)
- [ ] `JWT_SECRET_KEY` set (generated)
- [ ] `SUPABASE_URL` set
- [ ] `SUPABASE_ANON_KEY` set
- [ ] `SUPABASE_SERVICE_KEY` set
- [ ] `ALLOWED_ORIGINS` set
- [ ] `LOG_LEVEL=DEBUG`

### Environment Variables (Production)
- [ ] `API_ENV=production`
- [ ] `SECRET_KEY` set (different from staging)
- [ ] `JWT_SECRET_KEY` set (different from staging)
- [ ] `SUPABASE_URL` set (production instance)
- [ ] `SUPABASE_ANON_KEY` set
- [ ] `SUPABASE_SERVICE_KEY` set
- [ ] `ALLOWED_ORIGINS` set (production domains)
- [ ] `LOG_LEVEL=INFO`
- [ ] `SENTRY_DSN` set (optional)

## Phase 4: CI/CD Verification

### Continuous Integration
- [ ] Push triggers CI workflow
- [ ] Pull requests trigger CI workflow
- [ ] Linting passes
- [ ] Tests pass
- [ ] Security scans complete
- [ ] Docker image builds successfully
- [ ] Coverage reports generated

### Staging Deployment
- [ ] Push to main triggers staging deployment
- [ ] Railway receives deployment
- [ ] Database migrations run
- [ ] Health checks pass
- [ ] Smoke tests pass
- [ ] Deployment URL accessible

### Production Deployment
- [ ] Manual workflow can be triggered
- [ ] Confirmation required
- [ ] Deployment succeeds
- [ ] Migrations run successfully
- [ ] Health checks pass
- [ ] Comprehensive smoke tests pass

## Phase 5: Testing & Validation

### Local Testing
- [ ] Unit tests pass (`make test-unit`)
- [ ] Integration tests pass (`make test-integration`)
- [ ] Coverage above 80% (`make test-cov`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Security checks pass (`make security-check`)

### Docker Testing
- [ ] Docker build succeeds (`make docker-build`)
- [ ] All services start (`make docker-up`)
- [ ] Services are healthy
- [ ] API accessible via Docker
- [ ] Database accessible
- [ ] Redis accessible

### Deployment Testing
- [ ] Staging deployment successful
- [ ] Health endpoint responds (staging)
- [ ] Version endpoint responds (staging)
- [ ] API docs accessible (staging)
- [ ] Database connection verified (staging)

## Phase 6: Documentation

### Required Documentation
- [ ] README.md updated
- [ ] CONTRIBUTING.md complete
- [ ] DEPLOYMENT.md complete
- [ ] INFRASTRUCTURE.md complete
- [ ] DEVOPS_SETUP_SUMMARY.md complete
- [ ] QUICK_REFERENCE.md available

### Optional Documentation
- [ ] API documentation generated
- [ ] Architecture diagrams created
- [ ] Runbooks created
- [ ] Troubleshooting guide updated

## Phase 7: Security

### Secret Management
- [ ] No secrets in code
- [ ] `.env` in `.gitignore`
- [ ] Secrets in Railway variables
- [ ] GitHub secrets configured
- [ ] Pre-commit hook detects secrets

### Container Security
- [ ] Non-root user in Dockerfile
- [ ] Multi-stage build used
- [ ] Security scanning enabled
- [ ] Minimal base image used

### Application Security
- [ ] CORS configured
- [ ] Rate limiting ready
- [ ] Input validation enabled
- [ ] Authentication ready
- [ ] RLS policies ready (Supabase)

## Phase 8: Monitoring & Observability

### Health Checks
- [ ] Health endpoint implemented
- [ ] Version endpoint implemented
- [ ] Railway health checks configured
- [ ] Liveness probe working
- [ ] Readiness probe working

### Logging
- [ ] Structured logging configured
- [ ] Log levels set correctly
- [ ] Logs viewable in Railway
- [ ] Error tracking configured (optional)

### Metrics
- [ ] Railway metrics accessible
- [ ] CPU usage visible
- [ ] Memory usage visible
- [ ] Request count visible
- [ ] Response time visible

## Phase 9: Rollback & Recovery

### Rollback Capability
- [ ] Previous deployments accessible
- [ ] Railway rollback tested
- [ ] Database rollback procedure documented
- [ ] Automatic rollback configured (staging)

### Backup & Recovery
- [ ] Supabase automatic backups enabled
- [ ] Recovery procedure documented
- [ ] Database backup verified
- [ ] Point-in-time recovery tested (optional)

## Phase 10: Final Verification

### Infrastructure Complete
- [ ] All files created (31 files)
- [ ] All workflows tested
- [ ] All environments configured
- [ ] All documentation complete

### Operational Readiness
- [ ] Team trained on deployment process
- [ ] Runbooks accessible
- [ ] Emergency contacts documented
- [ ] Escalation procedures defined

### Production Readiness
- [ ] Security audit passed
- [ ] Performance tested
- [ ] Load tested (optional)
- [ ] Disaster recovery plan created
- [ ] Monitoring alerts configured

## Success Criteria

### Must Have (Blocking)
- [x] CI/CD pipeline functional
- [x] Staging environment deployed
- [x] Tests passing with 80%+ coverage
- [x] Security scanning enabled
- [x] Documentation complete
- [x] Health checks working
- [ ] Production environment configured
- [ ] Rollback tested

### Should Have (Important)
- [x] Pre-commit hooks working
- [x] Docker local development working
- [x] Comprehensive test suite
- [x] Code quality tools configured
- [ ] Monitoring setup
- [ ] Error tracking (Sentry)

### Nice to Have (Optional)
- [ ] Performance testing
- [ ] Load testing
- [ ] Chaos engineering
- [ ] Advanced metrics
- [ ] Custom dashboards

## Post-Setup Tasks

### Immediate
1. [ ] Test full deployment cycle (local → staging → production)
2. [ ] Verify all team members have access
3. [ ] Schedule security review
4. [ ] Set up monitoring alerts

### Week 1
1. [ ] Monitor staging deployments
2. [ ] Review CI/CD performance
3. [ ] Optimize build times
4. [ ] Train team on workflows

### Month 1
1. [ ] Review and optimize costs
2. [ ] Performance tuning
3. [ ] Security audit
4. [ ] Documentation updates

## Troubleshooting

If any checklist item fails:

1. **Check logs**: `make docker-logs` or `railway logs`
2. **Verify environment**: `make env-check`
3. **Review documentation**: See CONTRIBUTING.md
4. **Check GitHub Actions**: View workflow runs
5. **Verify Railway**: Check Railway dashboard

## Help & Support

- **Quick Help**: See QUICK_REFERENCE.md
- **Development**: See CONTRIBUTING.md
- **Deployment**: See DEPLOYMENT.md
- **Infrastructure**: See INFRASTRUCTURE.md
- **Full Summary**: See DEVOPS_SETUP_SUMMARY.md

---

**Checklist Version**: 1.0.0
**Last Updated**: 2025-10-30

**Status Key**:
- [x] = Completed by DevOps setup
- [ ] = Requires user action
