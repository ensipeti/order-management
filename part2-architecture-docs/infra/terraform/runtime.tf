locals {
  writers = {
    london-api    = { region = "london", service_account = "order-api" }
    london-batch  = { region = "london", service_account = "batch-worker" }
    belgium-api   = { region = "belgium", service_account = "order-api" }
    belgium-batch = { region = "belgium", service_account = "batch-worker" }
  }
  writer_roles = {
    for pair in setproduct(keys(local.writers), ["roles/cloudsql.client", "roles/cloudsql.instanceUser"]) :
    "${pair[0]}-${pair[1]}" => { account = pair[0], role = pair[1] }
  }
}

resource "google_service_account" "writers" {
  for_each   = local.writers
  account_id = "${var.name}-${each.key}"
}

resource "google_project_iam_member" "writer_sql" {
  for_each = local.writer_roles
  project  = var.project_id
  role     = each.value.role
  member   = "serviceAccount:${google_service_account.writers[each.value.account].email}"
}

resource "google_service_account_iam_member" "writer_identity" {
  for_each           = local.writers
  service_account_id = google_service_account.writers[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[oms/${each.value.service_account}]"
}

resource "google_sql_user" "writers" {
  for_each = local.writers
  name     = trimsuffix(google_service_account.writers[each.key].email, ".gserviceaccount.com")
  instance = google_sql_database_instance.primary.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

resource "google_storage_bucket_iam_member" "batch_reads" {
  for_each = { for name, writer in local.writers : name => writer if writer.service_account == "batch-worker" }
  bucket   = google_storage_bucket.regional[each.value.region].name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${google_service_account.writers[each.key].email}"
  condition {
    title      = "batch-files"
    expression = "resource.name.startsWith('projects/_/buckets/${google_storage_bucket.regional[each.value.region].name}/objects/batches/')"
  }
}

resource "google_secret_manager_secret" "runtime" {
  for_each  = local.regions
  secret_id = "${var.name}-${each.key}-runtime"
  replication {
    user_managed {
      replicas { location = each.value.region }
    }
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "runtime_writers" {
  for_each  = local.writers
  secret_id = google_secret_manager_secret.runtime[each.value.region].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.writers[each.key].email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_books" {
  for_each  = local.regions
  secret_id = google_secret_manager_secret.runtime[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.books[each.key].email}"
}
