import axios from "axios";

const API = axios.create({
  baseURL: "https:startup-intelligence-production.up.railway.app",
});

export default API;