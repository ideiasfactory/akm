# GitHub Actions Secrets - Best Practices

## 🔒 Security Overview

GitHub Actions secrets are **encrypted environment variables** that allow you to store sensitive information securely. Even in public repositories, secrets remain private and are only accessible to repository owners and collaborators with appropriate permissions.

## ✅ What Makes Secrets Secure

### 1. **Automatic Protection**
- ✅ Secrets are **encrypted at rest** using AES-256
- ✅ **Masked in logs** - GitHub automatically redacts secret values
- ✅ **Not accessible to fork PRs** - Pull requests from forks don't have access
- ✅ **Audit logging** - All secret access is tracked

### 2. **Access Control**
- Only repository owners/admins can create/edit secrets
- Collaborators cannot view secret values (only names)
- Organization secrets can have fine-grained access policies

## 🛡️ Security Best Practices

### ✅ DO: Safe Practices

#### 1. **Use Secrets for All Sensitive Data**
```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_TOKEN: ${{ secrets.API_TOKEN }}
```

#### 2. **Never Log Secrets**
```python
# ❌ NEVER do this
print(f"Connection string: {os.getenv('DATABASE_URL')}")
logger.info(f"Token: {api_token}")

# ✅ DO this instead
logger.info("Connecting to database...")
logger.info("Authentication successful")
```

#### 3. **Use Environment-Specific Secrets**
```yaml
jobs:
  deploy:
    environment: production  # Uses production secrets
    runs-on: ubuntu-latest
```

#### 4. **Implement Least Privilege Access**
- Create database users with minimal permissions
- Use read-only tokens when possible
- Scope API keys to specific resources

```sql
-- Example: Limited database user
CREATE USER app_updater WITH PASSWORD '***';
GRANT SELECT, INSERT, UPDATE ON specific_table TO app_updater;
-- NO DELETE, DROP, or admin permissions
```

#### 5. **Rotate Secrets Regularly**
- Schedule rotation every 3-6 months
- Rotate immediately if compromise is suspected
- Use calendar reminders for rotation

#### 6. **Use GitHub-Hosted Runners**
```yaml
runs-on: ubuntu-latest  # ✅ Secure, isolated environment
# Not: runs-on: self-hosted  # ⚠️ Requires additional security
```

### ❌ DON'T: Dangerous Practices

#### 1. **Never Commit Secrets to Git**
```bash
# Always use .gitignore
.env
.env.local
*.key
*.pem
secrets/
```

#### 2. **Don't Echo or Print Secrets**
```yaml
# ❌ DANGEROUS
- run: echo "Secret is ${{ secrets.MY_SECRET }}"
- run: env | grep SECRET

# ✅ SAFE
- run: echo "Connecting with credentials..."
```

#### 3. **Don't Store Secrets in Code Comments**
```python
# ❌ NEVER
# DATABASE_URL = "postgresql://user:password@host:5432/db"

# ✅ ALWAYS use environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
```

#### 4. **Don't Use Secrets in URLs or Filenames**
```yaml
# ❌ BAD - Token appears in logs
- run: curl https://api.example.com?token=${{ secrets.API_TOKEN }}

# ✅ GOOD - Token in header
- run: curl -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" https://api.example.com
```

## 🔍 Common Attack Vectors

### 1. **Malicious Dependencies**
**Risk:** Compromised packages can read environment variables

**Mitigation:**
- Pin dependency versions in `requirements.txt`
- Use dependency scanning (Dependabot, Snyk)
- Review dependency updates before merging
- Consider using hash-based pinning:
  ```bash
  pip install --require-hashes -r requirements.txt
  ```

### 2. **Pull Request Exploits**
**Risk:** Malicious PR tries to exfiltrate secrets

**GitHub Protection:**
- Forks don't have access to secrets by default
- First-time contributors require approval
- You can review workflow changes before approval

**Additional Protection:**
```yaml
on:
  pull_request_target:  # Be careful with this trigger
    types: [labeled]     # Only run on specific label
```

### 3. **Log Injection**
**Risk:** Attacker crafts input to expose secrets in logs

**Mitigation:**
- Validate and sanitize all inputs
- Never use user input in log messages directly
- Use structured logging with field separation

```python
# ❌ Vulnerable
logger.info(f"Processing: {user_input}")

# ✅ Safe
logger.info("Processing user input", extra={"input_length": len(user_input)})
```

### 4. **Self-Hosted Runner Compromise**
**Risk:** Malware on self-hosted runner steals secrets

**Mitigation:**
- Use GitHub-hosted runners when possible
- Isolate self-hosted runners (containers, VMs)
- Regularly update and scan runner systems
- Never run untrusted code on self-hosted runners

## 🔐 Additional Security Layers

### 1. **IP Whitelisting**
If your service supports it, restrict access to GitHub Actions IPs:

```bash
# GitHub Actions IP ranges
curl https://api.github.com/meta | jq -r '.actions[]'
```

### 2. **Time-Limited Tokens**
Use tokens that expire automatically:
- OAuth tokens with refresh flow
- Temporary credentials (AWS STS, Azure Managed Identity)
- JWT with short expiration

### 3. **Secret Scanning**
Enable GitHub's secret scanning:
- Settings → Security → Secret scanning
- Alerts for accidentally committed secrets
- Partner patterns (AWS, Azure, Google, etc.)

### 4. **Environment Protection Rules**
Add manual approval gates:

```yaml
jobs:
  deploy:
    environment:
      name: production
      url: https://your-app.com
    runs-on: ubuntu-latest
```

Settings → Environments → Production:
- ✅ Required reviewers
- ✅ Wait timer
- ✅ Deployment branches

## 📊 Security Checklist

Before deploying workflows with secrets:

- [ ] All sensitive data stored as secrets (not in code)
- [ ] No secrets logged or printed in workflows
- [ ] `.gitignore` includes all local credential files
- [ ] Dependencies pinned and reviewed
- [ ] Using GitHub-hosted runners
- [ ] Secret scanning enabled
- [ ] Dependabot alerts enabled
- [ ] Least privilege database/API access configured
- [ ] Rotation schedule established (calendar reminder)
- [ ] Team members know not to log secrets
- [ ] Pull request reviews required before merge

## 🚨 Incident Response

If a secret is compromised:

1. **Immediately rotate the secret**
   - Generate new credentials
   - Update in GitHub Settings → Secrets
   - Revoke old credentials

2. **Audit access logs**
   - Check database/API access logs
   - Review GitHub audit log
   - Identify unauthorized access

3. **Update dependent services**
   - Notify affected systems
   - Update connection strings
   - Verify new credentials work

4. **Post-mortem**
   - Document how compromise occurred
   - Implement additional safeguards
   - Update team training

## 📚 Additional Resources

- [GitHub Docs: Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Docs: Security Hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Actions Security Best Practices](https://github.com/step-security/github-actions-goat)

## 🎓 Summary

**GitHub Actions secrets are secure by default**, but security requires vigilance:

- ✅ Use secrets for all sensitive data
- ✅ Never log secret values
- ✅ Rotate secrets regularly
- ✅ Review dependencies and PRs
- ✅ Use least privilege access
- ✅ Enable all GitHub security features

**Remember:** The weakest link in security is usually human error, not the technology. Train your team and follow these practices consistently.

---

**Last Updated:** November 2025  
**Review Schedule:** Quarterly
