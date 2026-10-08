output "clusters" {
  value = { for name, cluster in google_container_cluster.regional : name => {
    name = cluster.name, region = cluster.location
  } }
}

output "writer_connection_name" {
  value = google_sql_database_instance.primary.connection_name
}

output "replica_connection_name" {
  value = google_sql_database_instance.replica.connection_name
}

output "buckets" {
  value = { for name, bucket in google_storage_bucket.regional : name => bucket.name }
}

output "https_address" {
  value = google_compute_global_address.public.address
}

output "book_service_accounts" {
  value = { for name, account in google_service_account.books : name => account.email }
}

output "writer_service_accounts" {
  value = { for name, account in google_service_account.writers : name => account.email }
}

output "database_users" {
  value = { for name, user in google_sql_user.writers : name => user.name }
}

output "runtime_secret_resources" {
  value = { for name, secret in google_secret_manager_secret.runtime : name => secret.id }
}
