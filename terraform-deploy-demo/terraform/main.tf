terraform {
  required_providers {
    google = { source = "hashicorp/google"
    version = "7.23.0" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "demo_bucket" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = false

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}
