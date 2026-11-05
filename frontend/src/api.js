// Every call to the backend goes through this file.

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch {
    throw new Error("Cannot reach the backend. Check that the API server is running on port 8000.");
  }
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("json") ? await response.json() : null;
  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join(" ") : detail;
    throw new Error(message || "The backend could not be reached. Check that the API server is running on port 8000.");
  }
  return body;
}

const json = (method, data) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const api = {
  listProjects: () => request("/projects"),
  createProject: (data) => request("/projects", json("POST", data)),
  createSample: () => request("/projects/sample", { method: "POST" }),
  getProject: (id) => request(`/projects/${id}`),
  updateProject: (id, data) => request(`/projects/${id}`, json("PATCH", data)),
  deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),

  listDocuments: (id) => request(`/projects/${id}/documents`),
  addText: (id, text) => request(`/projects/${id}/documents/text`, json("POST", { text })),
  uploadFile: (id, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/projects/${id}/documents/upload`, { method: "POST", body: form });
  },
  deleteDocument: (id) => request(`/documents/${id}`, { method: "DELETE" }),

  analyze: (id, steps) => request(`/projects/${id}/analyze`, json("POST", { steps: steps || null })),

  listRequirements: (id) => request(`/projects/${id}/requirements`),
  addRequirement: (id, data) => request(`/projects/${id}/requirements`, json("POST", data)),
  updateRequirement: (id, data) => request(`/requirements/${id}`, json("PATCH", data)),

  listDuplicates: (id) => request(`/projects/${id}/duplicates`),
  markDuplicate: (id, data) => request(`/projects/${id}/duplicates`, json("POST", data)),
  updateDuplicate: (id, status) => request(`/duplicates/${id}`, json("PATCH", { status })),

  listIssues: (id) => request(`/projects/${id}/issues`),
  updateIssue: (id, status) => request(`/issues/${id}`, json("PATCH", { status })),

  listStories: (id) => request(`/projects/${id}/stories`),
  updateStory: (id, data) => request(`/stories/${id}`, json("PATCH", data)),

  systemStatus: () => request("/system/status"),
  chooseModel: (model) => request("/system/model", json("PUT", { model })),
  metrics: () => request("/model/metrics"),
  predict: (text) => request("/model/predict", json("POST", { text })),
};
