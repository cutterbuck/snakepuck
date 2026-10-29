# Raw HALO files, dbt state, golden snapshots and the serving export (serving/prod).
resource "google_storage_bucket" "data" {
  name                        = "snakepuck-data"
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle {
    prevent_destroy = true
  }
}

# A copy of serving/prod next to the Cloud Run service (dbt.yml syncs it after each
# export): reading Iowa from Virginia doubled the startup load of the marts.
resource "google_storage_bucket" "serving" {
  name                        = "snakepuck-serving-use4"
  location                    = "US-EAST4"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 604800
  }
}

# Terraform's own state, versioned so any earlier state can be recovered.
resource "google_storage_bucket" "tfstate" {
  name                        = "snakepuck-tfstate"
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  # CI writes both data buckets; the API only reads them.
  bucket_access = {
    data_pipeline    = { bucket = "snakepuck-data", role = "roles/storage.objectAdmin", member = local.pipeline }
    data_api         = { bucket = "snakepuck-data", role = "roles/storage.objectViewer", member = local.api }
    serving_pipeline = { bucket = "snakepuck-serving-use4", role = "roles/storage.objectAdmin", member = local.pipeline }
    serving_api      = { bucket = "snakepuck-serving-use4", role = "roles/storage.objectViewer", member = local.api }
  }
}

resource "google_storage_bucket_iam_member" "access" {
  for_each   = local.bucket_access
  depends_on = [google_storage_bucket.data, google_storage_bucket.serving]

  bucket = each.value.bucket
  role   = each.value.role
  member = each.value.member
}
