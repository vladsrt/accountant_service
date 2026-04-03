"use client"

import { useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  apiPostForm,
  apiPost,
  setTokens,
  clearTokens,
  getAccessToken,
} from "@/lib/api"

export function useAuth() {
  const router = useRouter()

  const token = typeof window !== "undefined" ? getAccessToken() : null
  const isAuthenticated = !!token

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await apiPostForm<{
        access_token: string
        refresh_token: string
      }>("/api/v1/auth/login", { username: email, password })

      setTokens(data.access_token, data.refresh_token)
      router.push("/dashboard")
    },
    [router],
  )

  const register = useCallback(async (email: string, password: string) => {
    await apiPost("/api/v1/auth/register", { email, password })
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    router.push("/auth")
  }, [router])

  return { token, isAuthenticated, login, register, logout }
}
