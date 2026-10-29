# The Cloud Run service itself is defined in site/service.yaml and deployed by CI with
# each image (site.yml); managing it here too would fight every deploy. Only its public
# access lives here.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = "snakepuck-api"
  location = local.run_region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
