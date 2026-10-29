# Keyless GitHub Actions login: workflows in this repository, on main, act as the
# pipeline service account (no keys stored anywhere).
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "repo" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "snakepuck-repo"
  display_name                       = "cutterbuck/snakepuck"
  attribute_condition                = "assertion.repository_id == '${local.github_repository_id}' && assertion.ref == 'refs/heads/main'"
  attribute_mapping = {
    "google.subject"          = "assertion.sub"
    "attribute.repository"    = "assertion.repository"
    "attribute.repository_id" = "assertion.repository_id"
    "attribute.ref"           = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

locals {
  github_principal = "principalSet://iam.googleapis.com/projects/${local.project_number}/locations/global/workloadIdentityPools/github/attribute.repository_id/${local.github_repository_id}"
}

resource "google_service_account_iam_member" "github_as_pipeline" {
  service_account_id = google_service_account.pipeline.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.github_principal
}

# Site images. Keeps the 5 most recent, deletes the rest after a day.
resource "google_artifact_registry_repository" "images" {
  location               = local.region
  repository_id          = "snakepuck"
  description            = "SnakePuck API images"
  format                 = "DOCKER"
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "86400s"
    }
  }

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
}

resource "google_artifact_registry_repository_iam_member" "pipeline_writes_images" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = local.pipeline
}
