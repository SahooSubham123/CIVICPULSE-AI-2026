import { apiJson } from '../../../lib/api/client.js'

export function getServiceAssistance(serviceRequest, jurisdiction) {
  return apiJson('/services/automation/assist', {
    method: 'POST',
    body: JSON.stringify({ service_request: serviceRequest, jurisdiction }),
  })
}

export function getServicePlans() {
  return apiJson('/services/automation/plans?limit=50')
}

export function inspectPortal(portalId, path) {
  return apiJson(`/services/automation/portals/${encodeURIComponent(portalId)}/inspect`, {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}
