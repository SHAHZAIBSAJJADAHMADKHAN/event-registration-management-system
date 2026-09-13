import { useCallback } from "react";
import { useAuth } from "../context/AuthContext";

export function useApi() {
  const { session } = useAuth();
  const accessToken = session?.access_token;
  return useCallback((request) => request(accessToken), [accessToken]);
}
