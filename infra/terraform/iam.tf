# Two service accounts: CI and the data pipeline, and the API's runtime identity.
resource "google_service_account" "pipeline" {
  account_id   = "snakepuck-pipeline"
  display_name = "SnakePuck data pipeline"
  description  = "Loads raw data, runs dbt, exports marts. Keyless: used via impersonation or as a Cloud Run/CI identity."
}

resource "google_service_account" "api" {
  account_id   = "snakepuck-api"
  display_name = "SnakePuck API (Cloud Run runtime)"
}

locals {
  # Spelled out rather than taken from the resources, so they're known at plan time
  # (import addresses need that).
  pipeline_email = "snakepuck-pipeline@${local.project}.iam.gserviceaccount.com"
  api_email      = "snakepuck-api@${local.project}.iam.gserviceaccount.com"
  pipeline       = "serviceAccount:${local.pipeline_email}"
  api            = "serviceAccount:${local.api_email}"
}

# CI runs dbt (BigQuery) and deploys the site (Cloud Run). It can't change IAM.
resource "google_project_iam_member" "pipeline" {
  for_each = toset(["roles/bigquery.dataEditor", "roles/bigquery.jobUser", "roles/run.developer"])

  project = local.project
  role    = each.value
  member  = local.pipeline
}

# CI deploys the service to run as the API account.
resource "google_service_account_iam_member" "pipeline_acts_as_api" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = local.pipeline
}
