terraform {
  required_version = ">= 1.13, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.7.0"
    }
  }
}

provider "google" {
  project = var.project_id
}

locals {
  regions = {
    london = {
      region = "europe-west2"
      zones  = ["europe-west2-a", "europe-west2-b", "europe-west2-c"]
      nodes  = "10.10.0.0/20"
      pods   = "10.20.0.0/16"
      svc    = "10.30.0.0/20"
      master = "172.16.0.0/28"
    }
    belgium = {
      region = "europe-west1"
      zones  = ["europe-west1-b", "europe-west1-c", "europe-west1-d"]
      nodes  = "10.40.0.0/20"
      pods   = "10.50.0.0/16"
      svc    = "10.60.0.0/20"
      master = "172.16.0.16/28"
    }
  }
  services = toset([
    "compute.googleapis.com", "container.googleapis.com", "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com", "storage.googleapis.com", "secretmanager.googleapis.com",
    "monitoring.googleapis.com", "logging.googleapis.com", "artifactregistry.googleapis.com"
  ])
}

resource "google_project_service" "required" {
  for_each           = local.services
  service            = each.value
  disable_on_destroy = false
}

resource "google_compute_network" "oms" {
  name                    = var.name
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
  depends_on              = [google_project_service.required]
}

resource "google_compute_subnetwork" "regional" {
  for_each                 = local.regions
  name                     = "${var.name}-${each.key}"
  region                   = each.value.region
  network                  = google_compute_network.oms.id
  ip_cidr_range            = each.value.nodes
  private_ip_google_access = true
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = each.value.pods
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = each.value.svc
  }
}

resource "google_compute_router" "regional" {
  for_each = local.regions
  name     = "${var.name}-${each.key}"
  region   = each.value.region
  network  = google_compute_network.oms.id
}

resource "google_compute_router_nat" "regional" {
  for_each                           = local.regions
  name                               = "${var.name}-${each.key}"
  router                             = google_compute_router.regional[each.key].name
  region                             = each.value.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = google_compute_subnetwork.regional[each.key].id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}

resource "google_service_account" "nodes" {
  account_id   = "${var.name}-nodes"
  display_name = "OMS GKE nodes"
}

resource "google_project_iam_member" "nodes" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter", "roles/artifactregistry.reader"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.nodes.email}"
}

resource "google_container_cluster" "regional" {
  for_each                 = local.regions
  name                     = "${var.name}-${each.key}"
  location                 = each.value.region
  node_locations           = each.value.zones
  network                  = google_compute_network.oms.id
  subnetwork               = google_compute_subnetwork.regional[each.key].id
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = true
  networking_mode          = "VPC_NATIVE"
  enable_shielded_nodes    = true
  release_channel { channel = "REGULAR" }
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = true
    master_ipv4_cidr_block  = each.value.master
  }
  workload_identity_config { workload_pool = "${var.project_id}.svc.id.goog" }
  secret_manager_config { enabled = true }
  network_policy {
    enabled  = true
    provider = "CALICO"
  }
  addons_config {
    network_policy_config { disabled = false }
  }
  logging_config { enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"] }
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
    managed_prometheus { enabled = true }
  }
  maintenance_policy {
    recurring_window {
      start_time = "2026-01-01T01:00:00Z"
      end_time   = "2026-01-01T05:00:00Z"
      recurrence = "FREQ=DAILY"
    }
  }
}

resource "google_container_node_pool" "regional" {
  for_each           = local.regions
  name               = "application"
  location           = each.value.region
  cluster            = google_container_cluster.regional[each.key].name
  node_locations     = each.value.zones
  initial_node_count = 1
  autoscaling {
    total_min_node_count = 3
    total_max_node_count = 12
  }
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
  node_config {
    machine_type    = "e2-standard-4"
    disk_size_gb    = 100
    service_account = google_service_account.nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    tags            = ["${var.name}-gke"]
    metadata        = { disable-legacy-endpoints = "true" }
    workload_metadata_config { mode = "GKE_METADATA" }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
}

resource "google_compute_global_address" "sql_range" {
  name          = "${var.name}-sql"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  address       = "10.70.0.0"
  network       = google_compute_network.oms.id
}

resource "google_service_networking_connection" "sql" {
  network                 = google_compute_network.oms.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_range.name]
}

resource "google_sql_database_instance" "primary" {
  name                = "${var.name}-london"
  region              = "europe-west2"
  database_version    = "POSTGRES_17"
  deletion_protection = true
  depends_on          = [google_service_networking_connection.sql]
  settings {
    tier              = "db-custom-2-7680"
    availability_type = "REGIONAL"
    disk_autoresize   = true
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.oms.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
      transaction_log_retention_days = 7
    }
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
}

resource "google_sql_database_instance" "replica" {
  name                 = "${var.name}-belgium"
  region               = "europe-west1"
  database_version     = "POSTGRES_17"
  master_instance_name = google_sql_database_instance.primary.name
  deletion_protection  = true
  settings {
    tier              = "db-custom-2-7680"
    availability_type = "REGIONAL"
    disk_autoresize   = true
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.oms.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
}

resource "google_sql_database" "orders" {
  name     = "orders"
  instance = google_sql_database_instance.primary.name
}

resource "google_storage_bucket" "regional" {
  for_each                    = local.regions
  name                        = "${var.project_id}-${var.name}-${each.key}"
  location                    = each.value.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning { enabled = true }
  lifecycle_rule {
    condition { num_newer_versions = 3 }
    action { type = "Delete" }
  }
  depends_on = [google_project_service.required]
}

resource "google_service_account" "books" {
  for_each   = local.regions
  account_id = "${var.name}-${each.key}-books"
}

resource "google_storage_bucket_iam_member" "snapshots" {
  for_each = local.regions
  bucket   = google_storage_bucket.regional[each.key].name
  role     = "roles/storage.objectUser"
  member   = "serviceAccount:${google_service_account.books[each.key].email}"
}

resource "google_service_account_iam_member" "book_identity" {
  for_each           = local.regions
  service_account_id = google_service_account.books[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[oms/order-book]"
}
