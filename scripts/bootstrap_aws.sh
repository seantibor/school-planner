#!/usr/bin/env bash
# Bootstrap AWS resources needed before the first Terraform apply.
# Run this once. Requires the AWS CLI configured with admin-ish credentials.
#
# What this creates:
#   1. S3 bucket for Terraform state (versioned, encrypted)
#   2. GitHub OIDC identity provider (if not already present)
#   3. IAM role for GitHub Actions to assume (deploy permissions)
#
# After running this, set these GitHub repo secrets:
#   AWS_DEPLOY_ROLE_ARN = (printed at the end)
#   TF_STATE_BUCKET = school-planner-tfstate-<account_id>

set -euo pipefail

REGION="us-east-2"
REPO="seantibor/school-planner"

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="school-planner-tfstate-${ACCOUNT_ID}"

echo "=== AWS Bootstrap for school-planner ==="
echo "Region:     ${REGION}"
echo "Account:    ${ACCOUNT_ID}"
echo "TF Bucket:  ${BUCKET_NAME}"
echo ""

# --- 1. Terraform state bucket ---
echo "→ Creating Terraform state bucket..."
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "  Bucket already exists, skipping."
else
    aws s3api create-bucket \
        --bucket "${BUCKET_NAME}" \
        --region "${REGION}" \
        --create-bucket-configuration LocationConstraint="${REGION}"
    aws s3api put-bucket-versioning \
        --bucket "${BUCKET_NAME}" \
        --versioning-configuration Status=Enabled
    aws s3api put-bucket-encryption \
        --bucket "${BUCKET_NAME}" \
        --server-side-encryption-configuration \
        '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
    aws s3api put-public-access-block \
        --bucket "${BUCKET_NAME}" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    echo "  Created and configured."
fi

# --- 2. GitHub OIDC provider ---
echo ""
echo "→ Checking GitHub OIDC provider..."
OIDC_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "${OIDC_ARN}" >/dev/null 2>&1; then
    echo "  Already exists, skipping."
else
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
        --client-id-list "sts.amazonaws.com"
    echo "  Created."
fi

# --- 3. IAM deploy role ---
echo ""
echo "→ Creating GitHub Actions deploy role..."
ROLE_NAME="school-planner-github-deploy"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "${OIDC_ARN}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:${REPO}:*"
                }
            }
        }
    ]
}
EOF
)

DEPLOY_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Lambda",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration",
                "lambda:DeleteFunction",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:GetPolicy",
                "lambda:ListVersionsByFunction",
                "lambda:PublishVersion"
            ],
            "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:school-planner-*"
        },
        {
            "Sid": "APIGateway",
            "Effect": "Allow",
            "Action": [
                "apigateway:GET",
                "apigateway:POST",
                "apigateway:PUT",
                "apigateway:PATCH",
                "apigateway:DELETE"
            ],
            "Resource": "arn:aws:apigateway:${REGION}::*"
        },
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:GetRolePolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PassRole",
                "iam:ListRolePolicies",
                "iam:ListAttachedRolePolicies"
            ],
            "Resource": "arn:aws:iam::${ACCOUNT_ID}:role/school-planner-*"
        },
        {
            "Sid": "TerraformState",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF
)

if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
    echo "  Role already exists, updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-document "${TRUST_POLICY}"
else
    aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "${TRUST_POLICY}" \
        --description "GitHub Actions deploy role for school-planner"
fi

aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name "school-planner-deploy" \
    --policy-document "${DEPLOY_POLICY}"
echo "  Done."

# --- Summary ---
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Add these as GitHub repository secrets:"
echo "  AWS_DEPLOY_ROLE_ARN = ${ROLE_ARN}"
echo "  TF_STATE_BUCKET     = ${BUCKET_NAME}"
echo ""
echo "Then update infra/variables.tf:"
echo "  frontend_origin = \"https://seantibor.github.io\""
echo ""
echo "First deploy:"
echo "  cd lambda && uv pip install --target package -r requirements.txt && cp *.py package/ && cd package && zip -r ../package.zip . && cd ../.."
echo "  cd infra && terraform init -backend-config=\"bucket=${BUCKET_NAME}\" -backend-config=\"key=school-planner/terraform.tfstate\" -backend-config=\"region=${REGION}\""
echo "  terraform apply -var=\"frontend_origin=https://seantibor.github.io\""
echo "  # Copy the api_url output into frontend/app.js"
