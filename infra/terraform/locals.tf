locals {
  project = "snakepuck"
  # Iowa: the warehouse, the data, images. Cheapest region, with every service.
  region = "us-central1"
  # N. Virginia: the Cloud Run service and its copy of the serving data, near the
  # East Coast visitors.
  run_region = "us-east4"
  domain     = "snakepuck.com"
  # GitHub Actions in cutterbuck/snakepuck, by numeric id (survives a rename).
  github_repository_id = "1150873071"
}

data "google_project" "this" {}

locals {
  project_number = data.google_project.this.number
}
