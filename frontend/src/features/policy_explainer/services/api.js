import { apiJson } from '../../../lib/api/client.js'

export function listPolicyDocuments() {
  return apiJson('/policy/documents')
}

export function askPolicyQuestion(question, language) {
  return apiJson('/policy/ask', {
    method: 'POST',
    body: JSON.stringify({ question, language }),
  })
}

export function uploadPolicyDocument(formData) {
  return apiJson('/policy/documents/upload', {
    method: 'POST',
    body: formData,
  })
}

export function setPolicyPublication(documentId, isPublished) {
  return apiJson(`/policy/documents/${encodeURIComponent(documentId)}/publication`, {
    method: 'PATCH',
    body: JSON.stringify({ is_published: isPublished }),
  })
}
