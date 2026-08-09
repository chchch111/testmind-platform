import { AUTH_TOKEN_KEY, CURRENT_USER_ID_KEY, CURRENT_USER_KEY } from './constants'

export function getAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAuthToken(token) {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token || '')
}

export function getCurrentUser() {
  try {
    return JSON.parse(window.localStorage.getItem(CURRENT_USER_KEY) || 'null')
  } catch {
    return null
  }
}

export function setCurrentUser(user) {
  if (!user) {
    window.localStorage.removeItem(CURRENT_USER_KEY)
    window.localStorage.removeItem(CURRENT_USER_ID_KEY)
    return
  }
  window.localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
  window.localStorage.setItem(CURRENT_USER_ID_KEY, String(user.user_id || 1))
}

export function getCurrentUserId() {
  const user = getCurrentUser()
  if (user?.user_id) {
    return Number(user.user_id)
  }
  const value = window.localStorage.getItem(CURRENT_USER_ID_KEY)
  return Number(value || 1)
}

export function setCurrentUserId(userId) {
  window.localStorage.setItem(CURRENT_USER_ID_KEY, String(userId || 1))
}

export function isLoggedIn() {
  return Boolean(getAuthToken() && getCurrentUser())
}

export function saveLoginState(token, user) {
  setAuthToken(token)
  setCurrentUser(user)
}

export function clearAuth() {
  window.localStorage.removeItem(AUTH_TOKEN_KEY)
  window.localStorage.removeItem(CURRENT_USER_KEY)
  window.localStorage.removeItem(CURRENT_USER_ID_KEY)
}
