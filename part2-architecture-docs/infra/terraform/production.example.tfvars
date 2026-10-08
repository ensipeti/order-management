project_id = "your-gcp-project"
domain     = "orders.example.com"

# Both regional gateway Services must exist before these backends can be attached.
gateway_negs = {
  europe-west2-a = "oms-kong-london"
  europe-west2-b = "oms-kong-london"
  europe-west2-c = "oms-kong-london"
  europe-west1-b = "oms-kong-belgium"
  europe-west1-c = "oms-kong-belgium"
  europe-west1-d = "oms-kong-belgium"
}
