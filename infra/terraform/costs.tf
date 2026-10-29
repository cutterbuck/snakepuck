# Cost guardrails: BigQuery query usage capped at 50 GiB a day (per project and per
# user), and a $10/month budget alert.
resource "google_cloud_quotas_quota_preference" "bigquery_daily" {
  for_each = {
    "query-usage-per-day-50gib"          = "QueryUsagePerDay"
    "query-usage-per-user-per-day-50gib" = "QueryUsagePerUserPerDay"
  }

  parent   = "projects/${local.project}"
  name     = each.key
  service  = "bigquery.googleapis.com"
  quota_id = each.value

  quota_config {
    preferred_value = "51200"
  }

  # Sent with a change, never read back. Lowering a cap below recent usage needs
  # ignore_safety_checks = "QUOTA_DECREASE_BELOW_USAGE" (see infra/README.md).
  lifecycle {
    ignore_changes = [ignore_safety_checks]
  }
}

resource "google_billing_budget" "monthly" {
  billing_account = data.google_project.this.billing_account
  display_name    = "snakepuck monthly"

  budget_filter {
    projects               = ["projects/${local.project_number}"]
    calendar_period        = "MONTH"
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "10"
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }
}
