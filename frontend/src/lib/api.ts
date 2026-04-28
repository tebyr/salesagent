import axios from "axios";
import Cookies from "js-cookie";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Inyectar token en cada request
api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirigir a login si 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const login = async (email: string, password: string) => {
  const form = new FormData();
  form.append("username", email);
  form.append("password", password);
  const res = await api.post("/admin/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
};

// --- Dashboard ---
export const getDashboardKPIs = () => api.get("/admin/dashboard/kpis").then((r) => r.data);
export const getVendorsPerformance = () => api.get("/admin/dashboard/salespersons-performance").then((r) => r.data);

// --- Vendors ---
export const getVendors = (params?: Record<string, string>) =>
  api.get("/admin/salespersons/", { params }).then((r) => r.data);
export const createVendor = (data: Record<string, unknown>) =>
  api.post("/admin/salespersons/", data).then((r) => r.data);
export const updateVendor = (id: string, data: Record<string, unknown>) =>
  api.patch(`/admin/salespersons/${id}`, data).then((r) => r.data);
export const deleteVendor = (id: string) => api.delete(`/admin/salespersons/${id}`);

// --- Clients ---
export const getClients = (params?: Record<string, string | number | undefined>) =>
  api.get("/admin/clients/", { params }).then((r) => r.data);
export const createClient = (data: Record<string, unknown>) =>
  api.post("/admin/clients/", data).then((r) => r.data);
export const updateClient = (id: string, data: Record<string, unknown>) =>
  api.patch(`/admin/clients/${id}`, data).then((r) => r.data);
export const deleteClient = (id: string) => api.delete(`/admin/clients/${id}`);

// --- Goals ---
export const getGoals = (params?: Record<string, string>) =>
  api.get("/admin/goals/", { params }).then((r) => r.data);
export const createGoal = (data: Record<string, unknown>) =>
  api.post("/admin/goals/", data).then((r) => r.data);
export const updateGoal = (id: string, data: Record<string, unknown>) =>
  api.patch(`/admin/goals/${id}`, data).then((r) => r.data);
export const bulkCreateGoals = (data: Record<string, unknown>) =>
  api.post("/admin/goals/bulk", data).then((r) => r.data);
export const deleteGoal = (id: string) => api.delete(`/admin/goals/${id}`);
// aliases
export const createGoalsBulk = bulkCreateGoals;

// --- Productos ---
export const getProductos = (params?: Record<string, string | number | undefined>) =>
  api.get("/admin/productos/", { params }).then((r) => r.data);
export const createProducto = (data: Record<string, unknown>) =>
  api.post("/admin/productos/", data).then((r) => r.data);
export const updateProducto = (id: string, data: Record<string, unknown>) =>
  api.patch(`/admin/productos/${id}`, data).then((r) => r.data);
export const deleteProducto = (id: string) => api.delete(`/admin/productos/${id}`);

// --- Zonas ---
export const getZonas = (params?: Record<string, string | boolean | undefined>) =>
  api.get("/admin/zonas/", { params }).then((r) => r.data);
export const createZona = (data: Record<string, unknown>) =>
  api.post("/admin/zonas/", data).then((r) => r.data);
export const updateZona = (id: string, data: Record<string, unknown>) =>
  api.patch(`/admin/zonas/${id}`, data).then((r) => r.data);
export const deleteZona = (id: string) => api.delete(`/admin/zonas/${id}`);

// --- Rutas ---
export const getRutas = (params?: Record<string, string | boolean | undefined>) =>
  api.get("/admin/rutas/", { params }).then((r) => r.data);
export const createRuta = (data: Record<string, unknown>) =>
  api.post("/admin/rutas/", data).then((r) => r.data);
export const updateRuta = (id: string, data: Record<string, unknown>) =>
  api.patch(`/admin/rutas/${id}`, data).then((r) => r.data);
export const deleteRuta = (id: string) => api.delete(`/admin/rutas/${id}`);

// --- Settings ---
export const getTenantSettings = () => api.get("/admin/settings/").then((r) => r.data);
export const updateTenantSettings = (data: Record<string, unknown>) =>
  api.patch("/admin/settings/", data).then((r) => r.data);
export const updateWhatsAppConfig = (data: Record<string, string>) =>
  api.put("/admin/settings/whatsapp", data).then((r) => r.data);
export const updateScheduleConfig = (data: Record<string, unknown>) =>
  api.put("/admin/settings/schedule", data).then((r) => r.data);
export const testWhatsAppConnection = () =>
  api.post("/admin/settings/test-whatsapp").then((r) => r.data);
// aliases for backward compat
export const updateSecurityConfig = (data: { session_timeout_minutes: number; session_warning_minutes: number }) =>
  api.put("/admin/settings/security", data).then((r) => r.data);

export const getSettings = getTenantSettings;
export const updateSettings = updateTenantSettings;
export const configureWhatsApp = updateWhatsAppConfig;
export const updateSchedule = updateScheduleConfig;
export const testWhatsApp = testWhatsAppConnection;
