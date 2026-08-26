import type { Project } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'

export async function fetchProjects(): Promise<Project[] | null> {
  try {
    const response = await fetch(`${API_BASE}/projects`)
    if (!response.ok) {
      return null
    }
    return (await response.json()) as Project[]
  } catch {
    return null
  }
}

export async function fetchLuaFile(name: string): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(name)}/main.lua`)
    if (!response.ok) {
      return null
    }
    return await response.text()
  } catch {
    return null
  }
}
