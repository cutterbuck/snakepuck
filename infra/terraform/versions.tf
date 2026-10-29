# SnakePuck's GCP platform: everything except the Cloud Run service's own settings
# (site/service.yaml, deployed by CI with each image), the datasets dbt creates for dev
# and CI, and Firebase's routing rules (infra/firebase, deployed with the Firebase CLI).
#
#   cd infra/terraform && terraform init && terraform plan
#
# Uses the gcloud application-default login. State is in gs://snakepuck-tfstate
# (versioned), created by hand once and then imported here.

terraform {
  required_version = ">= 1.10"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.9"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 8.9"
    }
  }

  backend "gcs" {
    bucket = "snakepuck-tfstate"
    prefix = "prod"
  }
}

# The quota project for API calls is this project (needed by the budget and quota APIs
# under a user login).
provider "google" {
  project               = local.project
  region                = local.region
  user_project_override = true
  billing_project       = local.project
}

provider "google-beta" {
  project               = local.project
  region                = local.region
  user_project_override = true
  billing_project       = local.project
}
