# Terraform Bootstrap — Setup Guide

This document explains every decision made in the `infrastructure/bootstrap/` module,
which is the **first thing that must exist before any other Terraform module can run**.

---

## Why a Bootstrap Module?

Terraform stores its own state — a record of what it has created — in a file called
`terraform.tfstate`. By default this lives on your local disk, which creates two problems:

1. **No collaboration.** No-one else on the team can run Terraform safely; the state is on your machine.
2. **No locking.** Two people running `terraform apply` at the same time can corrupt state.

The standard solution is to store state remotely (S3) and use a distributed lock
(DynamoDB) so only one process can modify state at a time. The bootstrap module
creates those two resources. Every other module in this project will then reference
them as its backend.

---

## Prerequisites

### 1. AWS CLI Profile

The module uses the named profile `sequencer-mgmt` rather than default credentials.

**Why a named profile instead of `AWS_ACCESS_KEY_ID` env vars?**

- Env vars are easy to leak in CI logs, shell history, and screenshots.
- Named profiles live in `~/.aws/credentials`, are never committed, and can be
  rotated without changing any Terraform code.
- They also support IAM role assumption (`role_arn`) for future multi-account setups.

Set it up once:

```bash
aws configure --profile sequencer-mgmt
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region:        us-east-1
# Default output format: json
```

Verify it works:

```bash
aws sts get-caller-identity --profile sequencer-mgmt
```

You should see your account ID, user ARN, and user ID.

### 2. Terraform CLI

```bash
brew install terraform        # macOS
terraform -version            # must be >= 1.5.0
```

**Why >= 1.5.0?**  
Version 1.5 introduced native `check` blocks and stabilised the S3 backend
configuration syntax we use here. Anything older will reject the config.

---

## The `versions.tf` File

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "sequencer-tf-state-893061519791"
    key            = "bootstrap/terraform.tfstate"
    region         = "us-east-1"
    profile        = "sequencer-mgmt"
    dynamodb_table = "sequencer-tf-locks"
    encrypt        = true
  }
}
```

### `required_version`
Pins the Terraform CLI itself. CI will fail fast if someone tries to apply with
an older binary rather than silently producing incompatible state.

### `required_providers` — `~> 5.60`
The `~>` (pessimistic constraint) operator means **>= 5.60 and < 6.0**.

- Allows patch and minor bumps automatically (`5.61`, `5.99`, …).
- Blocks a major-version bump that could contain breaking changes.
- The exact resolved version is pinned in `.terraform.lock.hcl` so every
  `terraform init` produces the identical provider binary regardless of when it runs.

### The `backend "s3"` block — chicken-and-egg problem

There is an intentional bootstrapping paradox here: the backend block references
the S3 bucket and DynamoDB table **that this very module creates**.

**How to handle it on first run:**

1. Comment out the `backend "s3"` block entirely, or delete it temporarily.
2. Run `terraform init && terraform apply` — this stores state locally.
3. The bucket and DynamoDB table now exist in AWS.
4. Restore the `backend "s3"` block.
5. Run `terraform init` again — Terraform will prompt:
   ```
   Do you want to copy existing state to the new backend? yes
   ```
6. Local state is migrated to S3. Delete the local `terraform.tfstate` file.

From this point on state lives in S3 and the bootstrap is self-hosting.

### `key = "bootstrap/terraform.tfstate"`
Each module gets its own key (path) inside the bucket. Using a prefix (`bootstrap/`)
keeps state files organised when more modules are added later
(e.g. `networking/terraform.tfstate`, `app/terraform.tfstate`).

### `encrypt = true`
Forces server-side encryption on the state object in S3. Required even though the
bucket already has a default encryption policy — belt-and-suspenders for state files
which can contain secrets output by resources.

---

## The `main.tf` File

### Provider block

```hcl
provider "aws" {
  region  = "us-east-1"
  profile = "sequencer-mgmt"
}
```

Region is hard-coded to `us-east-1`. This is the management account root;
application workloads in other regions will be handled by separate provider
aliases in future modules.

### `data "aws_caller_identity" "current"`

```hcl
data "aws_caller_identity" "current" {}
```

Fetches the AWS account ID at plan time. This is used to construct the S3
bucket name:

```hcl
bucket = "sequencer-tf-state-${data.aws_caller_identity.current.account_id}"
```

**Why embed the account ID in the bucket name?**

S3 bucket names are globally unique across all AWS accounts. Using the account ID
as a suffix guarantees uniqueness without manual coordination, and makes it
immediately obvious in the AWS console which account owns the bucket.

---

### S3 State Bucket

#### `prevent_destroy = true`

```hcl
lifecycle {
  prevent_destroy = true
}
```

If you run `terraform destroy`, Terraform will refuse to delete this bucket.
Losing the state bucket means losing the record of everything Terraform manages —
essentially orphaning all infrastructure. This lifecycle rule is a hard guard
against accidental destruction.

#### Versioning

```hcl
resource "aws_s3_bucket_versioning" "tf_state" {
  versioning_configuration {
    status = "Enabled"
  }
}
```

Every `terraform apply` writes a new state object to S3. With versioning enabled,
previous versions are retained. If a bad apply corrupts state, you can roll back
to the last known-good version from the S3 console or AWS CLI.

#### Server-Side Encryption

```hcl
sse_algorithm = "AES256"
```

State files can contain sensitive values (passwords, tokens) output by resources.
AES-256 (S3-managed keys, SSE-S3) encrypts at rest with zero operational overhead.
SSE-KMS (customer-managed keys) is not used here because it adds cost and complexity
that is not yet warranted at this stage.

#### Public Access Block

```hcl
block_public_acls       = true
block_public_policy     = true
ignore_public_acls      = true
restrict_public_buckets = true
```

All four flags are set. Even if someone accidentally adds a public bucket policy
or ACL, these settings override and keep the bucket private. This is belt-and-
suspenders: the bucket has no public ACLs, but we block them at the account level
anyway.

---

### DynamoDB Lock Table

```hcl
resource "aws_dynamodb_table" "tf_locks" {
  name         = "sequencer-tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
```

#### How locking works

When `terraform plan` or `terraform apply` starts, it writes a lock item to this
table with a unique ID. Any concurrent Terraform process checks for that item and
exits with an error if one exists. When the operation finishes, the lock item is
deleted.

#### `billing_mode = "PAY_PER_REQUEST"`

The lock table is written to only during Terraform runs — sporadic, low-frequency
writes. Provisioned throughput (the alternative) requires you to pre-allocate RCUs
and WCUs and pay for them 24/7. PAY_PER_REQUEST charges only for actual usage,
which is effectively free for this workload.

#### `hash_key = "LockID"` (type String)

This is the schema Terraform's S3 backend expects. It is not configurable — the
attribute name must be exactly `LockID`.

---

## Running the Bootstrap

```bash
cd infrastructure/bootstrap

# 1. First-time only: comment out the backend "s3" block in versions.tf

# 2. Initialise (downloads provider)
terraform init

# 3. Review what will be created
terraform plan

# 4. Create the bucket and DynamoDB table
terraform apply

# 5. Restore the backend "s3" block in versions.tf, then migrate local state to S3
terraform init
# → "Do you want to copy existing state to the new backend?" → yes

# 6. Clean up local state
rm terraform.tfstate terraform.tfstate.backup
```

---

## The `.terraform.lock.hcl` File

```
# This file is maintained automatically by "terraform init".
# Manual edits may be lost in future updates.
```

This file records the exact provider version and platform-specific checksums
resolved by `terraform init`. It should always be committed to git.

**Why commit it?**

- Guarantees every developer and every CI run downloads the identical provider binary.
- Prevents silent drift where a new provider minor version changes resource behaviour.
- `terraform init -upgrade` is the intentional, explicit way to update it.

**What not to commit:**

| Path | Reason |
|---|---|
| `.terraform/` | Contains the actual provider binary — large, platform-specific, re-downloadable |
| `*.tfstate` | Contains live infrastructure state, potentially secrets |
| `*.tfvars` | Often contains secrets (keys, passwords) |

All three are covered by the `.gitignore` added at the repo root.

---

## What Comes Next

Once bootstrap is applied and state is in S3, subsequent modules reference this
backend by declaring their own `backend "s3"` block with a different `key`:

```hcl
# infrastructure/networking/versions.tf
backend "s3" {
  bucket         = "sequencer-tf-state-893061519791"
  key            = "networking/terraform.tfstate"
  region         = "us-east-1"
  profile        = "sequencer-mgmt"
  dynamodb_table = "sequencer-tf-locks"
  encrypt        = true
}
```

The bucket and lock table are shared across all modules; only the `key` changes.
