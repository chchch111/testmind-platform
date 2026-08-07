import { CURRENT_USER_ID_KEY } from './constants'

export function getCurrentUserId() {
  const value = window.localStorage.getItem(CURRENT_USER_ID_KEY)
  return Number(value || 1)
}

export function setCurrentUserId(userId) {
  window.localStorage.setItem(CURRENT_USER_ID_KEY, String(userId || 1))
}
