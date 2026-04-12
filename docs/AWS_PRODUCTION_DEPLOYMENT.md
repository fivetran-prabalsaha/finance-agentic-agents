# AWS Production Deployment Guide

**Project**: SOD Compliance System with RBAC
**Target Environment**: AWS Cloud
**Date**: 2026-02-13
**Version**: 1.0

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Infrastructure Setup](#aws-infrastructure-setup)
3. [Database Setup (RDS PostgreSQL)](#database-setup)
4. [Application Deployment (ECS/EC2)](#application-deployment)
5. [Environment Configuration](#environment-configuration)
6. [NetSuite Integration](#netsuite-integration)
7. [Security Setup](#security-setup)
8. [Monitoring & Logging](#monitoring--logging)
9. [Deployment Steps](#deployment-steps)
10. [Post-Deployment Verification](#post-deployment-verification)
11. [Maintenance & Operations](#maintenance--operations)
12. [Troubleshooting](#troubleshooting)
13. [Cost Estimates](#cost-estimates)

---

## Prerequisites

### Required Access

- ✅ AWS Account with admin access (or IAM roles for RDS, ECS, EC2, VPC, Secrets Manager)
- ✅ NetSuite Admin access (for RESTlet deployment and OAuth setup)
- ✅ GitHub/Git access (to clone repository)
- ✅ Jira Admin access (for API token creation)
- ✅ Anthropic API key (for Claude)

### Required Tools

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version  # Should be 2.x

# Install Docker (for containerization)
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install PostgreSQL client (for database management)
sudo yum install -y postgresql15

# Install Python 3.11+
sudo yum install -y python3.11 python3.11-pip
```

### AWS CLI Configuration

```bash
# Configure AWS credentials
aws configure
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: us-east-1  # Or your preferred region
# Default output format: json

# Test configuration
aws sts get-caller-identity
```

---

## AWS Infrastructure Setup

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    VPC (10.0.0.0/16)                   │ │
│  │                                                        │ │
│  │  ┌──────────────────┐    ┌──────────────────┐        │ │
│  │  │  Public Subnet   │    │  Public Subnet   │        │ │
│  │  │  (10.0.1.0/24)   │    │  (10.0.2.0/24)   │        │ │
│  │  │                  │    │                  │        │ │
│  │  │  ┌────────────┐  │    │  ┌────────────┐  │        │ │
│  │  │  │ ECS Task   │  │    │  │ ECS Task   │  │        │ │
│  │  │  │ (MCP Server)│  │    │  │ (Replica)  │  │        │ │
│  │  │  └────────────┘  │    │  └────────────┘  │        │ │
│  │  │                  │    │                  │        │ │
│  │  │  ┌────────────┐  │    │                  │        │ │
│  │  │  │ ALB        │  │    │                  │        │ │
│  │  │  └────────────┘  │    │                  │        │ │
│  │  └──────────────────┘    └──────────────────┘        │ │
│  │                                                        │ │
│  │  ┌──────────────────┐    ┌──────────────────┐        │ │
│  │  │ Private Subnet   │    │ Private Subnet   │        │ │
│  │  │ (10.0.3.0/24)    │    │ (10.0.4.0/24)    │        │ │
│  │  │                  │    │                  │        │ │
│  │  │  ┌────────────┐  │    │  ┌────────────┐  │        │ │
│  │  │  │ RDS        │  │    │  │ RDS        │  │        │ │
│  │  │  │ Primary    │◄─┼────┼─►│ Read       │  │        │ │
│  │  │  │ PostgreSQL │  │    │  │ Replica    │  │        │ │
│  │  │  └────────────┘  │    │  └────────────┘  │        │ │
│  │  └──────────────────┘    └──────────────────┘        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ AWS Services                                           │ │
│  │  • Secrets Manager (credentials)                       │ │
│  │  • CloudWatch (logs & metrics)                         │ │
│  │  • S3 (backups & reports)                              │ │
│  │  • Route 53 (DNS)                                      │ │
│  │  • Certificate Manager (SSL)                           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

External:
• NetSuite (RESTlet API)
• Anthropic Claude API
• Jira API
```

### Step 1: Create VPC

```bash
# Create VPC
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=compliance-vpc}]'

# Save VPC ID
export VPC_ID="vpc-xxxxxxxxxxxxx"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames
```

### Step 2: Create Subnets

```bash
# Public Subnet 1 (us-east-1a)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=compliance-public-1a}]'

export PUBLIC_SUBNET_1="subnet-xxxxxxxxxxxxx"

# Public Subnet 2 (us-east-1b)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=compliance-public-1b}]'

export PUBLIC_SUBNET_2="subnet-xxxxxxxxxxxxx"

# Private Subnet 1 (us-east-1a)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=compliance-private-1a}]'

export PRIVATE_SUBNET_1="subnet-xxxxxxxxxxxxx"

# Private Subnet 2 (us-east-1b)
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=compliance-private-1b}]'

export PRIVATE_SUBNET_2="subnet-xxxxxxxxxxxxx"
```

### Step 3: Create Internet Gateway & NAT Gateway

```bash
# Create Internet Gateway
aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=compliance-igw}]'

export IGW_ID="igw-xxxxxxxxxxxxx"

# Attach to VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# Allocate Elastic IP for NAT Gateway
aws ec2 allocate-address --domain vpc

export EIP_ALLOC_ID="eipalloc-xxxxxxxxxxxxx"

# Create NAT Gateway in public subnet
aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET_1 \
  --allocation-id $EIP_ALLOC_ID \
  --tag-specifications 'ResourceType=nat-gateway,Tags=[{Key=Name,Value=compliance-nat}]'

export NAT_GW_ID="nat-xxxxxxxxxxxxx"

# Wait for NAT Gateway to be available (takes ~5 minutes)
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_ID
```

### Step 4: Create Route Tables

```bash
# Create public route table
aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=compliance-public-rt}]'

export PUBLIC_RT_ID="rtb-xxxxxxxxxxxxx"

# Add route to Internet Gateway
aws ec2 create-route \
  --route-table-id $PUBLIC_RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

# Associate public subnets
aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_1
aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_2

# Create private route table
aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=compliance-private-rt}]'

export PRIVATE_RT_ID="rtb-xxxxxxxxxxxxx"

# Add route to NAT Gateway
aws ec2 create-route \
  --route-table-id $PRIVATE_RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_ID

# Associate private subnets
aws ec2 associate-route-table --route-table-id $PRIVATE_RT_ID --subnet-id $PRIVATE_SUBNET_1
aws ec2 associate-route-table --route-table-id $PRIVATE_RT_ID --subnet-id $PRIVATE_SUBNET_2
```

### Step 5: Create Security Groups

```bash
# ALB Security Group (allow HTTP/HTTPS from internet)
aws ec2 create-security-group \
  --group-name compliance-alb-sg \
  --description "Security group for Application Load Balancer" \
  --vpc-id $VPC_ID

export ALB_SG_ID="sg-xxxxxxxxxxxxx"

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# ECS Task Security Group (allow traffic from ALB only)
aws ec2 create-security-group \
  --group-name compliance-ecs-sg \
  --description "Security group for ECS tasks" \
  --vpc-id $VPC_ID

export ECS_SG_ID="sg-xxxxxxxxxxxxx"

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG_ID \
  --protocol tcp --port 8080 \
  --source-group $ALB_SG_ID

# RDS Security Group (allow PostgreSQL from ECS only)
aws ec2 create-security-group \
  --group-name compliance-rds-sg \
  --description "Security group for RDS PostgreSQL" \
  --vpc-id $VPC_ID

export RDS_SG_ID="sg-xxxxxxxxxxxxx"

aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp --port 5432 \
  --source-group $ECS_SG_ID
```

---

## Database Setup

### Step 1: Create RDS Subnet Group

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name compliance-db-subnet-group \
  --db-subnet-group-description "Subnet group for compliance database" \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --tags "Key=Name,Value=compliance-db-subnet-group"
```

### Step 2: Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier compliance-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username compliance_admin \
  --master-user-password 'CHANGE_ME_STRONG_PASSWORD' \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --vpc-security-group-ids $RDS_SG_ID \
  --db-subnet-group-name compliance-db-subnet-group \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --multi-az \
  --publicly-accessible false \
  --enable-iam-database-authentication \
  --monitoring-interval 60 \
  --enable-cloudwatch-logs-exports '["postgresql"]' \
  --deletion-protection \
  --tags "Key=Name,Value=compliance-db" "Key=Environment,Value=production"

# Wait for RDS to be available (takes ~10-15 minutes)
aws rds wait db-instance-available --db-instance-identifier compliance-db

# Get RDS endpoint
aws rds describe-db-instances \
  --db-instance-identifier compliance-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text

export RDS_ENDPOINT="compliance-db.xxxxxxxxxxxxx.us-east-1.rds.amazonaws.com"
```

### Step 3: Store Database Credentials in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name compliance/database \
  --description "Database credentials for compliance system" \
  --secret-string '{
    "username": "compliance_admin",
    "password": "CHANGE_ME_STRONG_PASSWORD",
    "host": "'$RDS_ENDPOINT'",
    "port": 5432,
    "dbname": "compliance_db"
  }'

export DB_SECRET_ARN="arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:compliance/database-XXXXXX"
```

### Step 4: Create Database and Extensions

```bash
# Connect to RDS (you'll need a bastion host or VPN to access private subnet)
# Option 1: Use AWS Systems Manager Session Manager
# Option 2: Temporary EC2 bastion in public subnet

# For now, using psql from a bastion host:
psql -h $RDS_ENDPOINT -U compliance_admin -d postgres

# In psql:
CREATE DATABASE compliance_db;
\c compliance_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For pgvector

-- Create application user
CREATE USER compliance_user WITH PASSWORD 'ANOTHER_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE compliance_db TO compliance_user;
GRANT ALL ON SCHEMA public TO compliance_user;

-- Exit psql
\q
```

### Step 5: Run Database Migrations

```bash
# Clone repository on bastion or use AWS CodeBuild
git clone https://github.com/fivetran-prabalsaha/finance-agentic-agents.git
cd finance-agentic-agents/compliance-agent

# Set environment variable
export DATABASE_URL="postgresql://compliance_user:ANOTHER_STRONG_PASSWORD@$RDS_ENDPOINT:5432/compliance_db"

# Install dependencies
python3.11 -m pip install -r requirements.txt

# Run Alembic migrations
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt"

# Should see:
# - users
# - roles
# - user_roles
# - sod_rules
# - permissions
# - violations
# - compliance_scans
# - approved_exceptions
# - exception_controls
# - exception_reviews
# - exception_violations
# - sync_metadata
```

---

## Application Deployment

### Option A: ECS Fargate (Recommended - Serverless)

#### Step 1: Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name compliance-agent \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

export ECR_REPO_URI="ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/compliance-agent"

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REPO_URI
```

#### Step 2: Build and Push Docker Image

```bash
# Create Dockerfile
cat > Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory for reports
RUN mkdir -p /app/output/role_analysis

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["python", "-m", "mcp.mcp_server"]
EOF

# Build image
docker build -t compliance-agent:latest .

# Tag for ECR
docker tag compliance-agent:latest $ECR_REPO_URI:latest
docker tag compliance-agent:latest $ECR_REPO_URI:v1.0.0

# Push to ECR
docker push $ECR_REPO_URI:latest
docker push $ECR_REPO_URI:v1.0.0
```

#### Step 3: Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name compliance-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1 \
    capacityProvider=FARGATE_SPOT,weight=4 \
  --tags "Key=Name,Value=compliance-cluster"

export ECS_CLUSTER="compliance-cluster"
```

#### Step 4: Create Task Execution Role

```bash
# Create IAM role for ECS task execution
cat > task-execution-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://task-execution-role-trust-policy.json

# Attach managed policies
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add Secrets Manager access
cat > secrets-manager-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ],
      "Resource": [
        "$DB_SECRET_ARN",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:compliance/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name SecretsManagerAccess \
  --policy-document file://secrets-manager-policy.json

export EXECUTION_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole"
```

#### Step 5: Create Task Role (for application permissions)

```bash
# Create IAM role for ECS task
cat > task-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name complianceTaskRole \
  --assume-role-policy-document file://task-role-trust-policy.json

# Add application permissions
cat > task-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::compliance-reports-bucket/*",
        "arn:aws:s3:::compliance-reports-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name complianceTaskRole \
  --policy-name ComplianceApplicationPolicy \
  --policy-document file://task-role-policy.json

export TASK_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/complianceTaskRole"
```

#### Step 6: Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/compliance-agent

aws logs put-retention-policy \
  --log-group-name /ecs/compliance-agent \
  --retention-in-days 30
```

#### Step 7: Create ECS Task Definition

```bash
# Store secrets in Secrets Manager
aws secretsmanager create-secret \
  --name compliance/netsuite \
  --secret-string '{
    "NETSUITE_ACCOUNT_ID": "5260239_SB1",
    "NETSUITE_CONSUMER_KEY": "your_consumer_key",
    "NETSUITE_CONSUMER_SECRET": "your_consumer_secret",
    "NETSUITE_TOKEN_ID": "your_token_id",
    "NETSUITE_TOKEN_SECRET": "your_token_secret",
    "NETSUITE_RESTLET_URL": "https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=xxx&deploy=1"
  }'

aws secretsmanager create-secret \
  --name compliance/anthropic \
  --secret-string '{
    "ANTHROPIC_API_KEY": "sk-ant-your-key-here"
  }'

aws secretsmanager create-secret \
  --name compliance/jira \
  --secret-string '{
    "JIRA_URL": "https://your-company.atlassian.net",
    "JIRA_API_TOKEN": "your_jira_api_token",
    "JIRA_EMAIL": "your-email@company.com",
    "JIRA_PROJECT": "COMP"
  }'

# Create task definition JSON
cat > task-definition.json <<EOF
{
  "family": "compliance-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "compliance-agent",
      "image": "$ECR_REPO_URI:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "$DB_SECRET_ARN:username::"
        },
        {
          "name": "NETSUITE_ACCOUNT_ID",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:compliance/netsuite:NETSUITE_ACCOUNT_ID::"
        },
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:compliance/anthropic:ANTHROPIC_API_KEY::"
        },
        {
          "name": "JIRA_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:compliance/jira:JIRA_URL::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/compliance-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:8080/health\")' || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

export TASK_DEF_ARN="arn:aws:ecs:us-east-1:ACCOUNT_ID:task-definition/compliance-agent:1"
```

#### Step 8: Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name compliance-alb \
  --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
  --security-groups $ALB_SG_ID \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --tags "Key=Name,Value=compliance-alb"

export ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:loadbalancer/app/compliance-alb/xxxxxxxxxxxxx"

# Get ALB DNS name
aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text

export ALB_DNS="compliance-alb-xxxxxxxxxxxxx.us-east-1.elb.amazonaws.com"

# Create target group
aws elbv2 create-target-group \
  --name compliance-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-enabled \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

export TG_ARN="arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:targetgroup/compliance-tg/xxxxxxxxxxxxx"

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# (Optional) Add HTTPS listener with ACM certificate
# aws elbv2 create-listener \
#   --load-balancer-arn $ALB_ARN \
#   --protocol HTTPS \
#   --port 443 \
#   --certificates CertificateArn=arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/xxxxx \
#   --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

#### Step 9: Create ECS Service

```bash
aws ecs create-service \
  --cluster $ECS_CLUSTER \
  --service-name compliance-service \
  --task-definition compliance-agent:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PUBLIC_SUBNET_1,$PUBLIC_SUBNET_2],
    securityGroups=[$ECS_SG_ID],
    assignPublicIp=ENABLED
  }" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=compliance-agent,containerPort=8080" \
  --health-check-grace-period-seconds 60 \
  --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
  --enable-execute-command

# Wait for service to be stable
aws ecs wait services-stable \
  --cluster $ECS_CLUSTER \
  --services compliance-service
```

---

### Option B: EC2 Instance (Alternative - More Control)

```bash
# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \  # Amazon Linux 2023
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids $ECS_SG_ID \
  --subnet-id $PUBLIC_SUBNET_1 \
  --iam-instance-profile Name=complianceInstanceProfile \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=compliance-server}]'

export EC2_INSTANCE_ID="i-xxxxxxxxxxxxx"

# user-data.sh content:
cat > user-data.sh <<'EOF'
#!/bin/bash
yum update -y
yum install -y python3.11 python3.11-pip git postgresql15

# Clone repository
cd /opt
git clone https://github.com/fivetran-prabalsaha/finance-agentic-agents.git
cd finance-agentic-agents/compliance-agent

# Install dependencies
python3.11 -m pip install -r requirements.txt

# Get secrets from Secrets Manager
aws secretsmanager get-secret-value --secret-id compliance/database --query SecretString --output text > /opt/.env

# Run database migrations
export DATABASE_URL=$(cat /opt/.env | jq -r '.database_url')
alembic upgrade head

# Create systemd service
cat > /etc/systemd/system/compliance-agent.service <<'SYSTEMD'
[Unit]
Description=Compliance MCP Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/finance-agentic-agents/compliance-agent
EnvironmentFile=/opt/.env
ExecStart=/usr/bin/python3.11 -m mcp.mcp_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

# Start service
systemctl daemon-reload
systemctl enable compliance-agent
systemctl start compliance-agent
EOF
```

---

## Environment Configuration

### Create Complete Environment File

```bash
# Store all environment variables in AWS Secrets Manager
aws secretsmanager create-secret \
  --name compliance/environment \
  --secret-string '{
    "DATABASE_URL": "postgresql://compliance_user:PASSWORD@'$RDS_ENDPOINT':5432/compliance_db",
    "NETSUITE_ACCOUNT_ID": "5260239_SB1",
    "NETSUITE_CONSUMER_KEY": "your_key",
    "NETSUITE_CONSUMER_SECRET": "your_secret",
    "NETSUITE_TOKEN_ID": "your_token_id",
    "NETSUITE_TOKEN_SECRET": "your_token_secret",
    "NETSUITE_RESTLET_URL": "https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=xxx&deploy=1",
    "ANTHROPIC_API_KEY": "sk-ant-your-key",
    "OPENAI_API_KEY": "sk-your-openai-key",
    "JIRA_URL": "https://your-company.atlassian.net",
    "JIRA_API_TOKEN": "your_jira_token",
    "JIRA_EMAIL": "your-email@company.com",
    "JIRA_PROJECT": "COMP",
    "LOG_LEVEL": "INFO",
    "ENVIRONMENT": "production"
  }'
```

---

## NetSuite Integration

### Step 1: Deploy RESTlet in NetSuite

1. **Log into NetSuite**
2. Navigate to **Customization > Scripting > Scripts > New**
3. Upload RESTlet script from `restlets/netsuite_compliance_restlet.js`
4. Create Script Record:
   - Name: "Compliance Data RESTlet"
   - ID: "customscript_compliance_restlet"
   - Function: All methods (GET, POST, PUT, DELETE)
5. Create Deployment:
   - Status: **Released**
   - Log Level: **Debug**
   - Audience: **Employees**
6. Copy the deployment URL

### Step 2: Set Up OAuth 1.0 in NetSuite

1. **Enable Token-Based Authentication**:
   - Setup > Company > Enable Features
   - SuiteCloud tab
   - Check "Token-Based Authentication"

2. **Create Integration Record**:
   - Setup > Integration > Manage Integrations > New
   - Name: "Compliance System Integration"
   - State: **Enabled**
   - Token-Based Authentication: **Checked**
   - Save and copy:
     - Consumer Key
     - Consumer Secret

3. **Create Access Token**:
   - Setup > Users/Roles > Access Tokens > New
   - Application Name: Select your integration
   - User: Select a service account user
   - Role: Administrator (or custom role with full read access)
   - Token Name: "Compliance System Token"
   - Save and copy:
     - Token ID
     - Token Secret

4. **Test Connection**:
```bash
# From bastion or EC2 instance
cd /opt/finance-agentic-agents/compliance-agent

python3 -c "
from services.netsuite_client import NetSuiteClient
client = NetSuiteClient()
users = client.get_all_users_paginated(page_size=10)
print(f'Successfully fetched {len(users)} users')
"
```

---

## Security Setup

### Step 1: Enable AWS WAF

```bash
# Create WAF WebACL
aws wafv2 create-web-acl \
  --name compliance-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=complianceWAF

# Associate with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:ACCOUNT_ID:regional/webacl/compliance-waf/xxxxx \
  --resource-arn $ALB_ARN
```

### Step 2: Enable AWS GuardDuty

```bash
aws guardduty create-detector --enable
```

### Step 3: Enable VPC Flow Logs

```bash
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/compliance-vpc
```

### Step 4: Enable AWS Config

```bash
aws configservice put-configuration-recorder \
  --configuration-recorder name=compliance-config-recorder,roleARN=arn:aws:iam::ACCOUNT_ID:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig

aws configservice start-configuration-recorder \
  --configuration-recorder-name compliance-config-recorder
```

### Step 5: Set Up AWS Backup

```bash
# Create backup plan
aws backup create-backup-plan \
  --backup-plan file://backup-plan.json

# backup-plan.json:
cat > backup-plan.json <<EOF
{
  "BackupPlanName": "compliance-backup-plan",
  "Rules": [
    {
      "RuleName": "DailyBackup",
      "TargetBackupVaultName": "Default",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 120,
      "Lifecycle": {
        "DeleteAfterDays": 30,
        "MoveToColdStorageAfterDays": 7
      }
    }
  ]
}
EOF

# Assign resources to backup plan
aws backup create-backup-selection \
  --backup-plan-id xxxxx \
  --backup-selection file://backup-selection.json
```

---

## Monitoring & Logging

### Step 1: Create CloudWatch Dashboard

```bash
aws cloudwatch put-dashboard \
  --dashboard-name compliance-dashboard \
  --dashboard-body file://dashboard.json
```

### Step 2: Set Up CloudWatch Alarms

```bash
# RDS CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name compliance-db-cpu-high \
  --alarm-description "Alert when DB CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DBInstanceIdentifier,Value=compliance-db \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:compliance-alerts

# ECS service alarm
aws cloudwatch put-metric-alarm \
  --alarm-name compliance-service-healthy-tasks-low \
  --alarm-description "Alert when healthy task count is below 1" \
  --metric-name HealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=TargetGroup,Value=targetgroup/compliance-tg/xxxxx \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:compliance-alerts

# Application error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name compliance-error-rate-high \
  --alarm-description "Alert when error rate exceeds 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:compliance-alerts
```

### Step 3: Enable X-Ray Tracing

```bash
# Add X-Ray daemon sidecar to ECS task definition
# Update task definition to include X-Ray container
```

---

## Deployment Steps

### Complete Deployment Checklist

```bash
# ✅ 1. Infrastructure Setup
□ VPC and subnets created
□ Internet Gateway and NAT Gateway configured
□ Route tables associated
□ Security groups created
□ RDS PostgreSQL instance running
□ Database initialized with extensions

# ✅ 2. Application Deployment
□ ECR repository created
□ Docker image built and pushed
□ ECS cluster created
□ Task definition registered
□ ECS service running
□ ALB configured and healthy
□ Target group showing healthy targets

# ✅ 3. Configuration
□ All secrets stored in Secrets Manager
□ Environment variables configured
□ NetSuite OAuth credentials working
□ Anthropic API key validated
□ Jira integration configured

# ✅ 4. Security
□ IAM roles and policies configured
□ Security groups properly restricted
□ Secrets Manager access controlled
□ SSL/TLS certificate installed (if HTTPS)
□ WAF enabled (optional)

# ✅ 5. Monitoring
□ CloudWatch Logs collecting logs
□ CloudWatch Alarms configured
□ SNS topic for alerts created
□ Dashboard created
□ Backup plan configured

# ✅ 6. Testing
□ Health check endpoint responding
□ Database connectivity verified
□ NetSuite API calls successful
□ MCP tools responding correctly
□ RBAC authentication working
□ Exception approval workflow tested
```

---

## Post-Deployment Verification

### Step 1: Health Check

```bash
# Check ALB health
curl http://$ALB_DNS/health

# Should return:
# {"status": "healthy", "timestamp": "2026-02-13T10:00:00Z"}
```

### Step 2: Test MCP Tools

```bash
# Test via Claude Desktop or curl
curl -X POST http://$ALB_DNS/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Should return list of 14 tools
```

### Step 3: Test Database Connection

```bash
# From ECS task or EC2
python3 -c "
from models.database_config import DatabaseConfig
db = DatabaseConfig()
session = db.get_session()
from sqlalchemy import text
result = session.execute(text('SELECT COUNT(*) FROM users'))
print(f'User count: {result.scalar()}')
"
```

### Step 4: Test NetSuite Sync

```bash
# Trigger manual sync
curl -X POST http://$ALB_DNS/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "trigger_manual_sync",
      "arguments": {"sync_type": "full"}
    }
  }'
```

### Step 5: Test RBAC Authentication

```bash
# Test session initialization
curl -X POST http://$ALB_DNS/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "initialize_session",
      "arguments": {"my_email": "your-email@fivetran.com"}
    }
  }'
```

---

## Maintenance & Operations

### Daily Operations

**1. Monitor Logs:**
```bash
# View application logs
aws logs tail /ecs/compliance-agent --follow

# View RDS logs
aws rds download-db-log-file-portion \
  --db-instance-identifier compliance-db \
  --log-file-name error/postgresql.log.2026-02-13-10 \
  --output text
```

**2. Check Service Health:**
```bash
# Check ECS service status
aws ecs describe-services \
  --cluster $ECS_CLUSTER \
  --services compliance-service

# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN
```

**3. Monitor Metrics:**
```bash
# Check CloudWatch dashboard
# https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=compliance-dashboard
```

### Weekly Operations

**1. Review Backup Status:**
```bash
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name Default
```

**2. Review Security Findings:**
```bash
# Check GuardDuty findings
aws guardduty list-findings \
  --detector-id xxxxx \
  --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}'

# Check AWS Config compliance
aws configservice describe-compliance-by-config-rule
```

**3. Review Cost:**
```bash
# Check AWS Cost Explorer
# https://console.aws.amazon.com/cost-management/home#/dashboard
```

### Monthly Operations

**1. Rotate Secrets:**
```bash
# Rotate database password
aws secretsmanager rotate-secret \
  --secret-id compliance/database \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:ACCOUNT_ID:function:SecretsManagerRotation

# Rotate NetSuite tokens (manual in NetSuite)
# Rotate Jira API token (manual in Jira)
```

**2. Review and Update:**
```bash
# Update Docker image with latest code
git pull origin main
docker build -t compliance-agent:latest .
docker tag compliance-agent:latest $ECR_REPO_URI:v1.1.0
docker push $ECR_REPO_URI:v1.1.0

# Update ECS task definition
aws ecs register-task-definition --cli-input-json file://task-definition-v1.1.json

# Update ECS service
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service compliance-service \
  --task-definition compliance-agent:2
```

**3. Database Maintenance:**
```bash
# Run VACUUM and ANALYZE
psql $DATABASE_URL -c "VACUUM ANALYZE;"

# Check database size
psql $DATABASE_URL -c "
SELECT
  pg_size_pretty(pg_database_size('compliance_db')) as db_size,
  pg_size_pretty(pg_total_relation_size('violations')) as violations_size,
  pg_size_pretty(pg_total_relation_size('users')) as users_size;
"
```

### Scaling

**Horizontal Scaling (Add More Tasks):**
```bash
# Scale up
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service compliance-service \
  --desired-count 4

# Scale down
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service compliance-service \
  --desired-count 2
```

**Vertical Scaling (Larger Tasks):**
```bash
# Update task definition with more CPU/memory
# cpu: "2048" (2 vCPU)
# memory: "4096" (4 GB)
```

**Database Scaling:**
```bash
# Scale up RDS instance
aws rds modify-db-instance \
  --db-instance-identifier compliance-db \
  --db-instance-class db.t3.large \
  --apply-immediately

# Add read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier compliance-db-replica \
  --source-db-instance-identifier compliance-db
```

---

## Troubleshooting

### Issue: Service Not Starting

**Check ECS Task Logs:**
```bash
aws logs tail /ecs/compliance-agent --follow --since 10m
```

**Common Causes:**
- Database connection failure (check RDS security group)
- Missing environment variables (check Secrets Manager)
- Image pull failure (check ECR permissions)

### Issue: Database Connection Timeout

**Check Security Groups:**
```bash
# Ensure ECS security group can access RDS security group on port 5432
aws ec2 describe-security-groups --group-ids $RDS_SG_ID
```

**Test Connection from ECS Task:**
```bash
# Use ECS Exec to connect to running task
aws ecs execute-command \
  --cluster $ECS_CLUSTER \
  --task TASK_ID \
  --container compliance-agent \
  --interactive \
  --command "/bin/bash"

# Inside container:
psql $DATABASE_URL -c "SELECT 1;"
```

### Issue: NetSuite API Calls Failing

**Check OAuth Credentials:**
```bash
# Verify credentials in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id compliance/netsuite \
  --query SecretString \
  --output text | jq
```

**Test NetSuite Connection:**
```bash
python3 -c "
from services.netsuite_client import NetSuiteClient
client = NetSuiteClient()
try:
    users = client.get_all_users_paginated(page_size=1)
    print('✅ NetSuite connection successful')
except Exception as e:
    print(f'❌ NetSuite connection failed: {e}')
"
```

### Issue: High Memory Usage

**Check CloudWatch Metrics:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace ECS/ContainerInsights \
  --metric-name MemoryUtilized \
  --dimensions Name=ServiceName,Value=compliance-service \
  --start-time 2026-02-13T00:00:00Z \
  --end-time 2026-02-13T23:59:59Z \
  --period 3600 \
  --statistics Average
```

**Solution: Increase Task Memory**
```bash
# Update task definition with more memory
# memory: "4096" (4 GB)
```

---

## Cost Estimates

### Monthly AWS Costs (Estimated)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| **RDS PostgreSQL** | db.t3.medium, 100GB, Multi-AZ | ~$150 |
| **ECS Fargate** | 2 tasks, 1 vCPU, 2GB RAM | ~$60 |
| **Application Load Balancer** | 1 ALB, 2 AZs | ~$25 |
| **NAT Gateway** | 1 NAT, 100GB transfer | ~$45 |
| **CloudWatch Logs** | 10GB ingestion, 30-day retention | ~$5 |
| **Secrets Manager** | 5 secrets | ~$2 |
| **Data Transfer** | 100GB outbound | ~$9 |
| **S3** | 50GB storage (backups, reports) | ~$1 |
| **Route 53** | 1 hosted zone, 1M queries | ~$1 |
| **Total Estimated Cost** | | **~$298/month** |

### Cost Optimization Tips

1. **Use Fargate Spot**: Save 70% on compute costs
2. **Enable RDS Auto Scaling**: Scale storage as needed
3. **Use S3 Lifecycle Policies**: Move old reports to Glacier
4. **Enable CloudWatch Logs Retention**: Delete old logs
5. **Use Reserved Instances**: If running 24/7 (save 30-40%)

---

## Production Checklist

### Pre-Launch

- [ ] All infrastructure provisioned
- [ ] Database migrated and seeded
- [ ] Application deployed and healthy
- [ ] All secrets configured
- [ ] NetSuite integration tested
- [ ] RBAC authentication tested
- [ ] Monitoring and alarms configured
- [ ] Backup strategy implemented
- [ ] Security review completed
- [ ] Load testing completed
- [ ] Disaster recovery plan documented

### Launch Day

- [ ] Deploy to production
- [ ] Smoke tests passed
- [ ] Monitor logs for 2 hours
- [ ] Verify first NetSuite sync
- [ ] Test RBAC with real users
- [ ] Confirm alerts are working
- [ ] Update DNS (if needed)
- [ ] Notify team of launch

### Post-Launch (Week 1)

- [ ] Daily health checks
- [ ] Monitor CloudWatch dashboard
- [ ] Review GuardDuty findings
- [ ] Check backup success
- [ ] Gather user feedback
- [ ] Document any issues
- [ ] Plan optimizations

---

## Summary

This guide provides a comprehensive deployment strategy for the SOD Compliance System on AWS. Key points:

✅ **Infrastructure**: VPC, RDS, ECS Fargate, ALB
✅ **Security**: IAM roles, Secrets Manager, WAF, security groups
✅ **Monitoring**: CloudWatch Logs, Alarms, Dashboard, X-Ray
✅ **Scalability**: Auto-scaling, read replicas, Fargate Spot
✅ **Cost**: ~$300/month for production environment
✅ **Maintenance**: Automated backups, log rotation, secret rotation

**Next Steps:**
1. Review this guide with your DevOps team
2. Provision AWS infrastructure following the steps
3. Deploy application to production
4. Configure monitoring and alerts
5. Train operations team on maintenance procedures

**Support:**
- AWS Support: https://console.aws.amazon.com/support
- Compliance Agent Issues: https://github.com/fivetran-prabalsaha/finance-agentic-agents/issues
- NetSuite Support: https://system.netsuite.com/app/login/secure/support.nl

---

**Document Version**: 1.0
**Last Updated**: 2026-02-13
**Maintained By**: DevOps Team
