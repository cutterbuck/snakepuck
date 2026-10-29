# Firebase Hosting serves snakepuck.com and forwards every request to Cloud Run (rules in
# infra/firebase/firebase.json). www redirects to the apex.
resource "google_firebase_project" "this" {
  provider = google-beta
  project  = local.project
}

resource "google_firebase_hosting_site" "site" {
  provider = google-beta
  site_id  = "snakepuck"
}

resource "google_firebase_hosting_custom_domain" "apex" {
  provider              = google-beta
  site_id               = google_firebase_hosting_site.site.site_id
  custom_domain         = local.domain
  wait_dns_verification = false
}

resource "google_firebase_hosting_custom_domain" "www" {
  provider              = google-beta
  site_id               = google_firebase_hosting_site.site.site_id
  custom_domain         = "www.${local.domain}"
  redirect_target       = local.domain
  wait_dns_verification = false
}
