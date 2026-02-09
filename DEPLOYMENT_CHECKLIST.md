# Deployment Checklist
## ML Portfolio - mvanslyke-ml.com

Use this checklist to ensure everything is configured correctly.

---

## ☑️ Pre-Deployment Checklist

### AWS Account Setup

- [ ] AWS account created and verified
- [ ] Credit card added to AWS account
- [ ] AWS CLI installed locally
- [ ] AWS credentials configured (`aws configure`)
- [ ] Can run `aws sts get-caller-identity` successfully

### Domain Setup

- [ ] Domain registered (mvanslyke-ml.com)
- [ ] Access to DNS management (Route 53 or external provider)
- [ ] Can add DNS records

### Local Environment

- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] GitHub account created
- [ ] Code editor installed (VSCode, Sublime, etc.)

---

## ☑️ AWS Infrastructure Setup

### S3 Buckets

- [ ] Website bucket created: `mvanslyke-ml.com`
- [ ] Static website hosting enabled on bucket
- [ ] Bucket policy set for public read access
- [ ] Public access block removed
- [ ] Models bucket created: `mvanslyke-ml-models`
- [ ] Can access: `http://mvanslyke-ml.com.s3-website-us-east-1.amazonaws.com`

### CloudFront Distribution

- [ ] CloudFront distribution created
- [ ] Origin set to S3 website endpoint (not bucket!)
- [ ] Default root object set to: `index.html`
- [ ] Viewer protocol policy set to: Redirect HTTP to HTTPS
- [ ] Distribution status: Deployed
- [ ] Can access: `https://[distribution-id].cloudfront.net`
- [ ] Distribution ID saved for GitHub Secrets

### SSL Certificate (ACM)

- [ ] Certificate requested in us-east-1 region
- [ ] DNS validation records added
- [ ] Certificate status: Issued
- [ ] Certificate ARN saved

### CloudFront Custom Domain

- [ ] Alternate domain name (CNAME) added: `mvanslyke-ml.com`
- [ ] SSL certificate attached to distribution
- [ ] DNS A record points to CloudFront
- [ ] Can access: `https://mvanslyke-ml.com`

### IAM Roles

- [ ] IAM role created: `MLPortfolioLambdaRole`
- [ ] Basic execution policy attached
- [ ] S3 read-only access attached

---

## ☑️ GitHub Repository Setup

### Repository Configuration

- [ ] GitHub repository created: `ml-portfolio`
- [ ] Repository cloned locally
- [ ] All project files copied to repository
- [ ] Directory structure created:
  - [ ] `website/`
  - [ ] `projects/`
  - [ ] `models/`
  - [ ] `scripts/`
  - [ ] `.github/workflows/`

### GitHub Secrets

- [ ] `AWS_ACCESS_KEY_ID` added
- [ ] `AWS_SECRET_ACCESS_KEY` added
- [ ] `CLOUDFRONT_DISTRIBUTION_ID` added
- [ ] Secrets verified (no typos)

### GitHub Actions Workflow

- [ ] Workflow file exists: `.github/workflows/deploy.yml`
- [ ] Workflow syntax is valid
- [ ] Can trigger workflow manually

---

## ☑️ Website Files

### Core Files

- [ ] `website/index.html` exists
- [ ] `website/styles.css` exists
- [ ] `website/app.js` exists
- [ ] Personal information updated in `index.html`:
  - [ ] Name updated
  - [ ] Email updated
  - [ ] GitHub link updated
  - [ ] LinkedIn link updated
  - [ ] Stats updated

### Content Files

- [ ] At least one project created in `projects/`
- [ ] Project has valid YAML frontmatter
- [ ] `projects.json` can be generated successfully
- [ ] Website loads correctly locally (`python3 -m http.server 8000`)

---

## ☑️ Deployment Scripts

### Python Dependencies

- [ ] `boto3` installed
- [ ] `pyyaml` installed
- [ ] Can run: `python3 scripts/generate_projects.py`
- [ ] Can run: `python3 scripts/deploy_lambda.py`
- [ ] Can run: `python3 scripts/update_api_gateway.py`

### Script Configuration

- [ ] S3 bucket name correct in scripts: `mvanslyke-ml.com`
- [ ] Models bucket correct: `mvanslyke-ml-models`
- [ ] Domain correct: `mvanslyke-ml.com`
- [ ] API domain correct: `api.mvanslyke-ml.com`

---

## ☑️ ML Model Setup (Optional)

### Model Files

- [ ] Model directory created: `models/[model-name]/`
- [ ] `config.yml` file created
- [ ] `lambda_function.py` file created
- [ ] `requirements.txt` file created
- [ ] Model file added (if < 40 MB)
- [ ] Config has correct values:
  - [ ] `name` field
  - [ ] `memory` field
  - [ ] `timeout` field
  - [ ] `api_route` field

### Lambda Testing

- [ ] Can package model locally
- [ ] Package size < 50 MB (or uploaded to S3 separately)
- [ ] Lambda function can be created manually
- [ ] Lambda function can be invoked successfully

---

## ☑️ First Deployment

### Initial Push

- [ ] All files committed to git
- [ ] Files pushed to GitHub main branch
- [ ] GitHub Actions workflow triggered
- [ ] All jobs completed successfully:
  - [ ] Deploy Website to S3
  - [ ] Deploy Lambda Functions (if models exist)
  - [ ] Update Projects with Lambda Demos

### Verification

- [ ] Website accessible at: `https://mvanslyke-ml.com`
- [ ] Projects appear on website
- [ ] Styles load correctly
- [ ] JavaScript works (particles, filters, etc.)
- [ ] No console errors (F12)

### API Verification (if models deployed)

- [ ] API Gateway created
- [ ] API endpoints documented in `.build/api_docs.json`
- [ ] Can call API with curl
- [ ] CORS headers present in response
- [ ] Demo button works on website

---

## ☑️ Post-Deployment Testing

### Website Testing

- [ ] Test on desktop browser
- [ ] Test on mobile browser
- [ ] Test all navigation links
- [ ] Test project filters
- [ ] Test demo modal (if applicable)
- [ ] Test contact links

### Performance Testing

- [ ] Website loads in < 3 seconds
- [ ] Images optimized and compressed
- [ ] CloudFront cache working (check response headers)
- [ ] No 404 errors
- [ ] HTTPS working (lock icon in browser)

### SEO & Metadata

- [ ] Page title set correctly
- [ ] Meta description set
- [ ] Favicon added (optional)
- [ ] Google Analytics added (optional)

---

## ☑️ Ongoing Operations

### Daily Workflow

- [ ] Can add new projects by creating markdown files
- [ ] Can deploy new models by adding model directories
- [ ] Can update website by editing files
- [ ] All changes auto-deploy on git push

### Monitoring Setup

- [ ] CloudWatch logs accessible
- [ ] Can view GitHub Actions logs
- [ ] Cost Explorer enabled in AWS
- [ ] Billing alerts set up (recommended)

### Backup & Recovery

- [ ] Repository backed up on GitHub
- [ ] Important files version controlled
- [ ] Know how to invalidate CloudFront cache
- [ ] Know how to redeploy Lambda functions

---

## ☑️ Cost Optimization

### Free Tier Verification

- [ ] Account is in first 12 months (free tier)
- [ ] Or: Monitoring costs in Cost Explorer
- [ ] Budget alert set at $5/month

### Optimization Steps

- [ ] CloudFront compression enabled
- [ ] Appropriate cache TTLs set
- [ ] Lambda memory sized appropriately
- [ ] Lambda timeout not excessive
- [ ] S3 lifecycle policies set (optional)
- [ ] No unused Lambda functions
- [ ] No unused API Gateway APIs

---

## ☑️ Security Checklist

### AWS Security

- [ ] Root account has MFA enabled
- [ ] IAM user has MFA enabled
- [ ] Access keys rotated regularly
- [ ] Minimal IAM permissions used
- [ ] S3 bucket not publicly writable (only readable)
- [ ] CloudFront HTTPS enforced

### GitHub Security

- [ ] GitHub account has 2FA enabled
- [ ] Repository secrets are secure
- [ ] No sensitive data in git history
- [ ] AWS credentials never committed to code

---

## ☑️ Documentation

- [ ] README.md updated with project-specific info
- [ ] Setup guide reviewed and understood
- [ ] Debugging guide bookmarked
- [ ] Contact information updated
- [ ] License file added (optional)

---

## ✅ Final Verification

Run this final check before considering deployment complete:

```bash
# 1. Website loads
curl -I https://mvanslyke-ml.com
# Should return: HTTP/2 200

# 2. Projects load
curl -s https://mvanslyke-ml.com/projects.json | python3 -m json.tool
# Should return: Valid JSON with your projects

# 3. GitHub Actions successful
# Check: https://github.com/mvanslyke/ml-portfolio/actions
# Should show: ✅ green checkmarks

# 4. Costs are reasonable
aws ce get-cost-and-usage \
  --time-period Start=$(date -v-7d +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost
# Should show: < $1/day

# 5. All components working
bash health_check.sh
# Should show: All ✅
```

---

## 🎉 Deployment Complete!

Once all items are checked off, your ML portfolio is:

✅ **Live** at https://mvanslyke-ml.com  
✅ **Auto-deploying** on every git push  
✅ **Secure** with HTTPS and proper IAM  
✅ **Cost-efficient** at ~$1-3/month  
✅ **Professional** and production-ready  

**Next Steps:**
1. Share your portfolio on LinkedIn
2. Add to your resume
3. Start building cool ML projects
4. Watch them deploy automatically!

---

## 📝 Maintenance Schedule

### Weekly
- [ ] Check GitHub Actions for failed builds
- [ ] Review CloudWatch logs for errors
- [ ] Test live demos

### Monthly  
- [ ] Review AWS costs in Cost Explorer
- [ ] Rotate AWS access keys (every 90 days)
- [ ] Update Python dependencies in requirements.txt
- [ ] Add new projects

### Quarterly
- [ ] Review and update resume with new projects
- [ ] Optimize Lambda functions
- [ ] Review S3 storage usage
- [ ] Update skills section

---

**Congratulations on deploying your professional ML portfolio!** 🚀
