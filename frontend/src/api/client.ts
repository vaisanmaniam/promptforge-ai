import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL,
  timeout: 5000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Provide standardized error structure
    const customError = {
      message: error.response?.data?.message || error.message || "Network request failed",
      status: error.response?.status || 0,
      details: error.response?.data || null,
    };
    return Promise.reject(customError);
  }
);
