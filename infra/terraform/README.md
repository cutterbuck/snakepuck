# Terraform: the GCP platform

Everything in the `snakepuck` GCP project is defined here, except:

- **the Cloud Run service's settings**, in `site/service.yaml`, deployed by CI with each
  image (`.github/workflows/site.yml`). Its public access is here (`run.tf`).
- **dbt's own datasets** for dev and CI (`dbt_dev_*`, `dbt_ci_*`), which dbt creates.
- **Firebase Hosting's routing rules**, in `infra/firebase/`, deployed with the Firebase CLI.

| File | What |
|---|---|
| `apis.tf` | the APIs the project relies on |
| `storage.tf` | the data, serving and Terraform state buckets, and who can read or write them |
| `bigquery.tf` | the prod datasets |
| `iam.tf` | the pipeline and API service accounts and their roles |
| `ci.tf` | GitHub Actions' keyless login, the image registry |
| `run.tf` | the site's public access |
| `dns.tf` | the snakepuck.com zone and records |
| `firebase.tf` | Firebase, the hosting site, snakepuck.com and the www redirect |
| `costs.tf` | the BigQuery daily query caps and the monthly budget alert |

## Making a change

```bash
cd infra/terraform
terraform init          # once per checkout
terraform plan          # read it: what will be created, changed or destroyed
terraform apply         # shows the plan again and asks before changing anything
```

It uses the gcloud application-default login (`gcloud auth application-default login`).
State is in `gs://snakepuck-tfstate/prod` (versioned: any earlier state can be restored).
The data buckets, the prod datasets, the DNS zone and the state bucket have
`prevent_destroy`, so a plan that would delete them fails instead.

## History

The project was set up by hand first (the commands are in `infra/README.md`) and adopted
here on 2026-10-29: 54 resources imported with `import` blocks, until `plan` showed only
imports and no changes, then applied. Nothing was recreated. The import blocks were then
removed.
