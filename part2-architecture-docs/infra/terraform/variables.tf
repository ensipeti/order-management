variable "project_id" {
  description = "GCP project with billing enabled. No resources are deployed by validation."
  type        = string
}

variable "name" {
  description = "Resource prefix."
  type        = string
  default     = "oms"
}

variable "domain" {
  description = "Public DNS name for the HTTPS certificate."
  type        = string
}

variable "gateway_negs" {
  description = "Standalone Kong NEG names keyed by zone; supplied after the gateway Services exist."
  type        = map(string)
  default     = {}
}
