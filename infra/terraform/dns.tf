# snakepuck.com's DNS (registrar: GoDaddy, nameservers ns-cloud-a{1..4}.googledomains.com).
resource "google_dns_managed_zone" "site" {
  name        = "snakepuck-com"
  dns_name    = "${local.domain}."
  description = "snakepuck.com (moved from DigitalOcean 2026-10-28)"
  visibility  = "public"

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  # Firebase Hosting's address, its ownership check and certificate challenge (keep both
  # TXT records: renewals use them), and www, which Firebase redirects to the apex.
  dns_records = {
    apex_a   = { name = "${local.domain}.", type = "A", rrdatas = ["199.36.158.100"] }
    apex_txt = { name = "${local.domain}.", type = "TXT", rrdatas = ["\"hosting-site=snakepuck\""] }
    acme_txt = { name = "_acme-challenge.${local.domain}.", type = "TXT", rrdatas = ["\"jJmTESDLJNFi9sa4cRk9fFnV4haDshwb5tHXATRn4ww\""] }
    www      = { name = "www.${local.domain}.", type = "CNAME", rrdatas = ["snakepuck.web.app."] }
  }
}

resource "google_dns_record_set" "site" {
  for_each = local.dns_records

  managed_zone = google_dns_managed_zone.site.name
  name         = each.value.name
  type         = each.value.type
  ttl          = 300
  rrdatas      = each.value.rrdatas
}
