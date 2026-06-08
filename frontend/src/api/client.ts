import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default client;
