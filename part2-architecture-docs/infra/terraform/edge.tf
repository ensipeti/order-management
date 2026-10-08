resource "google_compute_global_address" "public" {
  name = "${var.name}-https"
}

resource "google_compute_security_policy" "waf" {
  name = "${var.name}-waf"
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v33-stable') || evaluatePreconfiguredWaf('xss-v33-stable')"
      }
    }
    description = "SQL injection and XSS rules"
  }
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
  }
}

resource "google_compute_health_check" "gateway" {
  name = "${var.name}-gateway"
  http_health_check {
    port         = 8000
    request_path = "/health"
  }
}

# GKE creates one standalone NEG per zone for each Kong proxy Service.
data "google_compute_network_endpoint_group" "gateway" {
  for_each = var.gateway_negs
  name     = each.value
  zone     = each.key
}

resource "google_compute_backend_service" "gateway" {
  name                  = "${var.name}-gateway"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 5
  health_checks         = [google_compute_health_check.gateway.id]
  security_policy       = google_compute_security_policy.waf.id
  dynamic "backend" {
    for_each = data.google_compute_network_endpoint_group.gateway
    content {
      group                 = backend.value.id
      balancing_mode        = "RATE"
      max_rate_per_endpoint = 1000
    }
  }
  log_config {
    enable      = true
    sample_rate = 1
  }
}

resource "google_compute_url_map" "https" {
  name            = "${var.name}-https"
  default_service = google_compute_backend_service.gateway.id
}

resource "google_compute_managed_ssl_certificate" "public" {
  name = "${var.name}-https"
  managed { domains = [var.domain] }
}

resource "google_compute_target_https_proxy" "public" {
  name             = "${var.name}-https"
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_managed_ssl_certificate.public.id]
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${var.name}-https"
  ip_address            = google_compute_global_address.public.address
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  target                = google_compute_target_https_proxy.public.id
}

resource "google_compute_firewall" "gateway_health" {
  name          = "${var.name}-gateway-health"
  network       = google_compute_network.oms.name
  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
  target_tags   = ["${var.name}-gke"]
  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }
}
