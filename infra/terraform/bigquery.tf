# The prod datasets. raw and golden are loaded by infra/load_raw.sh; dbt builds the rest
# (its dev and CI datasets, dbt_dev_* and dbt_ci_*, are dbt's own and not managed here).
resource "google_bigquery_dataset" "prod" {
  for_each = toset(["raw", "golden", "staging", "intermediate", "reference", "marts"])

  dataset_id                 = each.value
  location                   = local.region
  delete_contents_on_destroy = false

  lifecycle {
    prevent_destroy = true
  }
}
